# Plan de Desarrollo - Sistema LMS S.D. S.A.S.

## Sistema de Gestión de Capacitaciones y Plan de Formación

**Versión:** 1.0
**Fecha:** Enero 2026
**Proyecto:** LMS para gestión de competencias en trabajo de alto riesgo

---

## 1. Resumen Ejecutivo

Este documento presenta el plan de desarrollo para el Sistema LMS de S.D. S.A.S., una plataforma integral de gestión del aprendizaje diseñada para garantizar que el personal que opera en líneas de transmisión eléctrica cuente con las competencias necesarias para ejecutar trabajos de alto riesgo de manera segura.

### 1.1 Alcance del Proyecto

| Componente | Descripción |
|------------|-------------|
| **Web App** | Aplicación web responsive para administración y consumo de contenido |
| **App Móvil** | Aplicaciones nativas Android/iOS con soporte offline completo |
| **Backend API** | API REST escalable para gestión de datos y lógica de negocio |
| **CMS** | Sistema de gestión de contenido educativo (LCMS) |
| **Analytics** | Dashboard de reportes y analítica |

---

## 2. Stack Tecnológico Recomendado

### 2.1 Frontend Web

| Tecnología | Justificación |
|------------|---------------|
| **Next.js 14** | Framework React con SSR, optimización automática, excelente SEO |
| **TypeScript** | Tipado estático para mayor robustez y mantenibilidad |
| **Tailwind CSS** | Utilidades CSS para desarrollo rápido y consistente |
| **Shadcn/ui** | Componentes accesibles y personalizables |
| **TanStack Query** | Gestión de estado del servidor y caché |
| **Zustand** | Estado global ligero |
| **React Hook Form + Zod** | Formularios con validación robusta |

### 2.2 Aplicación Móvil

| Tecnología | Justificación |
|------------|---------------|
| **React Native** | Código compartido entre Android/iOS, ecosistema maduro |
| **Expo** | Desarrollo acelerado, OTA updates, build service |
| **WatermelonDB** | Base de datos offline-first de alto rendimiento |
| **React Native MMKV** | Almacenamiento local ultrarrápido |
| **React Native Background Fetch** | Sincronización en segundo plano |
| **Notifee** | Notificaciones push avanzadas |

### 2.3 Backend

| Tecnología | Justificación |
|------------|---------------|
| **Node.js + NestJS** | Framework enterprise-grade, modular, TypeScript nativo |
| **PostgreSQL** | Base de datos relacional robusta, soporte JSON |
| **Redis** | Caché, colas de trabajo, sesiones |
| **MinIO/S3** | Almacenamiento de objetos para multimedia |
| **BullMQ** | Colas de trabajo para tareas asíncronas |
| **Prisma** | ORM type-safe con migraciones |

### 2.4 Infraestructura

| Tecnología | Justificación |
|------------|---------------|
| **AWS** | Presencia en región São Paulo (cercana a Colombia) |
| **Docker + Kubernetes (EKS)** | Orquestación de contenedores escalable |
| **Terraform** | Infraestructura como código |
| **GitHub Actions** | CI/CD automatizado |
| **CloudFront CDN** | Distribución global de contenido multimedia |
| **AWS Cognito** | Autenticación y autorización |

### 2.5 Servicios Adicionales

| Servicio | Uso |
|----------|-----|
| **AWS SES** | Envío de correos transaccionales |
| **AWS SNS** | Notificaciones push y SMS |
| **FFmpeg** | Procesamiento y compresión de video |
| **Sharp** | Optimización de imágenes |
| **SCORM Cloud API** | Reproducción de contenido SCORM |

---

## 3. Arquitectura del Sistema

### 3.1 Diagrama de Alto Nivel

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              CLIENTES                                        │
├─────────────────┬─────────────────┬─────────────────┬───────────────────────┤
│   Web App       │   Android App   │    iOS App      │   Portal Auditor ISA  │
│   (Next.js)     │  (React Native) │ (React Native)  │      (Next.js)        │
└────────┬────────┴────────┬────────┴────────┬────────┴───────────┬───────────┘
         │                 │                 │                     │
         └─────────────────┴────────┬────────┴─────────────────────┘
                                    │
                           ┌────────▼────────┐
                           │   CloudFront    │
                           │      CDN        │
                           └────────┬────────┘
                                    │
                           ┌────────▼────────┐
                           │  Load Balancer  │
                           │    (AWS ALB)    │
                           └────────┬────────┘
                                    │
         ┌──────────────────────────┼──────────────────────────┐
         │                          │                          │
┌────────▼────────┐       ┌────────▼────────┐       ┌────────▼────────┐
│   API Gateway   │       │   API Gateway   │       │   API Gateway   │
│   (Instance 1)  │       │   (Instance 2)  │       │   (Instance N)  │
└────────┬────────┘       └────────┬────────┘       └────────┬────────┘
         │                         │                          │
         └─────────────────────────┼──────────────────────────┘
                                   │
         ┌─────────────────────────┼─────────────────────────┐
         │                         │                         │
┌────────▼────────┐      ┌────────▼────────┐      ┌─────────▼───────┐
│  Auth Service   │      │  Core LMS API   │      │ Content Service │
│   (NestJS)      │      │    (NestJS)     │      │    (NestJS)     │
└────────┬────────┘      └────────┬────────┘      └────────┬────────┘
         │                        │                         │
         │              ┌─────────┴─────────┐              │
         │              │                   │              │
    ┌────▼────┐    ┌────▼────┐       ┌─────▼─────┐   ┌────▼────┐
    │ Cognito │    │PostgreSQL│       │   Redis   │   │  MinIO  │
    │         │    │  (RDS)   │       │(ElastiCache│   │  (S3)   │
    └─────────┘    └──────────┘       └───────────┘   └─────────┘
```

### 3.2 Microservicios

| Servicio | Responsabilidad |
|----------|-----------------|
| **auth-service** | Autenticación, autorización, gestión de sesiones |
| **user-service** | Gestión de usuarios, perfiles, roles |
| **course-service** | Gestión de cursos, módulos, contenido |
| **learning-path-service** | Rutas de aprendizaje, prerrequisitos |
| **assessment-service** | Evaluaciones, banco de preguntas, calificación |
| **certification-service** | Certificados, vencimientos, validación QR |
| **lesson-learned-service** | Lecciones aprendidas, micro-learning |
| **preop-talk-service** | Charlas pre-operacionales, asistencia |
| **notification-service** | Push, email, SMS |
| **sync-service** | Sincronización offline, cola de cambios |
| **report-service** | Reportes, dashboards, exportaciones |
| **integration-service** | Integraciones con sistemas externos |

---

## 4. Fases de Desarrollo

### Fase 0: Preparación y Setup (Semanas 1-2)

#### Objetivos
- Establecer entorno de desarrollo
- Configurar infraestructura base
- Definir estándares de código

#### Entregables

| Tarea | Descripción |
|-------|-------------|
| Repositorio monorepo | Setup con Turborepo para web, móvil y backend |
| CI/CD Pipeline | GitHub Actions para build, test, deploy |
| Infraestructura base | Terraform para AWS (VPC, RDS, S3, etc.) |
| Ambientes | Dev, Staging, Production |
| Documentación técnica | ADRs, guías de contribución |
| Diseño UI/UX | Wireframes y mockups en Figma |

#### Estructura del Monorepo

```
sd-lms/
├── apps/
│   ├── web/                 # Next.js web app
│   ├── mobile/              # React Native app
│   ├── admin/               # Panel de administración
│   └── api/                 # NestJS backend
├── packages/
│   ├── ui/                  # Componentes compartidos
│   ├── database/            # Prisma schema y cliente
│   ├── config/              # Configuraciones compartidas
│   ├── types/               # Tipos TypeScript compartidos
│   └── utils/               # Utilidades compartidas
├── infrastructure/
│   ├── terraform/           # IaC
│   ├── kubernetes/          # Manifests K8s
│   └── docker/              # Dockerfiles
├── docs/                    # Documentación
└── scripts/                 # Scripts de utilidad
```

---

### Fase 1: Core Backend y Autenticación (Semanas 3-6)

#### Objetivos
- Implementar servicios backend core
- Sistema de autenticación robusto
- Gestión de usuarios y roles

#### Módulos a Desarrollar

##### 1.1 Servicio de Autenticación
```typescript
// Funcionalidades
- Login con email/password
- Autenticación de dos factores (2FA)
- Gestión de sesiones
- Refresh tokens
- Logout y revocación de tokens
- Recuperación de contraseña
- Integración con AWS Cognito
```

##### 1.2 Servicio de Usuarios
```typescript
// Funcionalidades
- CRUD de usuarios
- Gestión de perfiles (Admin, Supervisor, Colaborador, Auditor, Instructor)
- Asignación de roles y permisos
- Vinculación con contratos
- Importación masiva (CSV/Excel)
- Histórico de contratos
- Estados de usuario (activo, inactivo, suspendido)
```

##### 1.3 Modelo de Datos Inicial

```prisma
// schema.prisma (extracto)

model User {
  id                String    @id @default(cuid())
  email             String    @unique
  passwordHash      String
  firstName         String
  lastName          String
  documentType      String    // CC, CE, etc.
  documentNumber    String    @unique
  phone             String?
  role              Role      @relation(fields: [roleId], references: [id])
  roleId            String
  status            UserStatus @default(ACTIVE)
  jobPosition       String
  workFront         String?
  hireDate          DateTime
  contracts         UserContract[]
  enrollments       Enrollment[]
  certifications    Certification[]
  createdAt         DateTime  @default(now())
  updatedAt         DateTime  @updatedAt
}

model Role {
  id          String   @id @default(cuid())
  name        String   @unique // ADMIN, SUPERVISOR, WORKER, AUDITOR, INSTRUCTOR
  permissions Permission[]
  users       User[]
}

model Contract {
  id          String   @id @default(cuid())
  code        String   @unique // ej: "ISA 4620004459"
  name        String
  client      String
  startDate   DateTime
  endDate     DateTime?
  users       UserContract[]
  courses     CourseContract[]
}
```

#### Entregables Fase 1
- [ ] API de autenticación completa
- [ ] API de gestión de usuarios
- [ ] Sistema de roles y permisos
- [ ] Importación masiva de usuarios
- [ ] Documentación API (Swagger/OpenAPI)
- [ ] Tests unitarios y de integración (cobertura >80%)

---

### Fase 2: Gestión de Contenidos (LCMS) (Semanas 7-10)

#### Objetivos
- Sistema de gestión de cursos
- Soporte para múltiples formatos de contenido
- Versionamiento de contenidos

#### Módulos a Desarrollar

##### 2.1 Servicio de Cursos
```typescript
// Funcionalidades
- CRUD de cursos
- Módulos y lecciones
- Soporte multimedia (video, PDF, audio, imágenes)
- Contenido SCORM (1.2 y 2004)
- Versionamiento de contenido
- Categorización (tema, riesgo, obligatoriedad)
- Estados (borrador, publicado, archivado)
```

##### 2.2 Servicio de Contenido Multimedia
```typescript
// Funcionalidades
- Upload de archivos (chunked para videos grandes)
- Procesamiento de video (transcoding, compresión)
- Generación de thumbnails
- CDN integration para streaming
- Soporte offline (manifest de descarga)
- Biblioteca de recursos
```

##### 2.3 Modelo de Datos

```prisma
model Course {
  id              String    @id @default(cuid())
  code            String    @unique
  title           String
  description     String
  duration        Int       // minutos
  type            CourseType // MANDATORY, OPTIONAL, REFRESHER
  riskLevel       RiskLevel
  thumbnailUrl    String?
  status          CourseStatus @default(DRAFT)
  version         Int       @default(1)
  modules         Module[]
  enrollments     Enrollment[]
  contracts       CourseContract[]
  targetProfiles  String[]  // ["LINIERO", "JEFE_CUADRILLA"]
  prerequisites   Course[]  @relation("Prerequisites")
  createdBy       String
  createdAt       DateTime  @default(now())
  updatedAt       DateTime  @updatedAt
}

model Module {
  id          String    @id @default(cuid())
  courseId    String
  course      Course    @relation(fields: [courseId], references: [id])
  title       String
  description String?
  order       Int
  lessons     Lesson[]
}

model Lesson {
  id          String    @id @default(cuid())
  moduleId    String
  module      Module    @relation(fields: [moduleId], references: [id])
  title       String
  type        LessonType // VIDEO, PDF, SCORM, INTERACTIVE, QUIZ
  contentUrl  String
  duration    Int       // minutos
  order       Int
  isOffline   Boolean   @default(true)
  metadata    Json?     // información adicional según tipo
}

model MediaAsset {
  id            String   @id @default(cuid())
  filename      String
  originalName  String
  mimeType      String
  size          Int
  url           String
  thumbnailUrl  String?
  offlineUrl    String?  // URL para descarga offline (comprimido)
  status        AssetStatus @default(PROCESSING)
  metadata      Json?
  createdAt     DateTime @default(now())
}
```

#### Entregables Fase 2
- [ ] API de gestión de cursos
- [ ] Sistema de upload y procesamiento multimedia
- [ ] Soporte SCORM básico
- [ ] Biblioteca de recursos
- [ ] Editor de cursos (web admin)
- [ ] Versionamiento de contenidos

---

### Fase 3: Rutas de Aprendizaje y Evaluaciones (Semanas 11-14)

#### Objetivos
- Sistema de rutas de aprendizaje con prerrequisitos
- Motor de evaluaciones completo
- Sistema de certificación

#### Módulos a Desarrollar

##### 3.1 Servicio de Rutas de Aprendizaje
```typescript
// Funcionalidades
- Definición de rutas por perfil ocupacional
- Prerrequisitos y secuenciación
- Fechas límite y vencimientos
- Asignación automática según perfil
- Bloqueo de avance sin completar prerrequisitos
- Notificaciones de cursos pendientes/vencidos
```

##### 3.2 Servicio de Evaluaciones
```typescript
// Funcionalidades
- Banco de preguntas por tema
- Tipos de pregunta: múltiple, V/F, ordenamiento, asociación
- Aleatorización de preguntas
- Tiempo límite configurable
- Intentos máximos configurables
- Retroalimentación inmediata
- Evaluación de escenarios (simulaciones)
- Evaluación práctica (checklist con firma digital)
```

##### 3.3 Servicio de Certificación
```typescript
// Funcionalidades
- Generación de certificados PDF
- Código QR de verificación
- Firma digital del responsable
- Fechas de vencimiento
- Alertas de renovación (30 días antes)
- Verificación pública de certificados
- Pasaporte de competencias
```

##### 3.4 Modelo de Datos

```prisma
model LearningPath {
  id              String   @id @default(cuid())
  name            String
  description     String
  targetProfile   String   // LINIERO, JEFE_CUADRILLA, etc.
  totalHours      Int
  isActive        Boolean  @default(true)
  steps           LearningPathStep[]
  enrollments     Enrollment[]
}

model LearningPathStep {
  id              String   @id @default(cuid())
  learningPathId  String
  learningPath    LearningPath @relation(fields: [learningPathId], references: [id])
  courseId        String
  course          Course   @relation(fields: [courseId], references: [id])
  order           Int
  isRequired      Boolean  @default(true)
  daysToComplete  Int?     // días máximos para completar
}

model Assessment {
  id              String   @id @default(cuid())
  courseId        String
  course          Course   @relation(fields: [courseId], references: [id])
  title           String
  type            AssessmentType // THEORETICAL, PRACTICAL, SCENARIO
  passingScore    Int      @default(80)
  maxAttempts     Int      @default(3)
  timeLimit       Int?     // minutos
  randomize       Boolean  @default(true)
  questionsCount  Int      // preguntas a mostrar del banco
  questions       Question[]
  attempts        AssessmentAttempt[]
}

model Question {
  id              String   @id @default(cuid())
  assessmentId    String
  assessment      Assessment @relation(fields: [assessmentId], references: [id])
  text            String
  type            QuestionType // MULTIPLE_CHOICE, TRUE_FALSE, ORDERING, MATCHING
  options         Json     // opciones y respuesta correcta
  points          Int      @default(1)
  feedback        String?  // retroalimentación
  mediaUrl        String?  // imagen o video adjunto
}

model Certification {
  id              String   @id @default(cuid())
  userId          String
  user            User     @relation(fields: [userId], references: [id])
  courseId        String
  course          Course   @relation(fields: [courseId], references: [id])
  issueDate       DateTime @default(now())
  expirationDate  DateTime?
  certificateUrl  String
  qrCode          String   @unique
  signedBy        String
  status          CertStatus @default(VALID)
}
```

#### Entregables Fase 3
- [ ] Sistema de rutas de aprendizaje
- [ ] Motor de evaluaciones teóricas
- [ ] Evaluaciones prácticas con checklist
- [ ] Generación de certificados
- [ ] Verificación QR de certificados
- [ ] Alertas de vencimiento

---

### Fase 4: Aplicación Móvil - Core (Semanas 15-18)

#### Objetivos
- App móvil funcional Android/iOS
- Capacidad offline completa
- Sincronización robusta

#### Módulos a Desarrollar

##### 4.1 Core Mobile
```typescript
// Funcionalidades
- Autenticación biométrica
- Dashboard personal
- Navegación de cursos
- Reproductor de contenido
- Realización de evaluaciones
- Visualización de certificados
```

##### 4.2 Sistema Offline
```typescript
// Funcionalidades
- Descarga selectiva de cursos
- Base de datos local (WatermelonDB)
- Cola de sincronización
- Resolución de conflictos
- Indicador de estado de sincronización
- Gestión de almacenamiento
- Compresión de contenido offline
```

##### 4.3 Arquitectura Offline

```
┌─────────────────────────────────────────────────────────────┐
│                      REACT NATIVE APP                        │
├─────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │   UI Layer  │  │ State Mgmt  │  │  Offline Manager    │  │
│  │  (Screens)  │  │  (Zustand)  │  │                     │  │
│  └──────┬──────┘  └──────┬──────┘  └──────────┬──────────┘  │
│         │                │                     │             │
│         └────────────────┼─────────────────────┘             │
│                          │                                   │
│  ┌───────────────────────▼───────────────────────────────┐  │
│  │                   Repository Layer                     │  │
│  │  ┌─────────────────┐     ┌─────────────────────────┐  │  │
│  │  │  Online Repo    │     │     Offline Repo        │  │  │
│  │  │   (API Client)  │     │   (WatermelonDB)        │  │  │
│  │  └────────┬────────┘     └───────────┬─────────────┘  │  │
│  │           │                          │                 │  │
│  │  ┌────────▼────────────────────────▼──────────────┐   │  │
│  │  │              Sync Engine                        │   │  │
│  │  │  - Conflict Resolution                          │   │  │
│  │  │  - Queue Management                             │   │  │
│  │  │  - Background Sync                              │   │  │
│  │  └─────────────────────────────────────────────────┘   │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                              │
│  ┌───────────────────────────────────────────────────────┐  │
│  │                 Local Storage                          │  │
│  │  ┌──────────────┐  ┌──────────────┐  ┌─────────────┐  │  │
│  │  │ WatermelonDB │  │    MMKV      │  │ File System │  │  │
│  │  │  (SQL Data)  │  │  (Key-Value) │  │  (Media)    │  │  │
│  │  └──────────────┘  └──────────────┘  └─────────────┘  │  │
│  └───────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

#### Entregables Fase 4
- [ ] App móvil funcional (Android + iOS)
- [ ] Sistema de descarga offline
- [ ] Reproductor de video offline
- [ ] Evaluaciones offline
- [ ] Sincronización automática
- [ ] Push notifications

---

### Fase 5: Lecciones Aprendidas y Charlas Pre-Operacionales (Semanas 19-22)

#### Objetivos
- Repositorio de lecciones aprendidas
- Sistema de charlas pre-operacionales digitales
- Generación de micro-learning

#### Módulos a Desarrollar

##### 5.1 Servicio de Lecciones Aprendidas
```typescript
// Funcionalidades
- Creación de lecciones (plantilla estandarizada)
- Categorización (accidente, casi-accidente, buena práctica)
- Vinculación con cursos relacionados
- Generación automática de micro-learning
- Notificación a todo el personal
- Quiz de comprensión
- Histórico de visualizaciones
```

##### 5.2 Servicio de Charlas Pre-Operacionales
```typescript
// Funcionalidades
- Biblioteca de charlas de 5 minutos
- Selección según actividad del día
- Registro de asistencia (QR + geolocalización)
- Foto grupal opcional
- Pregunta "¿Qué puede salir mal hoy?"
- Mini-evaluación de 3 preguntas
- Recordatorio de SWA recientes
- Funcionamiento offline
```

##### 5.3 Modelo de Datos

```prisma
model LessonLearned {
  id              String   @id @default(cuid())
  title           String
  eventDate       DateTime
  type            LessonType // ACCIDENT, NEAR_MISS, OBSERVATION, BEST_PRACTICE
  whatHappened    String   @db.Text
  whyHappened     String   @db.Text
  whatWeLearned   String   @db.Text
  whatWeChanged   String   @db.Text
  mediaUrls       String[] // fotos, diagramas
  applicableContracts String[]
  relatedCourses  Course[]
  microLearning   MicroLearning?
  isPublished     Boolean  @default(false)
  publishedAt     DateTime?
  views           LessonView[]
  quizzes         LessonQuiz[]
  createdBy       String
  createdAt       DateTime @default(now())
}

model PreOpTalk {
  id              String   @id @default(cuid())
  title           String
  content         String   @db.Text
  duration        Int      // minutos (típicamente 5)
  category        String   // tema
  activityTypes   String[] // actividades relacionadas
  mediaUrl        String?
  questions       Json     // 3 preguntas de verificación
  isActive        Boolean  @default(true)
}

model PreOpTalkSession {
  id              String   @id @default(cuid())
  talkId          String
  talk            PreOpTalk @relation(fields: [talkId], references: [id])
  conductedBy     String   // userId del jefe de cuadrilla
  location        Json     // {lat, lng, accuracy}
  timestamp       DateTime @default(now())
  photoUrl        String?
  plannedActivity String
  whatCouldGoWrong String[] // respuestas de los trabajadores
  attendees       PreOpAttendance[]
  quizResponses   Json     // respuestas al mini-quiz
}

model PreOpAttendance {
  id              String   @id @default(cuid())
  sessionId       String
  session         PreOpTalkSession @relation(fields: [sessionId], references: [id])
  userId          String
  user            User     @relation(fields: [userId], references: [id])
  signatureType   String   // QR, MANUAL
  timestamp       DateTime @default(now())
  location        Json?
}
```

#### Entregables Fase 5
- [ ] Sistema de lecciones aprendidas
- [ ] Generador de micro-learning
- [ ] Módulo de charlas pre-operacionales
- [ ] Registro de asistencia con QR
- [ ] Geolocalización de charlas
- [ ] Funcionamiento offline completo

---

### Fase 6: Reportes y Analytics (Semanas 23-26)

#### Objetivos
- Dashboards para todos los perfiles
- Reportes exportables
- Integración con operaciones

#### Módulos a Desarrollar

##### 6.1 Servicio de Reportes
```typescript
// Dashboards
- Cumplimiento general del plan de formación
- Trabajadores con formación vencida
- Brechas de competencias por contrato
- Horas de formación ejecutadas vs planificadas
- Ranking de módulos con mayor reprobación
- Estado de formación por equipo

// Reportes Exportables
- Matriz de competencias
- Certificaciones vigentes/vencidas
- Registro de charlas pre-operacionales
- Detalle de evaluaciones
- Informe para ARL
- Informe para auditorías SST
```

##### 6.2 Portal Auditor ISA
```typescript
// Funcionalidades (solo lectura)
- Dashboard de cumplimiento
- Evidencias de formación
- Histórico de formación por trabajador
- Exportación de reportes
- Verificación de certificados
```

##### 6.3 Integración con Operaciones
```typescript
// Funcionalidades
- API para verificar formación antes de asignar actividades
- Pasaporte de Competencias digital
- Bloqueo suave/duro configurable
- Sugerencia de cursos tras casi-accidentes
```

#### Entregables Fase 6
- [ ] Dashboard administrativo
- [ ] Dashboard supervisores
- [ ] Portal auditor ISA
- [ ] Reportes exportables (PDF, Excel)
- [ ] API de integración con operaciones
- [ ] Alertas automáticas

---

### Fase 7: Gamificación y Notificaciones (Semanas 27-28)

#### Objetivos
- Sistema de gamificación completo
- Notificaciones multicanal

#### Módulos a Desarrollar

##### 7.1 Sistema de Gamificación
```typescript
// Elementos
- Puntos por completar cursos y evaluaciones
- Insignias (Experto en Altura, Héroe SWA, etc.)
- Rankings por cuadrilla e individual
- Progreso visual (barras, mapas)
- Reconocimientos especiales
```

##### 7.2 Sistema de Notificaciones
```typescript
// Canales
- Push notifications (móvil)
- Email (SES)
- SMS (SNS) para urgentes

// Eventos
- Nuevo curso asignado
- Curso próximo a vencer
- Curso vencido
- Nueva lección aprendida
- Certificado emitido
- Evaluación reprobada
```

#### Entregables Fase 7
- [ ] Sistema de puntos e insignias
- [ ] Rankings y leaderboards
- [ ] Notificaciones push
- [ ] Notificaciones email
- [ ] Notificaciones SMS
- [ ] Panel de configuración de notificaciones

---

### Fase 8: Pruebas, Optimización y Despliegue (Semanas 29-32)

#### Objetivos
- Testing exhaustivo
- Optimización de rendimiento
- Despliegue a producción

#### Actividades

##### 8.1 Testing
```
- Pruebas unitarias (cobertura >80%)
- Pruebas de integración
- Pruebas E2E (Cypress para web, Detox para móvil)
- Pruebas de carga (k6)
- Pruebas de seguridad (OWASP)
- Pruebas de usabilidad con usuarios reales
- Pruebas de funcionamiento offline
```

##### 8.2 Optimización
```
- Optimización de queries (análisis EXPLAIN)
- Caché estratégico (Redis)
- Compresión de assets
- Lazy loading
- Code splitting
- Optimización de imágenes y videos
```

##### 8.3 Despliegue
```
- Configuración de producción
- Migración de datos
- Capacitación a administradores
- Documentación de usuario
- Runbooks operativos
- Monitoreo (DataDog/CloudWatch)
```

#### Entregables Fase 8
- [ ] Suite de tests completa
- [ ] Documentación de usuario
- [ ] Manual de administrador
- [ ] Runbooks operativos
- [ ] Sistema desplegado en producción
- [ ] Capacitación completada

---

## 5. Cronograma General

```
                            2026
        ENE     FEB     MAR     ABR     MAY     JUN     JUL     AGO
        ─────────────────────────────────────────────────────────────
Fase 0  ████                                                          Setup
Fase 1      ████████                                                  Auth & Users
Fase 2              ████████                                          LCMS
Fase 3                      ████████                                  Learning Paths
Fase 4                              ████████                          Mobile Core
Fase 5                                      ████████                  Lecciones
Fase 6                                              ████████          Reportes
Fase 7                                                      ████      Gamificación
Fase 8                                                          ████  Deploy

        S1-2    S3-6    S7-10   S11-14  S15-18  S19-22  S23-26  S27-32
```

---

## 6. Equipo Recomendado

### Equipo Core

| Rol | Cantidad | Responsabilidades |
|-----|----------|-------------------|
| **Tech Lead / Arquitecto** | 1 | Arquitectura, decisiones técnicas, code review |
| **Backend Developer Senior** | 2 | APIs, servicios, integraciones |
| **Frontend Developer Senior** | 1 | Web app, panel admin |
| **Mobile Developer Senior** | 2 | App React Native, offline |
| **DevOps Engineer** | 1 | Infraestructura, CI/CD, monitoreo |
| **QA Engineer** | 1 | Testing, automatización |
| **UX/UI Designer** | 1 | Diseño de interfaces, experiencia de usuario |

### Equipo Extendido

| Rol | Cantidad | Responsabilidades |
|-----|----------|-------------------|
| **Product Owner** | 1 (cliente) | Priorización, validación |
| **Scrum Master** | 1 | Facilitación, mejora continua |
| **Diseñador Instruccional** | 1 | Contenido educativo |

---

## 7. Riesgos y Mitigaciones

| Riesgo | Probabilidad | Impacto | Mitigación |
|--------|--------------|---------|------------|
| Complejidad del modo offline | Alta | Alto | PoC temprano en Fase 0, experto en sync |
| Conectividad en zonas remotas | Alta | Alto | Diseño offline-first, compresión agresiva |
| Adopción por usuarios operativos | Media | Alto | UX simple, capacitación, gamificación |
| Integración SCORM | Media | Medio | Usar librería probada (scorm-again) |
| Escalabilidad | Baja | Alto | Arquitectura cloud-native desde inicio |
| Cumplimiento normativo | Baja | Alto | Revisión legal temprana, cifrado |

---

## 8. Métricas de Éxito Técnico

| Métrica | Target |
|---------|--------|
| Tiempo de carga inicial (web) | < 3s |
| Tiempo de carga inicial (móvil) | < 2s |
| Uptime | 99.5% |
| Sincronización offline | < 30s para 1 día de trabajo |
| Cobertura de tests | > 80% |
| Tamaño de APK | < 50MB |
| Memoria máxima (móvil) | < 200MB |

---

## 9. Próximos Pasos Inmediatos

1. **Validar este plan** con stakeholders de S.D. S.A.S.
2. **Definir MVP** - Priorizar funcionalidades para primera release
3. **Configurar repositorio** y ambiente de desarrollo
4. **Iniciar diseño UX/UI** de las pantallas principales
5. **Comenzar Fase 0** - Setup de infraestructura base

---

*Documento generado como parte del plan de desarrollo del Sistema LMS para S.D. S.A.S.*
