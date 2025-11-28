"""
Forms de la aplicación 'monedas'.

Contiene formularios para la gestión de Moneda y TasaCambio:

- MonedaForm: creación y edición de monedas, con validaciones de código único
  y restricción de moneda base (solo 'PYG').
- TasaCambioForm: creación y edición de tasas de cambio, validando que
  venta >= compra y limitando la selección a monedas activas no base.

Los widgets utilizan clases de Bootstrap para una interfaz consistente.
"""
import json
from pathlib import Path
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
        # Solo monedas activas, no base y que no tengan ya un precio base/comisión asignado, excepto la actual en edición
        usadas = list(PrecioBaseComision.objects.values_list('moneda_id', flat=True))
        moneda_actual_id = self.instance.moneda_id if self.instance and self.instance.pk else None
        if moneda_actual_id in usadas:
            usadas.remove(moneda_actual_id)
        self.fields['moneda'].queryset = Moneda.objects.filter(activa=True, es_base=False).exclude(id__in=usadas)


class MonedaForm(forms.ModelForm):
    """
    Formulario para crear o editar monedas.

    Validaciones principales:
    - Código de moneda único, considerando monedas inactivas.
    - Solo 'PYG' puede ser moneda base del sistema.
    """

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Leer denominaciones.json y extraer códigos únicos
        json_path = Path(__file__).resolve().parent.parent / 'tauser' / 'denominaciones.json'
        try:
            with open(json_path, encoding='utf-8') as f:
                data = json.load(f)
            codigos = sorted(set([item['currency'] for item in data]))
        except Exception:
            codigos = []
        # Obtener los códigos ya existentes en la base de datos (incluyendo inactivas)
        from .models import Moneda
        existentes = set(Moneda.objects.all_with_inactive().values_list('codigo', flat=True))
        # Si es edición, permitir el código actual
        codigo_actual = self.instance.codigo if self.instance and self.instance.pk else None
        codigos_filtrados = [c for c in codigos if c not in existentes or c == codigo_actual]

        self.fields['codigo'].widget = forms.Select(choices=[(c, c) for c in codigos_filtrados], attrs={'class': 'form-select'})

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
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Guaraní paraguayo'}),
            'simbolo': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '₲'}),
            'decimales': forms.NumberInput(attrs={'class': 'form-control', 'min': 0, 'max': 6}),
            'activa': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

    def clean_codigo(self):
        """
        Valida que el código de la moneda sea único y cumple con las restricciones del sistema.

        :returns: Código de moneda validado y normalizado.
        :rtype: str
        :raises ValidationError: Si el código ya existe.
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
        Realiza validaciones generales del formulario de moneda, como restricciones de moneda base.

        :returns: Datos validados del formulario.
        :rtype: dict
        :raises ValidationError: Si alguna validación general falla.
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
        Realiza validaciones generales del formulario de tasa de cambio.

        :returns: Datos validados del formulario.
        :rtype: dict
        :raises ValidationError: Si la tasa de venta es menor que la de compra.
        """
        cleaned = super().clean()
        compra = cleaned.get('compra')
        venta = cleaned.get('venta')
        if compra and venta and venta < compra:
            raise ValidationError('El precio de venta no puede ser menor al de compra.')
        return cleaned
