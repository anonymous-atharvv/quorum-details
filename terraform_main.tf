# ─────────────────────────────────────────────
# QUORUM — Core AWS Infrastructure (Terraform)
# terraform/main.tf
#
# Usage:
#   terraform init
#   terraform workspace new staging
#   terraform plan -var-file=staging.tfvars
#   terraform apply -var-file=staging.tfvars
# ─────────────────────────────────────────────

terraform {
  required_version = ">= 1.9.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.50"
    }
  }
  backend "s3" {
    bucket         = "quorum-terraform-state"
    key            = "infra/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "quorum-terraform-locks"
  }
}

provider "aws" {
  region = var.aws_region
  default_tags {
    tags = {
      Project     = "quorum"
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

# ── Variables ──────────────────────────────────────────────────────
variable "environment"     { type = string }
variable "aws_region"      { type = string  default = "us-east-1" }
variable "vpc_cidr"        { type = string  default = "10.0.0.0/16" }
variable "db_instance"     { type = string  default = "db.r7g.large" }
variable "db_password"     { type = string  sensitive = true }
variable "api_image_tag"   { type = string  default = "latest" }
variable "worker_image_tag"{ type = string  default = "latest" }
variable "api_desired_count"    { type = number default = 2 }
variable "worker_desired_count" { type = number default = 2 }

locals {
  name_prefix = "quorum-${var.environment}"
  is_prod     = var.environment == "production"
  azs         = ["${var.aws_region}a", "${var.aws_region}b"]
}

# ── VPC ────────────────────────────────────────────────────────────
resource "aws_vpc" "main" {
  cidr_block           = var.vpc_cidr
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = { Name = "${local.name_prefix}-vpc" }
}

resource "aws_internet_gateway" "main" {
  vpc_id = aws_vpc.main.id
  tags   = { Name = "${local.name_prefix}-igw" }
}

# Public subnets (ALB)
resource "aws_subnet" "public" {
  count                   = 2
  vpc_id                  = aws_vpc.main.id
  cidr_block              = cidrsubnet(var.vpc_cidr, 8, count.index)
  availability_zone       = local.azs[count.index]
  map_public_ip_on_launch = true
  tags = { Name = "${local.name_prefix}-public-${count.index + 1}" }
}

# Private subnets (ECS, RDS, ElastiCache)
resource "aws_subnet" "private" {
  count             = 2
  vpc_id            = aws_vpc.main.id
  cidr_block        = cidrsubnet(var.vpc_cidr, 8, count.index + 10)
  availability_zone = local.azs[count.index]
  tags = { Name = "${local.name_prefix}-private-${count.index + 1}" }
}

resource "aws_nat_gateway" "main" {
  count         = local.is_prod ? 2 : 1
  allocation_id = aws_eip.nat[count.index].id
  subnet_id     = aws_subnet.public[count.index].id
  tags          = { Name = "${local.name_prefix}-nat-${count.index + 1}" }
}

resource "aws_eip" "nat" {
  count  = local.is_prod ? 2 : 1
  domain = "vpc"
}

resource "aws_route_table" "private" {
  count  = local.is_prod ? 2 : 1
  vpc_id = aws_vpc.main.id
  route {
    cidr_block     = "0.0.0.0/0"
    nat_gateway_id = aws_nat_gateway.main[count.index].id
  }
  tags = { Name = "${local.name_prefix}-private-rt-${count.index + 1}" }
}

resource "aws_route_table_association" "private" {
  count          = 2
  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private[local.is_prod ? count.index : 0].id
}

# ── Security Groups ────────────────────────────────────────────────
resource "aws_security_group" "alb" {
  name   = "${local.name_prefix}-alb-sg"
  vpc_id = aws_vpc.main.id
  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTPS from internet"
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = { Name = "${local.name_prefix}-alb-sg" }
}

resource "aws_security_group" "api" {
  name   = "${local.name_prefix}-api-sg"
  vpc_id = aws_vpc.main.id
  ingress {
    from_port       = 8000
    to_port         = 8000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
    description     = "From ALB only"
  }
  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
  tags = { Name = "${local.name_prefix}-api-sg" }
}

resource "aws_security_group" "db" {
  name   = "${local.name_prefix}-db-sg"
  vpc_id = aws_vpc.main.id
  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.api.id]
    description     = "PostgreSQL from API/workers only"
  }
  tags = { Name = "${local.name_prefix}-db-sg" }
}

resource "aws_security_group" "redis" {
  name   = "${local.name_prefix}-redis-sg"
  vpc_id = aws_vpc.main.id
  ingress {
    from_port       = 6379
    to_port         = 6379
    protocol        = "tcp"
    security_groups = [aws_security_group.api.id]
    description     = "Redis from API/workers only"
  }
  tags = { Name = "${local.name_prefix}-redis-sg" }
}

# ── RDS PostgreSQL ────────────────────────────────────────────────
resource "aws_db_subnet_group" "main" {
  name       = "${local.name_prefix}-db-subnet"
  subnet_ids = aws_subnet.private[*].id
}

resource "aws_db_instance" "postgres" {
  identifier        = "${local.name_prefix}-postgres"
  engine            = "postgres"
  engine_version    = "16.3"
  instance_class    = var.db_instance
  allocated_storage = local.is_prod ? 100 : 20
  storage_type      = "gp3"
  storage_encrypted = true

  db_name  = "quorum"
  username = "quorum"
  password = var.db_password

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.db.id]
  publicly_accessible    = false
  multi_az               = local.is_prod

  backup_retention_period    = local.is_prod ? 7 : 1
  backup_window              = "03:00-04:00"
  maintenance_window         = "Mon:04:00-Mon:05:00"
  auto_minor_version_upgrade = true
  deletion_protection        = local.is_prod

  performance_insights_enabled = local.is_prod

  tags = { Name = "${local.name_prefix}-postgres" }
}

# ── ElastiCache Redis ─────────────────────────────────────────────
resource "aws_elasticache_subnet_group" "main" {
  name       = "${local.name_prefix}-redis-subnet"
  subnet_ids = aws_subnet.private[*].id
}

resource "aws_elasticache_cluster" "redis" {
  cluster_id           = "${local.name_prefix}-redis"
  engine               = "redis"
  node_type            = "cache.r7g.large"
  num_cache_nodes      = 1
  engine_version       = "7.1"
  parameter_group_name = "default.redis7"
  subnet_group_name    = aws_elasticache_subnet_group.main.name
  security_group_ids   = [aws_security_group.redis.id]

  tags = { Name = "${local.name_prefix}-redis" }
}

# ── ECS Cluster ───────────────────────────────────────────────────
resource "aws_ecs_cluster" "main" {
  name = "${local.name_prefix}-cluster"
  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

resource "aws_ecs_cluster_capacity_providers" "main" {
  cluster_name       = aws_ecs_cluster.main.name
  capacity_providers = ["FARGATE", "FARGATE_SPOT"]
  default_capacity_provider_strategy {
    base              = 1
    weight            = 100
    capacity_provider = "FARGATE"
  }
}

# ── ALB ───────────────────────────────────────────────────────────
resource "aws_lb" "api" {
  name               = "${local.name_prefix}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = aws_subnet.public[*].id
  idle_timeout       = 300  # 5 min (for WebSocket connections)

  access_logs {
    bucket  = aws_s3_bucket.logs.bucket
    prefix  = "alb"
    enabled = true
  }
}

resource "aws_lb_target_group" "api" {
  name        = "${local.name_prefix}-api-tg"
  port        = 8000
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    enabled             = true
    path                = "/health"
    healthy_threshold   = 2
    unhealthy_threshold = 3
    interval            = 30
    timeout             = 10
  }
}

# ── S3 (logs + recordings) ────────────────────────────────────────
resource "aws_s3_bucket" "logs" {
  bucket = "${local.name_prefix}-logs"
}

resource "aws_s3_bucket" "recordings" {
  bucket = "${local.name_prefix}-recordings"
}

resource "aws_s3_bucket_public_access_block" "recordings" {
  bucket                  = aws_s3_bucket.recordings.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_server_side_encryption_configuration" "recordings" {
  bucket = aws_s3_bucket.recordings.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "aws:kms"
    }
  }
}

resource "aws_s3_bucket_lifecycle_configuration" "recordings" {
  bucket = aws_s3_bucket.recordings.id
  rule {
    id     = "delete-recordings-after-30-days"
    status = "Enabled"
    expiration { days = 30 }
  }
}

# ── Outputs ───────────────────────────────────────────────────────
output "api_alb_dns"         { value = aws_lb.api.dns_name }
output "db_endpoint"         { value = aws_db_instance.postgres.endpoint }
output "redis_endpoint"      { value = aws_elasticache_cluster.redis.cache_nodes[0].address }
output "ecs_cluster_name"    { value = aws_ecs_cluster.main.name }
output "vpc_id"              { value = aws_vpc.main.id }
output "private_subnet_ids"  { value = aws_subnet.private[*].id }
