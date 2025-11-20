"""
Formularios para la aplicación de clientes.

Este módulo define los formularios y validaciones relacionados con la gestión de clientes
y las tasas de comisión. Contiene clases basadas en ModelForm para facilitar la
creación, edición y asignación de usuarios a clientes, así como la configuración de
descuentos por segmento.
"""

from django import forms
from decimal import Decimal
from .models import Cliente, TasaComision, LimiteClienteTipo


class ClienteForm(forms.ModelForm):
    """
    Formulario principal para la gestión de clientes.

    Permite crear o editar un cliente especificando:
    - nombre
    - tipo de cliente (segmento)
    - usuarios asociados

    Attributes:
        Meta (ModelForm.Meta): Configuración de campos, widgets y etiquetas.
    """

    class Meta:
        """
        Configuración del formulario ClienteForm.

        Attributes:
            model (Model): Modelo Cliente al que está asociado el formulario.
            fields (list): Campos a incluir en el formulario.
            widgets (dict): Widgets personalizados para la visualización de campos.
            labels (dict): Etiquetas legibles para los campos del formulario.
        """
        model = Cliente
        fields = ["nombre", "tipo", "usuarios"]
        widgets = {
            "usuarios": forms.CheckboxSelectMultiple,
        }
        labels = {
            "nombre": "Nombre del Cliente",
            "tipo": "Segmento del Cliente",
            "usuarios": "Usuarios Asociados",
        }


class AsignarUsuariosAClienteForm(forms.ModelForm):
    """
    Formulario para asignar usuarios a un cliente existente.

    Este formulario permite vincular o desvincular múltiples usuarios
    a un cliente ya registrado.

    Attributes:
        Meta (ModelForm.Meta): Configuración de campos y widgets.
    """

    class Meta:
        """
        Configuración del formulario AsignarUsuariosAClienteForm.

        Attributes:
            model (Model): Modelo Cliente al que está asociado el formulario.
            fields (list): Campos a incluir en el formulario.
            widgets (dict): Widgets personalizados para la visualización de campos.
        """
        model = Cliente
        fields = ["usuarios"]
        widgets = {
            "usuarios": forms.CheckboxSelectMultiple,
        }


class TasaComisionForm(forms.ModelForm):
    """
    Formulario para gestionar las tasas de comisión por tipo de cliente.

    Permite definir:
    - tipo de cliente (segmento)
    - porcentaje de descuento
    - rango de vigencia (desde/hasta)
    - estado de la tasa

    Attributes:
        Meta (ModelForm.Meta): Configuración de campos, widgets y etiquetas.

    Methods:
        clean_porcentaje():
            Valida el campo de porcentaje antes de guardar los datos limpios.
    """

    class Meta:
        """
        Configuración del formulario TasaComisionForm.

        Attributes:
            model (Model): Modelo TasaComision al que está asociado el formulario.
            fields (list): Campos a incluir en el formulario.
            widgets (dict): Widgets personalizados para cada campo.
            labels (dict): Etiquetas legibles para los campos del formulario.
        """
        model = TasaComision
        fields = ["tipo_cliente", "porcentaje", "vigente_desde", "vigente_hasta", "estado"]
        widgets = {
            "tipo_cliente": forms.Select(attrs={"class": "form-select"}),
            "porcentaje": forms.NumberInput(attrs={
                "class": "form-control",
                "step": "0.001",
                "min": "0",
                "placeholder": "Ej: 2.500  (descuento %)"
            }),
            "vigente_desde": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "vigente_hasta": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "estado": forms.Select(attrs={"class": "form-select"}),
        }
        labels = {
            "tipo_cliente": "Segmento",
            "porcentaje": "Descuento (%)",
            "vigente_desde": "Vigente desde",
            "vigente_hasta": "Vigente hasta",
            "estado": "Estado",
        }

    def clean_porcentaje(self):
        """
        Validación del campo 'porcentaje'.

        Returns:
            float: Valor del porcentaje validado.
        """
        v = self.cleaned_data["porcentaje"]
        return v


class LimiteClienteTipoForm(forms.ModelForm):
    class Meta:
        model = LimiteClienteTipo
        fields = ["tipo_cliente", "limite_diario", "limite_mensual"]
        labels = {
            "tipo_cliente": "Tipo de Cliente",
            "limite_diario": "Límite Diario (PYG)",
            "limite_mensual": "Límite Mensual (PYG)",
        }
        widgets = {
            "limite_diario": forms.TextInput(attrs={"class": "form-control", "inputmode": "numeric", "pattern": "[0-9.]*"}),
            "limite_mensual": forms.TextInput(attrs={"class": "form-control", "inputmode": "numeric", "pattern": "[0-9.]*"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['tipo_cliente'].disabled = True
        # Mostrar los valores como enteros con puntos de miles (sin decimales)
        for field in ['limite_diario', 'limite_mensual']:
            if self.initial.get(field) is not None:
                valor = int(Decimal(self.initial[field]))
                self.initial[field] = f"{valor:,}".replace(",", ".")
