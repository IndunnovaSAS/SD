"""
Forms for courses app.
"""

from django import forms
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from .models import Course, Category


class CategoryForm(forms.ModelForm):
    """Form for creating and editing categories."""

    class Meta:
        model = Category
        fields = ["name", "description", "parent", "icon", "color", "order", "is_active"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "input input-bordered w-full"}),
            "description": forms.Textarea(attrs={"class": "textarea textarea-bordered w-full", "rows": 3}),
            "parent": forms.Select(attrs={"class": "select select-bordered w-full"}),
            "icon": forms.TextInput(attrs={"class": "input input-bordered w-full", "placeholder": "ej: book, graduation-cap"}),
            "color": forms.TextInput(attrs={"class": "input input-bordered w-full", "type": "color"}),
            "order": forms.NumberInput(attrs={"class": "input input-bordered w-full"}),
            "is_active": forms.CheckboxInput(attrs={"class": "checkbox checkbox-primary"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Exclude current category from parent choices to prevent circular reference
        if self.instance.pk:
            self.fields["parent"].queryset = Category.objects.exclude(pk=self.instance.pk)
        self.fields["parent"].empty_label = "Sin categoría padre (raíz)"
        self.fields["parent"].required = False

    def clean_name(self):
        name = self.cleaned_data.get("name")
        # Check for duplicate name at same level
        parent = self.cleaned_data.get("parent")
        qs = Category.objects.filter(name=name, parent=parent)
        if self.instance.pk:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise forms.ValidationError(_("Ya existe una categoría con este nombre en el mismo nivel."))
        return name

    def save(self, commit=True):
        instance = super().save(commit=False)
        # Auto-generate slug from name if not set
        if not instance.slug:
            base_slug = slugify(instance.name)
            slug = base_slug
            counter = 1
            while Category.objects.filter(slug=slug).exclude(pk=instance.pk).exists():
                slug = f"{base_slug}-{counter}"
                counter += 1
            instance.slug = slug
        if commit:
            instance.save()
        return instance


class CourseCreateForm(forms.ModelForm):
    """Form for creating courses (staff only)."""

    target_profiles = forms.MultipleChoiceField(
        label=_("Perfiles objetivo"),
        choices=[
            ("LINIERO", "Liniero"),
            ("JEFE_CUADRILLA", "Jefe de Cuadrilla"),
            ("INGENIERO_RESIDENTE", "Ingeniero Residente"),
            ("COORDINADOR_HSEQ", "Coordinador HSEQ"),
            ("OPERADOR", "Operador"),
            ("TECNICO", "Técnico"),
        ],
        widget=forms.CheckboxSelectMultiple(),
        required=False,
    )

    class Meta:
        model = Course
        fields = [
            "code",
            "title",
            "description",
            "objectives",
            "course_type",
            "category",
            "target_profiles",
            "validity_months",
            "status",
        ]
        widgets = {
            "code": forms.TextInput(attrs={"class": "input input-bordered w-full"}),
            "title": forms.TextInput(attrs={"class": "input input-bordered w-full"}),
            "description": forms.Textarea(attrs={"class": "textarea textarea-bordered w-full", "rows": 4}),
            "objectives": forms.Textarea(attrs={"class": "textarea textarea-bordered w-full", "rows": 3}),
            "course_type": forms.Select(attrs={"class": "select select-bordered w-full"}),
            "category": forms.Select(attrs={"class": "select select-bordered w-full"}),
            "validity_months": forms.NumberInput(attrs={"class": "input input-bordered w-full"}),
            "status": forms.Select(attrs={"class": "select select-bordered w-full"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Filter active categories
        self.fields["category"].queryset = Category.objects.filter(is_active=True)
        self.fields["category"].empty_label = "Sin categoría"

    def clean_code(self):
        code = self.cleaned_data.get("code")
        if Course.objects.filter(code=code).exists():
            raise forms.ValidationError(_("Ya existe un curso con este código."))
        return code

    def clean_target_profiles(self):
        profiles = self.cleaned_data.get("target_profiles")
        return list(profiles) if profiles else []
