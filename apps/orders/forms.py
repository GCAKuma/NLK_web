from django import forms

from accounts.models import Address

from .models import Order, PaymentProof

INPUT_CLASS = "field-input"


class CheckoutForm(forms.ModelForm):
    """Collects shipping address, payment method and notes at checkout."""

    payment_method = forms.ChoiceField(
        choices=Order.PaymentMethod.choices,
        widget=forms.RadioSelect,
    )
    customer_notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={"class": INPUT_CLASS, "rows": 3}),
    )

    class Meta:
        model = Address
        fields = (
            "full_name", "phone_number", "address_line1", "address_line2",
            "city", "district", "postal_code",
        )
        widgets = {
            "full_name": forms.TextInput(attrs={"class": INPUT_CLASS}),
            "phone_number": forms.TextInput(attrs={"class": INPUT_CLASS}),
            "address_line1": forms.TextInput(attrs={"class": INPUT_CLASS}),
            "address_line2": forms.TextInput(attrs={"class": INPUT_CLASS}),
            "city": forms.TextInput(attrs={"class": INPUT_CLASS}),
            "district": forms.TextInput(attrs={"class": INPUT_CLASS}),
            "postal_code": forms.TextInput(attrs={"class": INPUT_CLASS}),
        }


class PaymentProofForm(forms.ModelForm):
    class Meta:
        model = PaymentProof
        fields = ("slip_image",)
        widgets = {
            "slip_image": forms.ClearableFileInput(attrs={"class": "block w-full text-sm"}),
        }
