# LISTADO DE AJUSTES — Aplicativo de Gestión de Formación y Capacitación

**Proyecto:** Salomón Durán - Intercolombia  
**Fecha de reunión:** Febrero 2026  
**Elaboró:** INDUNNOVA SAS

---

## 1. Resumen por Módulo

| Módulo | Alta | Media | Baja | Total |
|--------|:----:|:-----:|:----:|:-----:|
| Gestión de Usuarios | 6 | 2 | 0 | 8 |
| Perfiles Ocupacionales | 2 | 0 | 0 | 2 |
| Configuración General | 0 | 1 | 0 | 1 |
| Gestión de Cursos | 3 | 4 | 1 | 8 |
| Rutas de Aprendizaje | 1 | 1 | 1 | 3 |
| Charlas / Divulgaciones | 1 | 1 | 0 | 2 |
| Evaluaciones | 0 | 1 | 1 | 2 |
| Certificados | 0 | 2 | 0 | 2 |
| Lecciones Aprendidas | 0 | 1 | 0 | 1 |
| Reportería / Analítica | 0 | 1 | 0 | 1 |
| Interfaz | 1 | 0 | 1 | 2 |
| **TOTAL** | **14** | **14** | **4** | **32** |

---

## 2. Detalle de Ajustes

### Gestión de Usuarios

| ID | Tipo | Descripción | Prioridad |
|----|------|-------------|:---------:|
| USR-01 | 🔴 Eliminar | Eliminar campo **'Correo electrónico'** para usuarios operativos. La autenticación será con número de cédula. | Alta |
| USR-02 | 🔴 Eliminar | Eliminar campo **'Frente de trabajo'**. El personal rota constantemente entre proyectos, dato no confiable. | Media |
| USR-03 | 🔴 Eliminar | Eliminar campo **'Contacto de emergencia'**. Ya existe en plataforma de Talento Humano. | Media |
| USR-04 | 🔴 Eliminar | Eliminar estados 'Suspendido' y 'Periodo de prueba'. Solo quedan: **Activo / Inactivo**. | Alta |
| USR-05 | 🟢 Agregar | Agregar campo **'Tipo de vinculación'** con opciones: Directo / Contratista. | Alta |
| USR-06 | 🔵 Modificar | **Autenticación diferenciada:** operativos con cédula + contraseña asignada; administradores y coordinadores con correo corporativo. | Alta |
| USR-07 | 🟢 Agregar | **Perfil intermedio para coordinadores:** autenticación con correo, permisos de visualización de analíticas sin capacidad de modificación. | Alta |
| USR-08 | 🔵 Modificar | Al **cambiar perfil ocupacional** de un usuario, conservar historial completo de formación anterior y habilitar nueva ruta de aprendizaje. | Alta |

### Perfiles Ocupacionales

| ID | Tipo | Descripción | Prioridad |
|----|------|-------------|:---------:|
| PER-01 | 🟠 Nuevo módulo | Crear módulo separado para **gestión de perfiles ocupacionales** (crear, editar, vincular a rutas de aprendizaje). | Alta |
| PER-02 | 🔵 Configurar | Cada perfil se vincula automáticamente a rutas de aprendizaje específicas. Al asignar perfil a usuario, se cargan rutas y cursos correspondientes. | Alta |

### Configuración General

| ID | Tipo | Descripción | Prioridad |
|----|------|-------------|:---------:|
| GEO-01 | 🟢 Agregar | Implementar **filtro/selector por país** (Colombia, Panamá, Perú). Cada país con personal, rutas y contenidos independientes. | Media |

### Gestión de Cursos

| ID | Tipo | Descripción | Prioridad |
|----|------|-------------|:---------:|
| CUR-01 | 🔵 Modificar | Usar campo 'Categoría' para clasificación por **área:** SST, Ambiental, Forestal, Técnico, Calidad. Crear maestros de categorías y subcategorías. | Alta |
| CUR-02 | 🔴 Eliminar | Eliminar campo **'Nivel de riesgo'**. No es necesario para la gestión de cursos. | Baja |
| CUR-03 | 🔵 Modificar | **Duración del curso:** cálculo automático sumando duración de módulos/lecciones. No requiere digitación manual. | Media |
| CUR-04 | 🔵 Configurar | **Estados del curso:** Borrador (no visible), Publicado (disponible), Archivado (obsoleto, preserva info). | Media |
| CUR-05 | 🟢 Agregar | Agregar campo **'Vigencia'** configurable en meses. Sistema genera alertas de renovación. Si se deja vacío, curso no vence. | Alta |
| CUR-06 | 🟢 Agregar | Agregar campo **'Tipo de curso'**: Obligatorio, Opcional, Refuerzo. | Media |
| CUR-07 | 🟢 Agregar | Opción para marcar lecciones como **'Presencial'** con funcionalidad de carga de evidencias (fotos, listas de asistencia). | Alta |
| CUR-08 | 🔵 Configurar | **Estrategia de videos:** alojar en YouTube empresarial privado y enlazar desde el aplicativo. | Media |

### Rutas de Aprendizaje

| ID | Tipo | Descripción | Prioridad |
|----|------|-------------|:---------:|
| RUT-01 | 🔵 Configurar | Rutas **obligatorias** asociadas automáticamente al perfil ocupacional. Rutas **opcionales** disponibles para todos. | Alta |
| RUT-02 | 🔵 Configurar | Secciones visibles para usuario: 'Mis cursos' (asignados), 'Todos los cursos' (catálogo), 'Rutas de aprendizaje' (planes formativos). | Media |
| RUT-03 | 🔵 Modificar | Duración estimada de la ruta: suma automática de la duración de los cursos que la componen. | Baja |

### Charlas / Divulgaciones

| ID | Tipo | Descripción | Prioridad |
|----|------|-------------|:---------:|
| CHP-01 | 🟠 Desarrollar | **Sistema de divulgación de alertas/políticas:** cargar contenido, generar link con 1-2 preguntas de verificación, trazabilidad de acceso y completitud. | Alta |
| CHP-02 | 🟠 Desarrollar | **Repositorio de plantillas** para charlas recurrentes (ciclos de 2-3 meses). Material reutilizable y más robusto. | Media |

### Evaluaciones

| ID | Tipo | Descripción | Prioridad |
|----|------|-------------|:---------:|
| EVA-01 | 🔵 Configurar | **Tipos de evaluación:** Repaso general (durante curso), Examen final, Evaluaciones cortas (1-2 preguntas para alertas/divulgaciones). | Media |
| EVA-02 | 🟠 Desarrollar | **Módulo de casos prácticos:** presentar situaciones donde el usuario debe resolver escenarios. Complementa formación teórica. | Baja |

### Certificados

| ID | Tipo | Descripción | Prioridad |
|----|------|-------------|:---------:|
| CER-01 | 🔵 Configurar | **Generación automática** de certificados digitales al completar curso y aprobar evaluación. | Media |
| CER-02 | 🟢 Agregar | Botón para **carga de certificados de terceros** (cursos realizados fuera del aplicativo). | Media |

### Lecciones Aprendidas

| ID | Tipo | Descripción | Prioridad |
|----|------|-------------|:---------:|
| LEC-01 | 🟠 Desarrollar | **Repositorio de lecciones aprendidas** de proyectos/actividades. Accesible para consulta y aprendizaje organizacional. | Media |
2
### Reportería / Analítica

| ID | Tipo | Descripción | Prioridad |
|----|------|-------------|:---------:|
| REP-01 | 🔵 Configurar | **Dashboard de administrador** con estadísticas generales. Vista de colaborador con información personal y avance. | Media |

### Interfaz

| ID | Tipo | Descripción | Prioridad |
|----|------|-------------|:---------:|
| INT-01 | 🟠 Desarrollar | Completar **modo claro/oscuro** para facilitar lectura de contenidos formativos. | Baja |
| INT-02 | 🔵 Configurar | Garantizar **interfaz responsive** completa para acceso desde dispositivos móviles del personal operativo. | Alta |

---

## 3. Información Pendiente por Recibir

| Información Requerida | Responsable | Estado |
|------------------------|-------------|:------:|
| Listado de cargos | Linda Amaya | ⏳ Pendiente |
| Listado de perfiles ocupacionales | Linda Amaya | ⏳ Pendiente |
| Planes de formación por tipo de proyecto | Linda Amaya | ⏳ Pendiente |
| Listado de usuarios para importación | Linda Amaya | ⏳ Pendiente |
| Definir estrategia de contenidos (virtual vs. presencial) | Linda Amaya | ⏳ Pendiente |

---

## 4. Próxima Reunión

**Fecha:** Lunes siguiente a las 11:00 AM  
**Agenda:** Revisar avances con la información proporcionada por Linda y definir alcance final de contenidos.

---

### Leyenda de Tipos

- 🔴 **Eliminar** — Campos o funcionalidades a remover del sistema
- 🟢 **Agregar** — Nuevos campos o funcionalidades a incorporar
- 🔵 **Modificar / Configurar** — Cambios en lógica, comportamiento o parametrización existente
- 🟠 **Desarrollar / Nuevo módulo** — Módulos o funcionalidades nuevas por construir
