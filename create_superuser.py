#!/usr/bin/env python
"""Script para crear superusuario de Django"""

import os
from datetime import date

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.local")
django.setup()

from apps.accounts.models import User

# Crear superusuario
email = "admin@sd-lms.com"
password = "admin123"

if not User.objects.filter(email=email).exists():
    user = User.objects.create_superuser(
        email=email,
        password=password,
        first_name="Admin",
        last_name="SD LMS",
        document_type="CC",
        document_number="1234567890",
        phone="+573001234567",
        hire_date=date.today(),
    )
    print("✅ Superusuario creado exitosamente:")
    print(f"   Email: {email}")
    print(f"   Password: {password}")
    print("   Accede al admin en: http://35.184.159.138:8000/admin")
else:
    print(f"⚠️  El usuario {email} ya existe")
