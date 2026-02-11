"""
Script to create sample courses and learning paths for SD LMS.
"""

import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django.setup()

from django.contrib.auth import get_user_model

from apps.courses.models import Category, Course, Lesson, Module
from apps.learning_paths.models import LearningPath, PathCourse

User = get_user_model()


def create_categories():
    """Create course categories."""
    categories = [
        {
            "name": "Seguridad Eléctrica",
            "slug": "seguridad-electrica",
            "description": "Cursos sobre seguridad en trabajos eléctricos de alto riesgo",
            "color": "#EF4444",
            "icon": "bolt",
        },
        {
            "name": "Trabajo en Alturas",
            "slug": "trabajo-alturas",
            "description": "Formación para trabajo seguro en alturas",
            "color": "#F59E0B",
            "icon": "arrow-up",
        },
        {
            "name": "Primeros Auxilios",
            "slug": "primeros-auxilios",
            "description": "Atención de emergencias y primeros auxilios",
            "color": "#10B981",
            "icon": "heart",
        },
        {
            "name": "Procedimientos Operativos",
            "slug": "procedimientos-operativos",
            "description": "Procedimientos y protocolos operativos",
            "color": "#3B82F6",
            "icon": "clipboard",
        },
        {
            "name": "Equipos y Herramientas",
            "slug": "equipos-herramientas",
            "description": "Uso y mantenimiento de equipos",
            "color": "#8B5CF6",
            "icon": "wrench",
        },
    ]

    created_categories = []
    for cat_data in categories:
        cat, created = Category.objects.get_or_create(slug=cat_data["slug"], defaults=cat_data)
        if created:
            print(f"✓ Categoría creada: {cat.name}")
        else:
            print(f"- Categoría existente: {cat.name}")
        created_categories.append(cat)

    return created_categories


def create_courses(admin_user, categories):
    """Create sample courses."""
    courses_data = [
        {
            "code": "SEG-001",
            "title": "Fundamentos de Seguridad Eléctrica",
            "description": "Introducción a los conceptos básicos de seguridad en trabajos eléctricos, incluyendo riesgos, normatividad y equipos de protección personal.",
            "objectives": "- Identificar los riesgos eléctricos más comunes\n- Conocer la normatividad vigente (RETIE)\n- Usar correctamente los EPP\n- Aplicar procedimientos seguros de trabajo",
            "duration": 240,
            "course_type": "mandatory",
            # risk_level removed: "critical",
            "category": categories[0],
            "target_profiles": ["LINIERO", "JEFE_CUADRILLA", "TECNICO"],
            "validity_months": 12,
        },
        {
            "code": "SEG-002",
            "title": "Trabajo Seguro en Líneas Energizadas",
            "description": "Técnicas y procedimientos para trabajo en líneas de transmisión energizadas, incluyendo uso de pértiga y equipos especializados.",
            "objectives": "- Aplicar técnicas de trabajo en caliente\n- Usar correctamente pértiga y herramientas aisladas\n- Implementar procedimientos de bloqueo y señalización\n- Gestionar emergencias en líneas energizadas",
            "duration": 360,
            "course_type": "mandatory",
            # risk_level removed: "critical",
            "category": categories[0],
            "target_profiles": ["LINIERO", "JEFE_CUADRILLA"],
            "validity_months": 12,
        },
        {
            "code": "ALT-001",
            "title": "Trabajo en Alturas - Nivel Básico",
            "description": "Capacitación básica para trabajo seguro en alturas, uso de arnés, líneas de vida y técnicas de ascenso/descenso.",
            "objectives": "- Identificar riesgos del trabajo en alturas\n- Usar correctamente arnés y equipos anticaídas\n- Realizar inspección de equipos\n- Aplicar técnicas de rescate básicas",
            "duration": 480,
            "course_type": "mandatory",
            # risk_level removed: "high",
            "category": categories[1],
            "target_profiles": ["LINIERO", "JEFE_CUADRILLA", "TECNICO"],
            "validity_months": 24,
        },
        {
            "code": "ALT-002",
            "title": "Trabajo en Alturas - Nivel Avanzado",
            "description": "Técnicas avanzadas de trabajo en alturas para torres de transmisión, incluyendo rescate y situaciones de emergencia.",
            "objectives": "- Realizar trabajos complejos en torres\n- Ejecutar maniobras de rescate\n- Coordinar equipos de trabajo en altura\n- Gestionar situaciones de emergencia",
            "duration": 600,
            "course_type": "mandatory",
            # risk_level removed: "critical",
            "category": categories[1],
            "target_profiles": ["LINIERO", "JEFE_CUADRILLA"],
            "validity_months": 24,
        },
        {
            "code": "PRI-001",
            "title": "Primeros Auxilios Básicos",
            "description": "Atención inicial de emergencias médicas en campo, RCP, manejo de heridas y quemaduras.",
            "objectives": "- Evaluar signos vitales\n- Realizar RCP básico\n- Atender heridas y hemorragias\n- Manejar quemaduras eléctricas",
            "duration": 240,
            "course_type": "mandatory",
            # risk_level removed: "high",
            "category": categories[2],
            "target_profiles": ["LINIERO", "JEFE_CUADRILLA", "TECNICO", "COORDINADOR_HSEQ"],
            "validity_months": 24,
        },
        {
            "code": "PRO-001",
            "title": "Procedimientos Pre-Operacionales",
            "description": "Charlas de seguridad, análisis de riesgo, permisos de trabajo y comunicación efectiva en campo.",
            "objectives": "- Realizar análisis de riesgo ATS\n- Gestionar permisos de trabajo\n- Conducir charlas pre-operacionales\n- Implementar protocolos de comunicación",
            "duration": 180,
            "course_type": "mandatory",
            # risk_level removed: "medium",
            "category": categories[3],
            "target_profiles": ["JEFE_CUADRILLA", "COORDINADOR_HSEQ"],
            "validity_months": 12,
        },
        {
            "code": "EQU-001",
            "title": "Uso y Mantenimiento de Equipos de Protección",
            "description": "Selección, uso, inspección y mantenimiento de EPP para trabajo eléctrico de alto riesgo.",
            "objectives": "- Seleccionar EPP adecuado según el riesgo\n- Realizar inspección pre-uso\n- Mantener equipos en buen estado\n- Identificar criterios de descarte",
            "duration": 120,
            "course_type": "mandatory",
            # risk_level removed: "high",
            "category": categories[4],
            "target_profiles": ["LINIERO", "JEFE_CUADRILLA", "TECNICO"],
            "validity_months": 12,
        },
        {
            "code": "EQU-002",
            "title": "Herramientas Eléctricas Especializadas",
            "description": "Uso correcto de herramientas dieléctricas, pérstigas, detectores de tensión y equipos de medición.",
            "objectives": "- Usar herramientas dieléctricas correctamente\n- Operar pértigas telescópicas\n- Realizar mediciones de tensión\n- Mantener herramientas especializadas",
            "duration": 180,
            "course_type": "mandatory",
            # risk_level removed: "high",
            "category": categories[4],
            "target_profiles": ["LINIERO", "TECNICO"],
            "validity_months": 12,
        },
        {
            "code": "SEG-003",
            "title": "Cultura de Seguridad y Liderazgo",
            "description": "Desarrollo de cultura de seguridad, liderazgo en campo y toma de decisiones en situaciones de riesgo.",
            "objectives": "- Promover cultura de seguridad\n- Ejercer liderazgo positivo\n- Tomar decisiones bajo presión\n- Gestionar equipos de alto desempeño",
            "duration": 240,
            "course_type": "optional",
            # risk_level removed: "low",
            "category": categories[0],
            "target_profiles": ["JEFE_CUADRILLA", "INGENIERO_RESIDENTE", "COORDINADOR_HSEQ"],
            "validity_months": None,
        },
        {
            "code": "PRO-002",
            "title": "Gestión Ambiental en Campo",
            "description": "Manejo de residuos, protección ambiental y cumplimiento de normatividad ambiental en proyectos.",
            "objectives": "- Clasificar y disponer residuos\n- Prevenir contaminación\n- Cumplir normatividad ambiental\n- Implementar buenas prácticas",
            "duration": 120,
            "course_type": "optional",
            # risk_level removed: "low",
            "category": categories[3],
            "target_profiles": ["JEFE_CUADRILLA", "COORDINADOR_HSEQ"],
            "validity_months": None,
        },
    ]

    created_courses = []
    for course_data in courses_data:
        course, created = Course.objects.get_or_create(
            code=course_data["code"],
            defaults={
                **course_data,
                "created_by": admin_user,
                "status": "published",
            },
        )
        if created:
            print(f"✓ Curso creado: {course.code} - {course.title}")
            # Create sample modules and lessons
            create_sample_modules(course)
        else:
            print(f"- Curso existente: {course.code} - {course.title}")
        created_courses.append(course)

    return created_courses


def create_sample_modules(course):
    """Create sample modules and lessons for a course."""
    modules_data = [
        {
            "title": "Introducción",
            "description": "Conceptos básicos y fundamentos",
            "order": 1,
            "lessons": [
                {"title": "Bienvenida al curso", "duration": 10, "lesson_type": "video"},
                {"title": "Objetivos y alcance", "duration": 15, "lesson_type": "reading"},
            ],
        },
        {
            "title": "Contenido Principal",
            "description": "Desarrollo del contenido del curso",
            "order": 2,
            "lessons": [
                {"title": "Conceptos teóricos", "duration": 45, "lesson_type": "reading"},
                {"title": "Ejemplos prácticos", "duration": 60, "lesson_type": "video"},
                {"title": "Casos de estudio", "duration": 30, "lesson_type": "reading"},
            ],
        },
        {
            "title": "Evaluación",
            "description": "Verificación de conocimientos",
            "order": 3,
            "lessons": [
                {"title": "Repaso general", "duration": 20, "lesson_type": "reading"},
                {"title": "Examen final", "duration": 30, "lesson_type": "quiz"},
            ],
        },
    ]

    for module_data in modules_data:
        lessons = module_data.pop("lessons")
        module = Module.objects.create(course=course, **module_data)

        for i, lesson_data in enumerate(lessons, 1):
            Lesson.objects.create(module=module, order=i, **lesson_data)


def create_learning_paths(admin_user, courses):
    """Create sample learning paths."""
    # Find courses by code
    courses_dict = {course.code: course for course in courses}

    paths_data = [
        {
            "name": "Inducción Liniero - Nivel Básico",
            "description": "Ruta obligatoria para nuevos linieros. Incluye fundamentos de seguridad eléctrica, trabajo en alturas básico, primeros auxilios y uso de equipos de protección.",
            "target_profiles": ["LINIERO"],
            "is_mandatory": True,
            "estimated_duration": 30,
            "courses": ["SEG-001", "ALT-001", "PRI-001", "EQU-001"],
        },
        {
            "name": "Inducción Liniero - Nivel Avanzado",
            "description": "Formación avanzada para linieros con experiencia. Trabajo en líneas energizadas, alturas avanzadas y herramientas especializadas.",
            "target_profiles": ["LINIERO"],
            "is_mandatory": True,
            "estimated_duration": 45,
            "courses": ["SEG-002", "ALT-002", "EQU-002"],
        },
        {
            "name": "Formación Jefe de Cuadrilla",
            "description": "Ruta completa para jefes de cuadrilla. Incluye seguridad, liderazgo, procedimientos y gestión de equipos.",
            "target_profiles": ["JEFE_CUADRILLA"],
            "is_mandatory": True,
            "estimated_duration": 60,
            "courses": [
                "SEG-001",
                "SEG-002",
                "ALT-001",
                "ALT-002",
                "PRI-001",
                "PRO-001",
                "SEG-003",
            ],
        },
        {
            "name": "Certificación HSEQ",
            "description": "Formación para coordinadores de seguridad y salud ocupacional.",
            "target_profiles": ["COORDINADOR_HSEQ"],
            "is_mandatory": True,
            "estimated_duration": 40,
            "courses": ["SEG-001", "PRI-001", "PRO-001", "SEG-003", "PRO-002"],
        },
        {
            "name": "Refuerzo Anual - Personal de Campo",
            "description": "Actualización anual obligatoria para todo el personal de campo.",
            "target_profiles": ["LINIERO", "JEFE_CUADRILLA", "TECNICO"],
            "is_mandatory": True,
            "estimated_duration": 15,
            "courses": ["SEG-001", "EQU-001", "PRO-001"],
        },
    ]

    created_paths = []
    for path_data in paths_data:
        course_codes = path_data.pop("courses")

        path, created = LearningPath.objects.get_or_create(
            name=path_data["name"],
            defaults={
                **path_data,
                "created_by": admin_user,
                "status": "active",
            },
        )

        if created:
            print(f"✓ Ruta creada: {path.name}")

            # Add courses to path
            for order, course_code in enumerate(course_codes, 1):
                if course_code in courses_dict:
                    PathCourse.objects.create(
                        learning_path=path,
                        course=courses_dict[course_code],
                        order=order,
                        is_required=True,
                    )
        else:
            print(f"- Ruta existente: {path.name}")

        created_paths.append(path)

    return created_paths


def main():
    """Main function to create all sample data."""
    print("\n" + "=" * 60)
    print("Creando datos de ejemplo para SD LMS")
    print("=" * 60 + "\n")

    # Get admin user
    try:
        admin_user = User.objects.get(email="admin@sd-lms.com")
        print(f"✓ Usuario admin encontrado: {admin_user.email}\n")
    except User.DoesNotExist:
        print("✗ Error: No se encontró el usuario admin@sd-lms.com")
        print("  Por favor, cree el usuario admin primero.\n")
        return

    # Create categories
    print("Creando categorías...")
    categories = create_categories()
    print()

    # Create courses
    print("Creando cursos...")
    courses = create_courses(admin_user, categories)
    print()

    # Create learning paths
    print("Creando rutas de aprendizaje...")
    paths = create_learning_paths(admin_user, courses)
    print()

    print("=" * 60)
    print("Resumen:")
    print(f"  - {len(categories)} categorías")
    print(f"  - {len(courses)} cursos")
    print(f"  - {len(paths)} rutas de aprendizaje")
    print("=" * 60)
    print("\n✓ ¡Datos de ejemplo creados exitosamente!\n")


if __name__ == "__main__":
    main()
