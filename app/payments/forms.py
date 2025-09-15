from django import forms
from .models import PaymentMethod

class PaymentMethodForm(forms.ModelForm):
    """
    Formulario dinámico para crear y editar métodos de pago, mostrando campos según el tipo seleccionado.
    """
    class Meta:
        model = PaymentMethod
        fields = [
            'payment_type',
            # Cuenta bancaria
            'titular_cuenta', 'tipo_cuenta', 'banco', 'numero_cuenta',
            # Billetera
            'proveedor_billetera', 'billetera_email_telefono', 'billetera_titular',
            # Tarjeta
            'tarjeta_nombre', 'tarjeta_numero', 'tarjeta_vencimiento', 'tarjeta_cvv', 'tarjeta_marca',
        ]
        widgets = {
            'payment_type': forms.Select(attrs={'class': 'form-select'}),
            'titular_cuenta': forms.TextInput(attrs={'class': 'form-control'}),
            'tipo_cuenta': forms.TextInput(attrs={'class': 'form-control'}),
            'banco': forms.TextInput(attrs={'class': 'form-control'}),
            'numero_cuenta': forms.TextInput(attrs={'class': 'form-control'}),
            'proveedor_billetera': forms.TextInput(attrs={'class': 'form-control'}),
            'billetera_email_telefono': forms.TextInput(attrs={'class': 'form-control'}),
            'billetera_titular': forms.TextInput(attrs={'class': 'form-control'}),
            'tarjeta_nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'tarjeta_numero': forms.TextInput(attrs={'class': 'form-control'}),
            'tarjeta_vencimiento': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'MM/AA o MM/AAAA'}),
            'tarjeta_cvv': forms.TextInput(attrs={'class': 'form-control'}),
            'tarjeta_marca': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean(self):
        """
        Valida los campos requeridos según el tipo de método de pago seleccionado.
        """
        cleaned_data = super().clean()
        tipo = cleaned_data.get('payment_type')
        errors = {}
        if tipo == 'cuenta_bancaria':
            for field in ['titular_cuenta', 'tipo_cuenta', 'banco', 'numero_cuenta']:
                if not cleaned_data.get(field):
                    errors[field] = 'Este campo es obligatorio para cuenta bancaria.'
        elif tipo == 'billetera':
            for field in ['proveedor_billetera', 'billetera_email_telefono']:
                if not cleaned_data.get(field):
                    errors[field] = 'Este campo es obligatorio para billetera digital.'
        elif tipo == 'tarjeta':
            for field in ['tarjeta_nombre', 'tarjeta_numero', 'tarjeta_vencimiento', 'tarjeta_cvv']:
                if not cleaned_data.get(field):
                    errors[field] = 'Este campo es obligatorio para tarjeta de crédito.'
        if errors:
            raise forms.ValidationError(errors)
        return cleaned_data
