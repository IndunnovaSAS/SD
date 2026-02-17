"""
Script to create sample data for SD LMS dashboard.
Usage: python create_sample_data.py
"""

import os
import random
from datetime import date, timedelta
from decimal import Decimal

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.dev")
django.setup()

from django.contrib.auth import get_user_model
from django.utils import timezone

from apps.assessments.models import Assessment, AssessmentAttempt
from apps.certifications.models import Certificate
from apps.courses.models import Category, Course, Enrollment, Lesson, Module
from apps.learning_paths.models import LearningPath, PathAssignment, PathCourse

User = get_user_model()


# ── helpers ──────────────────────────────────────────────────────────
def rand_date(days_back=90):
    """Random datetime within the last N days."""
    delta = timedelta(days=random.randint(1, days_back))
    return timezone.now() - delta


def rand_recent(days_back=30):
    return timezone.now() - timedelta(days=random.randint(0, days_back))


# ── 1. Categories ────────────────────────────────────────────────────
def create_categories():
    categories_data = [
        {"name": "Seguridad Electrica", "slug": "seguridad-electrica",
         "description": "Seguridad en trabajos electricos", "color": "#EF4444", "icon": "bolt"},
        {"name": "Trabajo en Alturas", "slug": "trabajo-alturas",
         "description": "Formacion para trabajo en alturas", "color": "#F59E0B", "icon": "arrow-up"},
        {"name": "Primeros Auxilios", "slug": "primeros-auxilios",
         "description": "Atencion de emergencias", "color": "#10B981", "icon": "heart"},
        {"name": "Procedimientos Operativos", "slug": "procedimientos-operativos",
         "description": "Procedimientos y protocolos", "color": "#3B82F6", "icon": "clipboard"},
        {"name": "Equipos y Herramientas", "slug": "equipos-herramientas",
         "description": "Uso y mantenimiento de equipos", "color": "#8B5CF6", "icon": "wrench"},
    ]
    result = []
    for d in categories_data:
        obj, created = Category.objects.get_or_create(slug=d["slug"], defaults=d)
        print(f"  {'+ Creada' if created else '= Existe'}: {obj.name}")
        result.append(obj)
    return result


# ── 2. Users ─────────────────────────────────────────────────────────
def create_users(admin_user):
    users_data = [
        {"first_name": "Carlos", "last_name": "Rodriguez", "document_number": "1001001001",
         "job_profile": "LINIERO", "job_position": "Liniero Senior"},
        {"first_name": "Maria", "last_name": "Lopez", "document_number": "1001001002",
         "job_profile": "LINIERO", "job_position": "Liniero"},
        {"first_name": "Juan", "last_name": "Martinez", "document_number": "1001001003",
         "job_profile": "JEFE_CUADRILLA", "job_position": "Jefe de Cuadrilla"},
        {"first_name": "Andrea", "last_name": "Garcia", "document_number": "1001001004",
         "job_profile": "TECNICO", "job_position": "Tecnico Electricista"},
        {"first_name": "Luis", "last_name": "Hernandez", "document_number": "1001001005",
         "job_profile": "COORDINADOR_HSEQ", "job_position": "Coordinador HSEQ"},
        {"first_name": "Diana", "last_name": "Torres", "document_number": "1001001006",
         "job_profile": "INGENIERO_RESIDENTE", "job_position": "Ingeniero Residente"},
        {"first_name": "Pedro", "last_name": "Sanchez", "document_number": "1001001007",
         "job_profile": "LINIERO", "job_position": "Liniero"},
        {"first_name": "Sofia", "last_name": "Ramirez", "document_number": "1001001008",
         "job_profile": "TECNICO", "job_position": "Tecnico de Campo"},
        {"first_name": "Diego", "last_name": "Castro", "document_number": "1001001009",
         "job_profile": "OPERADOR", "job_position": "Operador de Grua"},
        {"first_name": "Laura", "last_name": "Morales", "document_number": "1001001010",
         "job_profile": "JEFE_CUADRILLA", "job_position": "Jefe de Cuadrilla"},
        {"first_name": "Andres", "last_name": "Vargas", "document_number": "1001001011",
         "job_profile": "LINIERO", "job_position": "Liniero Aprendiz"},
        {"first_name": "Camila", "last_name": "Diaz", "document_number": "1001001012",
         "job_profile": "TECNICO", "job_position": "Tecnico de Subestaciones"},
    ]
    result = [admin_user]
    for d in users_data:
        email = f"{d['first_name'].lower()}.{d['last_name'].lower()}@sd.com"
        user, created = User.objects.get_or_create(
            document_number=d["document_number"],
            defaults={
                **d,
                "email": email,
                "hire_date": date.today() - timedelta(days=random.randint(90, 730)),
                "is_active": True,
            },
        )
        if created:
            user.set_password("Test1234!")
            user.save()
            print(f"  + Creado: {user.get_full_name()} ({user.job_profile})")
        else:
            print(f"  = Existe: {user.get_full_name()}")
        result.append(user)
    return result


# ── 3. Courses ───────────────────────────────────────────────────────
def create_courses(admin_user, categories):
    courses_data = [
        {"code": "SEG-001", "title": "Fundamentos de Seguridad Electrica",
         "description": "Conceptos basicos de seguridad en trabajos electricos.",
         "course_type": "mandatory", "category": categories[0], "validity_months": 12},
        {"code": "SEG-002", "title": "Trabajo Seguro en Lineas Energizadas",
         "description": "Tecnicas para trabajo en lineas de transmision energizadas.",
         "course_type": "mandatory", "category": categories[0], "validity_months": 12},
        {"code": "ALT-001", "title": "Trabajo en Alturas - Nivel Basico",
         "description": "Capacitacion basica para trabajo seguro en alturas.",
         "course_type": "mandatory", "category": categories[1], "validity_months": 24},
        {"code": "ALT-002", "title": "Trabajo en Alturas - Nivel Avanzado",
         "description": "Tecnicas avanzadas de trabajo en alturas.",
         "course_type": "mandatory", "category": categories[1], "validity_months": 24},
        {"code": "PRI-001", "title": "Primeros Auxilios Basicos",
         "description": "Atencion inicial de emergencias medicas en campo.",
         "course_type": "mandatory", "category": categories[2], "validity_months": 24},
        {"code": "PRO-001", "title": "Procedimientos Pre-Operacionales",
         "description": "Charlas de seguridad y permisos de trabajo.",
         "course_type": "mandatory", "category": categories[3], "validity_months": 12},
        {"code": "EQU-001", "title": "Uso y Mantenimiento de EPP",
         "description": "Seleccion y uso de equipos de proteccion personal.",
         "course_type": "mandatory", "category": categories[4], "validity_months": 12},
        {"code": "EQU-002", "title": "Herramientas Electricas Especializadas",
         "description": "Uso de herramientas dielectricas y detectores de tension.",
         "course_type": "mandatory", "category": categories[4], "validity_months": 12},
        {"code": "SEG-003", "title": "Cultura de Seguridad y Liderazgo",
         "description": "Desarrollo de cultura de seguridad y liderazgo.",
         "course_type": "optional", "category": categories[0], "validity_months": None},
        {"code": "PRO-002", "title": "Gestion Ambiental en Campo",
         "description": "Manejo de residuos y cumplimiento ambiental.",
         "course_type": "optional", "category": categories[3], "validity_months": None},
    ]
    result = []
    for d in courses_data:
        now = timezone.now()
        obj, created = Course.objects.get_or_create(
            code=d["code"],
            defaults={
                **d,
                "created_by": admin_user,
                "status": "published",
                "published_at": now - timedelta(days=random.randint(30, 180)),
                "target_profiles": ["LINIERO", "JEFE_CUADRILLA", "TECNICO"],
            },
        )
        if created:
            _create_modules(obj)
            print(f"  + Creado: {obj.code} - {obj.title}")
        else:
            print(f"  = Existe: {obj.code} - {obj.title}")
        result.append(obj)
    return result


def _create_modules(course):
    for i, (title, desc) in enumerate(
        [("Introduccion", "Conceptos basicos"), ("Contenido Principal", "Desarrollo del tema"),
         ("Evaluacion", "Verificacion de conocimientos")], 1
    ):
        m = Module.objects.create(course=course, title=title, description=desc, order=i)
        for j in range(1, random.randint(2, 4)):
            Lesson.objects.create(
                module=m, title=f"Leccion {j}", order=j,
                duration=random.choice([10, 15, 20, 30, 45]),
                lesson_type=random.choice(["video", "reading", "reading"]),
            )


# ── 4. Enrollments ───────────────────────────────────────────────────
def create_enrollments(users, courses):
    """Create diverse enrollments: completed, in_progress, enrolled, expired."""
    count = 0
    non_admin = [u for u in users if not u.is_superuser]

    for user in non_admin:
        # Each user enrolls in 4-7 random courses
        sample_courses = random.sample(courses, k=min(random.randint(4, 7), len(courses)))
        for course in sample_courses:
            if Enrollment.objects.filter(user=user, course=course).exists():
                continue

            # Weighted random status
            r = random.random()
            if r < 0.35:
                status = "completed"
                progress = Decimal("100.00")
                started = rand_date(90)
                completed_at = started + timedelta(days=random.randint(3, 30))
            elif r < 0.60:
                status = "in_progress"
                progress = Decimal(str(random.randint(15, 85)))
                started = rand_date(60)
                completed_at = None
            elif r < 0.80:
                status = "enrolled"
                progress = Decimal("0")
                started = None
                completed_at = None
            else:
                status = "expired"
                progress = Decimal(str(random.randint(0, 50)))
                started = rand_date(180)
                completed_at = None

            Enrollment.objects.create(
                user=user, course=course, status=status, progress=progress,
                started_at=started, completed_at=completed_at,
                created_at=rand_date(120),
            )
            count += 1

    print(f"  + {count} inscripciones creadas")
    return count


# ── 5. Assessments & Attempts ────────────────────────────────────────
def create_assessments(admin_user, courses):
    assessments = []
    for course in courses[:7]:  # assessments for first 7 courses
        obj, created = Assessment.objects.get_or_create(
            title=f"Evaluacion - {course.title[:40]}",
            defaults={
                "course": course,
                "created_by": admin_user,
                "assessment_type": random.choice(["quiz", "exam"]),
                "passing_score": random.choice([70, 75, 80]),
                "time_limit": random.choice([30, 45, 60]),
                "max_attempts": 3,
                "status": "published",
            },
        )
        if created:
            print(f"  + Evaluacion: {obj.title[:50]}")
        assessments.append(obj)
    return assessments


def create_attempts(users, assessments):
    count = 0
    non_admin = [u for u in users if not u.is_superuser]

    for assessment in assessments:
        # 6-10 users attempt each assessment
        sample_users = random.sample(non_admin, k=min(random.randint(6, 10), len(non_admin)))
        for user in sample_users:
            if AssessmentAttempt.objects.filter(user=user, assessment=assessment).exists():
                continue

            score = Decimal(str(random.randint(45, 100)))
            passed = score >= assessment.passing_score
            started = rand_date(60)

            AssessmentAttempt.objects.create(
                user=user,
                assessment=assessment,
                status="graded",
                attempt_number=1,
                score=score,
                passed=passed,
                time_spent=random.randint(600, 3600),
                started_at=started,
                submitted_at=started + timedelta(minutes=random.randint(15, 55)),
                graded_at=started + timedelta(minutes=random.randint(56, 120)),
            )
            count += 1

    print(f"  + {count} intentos de evaluacion creados")
    return count


# ── 6. Certificates ──────────────────────────────────────────────────
def create_certificates(users, courses):
    count = 0
    completed = Enrollment.objects.filter(status="completed").select_related("user", "course")

    for enrollment in completed:
        if Certificate.objects.filter(user=enrollment.user, course=enrollment.course).exists():
            continue

        # 70% of completions get a certificate
        if random.random() > 0.70:
            continue

        issued_at = enrollment.completed_at or rand_date(60)
        validity = enrollment.course.validity_months
        if validity:
            expires_at = issued_at + timedelta(days=validity * 30)
        else:
            expires_at = None

        cert_num = f"SD-{enrollment.course.code}-{enrollment.user.id:04d}-{random.randint(1000, 9999)}"

        # Some certificates expire in the next 30 days (for dashboard widget)
        if count < 4 and expires_at:
            expires_at = timezone.now() + timedelta(days=random.randint(3, 25))

        Certificate.objects.create(
            user=enrollment.user,
            course=enrollment.course,
            certificate_number=cert_num,
            status="issued",
            score=enrollment.progress,
            issued_at=issued_at,
            expires_at=expires_at,
        )
        count += 1

    print(f"  + {count} certificados creados")
    return count


# ── 7. Learning Paths & Assignments ─────────────────────────────────
def create_learning_paths(admin_user, courses):
    courses_dict = {c.code: c for c in courses}
    paths_data = [
        {"name": "Induccion Liniero Basico", "description": "Ruta obligatoria para nuevos linieros.",
         "target_profiles": ["LINIERO"], "is_mandatory": True, "estimated_duration": 30,
         "codes": ["SEG-001", "ALT-001", "PRI-001", "EQU-001"]},
        {"name": "Formacion Jefe de Cuadrilla", "description": "Ruta completa para jefes de cuadrilla.",
         "target_profiles": ["JEFE_CUADRILLA"], "is_mandatory": True, "estimated_duration": 60,
         "codes": ["SEG-001", "SEG-002", "ALT-001", "ALT-002", "PRI-001", "PRO-001"]},
        {"name": "Certificacion HSEQ", "description": "Formacion para coordinadores HSEQ.",
         "target_profiles": ["COORDINADOR_HSEQ"], "is_mandatory": True, "estimated_duration": 40,
         "codes": ["SEG-001", "PRI-001", "PRO-001", "SEG-003", "PRO-002"]},
    ]
    result = []
    for d in paths_data:
        codes = d.pop("codes")
        obj, created = LearningPath.objects.get_or_create(
            name=d["name"],
            defaults={**d, "created_by": admin_user, "status": "active"},
        )
        if created:
            for i, code in enumerate(codes, 1):
                if code in courses_dict:
                    PathCourse.objects.create(
                        learning_path=obj, course=courses_dict[code], order=i, is_required=True)
            print(f"  + Ruta: {obj.name}")
        else:
            print(f"  = Existe: {obj.name}")
        result.append(obj)
    return result


def create_assignments(users, paths):
    count = 0
    non_admin = [u for u in users if not u.is_superuser]

    for path in paths:
        sample_users = random.sample(non_admin, k=min(random.randint(4, 8), len(non_admin)))
        for user in sample_users:
            if PathAssignment.objects.filter(user=user, learning_path=path).exists():
                continue

            r = random.random()
            if r < 0.3:
                status = "completed"
                progress = Decimal("100")
                due = date.today() + timedelta(days=random.randint(10, 60))
            elif r < 0.5:
                status = "in_progress"
                progress = Decimal(str(random.randint(20, 70)))
                due = date.today() + timedelta(days=random.randint(5, 45))
            elif r < 0.7:
                status = "assigned"
                progress = Decimal("0")
                due = date.today() + timedelta(days=random.randint(15, 60))
            else:
                # Overdue assignments for the dashboard widget
                status = random.choice(["assigned", "in_progress"])
                progress = Decimal(str(random.randint(0, 40)))
                due = date.today() - timedelta(days=random.randint(3, 30))

            PathAssignment.objects.create(
                user=user, learning_path=path, status=status,
                progress=progress, due_date=due,
                assigned_by=users[0],  # admin
            )
            count += 1

    print(f"  + {count} asignaciones creadas")
    return count


# ── main ─────────────────────────────────────────────────────────────
def main():
    """Main function to create all sample data."""
    print("\n" + "=" * 60)
    print("  SD LMS - Creando datos de ejemplo para dashboard")
    print("=" * 60)

    # Get or create admin user
    admin_user = User.objects.filter(is_superuser=True).first()
    if not admin_user:
        print("\nNo se encontro superusuario. Creando uno...")
        admin_user = User.objects.create_superuser(
            email="admin@sd.com", username="admin@sd.com", password="admin",
            first_name="Admin", last_name="SD",
            document_number="0000000000", hire_date=date.today(),
        )
    print(f"\nAdmin: {admin_user.email}")

    print("\n[1/7] Categorias...")
    categories = create_categories()

    print("\n[2/7] Usuarios...")
    users = create_users(admin_user)

    print("\n[3/7] Cursos...")
    courses = create_courses(admin_user, categories)

    print("\n[4/7] Inscripciones...")
    create_enrollments(users, courses)

    print("\n[5/7] Evaluaciones...")
    assessments = create_assessments(admin_user, courses)

    print("\n[6/7] Intentos de evaluacion...")
    create_attempts(users, assessments)

    print("\n[7/7] Certificados, Rutas y Asignaciones...")
    create_certificates(users, courses)
    paths = create_learning_paths(admin_user, courses)
    create_assignments(users, paths)

    # Summary
    print("\n" + "=" * 60)
    print("  Resumen:")
    print(f"    Categorias:    {Category.objects.count()}")
    print(f"    Usuarios:      {User.objects.count()}")
    print(f"    Cursos:        {Course.objects.count()}")
    print(f"    Inscripciones: {Enrollment.objects.count()}")
    print(f"    Evaluaciones:  {Assessment.objects.count()}")
    print(f"    Intentos:      {AssessmentAttempt.objects.count()}")
    print(f"    Certificados:  {Certificate.objects.count()}")
    print(f"    Rutas:         {LearningPath.objects.count()}")
    print(f"    Asignaciones:  {PathAssignment.objects.count()}")
    print("=" * 60)
    print("\n  Datos creados exitosamente!")
    print("  Recarga http://127.0.0.1:8000/accounts/ para ver el dashboard\n")


if __name__ == "__main__":
    main()
