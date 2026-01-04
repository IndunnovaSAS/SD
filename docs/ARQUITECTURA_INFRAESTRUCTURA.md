# Arquitectura de Infraestructura - Sistema LMS S.D. S.A.S.

## Propuesta de Infraestructura Cloud AWS

**Versión:** 1.0
**Fecha:** Enero 2026
**Región Principal:** sa-east-1 (São Paulo, Brasil)

---

## 1. Resumen de Infraestructura

### 1.1 Visión General

La infraestructura propuesta está diseñada para soportar una aplicación LMS crítica con los siguientes requisitos:

| Requisito | Especificación |
|-----------|----------------|
| **Disponibilidad** | 99.5% uptime |
| **Usuarios Concurrentes** | 200 inicial, escalable a 1,000 |
| **Almacenamiento** | 500GB inicial para multimedia |
| **Región** | LATAM (cumplimiento de datos Colombia) |
| **RTO** | < 4 horas |
| **RPO** | < 1 hora |

### 1.2 ¿Por qué AWS?

| Factor | Justificación |
|--------|---------------|
| **Proximidad** | Región São Paulo con baja latencia a Colombia (~30-50ms) |
| **Servicios Maduros** | EKS, RDS, S3, CloudFront ampliamente probados |
| **Cumplimiento** | Certificaciones SOC, ISO, para sector industrial |
| **Escalabilidad** | Auto-scaling nativo para picos de demanda |
| **Costo-efectividad** | Modelo pay-as-you-go, Reserved Instances para ahorro |

---

## 2. Diagrama de Arquitectura

```
                                    ┌──────────────────────────────────────────┐
                                    │              INTERNET                     │
                                    └─────────────────────┬────────────────────┘
                                                          │
                                    ┌─────────────────────▼────────────────────┐
                                    │              Route 53                     │
                                    │         (DNS + Health Checks)             │
                                    └─────────────────────┬────────────────────┘
                                                          │
                     ┌────────────────────────────────────┼────────────────────────────────────┐
                     │                                    │                                    │
          ┌──────────▼──────────┐            ┌───────────▼───────────┐           ┌────────────▼────────────┐
          │     CloudFront      │            │      CloudFront       │           │       CloudFront        │
          │   (Web App CDN)     │            │   (Media CDN)         │           │     (API Gateway)       │
          └──────────┬──────────┘            └───────────┬───────────┘           └────────────┬────────────┘
                     │                                   │                                    │
          ┌──────────▼──────────┐            ┌───────────▼───────────┐                       │
          │     S3 Bucket       │            │      S3 Bucket        │                       │
          │   (Static Assets)   │            │   (Media Storage)     │                       │
          └─────────────────────┘            └───────────────────────┘                       │
                                                                                             │
┌────────────────────────────────────────────────────────────────────────────────────────────┼─────────────────┐
│                                              VPC (10.0.0.0/16)                             │                 │
│                                                                                            │                 │
│  ┌─────────────────────────────────────────────────────────────────────────────────────────┼───────────────┐ │
│  │                                    Public Subnets (10.0.1.0/24, 10.0.2.0/24)            │               │ │
│  │                                                                                         │               │ │
│  │  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────▼─────────────┐ │ │
│  │  │   NAT Gateway   │    │   NAT Gateway   │    │   Bastion Host  │    │      Application Load         │ │ │
│  │  │      (AZ-a)     │    │      (AZ-b)     │    │   (t3.micro)    │    │        Balancer (ALB)         │ │ │
│  │  └────────┬────────┘    └────────┬────────┘    └─────────────────┘    └─────────────────┬─────────────┘ │ │
│  │           │                      │                                                      │               │ │
│  └───────────┼──────────────────────┼──────────────────────────────────────────────────────┼───────────────┘ │
│              │                      │                                                      │                 │
│  ┌───────────┼──────────────────────┼──────────────────────────────────────────────────────┼───────────────┐ │
│  │           │         Private Subnets (10.0.10.0/24, 10.0.11.0/24)                        │               │ │
│  │           │                      │                                                      │               │ │
│  │  ┌────────▼──────────────────────▼──────────────────────────────────────────────────────▼─────────────┐ │ │
│  │  │                                                                                                     │ │ │
│  │  │                              Amazon EKS Cluster                                                     │ │ │
│  │  │                                                                                                     │ │ │
│  │  │  ┌─────────────────────────────────────────────────────────────────────────────────────────────┐   │ │ │
│  │  │  │                              Node Group (t3.large x 3-6)                                     │   │ │ │
│  │  │  │                                                                                              │   │ │ │
│  │  │  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐       │   │ │ │
│  │  │  │  │ auth-service │ │ user-service │ │course-service│ │assess-service│ │ cert-service │       │   │ │ │
│  │  │  │  │   (2 pods)   │ │   (2 pods)   │ │   (2 pods)   │ │   (2 pods)   │ │   (2 pods)   │       │   │ │ │
│  │  │  │  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘       │   │ │ │
│  │  │  │                                                                                              │   │ │ │
│  │  │  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐       │   │ │ │
│  │  │  │  │lesson-service│ │preop-service │ │notif-service │ │report-service│ │ sync-service │       │   │ │ │
│  │  │  │  │   (2 pods)   │ │   (2 pods)   │ │   (2 pods)   │ │   (2 pods)   │ │   (2 pods)   │       │   │ │ │
│  │  │  │  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘       │   │ │ │
│  │  │  │                                                                                              │   │ │ │
│  │  │  └──────────────────────────────────────────────────────────────────────────────────────────────┘   │ │ │
│  │  │                                                                                                     │ │ │
│  │  └─────────────────────────────────────────────────────────────────────────────────────────────────────┘ │ │
│  │                                                                                                          │ │
│  └──────────────────────────────────────────────────────────────────────────────────────────────────────────┘ │
│                                                                                                               │
│  ┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐  │
│  │                              Database Subnets (10.0.20.0/24, 10.0.21.0/24)                             │  │
│  │                                                                                                        │  │
│  │  ┌─────────────────────────┐    ┌─────────────────────────┐    ┌─────────────────────────┐            │  │
│  │  │     RDS PostgreSQL      │    │    ElastiCache Redis    │    │   OpenSearch (Logs)     │            │  │
│  │  │     (Multi-AZ)          │    │     (Cluster Mode)      │    │    (2 nodes)            │            │  │
│  │  │   db.r6g.large          │    │   cache.r6g.large       │    │                         │            │  │
│  │  │   100GB SSD             │    │                         │    │                         │            │  │
│  │  └─────────────────────────┘    └─────────────────────────┘    └─────────────────────────┘            │  │
│  │                                                                                                        │  │
│  └────────────────────────────────────────────────────────────────────────────────────────────────────────┘  │
│                                                                                                               │
└───────────────────────────────────────────────────────────────────────────────────────────────────────────────┘

                    ┌─────────────────────────────────────────────────────────────────────┐
                    │                         Servicios Externos                           │
                    │                                                                      │
                    │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────┐ │
                    │  │  AWS Cognito │  │   AWS SES    │  │   AWS SNS    │  │   ECR    │ │
                    │  │   (Auth)     │  │   (Email)    │  │  (Push/SMS)  │  │ (Images) │ │
                    │  └──────────────┘  └──────────────┘  └──────────────┘  └──────────┘ │
                    │                                                                      │
                    │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  ┌──────────┐ │
                    │  │ AWS Secrets  │  │  CloudWatch  │  │   AWS WAF    │  │  Lambda  │ │
                    │  │   Manager    │  │ (Monitoring) │  │  (Firewall)  │  │(Workers) │ │
                    │  └──────────────┘  └──────────────┘  └──────────────┘  └──────────┘ │
                    │                                                                      │
                    └─────────────────────────────────────────────────────────────────────┘
```

---

## 3. Componentes de Infraestructura

### 3.1 Networking (VPC)

```hcl
# Configuración VPC
module "vpc" {
  source  = "terraform-aws-modules/vpc/aws"
  version = "5.0.0"

  name = "sd-lms-vpc"
  cidr = "10.0.0.0/16"

  azs              = ["sa-east-1a", "sa-east-1b"]
  public_subnets   = ["10.0.1.0/24", "10.0.2.0/24"]
  private_subnets  = ["10.0.10.0/24", "10.0.11.0/24"]
  database_subnets = ["10.0.20.0/24", "10.0.21.0/24"]

  enable_nat_gateway     = true
  single_nat_gateway     = false  # High availability
  enable_dns_hostnames   = true
  enable_dns_support     = true

  tags = {
    Environment = "production"
    Project     = "sd-lms"
  }
}
```

| Componente | Especificación | Propósito |
|------------|----------------|-----------|
| **VPC** | 10.0.0.0/16 | Red aislada |
| **Public Subnets** | 2 (Multi-AZ) | ALB, NAT Gateway, Bastion |
| **Private Subnets** | 2 (Multi-AZ) | EKS Worker Nodes |
| **Database Subnets** | 2 (Multi-AZ) | RDS, ElastiCache |
| **NAT Gateways** | 2 | Salida a internet desde private |

### 3.2 Compute (Amazon EKS)

```yaml
# EKS Cluster Configuration
apiVersion: eksctl.io/v1alpha5
kind: ClusterConfig

metadata:
  name: sd-lms-cluster
  region: sa-east-1
  version: "1.28"

managedNodeGroups:
  - name: general-workers
    instanceType: t3.large
    desiredCapacity: 3
    minSize: 2
    maxSize: 6
    volumeSize: 100
    volumeType: gp3
    labels:
      role: worker
    tags:
      k8s.io/cluster-autoscaler/enabled: "true"
    iam:
      withAddonPolicies:
        autoScaler: true
        cloudWatch: true
        ebs: true

  - name: media-processing
    instanceType: c5.xlarge
    desiredCapacity: 1
    minSize: 0
    maxSize: 3
    labels:
      role: media-processor
    taints:
      - key: dedicated
        value: media
        effect: NoSchedule
```

| Configuración | Especificación |
|---------------|----------------|
| **Versión K8s** | 1.28 |
| **Node Group Principal** | t3.large (2 vCPU, 8GB RAM) |
| **Nodos Iniciales** | 3 |
| **Auto-scaling** | 2-6 nodos |
| **Media Processing** | c5.xlarge (spot instances) |

### 3.3 Base de Datos (Amazon RDS)

```hcl
# RDS PostgreSQL Configuration
module "rds" {
  source  = "terraform-aws-modules/rds/aws"
  version = "6.0.0"

  identifier = "sd-lms-db"

  engine               = "postgres"
  engine_version       = "15.4"
  family               = "postgres15"
  major_engine_version = "15"
  instance_class       = "db.r6g.large"

  allocated_storage     = 100
  max_allocated_storage = 500
  storage_type          = "gp3"
  storage_encrypted     = true

  db_name  = "sdlms"
  username = "sdlms_admin"
  port     = 5432

  multi_az               = true
  db_subnet_group_name   = module.vpc.database_subnet_group
  vpc_security_group_ids = [module.security_group_rds.security_group_id]

  backup_retention_period = 30
  backup_window          = "03:00-04:00"
  maintenance_window     = "Mon:04:00-Mon:05:00"

  performance_insights_enabled = true

  parameters = [
    {
      name  = "max_connections"
      value = "200"
    }
  ]
}
```

| Configuración | Especificación |
|---------------|----------------|
| **Motor** | PostgreSQL 15 |
| **Instancia** | db.r6g.large (2 vCPU, 16GB RAM) |
| **Almacenamiento** | 100GB gp3 (auto-scale hasta 500GB) |
| **Multi-AZ** | Sí (alta disponibilidad) |
| **Backups** | 30 días retención |
| **Cifrado** | AES-256 |

### 3.4 Caché (Amazon ElastiCache)

```hcl
# ElastiCache Redis Configuration
module "elasticache" {
  source = "terraform-aws-modules/elasticache/aws"

  cluster_id           = "sd-lms-cache"
  engine               = "redis"
  engine_version       = "7.0"
  node_type            = "cache.r6g.large"
  num_cache_nodes      = 2
  parameter_group_name = "default.redis7"
  port                 = 6379

  subnet_group_name = module.vpc.elasticache_subnet_group
  security_group_ids = [module.security_group_redis.security_group_id]

  snapshot_retention_limit = 7
  snapshot_window         = "05:00-06:00"

  at_rest_encryption_enabled = true
  transit_encryption_enabled = true
}
```

| Configuración | Especificación |
|---------------|----------------|
| **Motor** | Redis 7.0 |
| **Nodos** | 2 (replica para HA) |
| **Instancia** | cache.r6g.large |
| **Cifrado** | En tránsito y reposo |

### 3.5 Almacenamiento (Amazon S3)

```hcl
# S3 Buckets Configuration
module "s3_media" {
  source = "terraform-aws-modules/s3-bucket/aws"

  bucket = "sd-lms-media-${var.environment}"
  acl    = "private"

  versioning = {
    enabled = true
  }

  lifecycle_rule = [
    {
      id      = "media-lifecycle"
      enabled = true

      transition = [
        {
          days          = 90
          storage_class = "STANDARD_IA"
        },
        {
          days          = 365
          storage_class = "GLACIER"
        }
      ]
    }
  ]

  server_side_encryption_configuration = {
    rule = {
      apply_server_side_encryption_by_default = {
        sse_algorithm = "AES256"
      }
    }
  }

  cors_rule = [
    {
      allowed_headers = ["*"]
      allowed_methods = ["GET", "PUT", "POST"]
      allowed_origins = ["https://*.sd-lms.com"]
      max_age_seconds = 3600
    }
  ]
}

module "s3_offline" {
  source = "terraform-aws-modules/s3-bucket/aws"

  bucket = "sd-lms-offline-${var.environment}"
  # Contenido comprimido para descarga offline
}

module "s3_backups" {
  source = "terraform-aws-modules/s3-bucket/aws"

  bucket = "sd-lms-backups-${var.environment}"
  # Backups de base de datos y configuraciones
}
```

| Bucket | Uso | Lifecycle |
|--------|-----|-----------|
| **sd-lms-media** | Videos, PDFs, imágenes | IA a 90 días, Glacier a 1 año |
| **sd-lms-offline** | Contenido comprimido para offline | IA a 30 días |
| **sd-lms-static** | Assets web (JS, CSS) | CDN cache |
| **sd-lms-backups** | Backups de DB | Glacier a 30 días |

### 3.6 CDN (Amazon CloudFront)

```hcl
# CloudFront Distribution
module "cloudfront_media" {
  source = "terraform-aws-modules/cloudfront/aws"

  aliases = ["media.sd-lms.com"]

  origin = {
    s3_media = {
      domain_name = module.s3_media.s3_bucket_bucket_regional_domain_name
      s3_origin_config = {
        origin_access_identity = aws_cloudfront_origin_access_identity.media.cloudfront_access_identity_path
      }
    }
  }

  default_cache_behavior = {
    target_origin_id       = "s3_media"
    viewer_protocol_policy = "redirect-to-https"
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    cached_methods         = ["GET", "HEAD"]
    compress               = true

    cache_policy_id          = "658327ea-f89d-4fab-a63d-7e88639e58f6" # CachingOptimized
    origin_request_policy_id = "88a5eaf4-2fd4-4709-b370-b4c650ea3fcf" # CORS-S3Origin
  }

  # Optimización para videos
  ordered_cache_behavior = [
    {
      path_pattern           = "*.mp4"
      target_origin_id       = "s3_media"
      viewer_protocol_policy = "redirect-to-https"

      min_ttl     = 86400    # 1 día
      default_ttl = 604800   # 7 días
      max_ttl     = 2592000  # 30 días
    }
  ]

  geo_restriction = {
    restriction_type = "whitelist"
    locations        = ["CO", "EC", "PE", "BR"] # Países de operación
  }

  viewer_certificate = {
    acm_certificate_arn = aws_acm_certificate.media.arn
    ssl_support_method  = "sni-only"
  }
}
```

| Configuración | Especificación |
|---------------|----------------|
| **Edge Locations** | Optimizado para LATAM |
| **TTL Videos** | 7 días default |
| **Compresión** | Gzip/Brotli habilitado |
| **Geo-restriction** | Solo países de operación |
| **HTTPS** | Certificado ACM |

---

## 4. Seguridad

### 4.1 AWS WAF (Web Application Firewall)

```hcl
# WAF Configuration
resource "aws_wafv2_web_acl" "main" {
  name  = "sd-lms-waf"
  scope = "CLOUDFRONT"

  default_action {
    allow {}
  }

  # Regla: Protección SQL Injection
  rule {
    name     = "AWSManagedRulesSQLiRuleSet"
    priority = 1

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesSQLiRuleSet"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "SQLiRuleSet"
      sampled_requests_enabled   = true
    }
  }

  # Regla: Rate Limiting
  rule {
    name     = "RateLimitRule"
    priority = 2

    action {
      block {}
    }

    statement {
      rate_based_statement {
        limit              = 2000
        aggregate_key_type = "IP"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "RateLimitRule"
      sampled_requests_enabled   = true
    }
  }

  # Regla: Known Bad Inputs
  rule {
    name     = "AWSManagedRulesKnownBadInputsRuleSet"
    priority = 3

    override_action {
      none {}
    }

    statement {
      managed_rule_group_statement {
        name        = "AWSManagedRulesKnownBadInputsRuleSet"
        vendor_name = "AWS"
      }
    }

    visibility_config {
      cloudwatch_metrics_enabled = true
      metric_name                = "KnownBadInputs"
      sampled_requests_enabled   = true
    }
  }
}
```

### 4.2 Security Groups

```hcl
# Security Groups
module "security_group_alb" {
  source = "terraform-aws-modules/security-group/aws"

  name        = "sd-lms-alb-sg"
  description = "Security group for ALB"
  vpc_id      = module.vpc.vpc_id

  ingress_with_cidr_blocks = [
    {
      from_port   = 443
      to_port     = 443
      protocol    = "tcp"
      cidr_blocks = "0.0.0.0/0"
    },
    {
      from_port   = 80
      to_port     = 80
      protocol    = "tcp"
      cidr_blocks = "0.0.0.0/0"
    }
  ]

  egress_with_cidr_blocks = [
    {
      from_port   = 0
      to_port     = 0
      protocol    = "-1"
      cidr_blocks = "0.0.0.0/0"
    }
  ]
}

module "security_group_eks" {
  source = "terraform-aws-modules/security-group/aws"

  name        = "sd-lms-eks-sg"
  description = "Security group for EKS nodes"
  vpc_id      = module.vpc.vpc_id

  ingress_with_source_security_group_id = [
    {
      from_port                = 0
      to_port                  = 65535
      protocol                 = "tcp"
      source_security_group_id = module.security_group_alb.security_group_id
    }
  ]
}

module "security_group_rds" {
  source = "terraform-aws-modules/security-group/aws"

  name        = "sd-lms-rds-sg"
  description = "Security group for RDS"
  vpc_id      = module.vpc.vpc_id

  ingress_with_source_security_group_id = [
    {
      from_port                = 5432
      to_port                  = 5432
      protocol                 = "tcp"
      source_security_group_id = module.security_group_eks.security_group_id
    }
  ]
}
```

### 4.3 Cifrado y Secrets

| Servicio | Cifrado |
|----------|---------|
| **RDS** | AES-256 (KMS) en reposo |
| **S3** | SSE-S3 |
| **ElastiCache** | TLS 1.3 en tránsito, AES-256 en reposo |
| **EBS** | AES-256 (KMS) |
| **Secrets** | AWS Secrets Manager |
| **Comunicación** | TLS 1.3 |

```hcl
# Secrets Manager
resource "aws_secretsmanager_secret" "db_credentials" {
  name = "sd-lms/db-credentials"

  tags = {
    Environment = var.environment
  }
}

resource "aws_secretsmanager_secret" "api_keys" {
  name = "sd-lms/api-keys"
}
```

### 4.4 IAM Roles y Políticas

```hcl
# EKS Service Account con IRSA
module "iam_eks_role" {
  source = "terraform-aws-modules/iam/aws//modules/iam-role-for-service-accounts-eks"

  role_name = "sd-lms-app-role"

  oidc_providers = {
    main = {
      provider_arn               = module.eks.oidc_provider_arn
      namespace_service_accounts = ["default:sd-lms-app"]
    }
  }

  role_policy_arns = {
    s3      = aws_iam_policy.s3_access.arn
    ses     = aws_iam_policy.ses_access.arn
    sns     = aws_iam_policy.sns_access.arn
    secrets = aws_iam_policy.secrets_access.arn
  }
}
```

---

## 5. Monitoreo y Observabilidad

### 5.1 Stack de Observabilidad

```
┌─────────────────────────────────────────────────────────────────┐
│                        OBSERVABILIDAD                            │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────┐   │
│  │  CloudWatch  │    │  CloudWatch  │    │    CloudWatch    │   │
│  │    Logs      │    │   Metrics    │    │     Alarms       │   │
│  └──────┬───────┘    └──────┬───────┘    └────────┬─────────┘   │
│         │                   │                     │              │
│         └───────────────────┼─────────────────────┘              │
│                             │                                    │
│                    ┌────────▼────────┐                          │
│                    │   CloudWatch    │                          │
│                    │   Dashboards    │                          │
│                    └────────┬────────┘                          │
│                             │                                    │
│         ┌───────────────────┼───────────────────┐               │
│         │                   │                   │               │
│  ┌──────▼──────┐    ┌──────▼──────┐    ┌──────▼──────┐        │
│  │    SNS      │    │   Lambda    │    │  OpenSearch │        │
│  │   Alerts    │    │  (Actions)  │    │   (Logs)    │        │
│  └─────────────┘    └─────────────┘    └─────────────┘        │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 5.2 Métricas Clave (CloudWatch)

```hcl
# CloudWatch Alarms
resource "aws_cloudwatch_metric_alarm" "cpu_high" {
  alarm_name          = "sd-lms-cpu-high"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "CPUUtilization"
  namespace           = "AWS/EKS"
  period              = "300"
  statistic           = "Average"
  threshold           = "80"
  alarm_description   = "CPU utilization is too high"
  alarm_actions       = [aws_sns_topic.alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "db_connections" {
  alarm_name          = "sd-lms-db-connections"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "2"
  metric_name         = "DatabaseConnections"
  namespace           = "AWS/RDS"
  period              = "300"
  statistic           = "Average"
  threshold           = "150"
  alarm_description   = "Database connections approaching limit"
  alarm_actions       = [aws_sns_topic.alerts.arn]
}

resource "aws_cloudwatch_metric_alarm" "api_errors" {
  alarm_name          = "sd-lms-api-5xx"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = "1"
  metric_name         = "HTTPCode_Target_5XX_Count"
  namespace           = "AWS/ApplicationELB"
  period              = "60"
  statistic           = "Sum"
  threshold           = "10"
  alarm_description   = "High 5XX error rate"
  alarm_actions       = [aws_sns_topic.alerts.arn]
}
```

### 5.3 Dashboards

| Dashboard | Métricas |
|-----------|----------|
| **Application Health** | Request rate, latency, error rate, active users |
| **Infrastructure** | CPU, memory, disk, network |
| **Database** | Connections, IOPS, latency, replication lag |
| **Business** | Cursos completados, evaluaciones, certificados emitidos |

---

## 6. CI/CD Pipeline

### 6.1 GitHub Actions Workflow

```yaml
# .github/workflows/deploy.yml
name: Deploy to AWS

on:
  push:
    branches: [main, staging]
  pull_request:
    branches: [main]

env:
  AWS_REGION: sa-east-1
  ECR_REPOSITORY: sd-lms
  EKS_CLUSTER: sd-lms-cluster

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '20'
          cache: 'npm'

      - name: Install dependencies
        run: npm ci

      - name: Run linter
        run: npm run lint

      - name: Run tests
        run: npm run test:coverage

      - name: Upload coverage
        uses: codecov/codecov-action@v3

  build:
    needs: test
    runs-on: ubuntu-latest
    if: github.event_name == 'push'

    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}

      - name: Login to Amazon ECR
        id: login-ecr
        uses: aws-actions/amazon-ecr-login@v2

      - name: Build and push API image
        env:
          ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
          IMAGE_TAG: ${{ github.sha }}
        run: |
          docker build -t $ECR_REGISTRY/$ECR_REPOSITORY-api:$IMAGE_TAG ./apps/api
          docker push $ECR_REGISTRY/$ECR_REPOSITORY-api:$IMAGE_TAG

      - name: Build and push Web image
        env:
          ECR_REGISTRY: ${{ steps.login-ecr.outputs.registry }}
          IMAGE_TAG: ${{ github.sha }}
        run: |
          docker build -t $ECR_REGISTRY/$ECR_REPOSITORY-web:$IMAGE_TAG ./apps/web
          docker push $ECR_REGISTRY/$ECR_REPOSITORY-web:$IMAGE_TAG

  deploy-staging:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/staging'
    environment: staging

    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}

      - name: Update kubeconfig
        run: aws eks update-kubeconfig --name ${{ env.EKS_CLUSTER }}-staging

      - name: Deploy to Kubernetes
        run: |
          helm upgrade --install sd-lms ./infrastructure/kubernetes/helm \
            --namespace staging \
            --set image.tag=${{ github.sha }} \
            --set environment=staging

  deploy-production:
    needs: build
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    environment: production

    steps:
      - uses: actions/checkout@v4

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v4
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: ${{ env.AWS_REGION }}

      - name: Update kubeconfig
        run: aws eks update-kubeconfig --name ${{ env.EKS_CLUSTER }}

      - name: Deploy to Kubernetes
        run: |
          helm upgrade --install sd-lms ./infrastructure/kubernetes/helm \
            --namespace production \
            --set image.tag=${{ github.sha }} \
            --set environment=production
```

### 6.2 Pipeline Flow

```
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌──────────┐    ┌────────────┐
│  Push   │───▶│  Test   │───▶│  Build  │───▶│ Staging  │───▶│ Production │
│  Code   │    │  Lint   │    │  Docker │    │  Deploy  │    │   Deploy   │
└─────────┘    └─────────┘    └─────────┘    └──────────┘    └────────────┘
                   │                              │                │
                   ▼                              ▼                ▼
              Coverage                       Auto Tests      Manual Approval
              Report                         (E2E)           Required
```

---

## 7. Disaster Recovery

### 7.1 Estrategia de Backup

| Componente | Estrategia | RPO | Retención |
|------------|------------|-----|-----------|
| **RDS** | Snapshots automáticos diarios | 1 hora | 30 días |
| **RDS** | Point-in-Time Recovery | 5 minutos | 7 días |
| **S3** | Versionamiento + Cross-Region Replication | Inmediato | Indefinido |
| **EBS** | Snapshots diarios | 24 horas | 14 días |
| **Secrets** | Replicación automática | Inmediato | - |

### 7.2 Plan de Recuperación

```
┌─────────────────────────────────────────────────────────────────┐
│                    DISASTER RECOVERY PLAN                        │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Nivel 1: Falla de Instancia (RTO: 5 min)                       │
│  ├── Auto-healing de Kubernetes                                  │
│  ├── Multi-AZ failover para RDS                                 │
│  └── ElastiCache replica promotion                               │
│                                                                  │
│  Nivel 2: Falla de AZ (RTO: 15 min)                             │
│  ├── Traffic shift via ALB                                       │
│  ├── EKS redistribución de pods                                  │
│  └── RDS failover automático                                     │
│                                                                  │
│  Nivel 3: Falla de Región (RTO: 4 horas)                        │
│  ├── Activar stack en región secundaria                          │
│  ├── Restore RDS desde S3 cross-region                          │
│  ├── DNS failover (Route 53)                                     │
│  └── Notificación a usuarios                                     │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 7.3 Runbook de Recuperación

```bash
# Runbook: Recuperación de Base de Datos
# Tiempo estimado: 30-60 minutos

# 1. Identificar último snapshot válido
aws rds describe-db-snapshots \
  --db-instance-identifier sd-lms-db \
  --query 'DBSnapshots[*].[DBSnapshotIdentifier,SnapshotCreateTime]'

# 2. Restaurar desde snapshot
aws rds restore-db-instance-from-db-snapshot \
  --db-instance-identifier sd-lms-db-restored \
  --db-snapshot-identifier <snapshot-id> \
  --db-instance-class db.r6g.large \
  --vpc-security-group-ids <sg-id>

# 3. Verificar estado
aws rds describe-db-instances \
  --db-instance-identifier sd-lms-db-restored \
  --query 'DBInstances[0].DBInstanceStatus'

# 4. Actualizar endpoint en secrets
aws secretsmanager update-secret \
  --secret-id sd-lms/db-credentials \
  --secret-string '{"host":"new-endpoint"}'

# 5. Reiniciar pods para reconectar
kubectl rollout restart deployment -n production
```

---

## 8. Estimación de Costos

### 8.1 Costos Mensuales Estimados (USD)

| Servicio | Configuración | Costo Estimado/Mes |
|----------|---------------|-------------------|
| **EKS Control Plane** | 1 cluster | $73 |
| **EC2 (EKS Nodes)** | 3x t3.large | $180 |
| **RDS PostgreSQL** | db.r6g.large Multi-AZ | $290 |
| **ElastiCache Redis** | 2x cache.r6g.large | $240 |
| **S3** | 500GB + requests | $30 |
| **CloudFront** | 1TB transfer | $85 |
| **NAT Gateway** | 2 gateways + data | $90 |
| **ALB** | 1 load balancer | $25 |
| **Route 53** | Hosted zone + queries | $5 |
| **Secrets Manager** | 10 secrets | $5 |
| **CloudWatch** | Logs + metrics | $50 |
| **WAF** | Web ACL + rules | $30 |
| **SES** | 10K emails | $1 |
| **SNS** | Push + SMS | $20 |
| **ECR** | Container images | $10 |
| **Cognito** | 200 MAU | $0 (free tier) |

### 8.2 Resumen de Costos

| Concepto | Costo Mensual | Costo Anual |
|----------|---------------|-------------|
| **Infraestructura Base** | ~$1,134 | ~$13,608 |
| **Reservas (1 año, -30%)** | ~$794 | ~$9,528 |
| **Soporte Business** | ~$100 | ~$1,200 |
| **Total Estimado** | ~$894 | ~$10,728 |

### 8.3 Optimización de Costos

| Estrategia | Ahorro Estimado |
|------------|-----------------|
| **Reserved Instances (1 año)** | 30% en EC2/RDS |
| **Savings Plans** | 20% en compute |
| **S3 Intelligent Tiering** | 40% en almacenamiento |
| **Spot Instances (media processing)** | 70% en procesamiento |
| **Right-sizing continuo** | 15% general |

---

## 9. Ambientes

### 9.1 Configuración por Ambiente

| Ambiente | Propósito | Configuración |
|----------|-----------|---------------|
| **Development** | Desarrollo local | Docker Compose |
| **Staging** | QA y pruebas | EKS (1 nodo), RDS (db.t3.medium) |
| **Production** | Producción | EKS (3+ nodos), RDS Multi-AZ |

### 9.2 Terraform Workspaces

```hcl
# terraform/environments/production/main.tf
terraform {
  backend "s3" {
    bucket         = "sd-lms-terraform-state"
    key            = "production/terraform.tfstate"
    region         = "sa-east-1"
    encrypt        = true
    dynamodb_table = "terraform-locks"
  }
}

module "infrastructure" {
  source = "../../modules"

  environment = "production"

  eks_node_count     = 3
  eks_instance_type  = "t3.large"
  rds_instance_class = "db.r6g.large"
  rds_multi_az       = true
  redis_node_count   = 2
}
```

---

## 10. Checklist de Implementación

### Fase 0: Setup Inicial

- [ ] Crear cuenta AWS y configurar Organizations
- [ ] Configurar IAM users y roles
- [ ] Crear repositorio Terraform
- [ ] Configurar backend remoto (S3 + DynamoDB)
- [ ] Crear VPC y networking base
- [ ] Configurar Route 53 hosted zone
- [ ] Solicitar certificados ACM
- [ ] Crear repositorios ECR
- [ ] Configurar GitHub Actions secrets

### Fase 1: Compute y Storage

- [ ] Desplegar EKS cluster
- [ ] Configurar node groups
- [ ] Instalar ingress controller (NGINX)
- [ ] Configurar cert-manager
- [ ] Crear buckets S3
- [ ] Configurar CloudFront distributions

### Fase 2: Datos y Caché

- [ ] Desplegar RDS PostgreSQL
- [ ] Configurar backups automáticos
- [ ] Desplegar ElastiCache Redis
- [ ] Configurar secrets en Secrets Manager
- [ ] Ejecutar migraciones de base de datos

### Fase 3: Seguridad y Monitoreo

- [ ] Configurar Security Groups
- [ ] Desplegar WAF
- [ ] Configurar CloudWatch dashboards
- [ ] Crear alarmas críticas
- [ ] Configurar SNS topics para alertas
- [ ] Habilitar CloudTrail

### Fase 4: CI/CD y Deploy

- [ ] Configurar GitHub Actions workflows
- [ ] Crear Helm charts
- [ ] Desplegar ambiente staging
- [ ] Ejecutar pruebas de carga
- [ ] Desplegar ambiente production
- [ ] Verificar disaster recovery

---

## 11. Contactos y Escalamiento

| Nivel | Tiempo Respuesta | Contacto |
|-------|------------------|----------|
| **L1: Incidentes menores** | < 4 horas | Equipo DevOps |
| **L2: Incidentes mayores** | < 1 hora | Tech Lead + DevOps |
| **L3: Incidentes críticos** | < 15 min | Gerencia + AWS Support |

---

*Documento generado como propuesta de infraestructura para el Sistema LMS de S.D. S.A.S.*
