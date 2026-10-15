from django import forms
from .models import Product


class ProductForm(forms.ModelForm):
    class Meta:
        model = Product

        fields = [
            "name",
            "description",
            "category",
            "price",
            "unit",
            "quantity",
            "image",
            "location",
            "is_available",
        ]

        widgets = {
            "name": forms.TextInput(attrs={
                "placeholder": "Example: Fresh Tomatoes",
            }),
            "description": forms.Textarea(attrs={
                "rows": 4,
                "placeholder": "Describe your farm product...",
            }),
            "price": forms.NumberInput(attrs={
                "min": "0.01",
                "step": "0.01",
            }),
            "quantity": forms.NumberInput(attrs={
                "min": "0",
            }),
            "unit": forms.TextInput(attrs={
                "placeholder": "kg, litre, dozen, etc.",
            }),
            "location": forms.TextInput(attrs={
                "placeholder": "Your village or town",
            }),
        }

    def clean_price(self):
        price = self.cleaned_data["price"]

        if price <= 0:
            raise forms.ValidationError(
                "Price must be greater than zero."
            )

        return price