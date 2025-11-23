from django import forms
import re
from commons.enums import PaymentTypeEnum
from .models import PaymentMethod, ComisionMetodoPago
# Formulario para editar comisiones por método de pago
class ComisionMetodoPagoForm(forms.ModelForm):
    class Meta:
        model = ComisionMetodoPago
        fields = ['tipo_metodo', 'porcentaje_comision']
        widgets = {
            'tipo_metodo': forms.Select(attrs={'class': 'form-select'}),
            'porcentaje_comision': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0', 'max': '100'}),
        }

class PaymentMethodForm(forms.ModelForm):
    """
    Formulario dinámico para crear y editar métodos de pago guardados.
    Solo incluye: CUENTA_BANCARIA y BILLETERA.
    """
    class Meta:
        model = PaymentMethod
        fields = [
            'payment_type',
            # Cuenta bancaria
            'titular_cuenta', 'tipo_cuenta', 'banco', 'numero_cuenta',
            # Billetera
            'proveedor_billetera', 'billetera_email_telefono', 'billetera_titular',
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
        }

    def clean(self):
        cleaned_data = super().clean()
        tipo = cleaned_data.get('payment_type')
        errors = {}

        if tipo == PaymentTypeEnum.CUENTA_BANCARIA.value:
            # Validar campos obligatorios
            for field in ['titular_cuenta', 'tipo_cuenta', 'banco', 'numero_cuenta']:
                if not cleaned_data.get(field):
                    errors[field] = 'Este campo es obligatorio para cuenta bancaria.'
            
            # Validar nombre del titular (solo letras y espacios)
            titular = cleaned_data.get('titular_cuenta')
            if titular and not re.match(r'^[A-Za-zÁÉÍÓÚáéíóúÑñ ]+$', titular):
                errors['titular_cuenta'] = 'El nombre del titular solo puede contener letras y espacios.'
            
            # Validar número de cuenta (solo números, mínimo 6 dígitos)
            numero_cuenta = cleaned_data.get('numero_cuenta')
            if numero_cuenta and not re.match(r'^\d{6,}$', numero_cuenta):
                errors['numero_cuenta'] = 'El número de cuenta debe tener al menos 6 dígitos y solo contener números.'
        
        elif tipo == PaymentTypeEnum.BILLETERA.value:
            # Validar campos obligatorios
            for field in ['proveedor_billetera', 'billetera_email_telefono']:
                if not cleaned_data.get(field):
                    errors[field] = 'Este campo es obligatorio para billetera digital.'
            
            # Validar proveedor de billetera (solo letras y espacios)
            proveedor = cleaned_data.get('proveedor_billetera')
            if proveedor and not re.match(r'^[A-Za-zÁÉÍÓÚáéíóúÑñ ]+$', proveedor):
                errors['proveedor_billetera'] = 'El proveedor solo puede contener letras y espacios.'
            
            # Validar nombre del titular de billetera (si se ingresa, solo letras y espacios)
            billetera_titular = cleaned_data.get('billetera_titular')
            if billetera_titular and not re.match(r'^[A-Za-zÁÉÍÓÚáéíóúÑñ ]+$', billetera_titular):
                errors['billetera_titular'] = 'El nombre del titular solo puede contener letras y espacios.'
            
            # Validar email o teléfono
            billetera_email_telefono = cleaned_data.get('billetera_email_telefono')
            if billetera_email_telefono:
                if billetera_email_telefono.isdigit():
                    # Solo números: debe empezar con 09 y tener 10 dígitos
                    if not re.match(r'^09\d{8}$', billetera_email_telefono):
                        errors['billetera_email_telefono'] = 'El número debe empezar con 09 y tener exactamente 10 dígitos.'
                else:
                    # Si contiene letras o símbolos, debe terminar en @gmail.com
                    if not billetera_email_telefono.endswith('@gmail.com'):
                        errors['billetera_email_telefono'] = 'El email debe terminar en @gmail.com.'
        
        if errors:
            raise forms.ValidationError(errors)
        
        return cleaned_data