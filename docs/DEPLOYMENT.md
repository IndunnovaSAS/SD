# Guia de Deployment en Google Cloud Platform

Esta guia describe el proceso completo para desplegar el Sistema LMS de S.D. S.A.S. en Google Cloud Platform.

## Tabla de Contenidos

- [Requisitos Previos](#requisitos-previos)
- [Configuracion de Google Cloud](#configuracion-de-google-cloud)
- [Cloud Run](#cloud-run)
- [Cloud SQL](#cloud-sql)
- [Cloud Storage](#cloud-storage)
- [Secret Manager](#secret-manager)
- [CI/CD con GitHub Actions](#cicd-con-github-actions)
- [Monitoreo con Cloud Logging](#monitoreo-con-cloud-logging)
- [Procedimientos de Rollback](#procedimientos-de-rollback)

---

## Requisitos Previos

### Herramientas Necesarias

1. **Google Cloud CLI (gcloud)**

```bash
# Instalacion en macOS
brew install google-cloud-sdk

# Instalacion en Linux
curl https://sdk.cloud.google.com | bash

# Verificar instalacion
gcloud version
```

2. **Docker**

```bash
# Verificar instalacion
docker --version
docker-compose --version
```

3. **Terraform** (opcional, para IaC)

```bash
# Instalacion en macOS
brew install terraform

# Verificar instalacion
terraform version
```

### Permisos Requeridos

El usuario o service account necesita los siguientes roles IAM:

| Rol | Proposito |
|-----|-----------|
| `roles/run.admin` | Administrar Cloud Run |
| `roles/cloudsql.admin` | Administrar Cloud SQL |
| `roles/storage.admin` | Administrar Cloud Storage |
| `roles/secretmanager.admin` | Administrar Secret Manager |
| `roles/iam.serviceAccountUser` | Usar service accounts |
| `roles/artifactregistry.writer` | Push imagenes Docker |
| `roles/logging.viewer` | Ver logs |
| `roles/monitoring.editor` | Configurar alertas |

### Configuracion Inicial de gcloud

```bash
# Autenticarse
gcloud auth login

# Configurar proyecto
gcloud config set project sd-lms-production

# Configurar region por defecto
gcloud config set run/region southamerica-east1

# Habilitar APIs necesarias
gcloud services enable \
  run.googleapis.com \
  sqladmin.googleapis.com \
  secretmanager.googleapis.com \
  storage.googleapis.com \
  artifactregistry.googleapis.com \
  cloudbuild.googleapis.com \
  logging.googleapis.com \
  monitoring.googleapis.com
```

---

## Configuracion de Google Cloud

### Estructura del Proyecto

```
GCP Organization
  |
  +-- Folder: SD-LMS
        |
        +-- Project: sd-lms-production (produccion)
        +-- Project: sd-lms-staging (staging)
```

### Crear Artifact Registry

```bash
# Crear repositorio para imagenes Docker
gcloud artifacts repositories create sd-lms \
  --repository-format=docker \
  --location=southamerica-east1 \
  --description="SD LMS Docker images"

# Configurar Docker para usar el registro
gcloud auth configure-docker southamerica-east1-docker.pkg.dev
```

### Crear VPC Connector

```bash
# Crear conector VPC para Cloud Run
gcloud compute networks vpc-access connectors create sd-lms-connector \
  --region=southamerica-east1 \
  --range=10.8.0.0/28
```

---

## Cloud Run

### Build de Imagen Docker

```bash
# Build local para testing
docker build -t sd-lms:local --target production .

# Build y push a Artifact Registry
docker build -t southamerica-east1-docker.pkg.dev/sd-lms-production/sd-lms/web:latest .
docker push southamerica-east1-docker.pkg.dev/sd-lms-production/sd-lms/web:latest
```

### Deploy del Servicio Web

```bash
gcloud run deploy sd-lms-web \
  --image=southamerica-east1-docker.pkg.dev/sd-lms-production/sd-lms/web:latest \
  --region=southamerica-east1 \
  --platform=managed \
  --allow-unauthenticated \
  --memory=2Gi \
  --cpu=2 \
  --min-instances=1 \
  --max-instances=10 \
  --timeout=300 \
  --concurrency=80 \
  --set-env-vars="DJANGO_SETTINGS_MODULE=config.settings.production" \
  --set-secrets="SECRET_KEY=django-secret-key:latest" \
  --set-secrets="DATABASE_URL=database-url:latest" \
  --set-secrets="REDIS_URL=redis-url:latest" \
  --vpc-connector=sd-lms-connector \
  --vpc-egress=private-ranges-only
```

### Deploy del Worker Celery

```bash
gcloud run deploy sd-lms-worker \
  --image=southamerica-east1-docker.pkg.dev/sd-lms-production/sd-lms/worker:latest \
  --region=southamerica-east1 \
  --platform=managed \
  --no-allow-unauthenticated \
  --memory=4Gi \
  --cpu=2 \
  --min-instances=1 \
  --max-instances=5 \
  --timeout=3600 \
  --set-env-vars="DJANGO_SETTINGS_MODULE=config.settings.production" \
  --set-secrets="SECRET_KEY=django-secret-key:latest" \
  --set-secrets="DATABASE_URL=database-url:latest" \
  --set-secrets="REDIS_URL=redis-url:latest" \
  --vpc-connector=sd-lms-connector \
  --command="celery" \
  --args="-A,config,worker,-l,WARNING,-Q,default,high_priority,low_priority"
```

### Cloud Run Jobs para Migraciones

```bash
# Crear job de migraciones
gcloud run jobs create sd-lms-migrate \
  --image=southamerica-east1-docker.pkg.dev/sd-lms-production/sd-lms/web:latest \
  --region=southamerica-east1 \
  --memory=1Gi \
  --task-timeout=600 \
  --set-env-vars="DJANGO_SETTINGS_MODULE=config.settings.production" \
  --set-secrets="SECRET_KEY=django-secret-key:latest" \
  --set-secrets="DATABASE_URL=database-url:latest" \
  --vpc-connector=sd-lms-connector \
  --command="python" \
  --args="manage.py,migrate,--noinput"

# Ejecutar migraciones
gcloud run jobs execute sd-lms-migrate --region=southamerica-east1 --wait
```

### Configurar Dominio Personalizado

```bash
# Mapear dominio
gcloud run domain-mappings create \
  --service=sd-lms-web \
  --domain=lms.sd.com.co \
  --region=southamerica-east1
```

---

## Cloud SQL

### Crear Instancia PostgreSQL

```bash
# Crear instancia principal
gcloud sql instances create sd-lms-db \
  --database-version=POSTGRES_16 \
  --tier=db-custom-2-8192 \
  --region=southamerica-east1 \
  --availability-type=REGIONAL \
  --storage-type=SSD \
  --storage-size=100GB \
  --storage-auto-increase \
  --backup-start-time=03:00 \
  --enable-point-in-time-recovery \
  --retained-backups-count=30 \
  --maintenance-window-day=SUN \
  --maintenance-window-hour=3 \
  --insights-config-query-insights-enabled \
  --no-assign-ip \
  --network=default

# Crear base de datos
gcloud sql databases create sdlms --instance=sd-lms-db

# Crear usuario
gcloud sql users create sdlms_user \
  --instance=sd-lms-db \
  --password='STRONG_PASSWORD_HERE'
```

### Crear Replica de Lectura

```bash
gcloud sql instances create sd-lms-db-replica \
  --master-instance-name=sd-lms-db \
  --region=southamerica-east1 \
  --tier=db-custom-2-8192 \
  --storage-type=SSD
```

### Conexion desde Cloud Run

Cloud Run se conecta automaticamente usando el Cloud SQL Auth Proxy integrado:

```bash
gcloud run services update sd-lms-web \
  --add-cloudsql-instances=sd-lms-production:southamerica-east1:sd-lms-db
```

La cadena de conexion en `DATABASE_URL` seria:

```
postgres://sdlms_user:PASSWORD@/sdlms?host=/cloudsql/sd-lms-production:southamerica-east1:sd-lms-db
```

### Backups Manuales

```bash
# Crear backup manual
gcloud sql backups create --instance=sd-lms-db --description="Pre-release backup"

# Listar backups
gcloud sql backups list --instance=sd-lms-db

# Restaurar desde backup
gcloud sql backups restore BACKUP_ID \
  --restore-instance=sd-lms-db-restored \
  --backup-instance=sd-lms-db
```

---

## Cloud Storage

### Crear Buckets

```bash
# Bucket para media (videos, documentos, etc.)
gcloud storage buckets create gs://sd-lms-media-production \
  --location=SOUTHAMERICA-EAST1 \
  --uniform-bucket-level-access \
  --versioning

# Bucket para archivos estaticos
gcloud storage buckets create gs://sd-lms-static-production \
  --location=SOUTHAMERICA-EAST1 \
  --uniform-bucket-level-access

# Bucket para backups
gcloud storage buckets create gs://sd-lms-backups-production \
  --location=SOUTHAMERICA-EAST1 \
  --storage-class=NEARLINE \
  --uniform-bucket-level-access
```

### Configurar CORS para Media

```bash
# Crear archivo cors.json
cat > cors.json << 'EOF'
[
  {
    "origin": ["https://lms.sd.com.co", "https://*.sd.com.co"],
    "method": ["GET", "PUT", "POST"],
    "responseHeader": ["Content-Type", "Content-MD5"],
    "maxAgeSeconds": 3600
  }
]
EOF

# Aplicar configuracion CORS
gcloud storage buckets update gs://sd-lms-media-production --cors-file=cors.json
```

### Configurar Lifecycle

```bash
# Crear archivo lifecycle.json
cat > lifecycle.json << 'EOF'
{
  "lifecycle": {
    "rule": [
      {
        "action": {"type": "SetStorageClass", "storageClass": "NEARLINE"},
        "condition": {"age": 90}
      },
      {
        "action": {"type": "SetStorageClass", "storageClass": "COLDLINE"},
        "condition": {"age": 365}
      }
    ]
  }
}
EOF

# Aplicar lifecycle
gcloud storage buckets update gs://sd-lms-media-production --lifecycle-file=lifecycle.json
```

### Configurar Cloud CDN

```bash
# Crear backend bucket con CDN
gcloud compute backend-buckets create sd-lms-media-cdn \
  --gcs-bucket-name=sd-lms-media-production \
  --enable-cdn \
  --cache-mode=CACHE_ALL_STATIC \
  --default-ttl=86400 \
  --max-ttl=604800
```

---

## Secret Manager

### Crear Secretos

```bash
# Django secret key
echo -n "$(python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())')" | \
  gcloud secrets create django-secret-key --data-file=-

# Database URL
echo -n "postgres://user:pass@/sdlms?host=/cloudsql/project:region:instance" | \
  gcloud secrets create database-url --data-file=-

# Redis URL
echo -n "redis://10.0.0.1:6379/0" | \
  gcloud secrets create redis-url --data-file=-

# Sentry DSN
echo -n "https://xxx@sentry.io/xxx" | \
  gcloud secrets create sentry-dsn --data-file=-

# SendGrid API Key
echo -n "SG.xxxx" | \
  gcloud secrets create sendgrid-api-key --data-file=-
```

### Dar Acceso a Cloud Run

```bash
# Obtener email del service account de Cloud Run
SA_EMAIL=$(gcloud run services describe sd-lms-web \
  --region=southamerica-east1 \
  --format='value(spec.template.spec.serviceAccountName)')

# Dar acceso a cada secreto
gcloud secrets add-iam-policy-binding django-secret-key \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding database-url \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/secretmanager.secretAccessor"

gcloud secrets add-iam-policy-binding redis-url \
  --member="serviceAccount:$SA_EMAIL" \
  --role="roles/secretmanager.secretAccessor"
```

### Rotar Secretos

```bash
# Agregar nueva version del secreto
echo -n "nuevo-valor" | gcloud secrets versions add django-secret-key --data-file=-

# Deshabilitar version anterior
gcloud secrets versions disable 1 --secret=django-secret-key

# Forzar redeploy para usar nueva version
gcloud run services update sd-lms-web \
  --region=southamerica-east1 \
  --update-env-vars=SECRET_VERSION=$(date +%s)
```

---

## CI/CD con GitHub Actions

### Configurar Secretos en GitHub

En GitHub repository > Settings > Secrets and variables > Actions:

| Secret | Descripcion |
|--------|-------------|
| `GCP_PROJECT_ID` | ID del proyecto GCP |
| `GCP_SA_KEY` | JSON de la service account |

### Crear Service Account para CI/CD

```bash
# Crear service account
gcloud iam service-accounts create github-actions \
  --display-name="GitHub Actions CI/CD"

# Asignar roles
gcloud projects add-iam-policy-binding sd-lms-production \
  --member="serviceAccount:github-actions@sd-lms-production.iam.gserviceaccount.com" \
  --role="roles/run.admin"

gcloud projects add-iam-policy-binding sd-lms-production \
  --member="serviceAccount:github-actions@sd-lms-production.iam.gserviceaccount.com" \
  --role="roles/artifactregistry.writer"

gcloud projects add-iam-policy-binding sd-lms-production \
  --member="serviceAccount:github-actions@sd-lms-production.iam.gserviceaccount.com" \
  --role="roles/iam.serviceAccountUser"

# Generar clave JSON
gcloud iam service-accounts keys create github-actions-key.json \
  --iam-account=github-actions@sd-lms-production.iam.gserviceaccount.com
```

### Workflow de CI

El archivo `.github/workflows/ci.yml` ejecuta:

1. **Lint & Type Check**: Ruff + mypy
2. **Tests**: pytest con cobertura
3. **Security Scan**: safety + bandit
4. **Build Docker**: Solo en push a main

### Workflow de Deploy

El archivo `.github/workflows/deploy.yml` ejecuta:

1. **Build & Push**: Construye imagen y la sube a Artifact Registry
2. **Deploy**: Despliega a Cloud Run (staging o production)
3. **Migrations**: Ejecuta migraciones como Cloud Run Job
4. **Notify**: Notifica resultado del deploy

### Deploy Manual

```bash
# Deploy a staging
gh workflow run deploy.yml -f environment=staging

# Deploy a production (requiere tag)
git tag v1.0.0
git push --tags
```

---

## Monitoreo con Cloud Logging

### Ver Logs de Cloud Run

```bash
# Logs en tiempo real
gcloud run services logs read sd-lms-web --region=southamerica-east1 --tail=100

# Logs con filtro
gcloud logging read 'resource.type="cloud_run_revision" AND resource.labels.service_name="sd-lms-web"' \
  --limit=50 \
  --format="table(timestamp,severity,textPayload)"
```

### Consultas de Logs Comunes

```bash
# Errores en las ultimas 24 horas
gcloud logging read 'severity>=ERROR AND timestamp>="2024-01-01T00:00:00Z"' \
  --limit=100

# Requests lentos (>2s)
gcloud logging read 'httpRequest.latency>"2s"' --limit=50

# Errores 5xx
gcloud logging read 'httpRequest.status>=500' --limit=50
```

### Configurar Alertas

```bash
# Crear canal de notificacion (Slack)
gcloud alpha monitoring channels create \
  --display-name="SD LMS Slack" \
  --type=slack \
  --channel-labels=channel_name=#sd-lms-alerts

# Crear alerta de error rate
gcloud alpha monitoring policies create \
  --display-name="High Error Rate" \
  --condition-display-name="5xx errors > 1%" \
  --condition-filter='resource.type="cloud_run_revision" AND metric.type="run.googleapis.com/request_count" AND metric.labels.response_code_class="5xx"' \
  --condition-threshold-value=0.01 \
  --condition-threshold-comparison=COMPARISON_GT \
  --notification-channels=CHANNEL_ID
```

### Dashboard Personalizado

El dashboard "SD LMS - Overview" muestra:

- Request Rate
- Error Rate (5xx)
- Latencia P95
- CPU/Memory Usage
- Conexiones a BD
- Usuarios activos

---

## Procedimientos de Rollback

### Rollback de Cloud Run

```bash
# Listar revisiones
gcloud run revisions list --service=sd-lms-web --region=southamerica-east1

# Rollback a revision especifica
gcloud run services update-traffic sd-lms-web \
  --region=southamerica-east1 \
  --to-revisions=sd-lms-web-00005-abc=100
```

### Rollback de Base de Datos

```bash
# 1. Identificar backup
gcloud sql backups list --instance=sd-lms-db

# 2. Crear nueva instancia desde backup
gcloud sql backups restore BACKUP_ID \
  --restore-instance=sd-lms-db-rollback \
  --backup-instance=sd-lms-db

# 3. Actualizar secreto con nueva instancia
echo -n "postgres://user:pass@/sdlms?host=/cloudsql/project:region:sd-lms-db-rollback" | \
  gcloud secrets versions add database-url --data-file=-

# 4. Forzar redeploy
gcloud run services update sd-lms-web \
  --region=southamerica-east1 \
  --update-env-vars=DB_INSTANCE=rollback
```

### Point-in-Time Recovery (PITR)

```bash
# Restaurar a un punto especifico en el tiempo
gcloud sql instances clone sd-lms-db sd-lms-db-pitr \
  --point-in-time="2024-01-15T10:30:00Z"
```

### Rollback de Migraciones Django

```bash
# 1. Conectarse a la BD via Cloud SQL Proxy
gcloud sql connect sd-lms-db --user=sdlms_user

# 2. Ejecutar job de rollback
gcloud run jobs create sd-lms-rollback \
  --image=southamerica-east1-docker.pkg.dev/sd-lms-production/sd-lms/web:PREVIOUS_TAG \
  --region=southamerica-east1 \
  --memory=1Gi \
  --task-timeout=600 \
  --set-env-vars="DJANGO_SETTINGS_MODULE=config.settings.production" \
  --set-secrets="DATABASE_URL=database-url:latest" \
  --vpc-connector=sd-lms-connector \
  --command="python" \
  --args="manage.py,migrate,app_name,0005"

gcloud run jobs execute sd-lms-rollback --region=southamerica-east1 --wait
```

### Checklist de Rollback

- [ ] Identificar la causa del problema
- [ ] Notificar al equipo
- [ ] Ejecutar rollback de la aplicacion
- [ ] Verificar funcionamiento
- [ ] Ejecutar rollback de BD si es necesario
- [ ] Verificar logs de errores
- [ ] Documentar el incidente
- [ ] Planificar fix para el proximo deploy

---

## Comandos Utiles

### Verificar Estado

```bash
# Estado de Cloud Run
gcloud run services describe sd-lms-web --region=southamerica-east1

# Estado de Cloud SQL
gcloud sql instances describe sd-lms-db

# Estado de secretos
gcloud secrets list
```

### Escalar Manualmente

```bash
# Escalar instancias minimas
gcloud run services update sd-lms-web \
  --region=southamerica-east1 \
  --min-instances=3

# Escalar instancias maximas
gcloud run services update sd-lms-web \
  --region=southamerica-east1 \
  --max-instances=20
```

### Costos

```bash
# Ver estimacion de costos
gcloud billing budgets list

# Ver uso actual
gcloud compute project-info describe --format="table(usageExportBucket)"
```

---

## Recursos

- [Cloud Run Documentation](https://cloud.google.com/run/docs)
- [Cloud SQL Documentation](https://cloud.google.com/sql/docs)
- [Secret Manager Documentation](https://cloud.google.com/secret-manager/docs)
- [Cloud Logging Documentation](https://cloud.google.com/logging/docs)
- [GitHub Actions for GCP](https://github.com/google-github-actions)
