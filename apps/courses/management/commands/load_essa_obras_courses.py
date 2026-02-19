"""
Management command to load ESSA OBRAS courses from the training plan.
FT-HSEQ-120_PC_V06_MANTENIMIENTO_ESSA_OBRAS.xlsx

Usage:
    python manage.py load_essa_obras_courses
    python manage.py load_essa_obras_courses --publish
    python manage.py load_essa_obras_courses --dry-run
"""

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.courses.models import Category, Course, Lesson, Module

# All profiles for "Todos los trabajadores"
ALL_PROFILES = [
    "LINIERO",
    "TECNICO",
    "OPERADOR",
    "JEFE_CUADRILLA",
    "INGENIERO_RESIDENTE",
    "COORDINADOR_HSEQ",
    "ADMINISTRADOR",
]

# Operative profiles for "todos los operativos"
OPERATIVE_PROFILES = [
    "LINIERO",
    "TECNICO",
    "OPERADOR",
    "JEFE_CUADRILLA",
]

CATEGORIES = [
    {
        "name": "Inducción y Reinducción",
        "slug": "induccion-reinduccion",
        "icon": "fas fa-user-plus",
        "color": "#3B82F6",
    },
    {
        "name": "Plan de Emergencias",
        "slug": "plan-emergencias",
        "icon": "fas fa-first-aid",
        "color": "#EF4444",
    },
    {
        "name": "Requisitos Legales SST",
        "slug": "requisitos-legales-sst",
        "icon": "fas fa-gavel",
        "color": "#8B5CF6",
    },
    {
        "name": "Identificación de Peligros y Riesgos",
        "slug": "identificacion-peligros-riesgos",
        "icon": "fas fa-exclamation-triangle",
        "color": "#F59E0B",
    },
    {
        "name": "Promoción y Prevención",
        "slug": "promocion-prevencion",
        "icon": "fas fa-shield-alt",
        "color": "#10B981",
    },
    {
        "name": "Gestión del Riesgo Eléctrico",
        "slug": "gestion-riesgo-electrico",
        "icon": "fas fa-bolt",
        "color": "#F97316",
    },
    {
        "name": "Riesgo Biomecánico y Osteomuscular",
        "slug": "riesgo-biomecanico-osteomuscular",
        "icon": "fas fa-running",
        "color": "#06B6D4",
    },
    {
        "name": "Investigación de Accidentes e Incidentes",
        "slug": "investigacion-accidentes",
        "icon": "fas fa-search",
        "color": "#EC4899",
    },
    {
        "name": "Inspecciones y Señalización",
        "slug": "inspecciones-senalizacion",
        "icon": "fas fa-clipboard-check",
        "color": "#14B8A6",
    },
    {
        "name": "Riesgo Psicosocial y Habilidades Blandas",
        "slug": "riesgo-psicosocial",
        "icon": "fas fa-brain",
        "color": "#A855F7",
    },
    {
        "name": "Riesgo Sociopolítico",
        "slug": "riesgo-sociopolitico",
        "icon": "fas fa-shield-virus",
        "color": "#64748B",
    },
    {
        "name": "Estilos de Vida Saludable",
        "slug": "estilos-vida-saludable",
        "icon": "fas fa-heartbeat",
        "color": "#F43F5E",
    },
    {
        "name": "Riesgo Mecánico",
        "slug": "riesgo-mecanico",
        "icon": "fas fa-cogs",
        "color": "#78716C",
    },
    {
        "name": "Riesgo Biológico",
        "slug": "riesgo-biologico",
        "icon": "fas fa-biohazard",
        "color": "#84CC16",
    },
    {
        "name": "Riesgo Auditivo y Ruido",
        "slug": "riesgo-auditivo-ruido",
        "icon": "fas fa-volume-up",
        "color": "#0EA5E9",
    },
    {
        "name": "Riesgo Locativo",
        "slug": "riesgo-locativo",
        "icon": "fas fa-hard-hat",
        "color": "#D97706",
    },
    {
        "name": "Seguridad Vial",
        "slug": "seguridad-vial",
        "icon": "fas fa-car",
        "color": "#2563EB",
    },
    {
        "name": "Riesgo Químico",
        "slug": "riesgo-quimico",
        "icon": "fas fa-flask",
        "color": "#7C3AED",
    },
    {
        "name": "Calidad ISO 9001",
        "slug": "calidad-iso-9001",
        "icon": "fas fa-certificate",
        "color": "#0D9488",
    },
    {
        "name": "Obras Civiles y Excavaciones",
        "slug": "obras-civiles-excavaciones",
        "icon": "fas fa-hard-hat",
        "color": "#B45309",
    },
    {
        "name": "Intervención de Vegetación",
        "slug": "intervencion-vegetacion",
        "icon": "fas fa-tree",
        "color": "#16A34A",
    },
]

COURSES = [
    {
        "code": "ESSA-OBR-001",
        "title": "Inducción/Reinducción SD SAS",
        "description": (
            "Divulgar al personal nuevo y antiguo los siguientes temas: "
            "general de la empresa, calidad, seguridad y salud en el trabajo, "
            "gestión ambiental, de acuerdo al cargo y otros temas."
        ),
        "objectives": (
            "- Conocer las políticas, objetivos y lineamientos del SG-SST y su aplicación en SD SAS.\n"
            "- Identificar los riesgos generales presentes en la empresa.\n"
            "- Reconocer los riesgos eléctricos asociados a sus funciones.\n"
            "- Identificar los riesgos específicos en actividades de poda, tala e intervención de vegetación.\n"
            "- Aplicar las acciones preventivas del SG-SST.\n"
            "- Reconocer sus derechos, deberes y responsabilidades frente a la SST.\n"
            "- Identificar y aplicar los procedimientos de trabajo seguro.\n"
            "- Conocer los mecanismos de reporte de accidentes, incidentes, actos y condiciones inseguras.\n"
            "- Identificar las rutas de evacuación, puntos de encuentro y roles en el plan de emergencias.\n"
            "- Aplicar prácticas de autocuidado y comportamiento seguro.\n"
            "- Fortalecer la cultura de prevención."
        ),
        "category_slug": "induccion-reinduccion",
        "duration_hours": 4,
        "methodology": "Magistral interactiva con el trabajador",
        "evaluation": "Evaluación Oral y Escrita con calificación",
        "target_profiles": ALL_PROFILES,
        "responsible": "COORDINADOR HSEQ",
    },
    {
        "code": "ESSA-OBR-002",
        "title": "Plan de Atención de Emergencias",
        "description": (
            "Capacitar a los trabajadores y contratistas en la identificación de amenazas, "
            "procedimientos y acciones a seguir frente a situaciones de emergencia, con el fin de "
            "prevenir lesiones, minimizar daños a las personas, instalaciones y al medio ambiente."
        ),
        "objectives": (
            "- Actuar de manera segura y ordenada frente a una emergencia.\n"
            "- Conocer su rol dentro del Plan de Atención de Emergencias.\n"
            "- Utilizar correctamente rutas de evacuación y equipos básicos.\n"
            "- Contribuir a una respuesta efectiva, reduciendo riesgos y consecuencias."
        ),
        "category_slug": "plan-emergencias",
        "duration_hours": 2,
        "methodology": "Teórico-Práctica",
        "evaluation": "Evaluación escrita y/o Taller",
        "target_profiles": OPERATIVE_PROFILES,
        "responsible": "COORDINADOR HSEQ",
    },
    {
        "code": "ESSA-OBR-003",
        "title": "Tema 1. Fundamentos de la Seguridad y Salud en el Trabajo",
        "description": (
            "Capacitar y fortalecer los conocimientos del personal en los fundamentos de la SST, "
            "con el fin de prevenir accidentes laborales y enfermedades de origen laboral, "
            "garantizar el cumplimiento del marco legal vigente, promover el respeto por los "
            "derechos y responsabilidades, y resaltar la importancia del correcto diligenciamiento "
            "de la documentación del SG-SST."
        ),
        "objectives": (
            "- Fortalecer conocimientos en los conceptos básicos de SST.\n"
            "- Reconocer el marco legal aplicable en SST, incluyendo ISO 45001.\n"
            "- Identificar los derechos y responsabilidades del trabajador y del empleador.\n"
            "- Comprender la importancia del correcto diligenciamiento de la documentación del SG-SST.\n"
            "- Promover conductas seguras y una cultura de autocuidado y prevención."
        ),
        "category_slug": "requisitos-legales-sst",
        "duration_hours": 2,
        "methodology": "Magistral interactiva con el trabajador",
        "evaluation": "Evaluación escrita y/o Taller",
        "target_profiles": OPERATIVE_PROFILES,
        "responsible": "COORDINADOR HSEQ",
    },
    {
        "code": "ESSA-OBR-004",
        "title": "Tema 2. Identificación de Peligros y Evaluación de Riesgos (IPER)",
        "description": (
            "Capacitar y fortalecer los conocimientos en la Identificación de Peligros y "
            "Evaluación de Riesgos (IPER), con el fin de reconocer los peligros presentes en "
            "las actividades del proyecto, evaluar los riesgos asociados y aplicar medidas de "
            "control eficaces."
        ),
        "objectives": (
            "- Identificar los tipos de peligros presentes en el proyecto.\n"
            "- Reconocer los peligros críticos y prioritarios en el sector eléctrico y construcción.\n"
            "- Comprender los métodos para identificar peligros en campo.\n"
            "- Aplicar criterios básicos para evaluar riesgos (probabilidad, consecuencia y nivel).\n"
            "- Identificar y establecer controles siguiendo la jerarquía de control."
        ),
        "category_slug": "identificacion-peligros-riesgos",
        "duration_hours": 2,
        "methodology": "Teórico-Práctica",
        "evaluation": "Evaluación escrita y/o Taller",
        "target_profiles": OPERATIVE_PROFILES,
        "responsible": "COORDINADOR HSEQ",
    },
    {
        "code": "ESSA-OBR-005",
        "title": "Tema 5. Reporte de Accidentes e Incidentes de Trabajo",
        "description": (
            "Capacitar y fortalecer los conocimientos sobre el reporte oportuno de accidentes "
            "e incidentes de trabajo, con el fin de prevenir la repetición de eventos, mejorar "
            "las condiciones de seguridad, cumplir con los requisitos legales y promover la "
            "participación activa de los trabajadores en la investigación."
        ),
        "objectives": (
            "- Comprender qué es un accidente de trabajo y qué es un incidente.\n"
            "- Reconocer la importancia del reporte inmediato.\n"
            "- Conocer el tiempo de reporte por parte del trabajador (inmediato).\n"
            "- Identificar el rol y la participación del trabajador en la investigación.\n"
            "- Fortalecer la cultura de prevención, autocuidado y reporte oportuno."
        ),
        "category_slug": "investigacion-accidentes",
        "duration_hours": 2,
        "methodology": "Teórica",
        "evaluation": "Evaluación escrita y/o Taller",
        "target_profiles": OPERATIVE_PROFILES,
        "responsible": "COORDINADOR HSEQ",
    },
    {
        "code": "ESSA-OBR-006",
        "title": "Tema 3. Técnicas de Observación y Reporte de Actos y Condiciones Inseguras",
        "description": (
            "Capacitar y fortalecer los conocimientos del personal en las técnicas de observación "
            "y reporte de actos y condiciones inseguras, con el fin de identificar oportunamente "
            "situaciones de riesgo, comunicarlas de manera efectiva y registrar correctamente la "
            "información."
        ),
        "objectives": (
            "- Fortalecer conocimientos en los métodos para observar actos y condiciones inseguras.\n"
            "- Aplicar técnicas de comunicación efectiva para reportar de forma clara y oportuna.\n"
            "- Utilizar adecuadamente el formato de registro de observación.\n"
            "- Promover una cultura de prevención, autocuidado y reporte oportuno."
        ),
        "category_slug": "promocion-prevencion",
        "duration_hours": 2,
        "methodology": "Teórico-Práctica",
        "evaluation": "Evaluación escrita y/o Taller",
        "target_profiles": OPERATIVE_PROFILES,
        "responsible": "COORDINADOR HSEQ",
    },
    {
        "code": "ESSA-OBR-007",
        "title": "Seguridad Eléctrica: Identificación de Riesgos, Medidas de Control y Roles",
        "description": (
            "Capacitar y fortalecer los conocimientos proporcionando herramientas para la "
            "identificación de riesgos eléctricos, resaltando la importancia del cumplimiento "
            "de las Reglas de Oro, el respeto de las distancias mínimas de seguridad, y el uso "
            "adecuado de equipos de control para garantizar la ejecución segura en AT, MT y BT."
        ),
        "objectives": (
            "- Identificar los riesgos eléctricos asociados a trabajos en AT, MT y BT.\n"
            "- Comprender y aplicar las Reglas de Oro de la Seguridad Eléctrica.\n"
            "- Reconocer la importancia de mantener distancias de seguridad mínimas.\n"
            "- Utilizar adecuadamente los equipos de control del riesgo eléctrico.\n"
            "- Aplicar medidas de control generales según tipo de personal.\n"
            "- Diferenciar roles y responsabilidades del personal especialista y NO especialista.\n"
            "- Realizar inspección de áreas de trabajo.\n"
            "- Reconocer y respetar las distancias de seguridad."
        ),
        "category_slug": "gestion-riesgo-electrico",
        "duration_hours": 2,
        "methodology": "Teórico-Práctica",
        "evaluation": "Evaluación escrita y/o Taller",
        "target_profiles": OPERATIVE_PROFILES,
        "responsible": "COORDINADOR HSEQ",
    },
    {
        "code": "ESSA-OBR-008",
        "title": "Intervención de Vegetación: Identificación de Peligros, Controles y Planeación Segura",
        "description": (
            "Capacitar y fortalecer los conocimientos para la identificación de peligros, "
            "aplicación de controles y planeación segura en actividades de intervención y "
            "mantenimiento de vegetación, garantizando la ejecución segura de los trabajos "
            "asociados a obras en proximidad a redes eléctricas."
        ),
        "objectives": (
            "- Reconocer los peligros asociados a la intervención de vegetación.\n"
            "- Aplicar medidas de control adecuadas.\n"
            "- Planear de manera segura las tareas de mantenimiento.\n"
            "- Fortalecer la cultura de seguridad en el equipo de trabajo.\n"
            "- Garantizar el cumplimiento de los procedimientos y normativas vigentes.\n"
            "- Desarrollar habilidades para la toma de decisiones seguras."
        ),
        "category_slug": "intervencion-vegetacion",
        "duration_hours": 2,
        "methodology": "Teórico-Práctica",
        "evaluation": "Evaluación escrita y/o Taller",
        "target_profiles": OPERATIVE_PROFILES,
        "responsible": "COORDINADOR HSEQ",
    },
    {
        "code": "ESSA-OBR-009",
        "title": "Manipulación y Transporte de Cargas, Posturas y Trabajo Repetitivo",
        "description": (
            "Capacitar y fortalecer los conocimientos, brindando herramientas prácticas para "
            "conocer y aplicar técnicas seguras en la manipulación y transporte de cargas, "
            "así como medidas preventivas frente a posturas forzadas y trabajos repetitivos, "
            "con el fin de prevenir y controlar los trastornos osteomusculares."
        ),
        "objectives": (
            "- Reconocer los riesgos ergonómicos presentes en el sector eléctrico y construcción.\n"
            "- Aplicar técnicas seguras de manipulación y transporte de cargas.\n"
            "- Implementar medidas preventivas frente a posturas forzadas.\n"
            "- Identificar los riesgos asociados al trabajo repetitivo.\n"
            "- Prevenir trastornos osteomusculares mediante buenas prácticas ergonómicas."
        ),
        "category_slug": "riesgo-biomecanico-osteomuscular",
        "duration_hours": 2,
        "methodology": "Teórico-Práctica",
        "evaluation": "Evaluación escrita y/o Taller",
        "target_profiles": OPERATIVE_PROFILES,
        "responsible": "COORDINADOR HSEQ",
    },
    {
        "code": "ESSA-OBR-010",
        "title": "Reporte de Accidentes, Incidentes y Lineamientos para su Investigación",
        "description": (
            "Capacitar y fortalecer los conocimientos sobre los lineamientos para el reporte "
            "e investigación de accidentes, incidentes y actos inseguros, asegurando el "
            "cumplimiento de la Resolución 1401 de 2007 y del procedimiento interno PR-HSEQ-05."
        ),
        "objectives": (
            "- Fortalecer conocimientos en los lineamientos para el reporte.\n"
            "- Conocer y aplicar los requisitos de la Resolución 1401 de 2007.\n"
            "- Aplicar correctamente el procedimiento PR-HSEQ-05.\n"
            "- Reconocer la importancia del reporte oportuno e inmediato.\n"
            "- Participar activamente en el proceso de investigación."
        ),
        "category_slug": "investigacion-accidentes",
        "duration_hours": 2,
        "methodology": "Magistral interactiva con el trabajador",
        "evaluation": "Evaluación escrita con calificación",
        "target_profiles": ALL_PROFILES,
        "responsible": "ARL SURA/COORDINADOR HSEQ",
    },
    {
        "code": "ESSA-OBR-011",
        "title": "Seguridad Eléctrica: Distancias de Seguridad, Técnica de Trabajo y Trabajo en Proximidad",
        "description": (
            "Capacitar y fortalecer los conocimientos en seguridad eléctrica, mediante la "
            "planeación y aplicación de distancias de seguridad, el uso de técnicas de trabajo "
            "seguro y la identificación de riesgos en actividades realizadas en proximidad "
            "a redes eléctricas."
        ),
        "objectives": (
            "- Fortalecer conocimientos en la planeación y aplicación de distancias de seguridad.\n"
            "- Aplicar técnicas de trabajo seguro en actividades eléctricas.\n"
            "- Identificar los peligros eléctricos presentes en trabajos en proximidad a redes.\n"
            "- Evaluar y valorar los riesgos asociados al trabajo en proximidad.\n"
            "- Aplicar controles efectivos que reduzcan la probabilidad de contacto eléctrico."
        ),
        "category_slug": "gestion-riesgo-electrico",
        "duration_hours": 2,
        "methodology": "Teórico-Práctica",
        "evaluation": "Evaluación escrita y/o Taller",
        "target_profiles": OPERATIVE_PROFILES,
        "responsible": "COORDINADOR HSEQ",
    },
    {
        "code": "ESSA-OBR-012",
        "title": "Señalización, Tipos de Señalización e Inspecciones",
        "description": (
            "Proporcionar a los trabajadores los conocimientos básicos y prácticos sobre "
            "señalización de seguridad y la realización de inspecciones de seguridad, que les "
            "permitan identificar los riesgos, utilizar correctamente los formatos de inspección, "
            "y apoyar la implementación efectiva de las medidas de control."
        ),
        "objectives": (
            "- Reconocer la importancia de la señalización como medida preventiva.\n"
            "- Identificar los tipos de señalización de seguridad y su correcta aplicación.\n"
            "- Comprender qué es una inspección de seguridad.\n"
            "- Aplicar correctamente los formatos de inspección.\n"
            "- Identificar actos y condiciones inseguras durante las inspecciones.\n"
            "- Contribuir activamente en la propuesta y seguimiento de medidas de control."
        ),
        "category_slug": "inspecciones-senalizacion",
        "duration_hours": 2,
        "methodology": "Magistral interactiva con el trabajador",
        "evaluation": "Evaluación escrita con calificación",
        "target_profiles": ALL_PROFILES,
        "responsible": "ARL SURA/COORDINADOR HSEQ",
    },
    {
        "code": "ESSA-OBR-013",
        "title": "Habilidades Blandas: ¿Líderes o Jefes?",
        "description": (
            "Capacitar y fortalecer los conocimientos del personal en habilidades blandas "
            "asociadas al liderazgo, sensibilizando sobre la importancia de los estilos de "
            "mando y los tipos de liderazgo, con el fin de fortalecer las habilidades del "
            "equipo de trabajo que influyen en la seguridad y salud en el trabajo."
        ),
        "objectives": (
            "- Sensibilizar al personal acerca de la diferencia entre jefe y líder.\n"
            "- Reconocer los conceptos básicos de liderazgo.\n"
            "- Identificar los diferentes tipos de liderazgo y su impacto.\n"
            "- Comprender el proceso de liderazgo y su relación con la cultura de seguridad.\n"
            "- Identificar conductas del anti-líder y sus consecuencias.\n"
            "- Brindar recomendaciones prácticas para fortalecer un liderazgo positivo."
        ),
        "category_slug": "riesgo-psicosocial",
        "duration_hours": 2,
        "methodology": "Magistral interactiva con el trabajador",
        "evaluation": "Evaluación escrita y/o Taller",
        "target_profiles": OPERATIVE_PROFILES,
        "responsible": "COORDINADOR HSEQ",
    },
    {
        "code": "ESSA-OBR-014",
        "title": "Liderazgo Inspirador: Empoderamiento y Comportamientos Seguros",
        "description": (
            "Capacitar y fortalecer los conocimientos del personal en liderazgo inspirador "
            "o transformacional, brindando herramientas que permitan incentivar cambios de "
            "comportamiento orientados a la ejecución de actividades seguras y a la generación "
            "de ambientes de trabajo saludables."
        ),
        "objectives": (
            "- Dar a conocer el concepto de liderazgo inspirador y transformacional.\n"
            "- Fortalecer las capacidades de liderazgo para influir en comportamientos seguros.\n"
            "- Promover el empoderamiento del personal como estrategia de prevención.\n"
            "- Reconocer la relación entre liderazgo, cultura de seguridad y ambientes saludables.\n"
            "- Brindar herramientas prácticas para generar cambios positivos."
        ),
        "category_slug": "riesgo-psicosocial",
        "duration_hours": 2,
        "methodology": "Magistral interactiva con el trabajador",
        "evaluation": "Evaluación escrita y/o Taller",
        "target_profiles": OPERATIVE_PROFILES,
        "responsible": "COORDINADOR HSEQ",
    },
    {
        "code": "ESSA-OBR-015",
        "title": "Riesgo Sociopolítico",
        "description": (
            "Capacitar y fortalecer los conocimientos del personal sobre los riesgos "
            "sociopolíticos presentes en el entorno laboral, dando a conocer las principales "
            "amenazas y las medidas de seguridad ante situaciones como artefactos explosivos, "
            "conflicto armado, secuestro, extorsión, hurto calificado u otros eventos asociados."
        ),
        "objectives": (
            "- Dar a conocer el concepto de riesgo sociopolítico y su impacto.\n"
            "- Identificar los principales riesgos sociopolíticos del sector eléctrico.\n"
            "- Sensibilizar sobre medidas preventivas y de autoprotección.\n"
            "- Brindar lineamientos de actuación ante artefactos explosivos.\n"
            "- Fortalecer la capacidad de reacción ante conflicto social, secuestro y extorsión."
        ),
        "category_slug": "riesgo-sociopolitico",
        "duration_hours": 2,
        "methodology": "Magistral interactiva con el trabajador",
        "evaluation": "Evaluación escrita con calificación",
        "target_profiles": ALL_PROFILES,
        "responsible": "ARL SURA/COORDINADOR HSEQ",
    },
    {
        "code": "ESSA-OBR-016",
        "title": "Trabajo Seguro en Obras Civiles (incluye Excavación)",
        "description": (
            "Fortalecer en los trabajadores prácticas seguras en la ejecución de actividades "
            "de obra civil con el fin de que puedan identificar riesgos, peligros y controles "
            "establecidos, uso correcto de EPP, uso seguro de herramientas y equipos."
        ),
        "objectives": (
            "- Reconocer los peligros y riesgos críticos asociados a excavaciones y obras civiles.\n"
            "- Aplicar medidas de control para prevenir derrumbes, atrapamientos y caídas.\n"
            "- Interpretar y cumplir los procedimientos de trabajo seguro.\n"
            "- Utilizar correctamente los EPP requeridos para cada actividad.\n"
            "- Identificar condiciones inseguras del terreno.\n"
            "- Garantizar el uso seguro de maquinaria y herramientas.\n"
            "- Actuar adecuadamente frente a situaciones de emergencia.\n"
            "- Promover una cultura preventiva y trabajo seguro en campo."
        ),
        "category_slug": "obras-civiles-excavaciones",
        "duration_hours": 2,
        "methodology": "Magistral interactiva con el trabajador",
        "evaluation": "Evaluación escrita con calificación",
        "target_profiles": ALL_PROFILES,
        "responsible": "ARL SURA/COORDINADOR HSEQ",
    },
    {
        "code": "ESSA-OBR-017",
        "title": "Tema 4. Promoción de la Cultura de Seguridad",
        "description": (
            "Capacitar y fortalecer los conocimientos del personal, promoviendo una cultura "
            "de seguridad basada en la prevención de riesgos, el autocuidado y el cumplimiento "
            "de las normas de seguridad, con el fin de reducir accidentes e incidentes."
        ),
        "objectives": (
            "- Importancia del uso adecuado de los EPP.\n"
            "- Importancia del cumplimiento de normas y procedimientos de seguridad.\n"
            "- Comprensión de accidentes e incidentes y la importancia del reporte oportuno."
        ),
        "category_slug": "promocion-prevencion",
        "duration_hours": 2,
        "methodology": "Magistral interactiva con el trabajador",
        "evaluation": "Evaluación escrita y/o Taller",
        "target_profiles": OPERATIVE_PROFILES,
        "responsible": "COORDINADOR HSEQ",
    },
    {
        "code": "ESSA-OBR-018",
        "title": "Prevención al Consumo de Drogas y Alcohol",
        "description": (
            "Capacitar y fortalecer los conocimientos del personal sobre la prevención del "
            "consumo de drogas y alcohol, promoviendo estilos de vida saludables y seguros, "
            "que contribuyan a la prevención de accidentes y riesgos laborales."
        ),
        "objectives": (
            "- Generar conciencia sobre los daños del consumo de sustancias psicoactivas.\n"
            "- Reconocer las consecuencias laborales del consumo en actividades de alto riesgo.\n"
            "- Identificar los impactos sociales y familiares.\n"
            "- Promover el autocuidado y la toma de decisiones responsables.\n"
            "- Prevenir enfermedades y accidentes derivados del consumo."
        ),
        "category_slug": "estilos-vida-saludable",
        "duration_hours": 2,
        "methodology": "Magistral interactiva con el trabajador",
        "evaluation": "Evaluación escrita con calificación",
        "target_profiles": ALL_PROFILES,
        "responsible": "ARL SURA/COORDINADOR HSEQ",
    },
    {
        "code": "ESSA-OBR-019",
        "title": "Riesgo Biomecánico en Actividades Operativas",
        "description": (
            "Capacitar y fortalecer los conocimientos del personal sobre el riesgo biomecánico "
            "presente en las actividades operativas, brindando herramientas para la prevención "
            "de lesiones musculoesqueléticas y la ejecución segura de las labores."
        ),
        "objectives": (
            "- Identificar el riesgo biomecánico asociado a las actividades operativas.\n"
            "- Prevenir lesiones musculoesqueléticas mediante posturas correctas.\n"
            "- Aplicar técnicas adecuadas de manipulación manual de materiales.\n"
            "- Utilizar correctamente herramientas y equipos, minimizando movimientos repetitivos.\n"
            "- Promover el autocuidado y la conciencia preventiva."
        ),
        "category_slug": "riesgo-biomecanico-osteomuscular",
        "duration_hours": 2,
        "methodology": "Magistral interactiva con el trabajador",
        "evaluation": "Evaluación escrita con calificación",
        "target_profiles": ALL_PROFILES,
        "responsible": "ARL SURA/COORDINADOR HSEQ",
    },
    {
        "code": "ESSA-OBR-020",
        "title": "Control del Fuego y Procedimiento Seguro de Evacuación",
        "description": (
            "Capacitar a los trabajadores para prevenir y controlar con seguridad conatos de "
            "incendio, mediante el uso adecuado de extintores, la identificación de rutas de "
            "evacuación seguras y la correcta aplicación de los procedimientos de evacuación."
        ),
        "objectives": (
            "- Identificar los riesgos de incendio presentes en su área de trabajo.\n"
            "- Reconocer los tipos de fuego y el extintor adecuado.\n"
            "- Aplicar correctamente la técnica de uso del extintor.\n"
            "- Actuar de manera rápida y ordenada ante un conato de incendio.\n"
            "- Identificar y utilizar las rutas de evacuación seguras.\n"
            "- Ejecutar el procedimiento de evacuación sin generar pánico.\n"
            "- Reconocer cuándo intentar controlar el fuego y cuándo evacuar.\n"
            "- Seguir las instrucciones de las brigadas y líderes de evacuación.\n"
            "- Contribuir a la protección de la vida y reducción de daños."
        ),
        "category_slug": "plan-emergencias",
        "duration_hours": 2,
        "methodology": "Teórico-Práctica",
        "evaluation": "Evaluación escrita con calificación",
        "target_profiles": ALL_PROFILES,
        "responsible": "ARL SURA/COORDINADOR HSEQ",
    },
    {
        "code": "ESSA-OBR-021",
        "title": "Tema 3. Formación de Líderes en SST - Habilidades Blandas",
        "description": (
            "Fortalecer y motivar en los trabajadores el desarrollo de una conciencia activa "
            "en seguridad y salud en el trabajo, fortaleciendo sus habilidades blandas y su "
            "rol como líderes en seguridad."
        ),
        "objectives": (
            "- Reconocer la importancia de la SST como responsabilidad individual y colectiva.\n"
            "- Desarrollar una conciencia activa en seguridad.\n"
            "- Identificar su rol como líder en seguridad.\n"
            "- Fortalecer habilidades blandas clave.\n"
            "- Promover y reforzar comportamientos seguros.\n"
            "- Comunicar de manera asertiva actos y condiciones inseguras.\n"
            "- Participar activamente en la prevención de accidentes.\n"
            "- Integrar la seguridad como un valor permanente."
        ),
        "category_slug": "riesgo-psicosocial",
        "duration_hours": 2,
        "methodology": "Magistral interactiva con el trabajador",
        "evaluation": "Evaluación escrita y/o Taller",
        "target_profiles": OPERATIVE_PROFILES,
        "responsible": "COORDINADOR HSEQ",
    },
    {
        "code": "ESSA-OBR-022",
        "title": "Riesgo Químico: Manipulación Segura de Sustancias Químicas",
        "description": (
            "Dar a conocer al personal los lineamientos para la rotulación, almacenamiento y "
            "manipulación segura de sustancias químicas, fortaleciendo la prevención de accidentes, "
            "enfermedades laborales y daños al ambiente, conforme al SGA."
        ),
        "objectives": (
            "- Identificar el riesgo químico presente en las sustancias utilizadas.\n"
            "- Reconocer la importancia de la rotulación según el SGA.\n"
            "- Aplicar prácticas seguras para la manipulación de sustancias químicas.\n"
            "- Adoptar lineamientos correctos para el almacenamiento.\n"
            "- Interpretar y utilizar las Hojas de Datos de Seguridad.\n"
            "- Comprender y aplicar la matriz de compatibilidad."
        ),
        "category_slug": "riesgo-quimico",
        "duration_hours": 2,
        "methodology": "Magistral interactiva con el trabajador",
        "evaluation": "Evaluación escrita con calificación",
        "target_profiles": ALL_PROFILES,
        "responsible": "ARL SURA/COORDINADOR HSEQ",
    },
    {
        "code": "ESSA-OBR-023",
        "title": "Técnicas de Observación: Tipos de Observación, Técnicas y Tipos de Feedback",
        "description": (
            "Fortalecer las técnicas de observación de conductas seguras e inseguras, aplicando "
            "la metodología de Seguridad Basada en el Comportamiento (SBC), con el fin de promover "
            "el reporte oportuno y prevenir la materialización de accidentes."
        ),
        "objectives": (
            "- Comprender los principios de la SBC como herramienta preventiva.\n"
            "- Reconocer los diferentes tipos de observación.\n"
            "- Aplicar técnicas efectivas de observación de conductas.\n"
            "- Valorar la importancia del reporte oportuno.\n"
            "- Brindar feedback efectivo, respetuoso y constructivo."
        ),
        "category_slug": "riesgo-psicosocial",
        "duration_hours": 2,
        "methodology": "Magistral interactiva con el trabajador",
        "evaluation": "Evaluación escrita con calificación",
        "target_profiles": ALL_PROFILES,
        "responsible": "ARL SURA/COORDINADOR HSEQ",
    },
    {
        "code": "ESSA-OBR-024",
        "title": "Uso y Cuidado Correcto de Equipos y Elementos de Protección Personal (EPP)",
        "description": (
            "Capacitar a los trabajadores en la correcta selección, uso, mantenimiento y "
            "almacenamiento del EPP, garantizando su eficacia como medida de control y "
            "contribuyendo a la minimización de los riesgos laborales."
        ),
        "objectives": (
            "- Reconocer la importancia del EPP como última barrera de protección.\n"
            "- Identificar y seleccionar correctamente los EPP según el riesgo y la actividad.\n"
            "- Utilizar adecuadamente el EPP garantizando su correcto ajuste.\n"
            "- Aplicar prácticas adecuadas de mantenimiento y limpieza.\n"
            "- Almacenar correctamente los EPP.\n"
            "- Promover el autocuidado y la responsabilidad individual."
        ),
        "category_slug": "promocion-prevencion",
        "duration_hours": 2,
        "methodology": "Magistral interactiva con el trabajador",
        "evaluation": "Taller práctico",
        "target_profiles": ALL_PROFILES,
        "responsible": "ARL SURA/COORDINADOR HSEQ",
    },
    {
        "code": "ESSA-OBR-025",
        "title": "Manipulación Segura de Herramientas y Equipos",
        "description": (
            "Capacitar al personal en acciones seguras para la manipulación, cargue, traslado "
            "y uso adecuado de herramientas y equipos, con enfoque en la prevención del riesgo "
            "mecánico, con el fin de evitar golpes, atrapamientos, choques, cortes y otros accidentes."
        ),
        "objectives": (
            "- Identificar el riesgo mecánico asociado a la manipulación de herramientas.\n"
            "- Reconocer las acciones inseguras que pueden generar accidentes.\n"
            "- Aplicar técnicas seguras de cargue y traslado.\n"
            "- Utilizar correctamente las herramientas y equipos.\n"
            "- Inspeccionar previamente las herramientas y equipos.\n"
            "- Promover el autocuidado y la responsabilidad individual."
        ),
        "category_slug": "riesgo-mecanico",
        "duration_hours": 2,
        "methodology": "Magistral interactiva con el trabajador",
        "evaluation": "Evaluación escrita con calificación",
        "target_profiles": ALL_PROFILES,
        "responsible": "ARL SURA/COORDINADOR HSEQ",
    },
    {
        "code": "ESSA-OBR-026",
        "title": "Gestión del Estrés y Salud Mental",
        "description": (
            "Fortalecer las competencias de los trabajadores en gestión del estrés y cuidado "
            "de la salud mental, mediante la adopción de técnicas y estrategias prácticas que "
            "favorezcan el equilibrio entre la vida personal y laboral."
        ),
        "objectives": (
            "- Reconocer el estrés laboral y sus principales causas.\n"
            "- Aplicar técnicas básicas de manejo del estrés.\n"
            "- Desarrollar estrategias para equilibrar la vida personal y laboral.\n"
            "- Fomentar el autocuidado y la conciencia emocional.\n"
            "- Promover ambientes laborales saludables."
        ),
        "category_slug": "estilos-vida-saludable",
        "duration_hours": 2,
        "methodology": "Magistral interactiva con el trabajador",
        "evaluation": "Evaluación escrita con calificación",
        "target_profiles": ALL_PROFILES,
        "responsible": "ARL SURA/COORDINADOR HSEQ",
    },
    {
        "code": "ESSA-OBR-027",
        "title": "Cultura de Seguridad (Psicosocial)",
        "description": (
            "Dar a conocer al personal la importancia del reporte de incidentes y condiciones "
            "inseguras, fortaleciendo la construcción de una mentalidad proactiva de seguridad, "
            "basada en la participación, la prevención y el autocuidado."
        ),
        "objectives": (
            "- Reconocer la importancia del reporte oportuno de incidentes.\n"
            "- Identificar barreras psicosociales que limitan el reporte.\n"
            "- Desarrollar una mentalidad proactiva de seguridad.\n"
            "- Fomentar la participación activa de los trabajadores.\n"
            "- Fortalecer la conciencia individual y colectiva."
        ),
        "category_slug": "riesgo-psicosocial",
        "duration_hours": 2,
        "methodology": "Magistral interactiva con el trabajador",
        "evaluation": "Evaluación escrita con calificación",
        "target_profiles": ALL_PROFILES,
        "responsible": "ARL SURA/COORDINADOR HSEQ",
    },
    {
        "code": "ESSA-OBR-028",
        "title": "Caídas a Nivel, Orden y Aseo",
        "description": (
            "Fortalecer en el personal la habilidad de identificar riesgos y peligros durante "
            "el desplazamiento por terrenos irregulares, promoviendo la importancia del orden "
            "y aseo en los sitios de trabajo y técnicas de desplazamiento."
        ),
        "objectives": (
            "- Identificar los riesgos asociados a caídas a nivel.\n"
            "- Reconocer los peligros generados por la falta de orden y aseo.\n"
            "- Desarrollar una actitud preventiva frente a las condiciones del entorno.\n"
            "- Técnicas básicas para desplazamiento por terrenos irregulares.\n"
            "- Aplicar acciones de control relacionadas con el orden y la señalización.\n"
            "- Promover el autocuidado y el cuidado colectivo."
        ),
        "category_slug": "riesgo-locativo",
        "duration_hours": 2,
        "methodology": "Magistral interactiva con el trabajador",
        "evaluation": "Evaluación escrita con calificación",
        "target_profiles": ALL_PROFILES,
        "responsible": "ARL SURA/COORDINADOR HSEQ",
    },
    {
        "code": "ESSA-OBR-029",
        "title": "Técnicas de Atención Básica de Emergencias por Evento Ambiental y Accidente Biológico",
        "description": (
            "Dar a conocer al personal técnicas básicas para la atención inicial de emergencias "
            "derivadas de eventos ambientales (derrames de sustancias químicas) y accidentes "
            "biológicos, con el fin de reducir el impacto en la salud, el ambiente y la seguridad."
        ),
        "objectives": (
            "- Identificar situaciones de emergencia ambiental y biológica.\n"
            "- Reconocer las acciones iniciales seguras ante un derrame de sustancias químicas.\n"
            "- Aplicar medidas básicas ante mordedura de serpiente o picadura de animales.\n"
            "- Actuar de forma segura ante contacto con plantas urticantes o venenosas.\n"
            "- Fortalecer la toma de decisiones bajo situaciones de emergencia."
        ),
        "category_slug": "riesgo-biologico",
        "duration_hours": 2,
        "methodology": "Magistral interactiva con el trabajador",
        "evaluation": "Evaluación escrita con calificación",
        "target_profiles": ALL_PROFILES,
        "responsible": "ARL SURA/COORDINADOR HSEQ",
    },
    {
        "code": "ESSA-OBR-030",
        "title": "Primeros Auxilios, Evacuación y Camillaje (Método PAS)",
        "description": (
            "Dar a conocer a los trabajadores las actuaciones y técnicas básicas de primeros "
            "auxilios, evacuación y camillaje, aplicando el método PAS (Proteger, Avisar, Socorrer), "
            "para la atención inmediata y segura de un lesionado."
        ),
        "objectives": (
            "- Reconocer situaciones de emergencia que requieran atención inmediata.\n"
            "- Aplicar correctamente el método PAS.\n"
            "- Actuar de forma segura para proteger la escena y al lesionado.\n"
            "- Ejecutar técnicas básicas de primeros auxilios.\n"
            "- Conocer técnicas seguras de evacuación y camillaje."
        ),
        "category_slug": "plan-emergencias",
        "duration_hours": 3,
        "methodology": "Teórico-Práctico",
        "evaluation": "Taller práctico y/o taller",
        "target_profiles": ALL_PROFILES,
        "responsible": "ARL SURA/COORDINADOR HSEQ",
    },
    {
        "code": "ESSA-OBR-031",
        "title": "Técnicas de Asertividad: Comunicación Asertiva y Habilidades Sociales",
        "description": (
            "Fortalecer en los trabajadores las habilidades sociales y de comunicación asertiva, "
            "que les permitan crear vínculos positivos, mejorar la convivencia laboral y facilitar "
            "el compromiso colectivo con la seguridad y el autocuidado."
        ),
        "objectives": (
            "- Comprender el concepto de asertividad.\n"
            "- Diferenciar los estilos de comunicación y su impacto en la seguridad.\n"
            "- Aplicar técnicas de comunicación asertiva.\n"
            "- Desarrollar habilidades sociales que promuevan el trabajo en equipo.\n"
            "- Facilitar la identificación y comunicación de riesgos."
        ),
        "category_slug": "riesgo-psicosocial",
        "duration_hours": 2,
        "methodology": "Magistral interactiva con el trabajador",
        "evaluation": "Evaluación escrita con calificación",
        "target_profiles": ALL_PROFILES,
        "responsible": "ARL SURA/COORDINADOR HSEQ",
    },
    {
        "code": "ESSA-OBR-032",
        "title": "Toma de Decisiones y Resolución de Problemas en la Gestión de Riesgos",
        "description": (
            "Brindar a los trabajadores herramientas para la toma de decisiones seguras y la "
            "resolución efectiva de problemas, fortaleciendo la evaluación de riesgos en tiempo "
            "real mediante el pensamiento crítico."
        ),
        "objectives": (
            "- Reconocer la importancia de la toma de decisiones en la gestión del riesgo.\n"
            "- Aplicar técnicas de evaluación de riesgos en tiempo real.\n"
            "- Desarrollar el pensamiento crítico.\n"
            "- Identificar factores que favorecen el error humano.\n"
            "- Implementar estrategias para minimizar errores humanos."
        ),
        "category_slug": "riesgo-psicosocial",
        "duration_hours": 2,
        "methodology": "Magistral interactiva con el trabajador",
        "evaluation": "Evaluación escrita con calificación",
        "target_profiles": ALL_PROFILES,
        "responsible": "ARL SURA/COORDINADOR HSEQ",
    },
    {
        "code": "ESSA-OBR-033",
        "title": "Desplazamientos Seguros en la Vía y Seguridad Vial",
        "description": (
            "Dar a conocer a los trabajadores buenas prácticas y conductas seguras de movilidad, "
            "promoviendo el respeto de los roles en la vía, el cumplimiento de la normatividad "
            "de tránsito y la identificación de factores de riesgo."
        ),
        "objectives": (
            "- Reconocer los diferentes roles en la vía y sus responsabilidades.\n"
            "- Adoptar comportamientos seguros durante los desplazamientos.\n"
            "- Fomentar el respeto por los demás actores viales.\n"
            "- Conocer y aplicar la normatividad básica de tránsito.\n"
            "- Identificar los factores de riesgo más comunes en la vía."
        ),
        "category_slug": "seguridad-vial",
        "duration_hours": 2,
        "methodology": "Magistral interactiva con el trabajador",
        "evaluation": "Evaluación escrita con calificación",
        "target_profiles": ALL_PROFILES,
        "responsible": "ARL SURA/COORDINADOR HSEQ",
    },
    {
        "code": "ESSA-OBR-034",
        "title": "Riesgo de Golpes por o contra Objetos",
        "description": (
            "Dar a conocer a los trabajadores las medidas de seguridad necesarias para prevenir "
            "accidentes por golpes de o contra objetos, durante actividades con riesgo de caída "
            "de objetos desde altura, almacenamiento y desplazamiento de materiales."
        ),
        "objectives": (
            "- Identificar los riesgos asociados a golpes por o contra objetos.\n"
            "- Reconocer situaciones con riesgo de caída de objetos desde altura.\n"
            "- Aplicar medidas de seguridad durante el almacenamiento de materiales.\n"
            "- Implementar prácticas seguras para el traslado en terrenos irregulares.\n"
            "- Fomentar el uso adecuado de EPP como medida preventiva.\n"
            "- Promover una actitud preventiva y de autocuidado."
        ),
        "category_slug": "riesgo-mecanico",
        "duration_hours": 2,
        "methodology": "Magistral interactiva con el trabajador",
        "evaluation": "Evaluación escrita con calificación",
        "target_profiles": ALL_PROFILES,
        "responsible": "ARL SURA/COORDINADOR HSEQ",
    },
    {
        "code": "ESSA-OBR-035",
        "title": "Riesgo Biológico: Bacterias, Virus, Hongos, Vegetación y Animales Venenosos",
        "description": (
            "Dar recomendaciones de seguridad y medidas preventivas al personal para la "
            "identificación y el manejo seguro del riesgo biológico, incluyendo exposición a "
            "bacterias, virus, hongos, vegetación urticante y animales venenosos."
        ),
        "objectives": (
            "- Identificar los principales riesgos biológicos en sus actividades laborales.\n"
            "- Reconocer la vegetación urticante, venenosa o punzante.\n"
            "- Identificar animales venenosos y aplicar comportamientos seguros.\n"
            "- Aplicar medidas de prevención ante contagios.\n"
            "- Conocer las recomendaciones de actuación ante un contacto biológico."
        ),
        "category_slug": "riesgo-biologico",
        "duration_hours": 2,
        "methodology": "Magistral interactiva con el trabajador",
        "evaluation": "Evaluación escrita con calificación",
        "target_profiles": ALL_PROFILES,
        "responsible": "ARL SURA/COORDINADOR HSEQ",
    },
    {
        "code": "ESSA-OBR-036",
        "title": "Riesgo Auditivo",
        "description": (
            "Dar a conocer a los trabajadores el riesgo asociado a la exposición al ruido, "
            "sus efectos en la salud auditiva, así como los cuidados y controles a implementar, "
            "con el fin de prevenir la pérdida de la audición."
        ),
        "objectives": (
            "- Identificar el riesgo auditivo derivado de la exposición al ruido.\n"
            "- Reconocer los efectos del ruido en la salud.\n"
            "- Conocer los límites de exposición al ruido.\n"
            "- Aplicar medidas de prevención y control.\n"
            "- Utilizar correctamente los elementos de protección auditiva.\n"
            "- Promover hábitos de autocuidado auditivo."
        ),
        "category_slug": "riesgo-auditivo-ruido",
        "duration_hours": 2,
        "methodology": "Magistral interactiva con el trabajador",
        "evaluation": "Evaluación escrita con calificación",
        "target_profiles": ALL_PROFILES,
        "responsible": "ARL SURA/COORDINADOR HSEQ",
    },
    {
        "code": "ESSA-OBR-037",
        "title": "Pausas Activas, Calistenias e Higiene Postural",
        "description": (
            "Dar a conocer a los trabajadores la importancia de la higiene postural, las pausas "
            "activas y la calistenia, mediante la aplicación de técnicas y ejercicios preventivos, "
            "con el fin de disminuir la fatiga laboral y prevenir trastornos osteomusculares."
        ),
        "objectives": (
            "- Reconocer la importancia de la higiene postural durante las actividades.\n"
            "- Identificar los riesgos ergonómicos asociados a malas posturas.\n"
            "- Aplicar pausas activas como estrategia preventiva.\n"
            "- Realizar ejercicios de calistenia y estiramiento.\n"
            "- Promover el autocuidado físico."
        ),
        "category_slug": "riesgo-biomecanico-osteomuscular",
        "duration_hours": 2,
        "methodology": "Teórico-Práctico",
        "evaluation": "Evaluación Oral",
        "target_profiles": ALL_PROFILES,
        "responsible": "ARL SURA/COORDINADOR HSEQ",
    },
    {
        "code": "ESSA-OBR-038",
        "title": "Prevención del Riesgo Cardiovascular y Otras Enfermedades",
        "description": (
            "Informar y concienciar a los trabajadores sobre la importancia de los estilos "
            "de vida saludables en la prevención y control de enfermedades cardiovasculares "
            "y otras enfermedades crónicas."
        ),
        "objectives": (
            "- Reconocer los principales factores de riesgo cardiovascular.\n"
            "- Identificar las enfermedades crónicas más frecuentes.\n"
            "- Comprender la relación entre los estilos de vida y la salud.\n"
            "- Promover hábitos saludables para la prevención.\n"
            "- Fomentar la responsabilidad individual frente al autocuidado."
        ),
        "category_slug": "estilos-vida-saludable",
        "duration_hours": 2,
        "methodology": "Magistral interactiva con el trabajador",
        "evaluation": "Evaluación escrita con calificación",
        "target_profiles": ALL_PROFILES,
        "responsible": "ARL SURA/COORDINADOR HSEQ",
    },
    {
        "code": "ESSA-OBR-039",
        "title": "Cuidado Visual",
        "description": (
            "Promover el cuidado de la salud visual de los trabajadores mediante la "
            "identificación de riesgos, la adopción de hábitos saludables y el uso "
            "adecuado de protección visual."
        ),
        "objectives": (
            "- Reconocer los factores de riesgo visual presentes en su puesto de trabajo.\n"
            "- Identificar síntomas de fatiga visual y alteraciones de la visión.\n"
            "- Aplicar buenas prácticas de cuidado visual.\n"
            "- Utilizar correctamente los elementos de protección visual.\n"
            "- Adoptar hábitos preventivos para el cuidado ocular.\n"
            "- Comprender la importancia de los controles médicos visuales.\n"
            "- Contribuir a un ambiente de trabajo seguro y saludable."
        ),
        "category_slug": "promocion-prevencion",
        "duration_hours": 2,
        "methodology": "Magistral interactiva con el trabajador",
        "evaluation": "Evaluación escrita con calificación",
        "target_profiles": ALL_PROFILES,
        "responsible": "ARL SURA/COORDINADOR HSEQ",
    },
    {
        "code": "ESSA-OBR-040",
        "title": "Manipulación y Transporte de Cargas, Posturas y Trabajo Repetitivo (Refuerzo)",
        "description": (
            "Brindar herramientas prácticas a los trabajadores para reconocer, aplicar y "
            "mantener técnicas seguras en la manipulación y transporte de cargas, así como "
            "medidas preventivas frente a posturas forzadas y trabajos repetitivos."
        ),
        "objectives": (
            "- Reconocer los riesgos osteomusculares asociados a la manipulación de cargas.\n"
            "- Aplicar correctamente técnicas seguras de manipulación.\n"
            "- Identificar posturas forzadas y adoptar posturas ergonómicas adecuadas.\n"
            "- Implementar medidas preventivas durante trabajos repetitivos.\n"
            "- Participar activamente en la prevención de lesiones musculoesqueléticas."
        ),
        "category_slug": "riesgo-biomecanico-osteomuscular",
        "duration_hours": 2,
        "methodology": "Taller Teórico-Práctico",
        "evaluation": "Evaluación escrita con calificación",
        "target_profiles": ALL_PROFILES,
        "responsible": "ARL SURA/COORDINADOR HSEQ",
    },
    {
        "code": "ESSA-OBR-041",
        "title": "Señalización e Inspecciones (Refuerzo)",
        "description": (
            "Proporcionar a los trabajadores los conocimientos básicos y prácticos sobre "
            "señalización de seguridad y la realización de inspecciones de seguridad, formatos "
            "y correcto diligenciamiento."
        ),
        "objectives": (
            "- Reconocer la importancia de la señalización como medida preventiva.\n"
            "- Identificar los tipos de señalización de seguridad y su correcta aplicación.\n"
            "- Comprender qué es una inspección de seguridad.\n"
            "- Aplicar correctamente los formatos de inspección.\n"
            "- Identificar actos y condiciones inseguras durante las inspecciones.\n"
            "- Contribuir activamente en la propuesta y seguimiento de medidas de control."
        ),
        "category_slug": "inspecciones-senalizacion",
        "duration_hours": 2,
        "methodology": "Magistral interactiva con el trabajador",
        "evaluation": "Evaluación escrita con calificación",
        "target_profiles": ALL_PROFILES,
        "responsible": "ARL SURA/COORDINADOR HSEQ",
    },
    {
        "code": "ESSA-OBR-042",
        "title": "Manejo Defensivo y Seguridad Vial: Vehículos Seguros y Factores de Riesgo",
        "description": (
            "Dar a conocer a los trabajadores buenas prácticas y conductas seguras de movilidad, "
            "basadas en la normatividad vigente en tránsito y transporte, que les permitan "
            "desempeñar de manera segura su rol en la seguridad vial."
        ),
        "objectives": (
            "- Reconocer la importancia de la seguridad vial en el ámbito laboral.\n"
            "- Identificar los roles de la seguridad vial y sus responsabilidades.\n"
            "- Aplicar principios de manejo defensivo.\n"
            "- Verificar condiciones de vehículos seguros.\n"
            "- Analizar los factores de riesgo viales.\n"
            "- Adoptar comportamientos seguros conforme a la normatividad."
        ),
        "category_slug": "seguridad-vial",
        "duration_hours": 2,
        "methodology": "Magistral interactiva con el trabajador",
        "evaluation": "Evaluación escrita con calificación",
        "target_profiles": ALL_PROFILES,
        "responsible": "ARL SURA/COORDINADOR HSEQ",
    },
    {
        "code": "ESSA-OBR-043",
        "title": "Sinergia Positiva",
        "description": (
            "Fortalecer en los colaboradores las habilidades necesarias para generar sinergia "
            "positiva, desarrollando las 5C del trabajo en equipo (Comunicación, Coordinación, "
            "Complementariedad, Confianza, Compromiso con cumplimiento de normas de seguridad)."
        ),
        "objectives": (
            "- Diferenciar un grupo de trabajo de un equipo de trabajo.\n"
            "- Comprender el concepto de sinergia positiva y su impacto.\n"
            "- Fortalecer las 5C del trabajo en equipo enfocado en seguridad.\n"
            "- Identificar los tipos de sinergia y su presencia en el entorno laboral.\n"
            "- Desarrollar habilidades básicas para la toma de decisiones en equipo.\n"
            "- Promover el compromiso individual y colectivo con las normas de seguridad."
        ),
        "category_slug": "riesgo-psicosocial",
        "duration_hours": 2,
        "methodology": "Magistral interactiva con el trabajador",
        "evaluation": "Evaluación escrita con calificación",
        "target_profiles": ALL_PROFILES,
        "responsible": "ARL SURA/COORDINADOR HSEQ",
    },
    {
        "code": "ESSA-OBR-044",
        "title": "Funcionamiento Auditivo y Uso e Higiene de Protección Auditiva",
        "description": (
            "Capacitar al personal sobre el funcionamiento del oído humano, su anatomía y "
            "cuidado, así como la importancia del uso correcto, mantenimiento e higiene de "
            "los protectores auditivos."
        ),
        "objectives": (
            "- Comprender el funcionamiento del sistema auditivo.\n"
            "- Identificar la anatomía del oído.\n"
            "- Reconocer los efectos del ruido sobre la audición.\n"
            "- Aplicar buenas prácticas para el cuidado del oído.\n"
            "- Usar correctamente los protectores auditivos.\n"
            "- Realizar adecuada limpieza y almacenamiento de la protección auditiva."
        ),
        "category_slug": "riesgo-auditivo-ruido",
        "duration_hours": 2,
        "methodology": "Magistral interactiva con el trabajador",
        "evaluation": "Evaluación escrita con calificación",
        "target_profiles": ALL_PROFILES,
        "responsible": "ARL SURA/COORDINADOR HSEQ",
    },
    {
        "code": "ESSA-OBR-045",
        "title": "Importancia del Ejercicio y Alimentación Sana-Saludable",
        "description": (
            "Dar a conocer a los trabajadores la importancia de la alimentación sana y la "
            "actividad física regular como pilares fundamentales de un estilo de vida saludable."
        ),
        "objectives": (
            "- Reconocer los beneficios de una alimentación equilibrada y la actividad física.\n"
            "- Comprender cómo el ejercicio y una dieta saludable fortalecen el sistema inmunológico.\n"
            "- Identificar hábitos alimenticios saludables.\n"
            "- Conocer recomendaciones básicas de actividad física.\n"
            "- Adoptar prácticas de autocuidado."
        ),
        "category_slug": "estilos-vida-saludable",
        "duration_hours": 2,
        "methodology": "Magistral interactiva con el trabajador",
        "evaluation": "Evaluación escrita con calificación",
        "target_profiles": ALL_PROFILES,
        "responsible": "ARL SURA/COORDINADOR HSEQ",
    },
    {
        "code": "ESSA-OBR-046",
        "title": "Gestión de Emergencias y Primeros Auxilios por Riesgo Eléctrico",
        "description": (
            "Capacitar a los trabajadores en la gestión de emergencias y atención en primeros "
            "auxilios frente a accidentes por riesgo eléctrico, proporcionando conocimientos "
            "básicos y procedimientos seguros para la atención inicial del electrocutado."
        ),
        "objectives": (
            "- Reconocer una emergencia por riesgo eléctrico y actuar de forma segura.\n"
            "- Identificar los efectos de una descarga eléctrica en el cuerpo humano.\n"
            "- Aplicar los protocolos básicos de primeros auxilios al electrocutado.\n"
            "- Reconocer y atender quemaduras eléctricas.\n"
            "- Activar correctamente la cadena de atención de emergencias.\n"
            "- Proteger su propia integridad durante la atención."
        ),
        "category_slug": "plan-emergencias",
        "duration_hours": 2,
        "methodology": "Teórico-Práctica",
        "evaluation": "Evaluación escrita con calificación",
        "target_profiles": ALL_PROFILES,
        "responsible": "ARL SURA/COORDINADOR HSEQ",
    },
    {
        "code": "ESSA-OBR-047",
        "title": "Manipulación de Herramientas de Corte",
        "description": (
            "Fortalecer en los trabajadores las conductas seguras en la manipulación de "
            "herramientas de corte (machete, motosierra, guadañadoras, podadoras de alturas), "
            "promoviendo la correcta elección, uso, inspección y mantenimiento."
        ),
        "objectives": (
            "- Identificar los riesgos asociados al uso de herramientas de corte.\n"
            "- Seleccionar la herramienta adecuada según la actividad.\n"
            "- Aplicar técnicas seguras de uso, transporte y almacenamiento.\n"
            "- Reconocer y corregir actos y condiciones inseguras.\n"
            "- Usar correctamente los EPP.\n"
            "- Realizar inspecciones básicas y mantenimiento preventivo."
        ),
        "category_slug": "riesgo-mecanico",
        "duration_hours": 3,
        "methodology": "Taller Teórico-Práctico",
        "evaluation": "Evaluación escrita con calificación",
        "target_profiles": ALL_PROFILES,
        "responsible": "ARL SURA/COORDINADOR HSEQ",
    },
    {
        "code": "ESSA-OBR-048",
        "title": "Gestión para el Cuidado Integral de la Salud (Prevención de Estrés, Depresión, Ansiedad)",
        "description": (
            "Brindar a los trabajadores herramientas prácticas para la prevención y manejo del "
            "estrés, la ansiedad y la depresión, mediante el reconocimiento de los factores de "
            "riesgo psicosocial, promoviendo el autocuidado y el bienestar integral."
        ),
        "objectives": (
            "- Comprender qué son los factores de riesgo psicosocial.\n"
            "- Identificar signos tempranos de estrés, ansiedad y depresión.\n"
            "- Reconocer factores psicosociales presentes en el trabajo.\n"
            "- Aplicar estrategias prácticas de prevención y manejo emocional.\n"
            "- Fortalecer habilidades de autocuidado y comunicación.\n"
            "- Conocer cuándo y cómo buscar apoyo oportuno."
        ),
        "category_slug": "riesgo-psicosocial",
        "duration_hours": 2,
        "methodology": "Magistral interactiva con el trabajador",
        "evaluation": "Evaluación escrita con calificación",
        "target_profiles": ALL_PROFILES,
        "responsible": "ARL SURA/COORDINADOR HSEQ",
    },
    {
        "code": "ESSA-OBR-049",
        "title": "Sistema de Gestión de la Calidad (ISO 9001:2015)",
        "description": (
            "Capacitar al personal en los principios, requisitos y responsabilidades establecidos "
            "en la Norma ISO 9001:2015, promoviendo la comprensión del Sistema de Gestión de la "
            "Calidad, la mejora continua y la orientación al cliente."
        ),
        "objectives": (
            "- Comprender qué es la ISO 9001 y para qué sirve.\n"
            "- Reconocer su rol y responsabilidad dentro del Sistema de Gestión.\n"
            "- Aplicar el enfoque basado en procesos y en riesgos.\n"
            "- Contribuir a la satisfacción del cliente.\n"
            "- Participar activamente en la mejora continua del SGC."
        ),
        "category_slug": "calidad-iso-9001",
        "duration_hours": 2,
        "methodology": "Magistral interactiva con el trabajador",
        "evaluation": "Evaluación escrita con calificación",
        "target_profiles": ALL_PROFILES,
        "responsible": "COORDINADOR HSEQ",
    },
]


class Command(BaseCommand):
    help = "Carga los cursos del plan de capacitación ESSA OBRAS 2026"

    def add_arguments(self, parser):
        parser.add_argument(
            "--publish",
            action="store_true",
            help="Publicar los cursos automáticamente después de crearlos",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Solo muestra lo que se haría sin crear nada en la BD",
        )
        parser.add_argument(
            "--user-email",
            type=str,
            default=None,
            help="Email del usuario que creará los cursos (por defecto: primer superuser)",
        )

    @transaction.atomic
    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        publish = options["publish"]
        user_email = options["user_email"]

        if dry_run:
            self.stdout.write(self.style.WARNING("=== MODO DRY RUN ===\n"))

        # Get or determine user
        if user_email:
            try:
                user = User.objects.get(email=user_email)
            except User.DoesNotExist:
                self.stderr.write(
                    self.style.ERROR(f"Usuario con email '{user_email}' no encontrado")
                )
                return
        else:
            user = User.objects.filter(is_superuser=True).first()
            if not user:
                user = User.objects.first()
            if not user:
                self.stderr.write(
                    self.style.ERROR("No se encontró ningún usuario en la BD")
                )
                return

        self.stdout.write(f"Usuario: {user.email}\n")

        # Create categories
        self.stdout.write(self.style.MIGRATE_HEADING("Creando categorías..."))
        categories_map = {}
        for idx, cat_data in enumerate(CATEGORIES):
            if dry_run:
                self.stdout.write(f"  [DRY] Categoría: {cat_data['name']}")
                categories_map[cat_data["slug"]] = None
            else:
                cat, created = Category.objects.get_or_create(
                    slug=cat_data["slug"],
                    defaults={
                        "name": cat_data["name"],
                        "icon": cat_data["icon"],
                        "color": cat_data["color"],
                        "order": idx,
                        "is_active": True,
                    },
                )
                categories_map[cat_data["slug"]] = cat
                status = "CREADA" if created else "YA EXISTÍA"
                self.stdout.write(f"  [{status}] {cat.name}")

        self.stdout.write(
            self.style.SUCCESS(f"\n  Total categorías: {len(CATEGORIES)}\n")
        )

        # Create courses
        self.stdout.write(self.style.MIGRATE_HEADING("Creando cursos..."))
        created_count = 0
        skipped_count = 0

        for course_data in COURSES:
            code = course_data["code"]
            title = course_data["title"]

            if dry_run:
                self.stdout.write(f"  [DRY] {code} - {title}")
                created_count += 1
                continue

            # Check if course already exists
            if Course.objects.filter(code=code).exists():
                self.stdout.write(
                    self.style.WARNING(f"  [EXISTE] {code} - {title}")
                )
                skipped_count += 1
                continue

            category = categories_map.get(course_data["category_slug"])

            course = Course.objects.create(
                code=code,
                title=title,
                description=course_data["description"],
                objectives=course_data["objectives"],
                course_type=Course.Type.MANDATORY,
                status=Course.Status.PUBLISHED if publish else Course.Status.DRAFT,
                published_at=timezone.now() if publish else None,
                target_profiles=course_data["target_profiles"],
                country=Course.Country.COLOMBIA,
                category=category,
                created_by=user,
            )

            # Create a single module for the course
            module = Module.objects.create(
                course=course,
                title=title,
                description=course_data["description"],
                order=0,
            )

            # Create a presential lesson within the module
            duration_minutes = course_data["duration_hours"] * 60
            Lesson.objects.create(
                module=module,
                title=title,
                description=course_data["description"],
                lesson_type=Lesson.Type.PRESENTIAL,
                duration=duration_minutes,
                order=0,
                is_mandatory=True,
                is_presential=True,
                metadata={
                    "methodology": course_data["methodology"],
                    "evaluation": course_data["evaluation"],
                    "responsible": course_data["responsible"],
                    "project": "ESSA OBRAS",
                    "contract": "ESSA EPM - Servicios de mantenimiento de líneas de transmisión de energía CW261422",
                    "year": 2026,
                },
            )

            created_count += 1
            self.stdout.write(self.style.SUCCESS(f"  [CREADO] {code} - {title}"))

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                f"Resumen: {created_count} cursos creados, {skipped_count} ya existían"
            )
        )

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    "\nModo DRY RUN: no se realizaron cambios en la base de datos"
                )
            )
        elif publish:
            self.stdout.write(
                self.style.SUCCESS("Todos los cursos fueron publicados automáticamente")
            )
        else:
            self.stdout.write(
                self.style.NOTICE(
                    "Los cursos fueron creados como BORRADOR. "
                    "Use --publish para publicarlos directamente."
                )
            )
