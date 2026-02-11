"""
Forms for learning paths app.
"""

from django import forms
from django.utils.translation import gettext_lazy as _

from .models import LearningPath


class LearningPathCreateForm(forms.ModelForm):
    """Form for creating learning paths (staff only)."""

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
        model = LearningPath
        fields = [
            "name",
            "description",
            "target_profiles",
            "estimated_duration",
            "is_mandatory",
            "status",
        ]
        widgets = {
            "name": forms.TextInput(attrs={"class": "input input-bordered w-full"}),
            "description": forms.Textarea(
                attrs={"class": "textarea textarea-bordered w-full", "rows": 4}
            ),
            "estimated_duration": forms.NumberInput(attrs={"class": "input input-bordered w-full"}),
            "is_mandatory": forms.CheckboxInput(attrs={"class": "checkbox checkbox-primary"}),
            "status": forms.Select(attrs={"class": "select select-bordered w-full"}),
        }

    def clean_target_profiles(self):
        profiles = self.cleaned_data.get("target_profiles")
        return list(profiles) if profiles else []
