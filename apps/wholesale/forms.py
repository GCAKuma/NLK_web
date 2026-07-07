from django import forms

from .models import QuotationRequest

INPUT_CLASS = "field-input"


class QuotationRequestForm(forms.ModelForm):
    class Meta:
        model = QuotationRequest
        fields = (
            "contact_name", "organization_name", "organization_type",
            "email", "phone", "requirements",
        )
        widgets = {
            "contact_name": forms.TextInput(attrs={"class": INPUT_CLASS}),
            "organization_name": forms.TextInput(attrs={"class": INPUT_CLASS}),
            "organization_type": forms.Select(attrs={"class": INPUT_CLASS}),
            "email": forms.EmailInput(attrs={"class": INPUT_CLASS}),
            "phone": forms.TextInput(attrs={"class": INPUT_CLASS}),
            "requirements": forms.Textarea(
                attrs={"class": INPUT_CLASS, "rows": 4,
                       "placeholder": "Tell us the items, quantities or requirements you need a quote for."}
            ),
        }
