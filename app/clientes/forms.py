"""
Formularios para la aplicación de clientes.
Define los formularios y validaciones para la gestión de clientes.
"""
from django import forms
from .models import Cliente, TasaComision


class ClienteForm(forms.ModelForm):
    """
    Formulario para la gestión de clientes.
    """
    class Meta:
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
    Formulario para asignar usuarios a un cliente.
    """
    class Meta:
        model = Cliente
        fields = ["usuarios"]
        widgets = {
    """
    Formularios para la aplicación de clientes.
    Define los formularios y validaciones para la gestión de clientes.
    """
    """
    Formulario para la gestión de clientes.
    """
    """
    Formulario para asignar usuarios a un cliente.
    """
        }


class TasaComisionForm(forms.ModelForm):
    class Meta:
        model = TasaComision
        fields = ["tipo_cliente", "porcentaje", "vigente_desde", "vigente_hasta", "estado"]
        widgets = {
            "tipo_cliente": forms.Select(attrs={"class": "form-select"}),
            "porcentaje": forms.NumberInput(attrs={
                "class": "form-control",
                "step": "0.001",
                "min": "0",
                "placeholder": "Ej: 2.500"
            }),
            "vigente_desde": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "vigente_hasta": forms.DateInput(attrs={"type": "date", "class": "form-control"}),
            "estado": forms.Select(attrs={"class": "form-select"}),
        }
        labels = {
            "tipo_cliente": "Segmento",
            "porcentaje": "Porcentaje (%)",
            "vigente_desde": "Vigente desde",
            "vigente_hasta": "Vigente hasta",
            "estado": "Estado",
        }

    def clean_porcentaje(self):
        v = self.cleaned_data["porcentaje"]
        # Normaliza coma/decimal si te vienen strings; Django ya valida Decimal en general
        return v
