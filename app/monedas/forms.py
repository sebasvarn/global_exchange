"""
Forms de la app 'monedas'.

- MonedaForm: formulario simple para ABM de Moneda. Los widgets incluyen
  clases Bootstrap para una UI consistente con el resto del sistema.
"""

from django import forms
from .models import Moneda


class MonedaForm(forms.ModelForm):
    class Meta:
        model = Moneda
        fields = ['codigo', 'nombre', 'simbolo', 'decimales', 'activa', 'es_base']
        labels = {
            'codigo': 'Código ISO',
            'nombre': 'Nombre de la moneda',
            'simbolo': 'Símbolo',
            'decimales': 'Cantidad de decimales',
            'activa': 'Activa para operar',
            'es_base': 'Marcar como moneda base',
        }
        widgets = {
            'codigo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'PYG'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Guaraní paraguayo'}),
            'simbolo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '₲'}),
            'decimales': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 6}),
            'activa': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'es_base': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
