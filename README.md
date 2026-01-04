# Sistema LMS - S.D. S.A.S.

## Sistema de Gestión de Capacitaciones y Plan de Formación

Sistema integral de gestión del aprendizaje (LMS) diseñado para garantizar que el personal de S.D. S.A.S. que opera en líneas de transmisión eléctrica cuente con las competencias necesarias para ejecutar trabajos de alto riesgo de manera segura.

---

## Documentación

| Documento | Descripción |
|-----------|-------------|
| [Plan de Desarrollo](./docs/PLAN_DE_DESARROLLO.md) | Fases, cronograma, stack tecnológico y equipo |
| [Arquitectura de Infraestructura](./docs/ARQUITECTURA_INFRAESTRUCTURA.md) | Propuesta de infraestructura AWS, costos y seguridad |

---

## Características Principales

- **Gestión de Usuarios**: Perfiles diferenciados (Admin, Supervisor, Colaborador, Auditor, Instructor)
- **LCMS**: Sistema de gestión de contenidos educativos con soporte multimedia
- **Rutas de Aprendizaje**: Secuenciación de cursos con prerrequisitos
- **Evaluaciones**: Teóricas, prácticas y de escenarios
- **Certificaciones**: Generación automática con QR de verificación
- **Lecciones Aprendidas**: Repositorio con generación de micro-learning
- **Charlas Pre-Operacionales**: Registro digital con geolocalización
- **Modo Offline**: Funcionamiento completo sin conectividad
- **Reportes y Analytics**: Dashboards para todos los perfiles

---

## Stack Tecnológico

### Frontend
- **Web**: Next.js 14, TypeScript, Tailwind CSS
- **Móvil**: React Native, Expo

### Backend
- **API**: NestJS, TypeScript
- **Base de Datos**: PostgreSQL
- **Caché**: Redis
- **Almacenamiento**: AWS S3

### Infraestructura
- **Cloud**: AWS (sa-east-1)
- **Orquestación**: Kubernetes (EKS)
- **CI/CD**: GitHub Actions
- **IaC**: Terraform

---

## Estructura del Proyecto

```
sd-lms/
├── apps/
│   ├── web/                 # Next.js web app
│   ├── mobile/              # React Native app
│   ├── admin/               # Panel de administración
│   └── api/                 # NestJS backend
├── packages/
│   ├── ui/                  # Componentes compartidos
│   ├── database/            # Prisma schema
│   ├── config/              # Configuraciones
│   ├── types/               # Tipos TypeScript
│   └── utils/               # Utilidades
├── infrastructure/
│   ├── terraform/           # IaC
│   ├── kubernetes/          # K8s manifests
│   └── docker/              # Dockerfiles
├── docs/                    # Documentación
└── scripts/                 # Scripts de utilidad
```

---

## Requisitos del Sistema

### Desarrollo
- Node.js 20+
- pnpm 8+
- Docker Desktop
- AWS CLI v2

### Producción
- AWS Account con permisos adecuados
- Dominio configurado en Route 53
- Certificados SSL (ACM)

---

## Inicio Rápido

```bash
# Clonar repositorio
git clone <repository-url>
cd sd-lms

# Instalar dependencias
pnpm install

# Configurar variables de entorno
cp .env.example .env

# Iniciar ambiente de desarrollo
docker-compose up -d
pnpm dev
```

---

## Licencia

Propiedad de S.D. S.A.S. - Todos los derechos reservados.

---

*Proyecto desarrollado para garantizar la seguridad y competencia del personal en trabajos de alto riesgo en líneas de transmisión eléctrica.*
