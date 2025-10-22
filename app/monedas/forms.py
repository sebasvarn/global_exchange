"""
Forms de la aplicación 'monedas'.

Contiene formularios para la gestión de Moneda y TasaCambio:

- MonedaForm: creación y edición de monedas, con validaciones de código único
  y restricción de moneda base (solo 'PYG').
- TasaCambioForm: creación y edición de tasas de cambio, validando que
  venta >= compra y limitando la selección a monedas activas no base.

Los widgets utilizan clases de Bootstrap para una interfaz consistente.
"""

from django import forms
from django.core.exceptions import ValidationError
from django.utils import timezone

from .models import Moneda, TasaCambio, PrecioBaseComision
class PrecioBaseComisionForm(forms.ModelForm):
    class Meta:
        model = PrecioBaseComision
        fields = ['moneda', 'precio_base', 'comision_compra', 'comision_venta']
        labels = {
            'moneda': 'Moneda',
            'precio_base': 'Precio base',
            'comision_compra': 'Comisión de compra',
            'comision_venta': 'Comisión de venta',
        }
        widgets = {
            'moneda': forms.Select(attrs={'class': 'form-select'}),
            'precio_base': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'}),
            'comision_compra': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'comision_venta': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['moneda'].queryset = Moneda.objects.filter(activa=True, es_base=False)


class MonedaForm(forms.ModelForm):
    """
    Formulario para crear o editar monedas.

    Validaciones principales:
    - Código de moneda único, considerando monedas inactivas.
    - Solo 'PYG' puede ser moneda base del sistema.
    """

    class Meta:
        model = Moneda
        fields = ['codigo', 'nombre', 'simbolo', 'decimales', 'activa']
        labels = {
            'codigo': 'Código ISO',
            'nombre': 'Nombre de la moneda',
            'simbolo': 'Símbolo',
            'decimales': 'Cantidad de decimales',
            'activa': 'Activa para operar',
        }
        widgets = {
            'codigo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'PYG'}),
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Guaraní paraguayo'}),
            'simbolo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '₲'}),
            'decimales': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 6}),
            'activa': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_codigo(self):
        """
        Valida que el código de la moneda sea único.

        :raises ValidationError: si ya existe otra moneda con el mismo código
        :return: código en mayúsculas
        """
        codigo = self.cleaned_data['codigo'].upper()
        if self.instance.pk:
            existe = Moneda.objects.all_with_inactive().exclude(pk=self.instance.pk).filter(codigo=codigo).exists()
        else:
            existe = Moneda.objects.all_with_inactive().filter(codigo=codigo).exists()

        if existe:
            raise ValidationError('Ya existe una moneda con este código.')

        return codigo

    def clean(self):
        """
        Validaciones generales del formulario.

        - Solo 'PYG' puede ser moneda base.
        :raises ValidationError: si se intenta asignar otra moneda como base
        :return: cleaned_data
        """
        cleaned_data = super().clean()
        codigo = cleaned_data.get('codigo', '').upper()

        if codigo != 'PYG' and self.instance.es_base:
            raise ValidationError('Solo la moneda PYG puede ser moneda base del sistema.')

        return cleaned_data


class TasaCambioForm(forms.ModelForm):
    """
    Formulario para crear o editar tasas de cambio.

    Validaciones principales:
    - La tasa de venta no puede ser menor que la de compra.
    - Solo se pueden seleccionar monedas activas que no sean base.
    """

    class Meta:
        model = TasaCambio
        fields = ['moneda', 'compra', 'venta', 'fuente', 'ts_fuente', 'activa']
        labels = {
            'moneda': 'Moneda',
            'compra': 'Compra',
            'venta': 'Venta',
            'fuente': 'Fuente',
            'ts_fuente': 'Timestamp de la fuente (opcional)'
        }
        widgets = {
            'moneda': forms.Select(attrs={'class': 'form-select'}),
            'compra': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'}),
            'venta': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0.01'}),
            'fuente': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Banco X / Manual / API'}),
            'ts_fuente': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'})
        }

    def __init__(self, *args, **kwargs):
        """
        Inicializa el formulario y limita la selección de moneda
        a monedas activas que no sean base.
        """
        super().__init__(*args, **kwargs)
        self.fields['moneda'].queryset = Moneda.objects.all().filter(activa=True, es_base=False)

    def clean(self):
        """
        Validaciones generales del formulario.

        - La tasa de venta no puede ser menor que la de compra.
        :raises ValidationError: si venta < compra
        :return: cleaned_data
        """
        cleaned = super().clean()
        compra = cleaned.get('compra')
        venta = cleaned.get('venta')
        if compra and venta and venta < compra:
            raise ValidationError('El precio de venta no puede ser menor al de compra.')
        return cleaned
