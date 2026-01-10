# Guia de Contribucion - SD LMS

Gracias por tu interes en contribuir al Sistema LMS de S.D. S.A.S. Este documento proporciona las pautas y mejores practicas para contribuir al proyecto.

## Tabla de Contenidos

- [Configuracion del Entorno de Desarrollo](#configuracion-del-entorno-de-desarrollo)
- [Convenciones de Codigo](#convenciones-de-codigo)
- [Estructura de Commits](#estructura-de-commits)
- [Proceso de Pull Requests](#proceso-de-pull-requests)
- [Ejecucion de Tests](#ejecucion-de-tests)
- [Pre-commit Hooks](#pre-commit-hooks)

---

## Configuracion del Entorno de Desarrollo

### Requisitos Previos

- Python 3.12+
- Docker Desktop
- Git
- Node.js 20+ (solo para desarrollo movil)

### Configuracion Inicial

1. **Clonar el repositorio**

```bash
git clone <repository-url>
cd sd-lms
```

2. **Crear entorno virtual Python**

```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate   # Windows
```

3. **Instalar dependencias de desarrollo**

```bash
pip install -r requirements/local.txt
```

4. **Configurar variables de entorno**

```bash
cp .env.example .env
```

Edita el archivo `.env` con tus configuraciones locales:

```env
DEBUG=True
SECRET_KEY=tu-clave-secreta-para-desarrollo
DATABASE_URL=postgres://postgres:postgres@localhost:5432/sd_lms
REDIS_URL=redis://localhost:6379/0
DJANGO_SETTINGS_MODULE=config.settings.local
```

5. **Iniciar servicios con Docker**

```bash
docker-compose up -d db redis
```

6. **Ejecutar migraciones**

```bash
python manage.py migrate
```

7. **Crear superusuario**

```bash
python manage.py createsuperuser
```

8. **Iniciar servidor de desarrollo**

```bash
python manage.py runserver
```

La aplicacion estara disponible en `http://localhost:8000`

### Servicios Opcionales

```bash
# Iniciar Celery worker para tareas asincronas
celery -A config worker -l INFO

# Iniciar Celery beat para tareas programadas
celery -A config beat -l INFO

# Iniciar Flower para monitoreo de Celery
docker-compose --profile monitoring up -d flower

# Iniciar MailHog para testing de emails
docker-compose --profile email up -d mailhog
```

---

## Convenciones de Codigo

### Python (PEP 8 + Ruff)

Utilizamos **Ruff** como linter y formateador unico para Python. Ruff esta configurado para ser compatible con PEP 8 y las mejores practicas de la comunidad Django.

#### Reglas Principales

- **Longitud maxima de linea**: 100 caracteres
- **Indentacion**: 4 espacios (no tabs)
- **Imports**: Ordenados automaticamente por Ruff (isort compatible)
- **Docstrings**: Estilo Google

#### Ejemplo de Codigo

```python
"""
Ejemplo de servicio siguiendo las convenciones del proyecto.
"""

from django.db import transaction
from django.utils import timezone

from apps.core.models import BaseModel


class ExampleService:
    """Servicio de ejemplo para operaciones de negocio."""

    @staticmethod
    def process_item(item_id: int) -> dict:
        """
        Procesa un item y retorna el resultado.

        Args:
            item_id: ID del item a procesar.

        Returns:
            Diccionario con el resultado del procesamiento.

        Raises:
            ValueError: Si el item no existe.
        """
        # Implementacion...
        pass
```

#### Comandos de Linting

```bash
# Verificar errores de linting
ruff check .

# Corregir errores automaticamente
ruff check --fix .

# Verificar formato
ruff format --check .

# Aplicar formato
ruff format .
```

### Type Hints

Utilizamos type hints de Python 3.12+ con verificacion via **mypy**.

```python
from typing import Optional


def get_user_name(user_id: int) -> Optional[str]:
    """Obtiene el nombre del usuario."""
    ...
```

```bash
# Verificar tipos
mypy apps/
```

### Django Templates

Utilizamos **djLint** para formateo de templates Django.

```bash
# Verificar templates
djlint templates/ --check

# Formatear templates
djlint templates/ --reformat
```

### CSS/JavaScript

- **CSS**: Tailwind CSS con clases utilitarias
- **JavaScript**: Alpine.js para interactividad, HTMX para AJAX

---

## Estructura de Commits

Seguimos la convencion de **Conventional Commits** para mensajes claros y generacion automatica de changelogs.

### Formato

```
<tipo>(<alcance>): <descripcion>

[cuerpo opcional]

[pie opcional]
```

### Tipos de Commit

| Tipo | Descripcion |
|------|-------------|
| `feat` | Nueva funcionalidad |
| `fix` | Correccion de bug |
| `docs` | Cambios en documentacion |
| `style` | Cambios de formato (no afectan logica) |
| `refactor` | Refactorizacion de codigo |
| `perf` | Mejoras de rendimiento |
| `test` | Agregar o modificar tests |
| `build` | Cambios en build o dependencias |
| `ci` | Cambios en CI/CD |
| `chore` | Tareas de mantenimiento |
| `revert` | Revertir un commit anterior |

### Alcance (Scope)

El alcance indica el modulo afectado:

- `accounts` - Usuarios y autenticacion
- `courses` - Gestion de cursos
- `assessments` - Evaluaciones
- `certifications` - Certificados
- `learning-paths` - Rutas de aprendizaje
- `notifications` - Notificaciones
- `reports` - Reportes
- `api` - API REST
- `infra` - Infraestructura
- `deps` - Dependencias

### Ejemplos

```bash
# Nueva funcionalidad
feat(courses): agregar soporte para contenido SCORM 2004

# Correccion de bug
fix(certifications): corregir generacion de QR en certificados

# Documentacion
docs(api): actualizar documentacion de endpoints de autenticacion

# Refactorizacion
refactor(assessments): extraer logica de calificacion a servicio

# Breaking change
feat(api)!: cambiar estructura de respuesta de autenticacion

BREAKING CHANGE: El campo 'token' ahora se llama 'access_token'
```

### Validacion

El hook de pre-commit valida automaticamente el formato de los mensajes usando **commitizen**.

---

## Proceso de Pull Requests

### Antes de Crear un PR

1. **Actualiza tu rama** con los ultimos cambios de `develop`:

```bash
git checkout develop
git pull origin develop
git checkout tu-rama
git rebase develop
```

2. **Ejecuta todos los checks**:

```bash
# Pre-commit hooks
pre-commit run --all-files

# Tests
pytest

# Type checking
mypy apps/
```

3. **Verifica que no hay conflictos**

### Creando el PR

1. **Crea una rama descriptiva**:

```bash
# Formato: tipo/descripcion-corta
git checkout -b feat/scorm-support
git checkout -b fix/certificate-qr-generation
git checkout -b refactor/assessment-service
```

2. **Empuja tu rama**:

```bash
git push -u origin tu-rama
```

3. **Crea el PR en GitHub** con:
   - Titulo claro siguiendo Conventional Commits
   - Descripcion detallada del cambio
   - Referencia a issues relacionados
   - Screenshots si hay cambios visuales

### Template de PR

```markdown
## Descripcion

Breve descripcion del cambio.

## Tipo de Cambio

- [ ] Nueva funcionalidad
- [ ] Correccion de bug
- [ ] Refactorizacion
- [ ] Documentacion
- [ ] Otro: _________

## Cambios Realizados

- Cambio 1
- Cambio 2
- Cambio 3

## Como Probar

1. Paso 1
2. Paso 2
3. Resultado esperado

## Checklist

- [ ] Los tests pasan localmente
- [ ] Se agregaron tests para los nuevos cambios
- [ ] La documentacion fue actualizada
- [ ] El codigo sigue las convenciones del proyecto
- [ ] No hay warnings de linting

## Issues Relacionados

Closes #123
```

### Proceso de Review

1. Al menos **1 aprobacion** requerida
2. Todos los checks de CI deben pasar
3. No conflictos con la rama destino
4. El reviewer verificara:
   - Funcionalidad correcta
   - Tests adecuados
   - Codigo limpio y mantenible
   - Documentacion actualizada

### Merge

- PRs a `develop`: Squash and merge
- PRs a `main`: Merge commit (para releases)

---

## Ejecucion de Tests

Utilizamos **pytest** como framework de testing con plugins para Django y cobertura.

### Ejecutar Tests

```bash
# Todos los tests
pytest

# Tests de una app especifica
pytest apps/accounts/

# Tests de un archivo especifico
pytest apps/accounts/tests/test_api.py

# Test especifico
pytest apps/accounts/tests/test_api.py::TestUserAPI::test_create_user

# Con output verbose
pytest -v

# Mostrar prints
pytest -s
```

### Cobertura de Codigo

```bash
# Ejecutar con cobertura
pytest --cov=apps

# Generar reporte HTML
pytest --cov=apps --cov-report=html

# Ver reporte en terminal
pytest --cov=apps --cov-report=term-missing
```

El reporte HTML se genera en `htmlcov/index.html`.

### Cobertura Minima

El proyecto requiere **80% de cobertura** minima. El CI fallara si la cobertura es menor.

### Ejecutar Tests en Paralelo

```bash
# Usar todos los cores disponibles
pytest -n auto

# Numero especifico de workers
pytest -n 4
```

### Fixtures

Utilizamos **factory_boy** para crear datos de prueba:

```python
# apps/accounts/tests/factories.py
import factory
from apps.accounts.models import User


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    email = factory.Sequence(lambda n: f"user{n}@example.com")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
```

### Estructura de Tests

```
apps/
  accounts/
    tests/
      __init__.py
      conftest.py      # Fixtures compartidas
      factories.py     # Factories de datos
      test_api.py      # Tests de API
      test_models.py   # Tests de modelos
      test_services.py # Tests de servicios
      test_views.py    # Tests de vistas
```

---

## Pre-commit Hooks

Utilizamos **pre-commit** para ejecutar validaciones automaticas antes de cada commit.

### Instalacion

```bash
# Instalar hooks
pre-commit install

# Instalar hook para commit messages
pre-commit install --hook-type commit-msg
```

### Hooks Configurados

| Hook | Descripcion |
|------|-------------|
| `trailing-whitespace` | Elimina espacios al final de lineas |
| `end-of-file-fixer` | Asegura nueva linea al final |
| `check-yaml` | Valida sintaxis YAML |
| `check-json` | Valida sintaxis JSON |
| `check-toml` | Valida sintaxis TOML |
| `check-added-large-files` | Previene archivos > 1MB |
| `check-merge-conflict` | Detecta marcadores de conflicto |
| `detect-private-key` | Detecta claves privadas |
| `debug-statements` | Detecta debuggers olvidados |
| `ruff` | Linting Python |
| `ruff-format` | Formateo Python |
| `mypy` | Verificacion de tipos |
| `djlint-django` | Linting de templates Django |
| `bandit` | Analisis de seguridad |
| `django-upgrade` | Actualiza sintaxis Django |
| `commitizen` | Valida mensajes de commit |

### Ejecucion Manual

```bash
# Ejecutar todos los hooks en archivos staged
pre-commit run

# Ejecutar todos los hooks en todos los archivos
pre-commit run --all-files

# Ejecutar un hook especifico
pre-commit run ruff

# Actualizar versiones de hooks
pre-commit autoupdate
```

### Saltarse Hooks (Solo en Emergencias)

```bash
# NO recomendado - solo para emergencias
git commit --no-verify -m "fix: hotfix urgente"
```

---

## Recursos Adicionales

- [Django Documentation](https://docs.djangoproject.com/)
- [Django REST Framework](https://www.django-rest-framework.org/)
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [Pytest Documentation](https://docs.pytest.org/)
- [Conventional Commits](https://www.conventionalcommits.org/)

---

## Soporte

Si tienes preguntas sobre el proceso de contribucion, contacta al equipo de desarrollo:

- Email: desarrollo@sd-sas.com
- Canal Slack: #sd-lms-dev
