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
            # Cheque
            'cheque_numero', 'cheque_banco', 'cheque_cuenta', 'cheque_orden', 'cheque_beneficiario', 'cheque_monto', 'cheque_moneda', 'cheque_fecha_emision',
        ]
        widgets = {
            'payment_type': forms.Select(attrs={'class': 'form-select'}),
            'titular_cuenta': forms.TextInput(attrs={'class': 'form-control'}),
            'tipo_cuenta': forms.TextInput(attrs={'class': 'form-control'}),
            'banco': forms.TextInput(attrs={'class': 'form-control'}),
            'tarjeta_vencimiento': forms.DateInput(attrs={'class': 'form-control', 'type': 'month', 'placeholder': 'MM/AAAA'}),
            'numero_cuenta': forms.TextInput(attrs={'class': 'form-control'}),
            'proveedor_billetera': forms.TextInput(attrs={'class': 'form-control'}),
            'billetera_email_telefono': forms.TextInput(attrs={'class': 'form-control'}),
            'billetera_titular': forms.TextInput(attrs={'class': 'form-control'}),
            'tarjeta_nombre': forms.TextInput(attrs={'class': 'form-control'}),
            'tarjeta_numero': forms.TextInput(attrs={'class': 'form-control', 'inputmode': 'numeric', 'pattern': '[0-9]*', 'maxlength': '16'}),
                # Eliminar el DateInput para tarjeta_vencimiento, solo usar TextInput con formato MM/AAAA
            'tarjeta_cvv': forms.TextInput(attrs={'class': 'form-control', 'inputmode': 'numeric', 'pattern': '[0-9]*', 'maxlength': '4'}),
            'tarjeta_marca': forms.TextInput(attrs={'class': 'form-control'}),
            'cheque_numero': forms.TextInput(attrs={'class': 'form-control'}),
            'cheque_banco': forms.TextInput(attrs={'class': 'form-control'}),
            'cheque_cuenta': forms.TextInput(attrs={'class': 'form-control'}),
            'cheque_orden': forms.TextInput(attrs={'class': 'form-control'}),
            'cheque_beneficiario': forms.TextInput(attrs={'class': 'form-control'}),
            'cheque_monto': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01', 'min': '0'}),
            'cheque_moneda': forms.TextInput(attrs={'class': 'form-control'}),
            'cheque_fecha_emision': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
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
            # Validar tipo de cuenta (solo letras y espacios)
            tipo_cuenta = cleaned_data.get('tipo_cuenta')
            if tipo_cuenta and not re.match(r'^[A-Za-zÁÉÍÓÚáéíóúÑñ ]+$', tipo_cuenta):
                errors['tipo_cuenta'] = 'El tipo de cuenta solo puede contener letras y espacios.'
            # Validar banco (letras, números, espacios, puntos, guiones y tildes)
            banco = cleaned_data.get('banco')
            if banco and not re.match(r'^[A-Za-zÁÉÍÓÚáéíóúÑñ0-9 .\-]+$', banco):
                errors['banco'] = 'El nombre del banco solo puede contener letras, números, espacios, puntos y guiones.'
            # Validar número de cuenta (solo números, mínimo 6 dígitos)
            numero_cuenta = cleaned_data.get('numero_cuenta')
            if numero_cuenta and not re.match(r'^\d{6,}$', numero_cuenta):
                errors['numero_cuenta'] = 'El número de cuenta debe tener al menos 6 dígitos y solo contener números.'
        elif tipo == PaymentTypeEnum.BILLETERA.value:
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
        elif tipo == PaymentTypeEnum.TARJETA.value:
            for field in ['tarjeta_nombre', 'tarjeta_numero', 'tarjeta_vencimiento', 'tarjeta_cvv', 'tarjeta_marca']:
                if not cleaned_data.get(field):
                    errors[field] = 'Este campo es obligatorio para tarjeta de crédito.'
            # Validar número de tarjeta (exactamente 16 dígitos)
            tarjeta_numero = cleaned_data.get('tarjeta_numero')
            if tarjeta_numero and (not tarjeta_numero.isdigit() or len(tarjeta_numero) != 16):
                errors['tarjeta_numero'] = 'El número de tarjeta debe tener exactamente 16 dígitos.'
            # Validar CVV (3 o 4 dígitos)
            tarjeta_cvv = cleaned_data.get('tarjeta_cvv')
            if tarjeta_cvv and (not tarjeta_cvv.isdigit() or len(tarjeta_cvv) not in [3, 4]):
                errors['tarjeta_cvv'] = 'El CVV debe tener 3 o 4 dígitos.'
            # Validar vencimiento (formato YYYY-MM y que no sea pasado)
            tarjeta_vencimiento = cleaned_data.get('tarjeta_vencimiento')
            if tarjeta_vencimiento:
                if not re.match(r'^\d{4}-\d{2}$', str(tarjeta_vencimiento)):
                    errors['tarjeta_vencimiento'] = 'El formato de la fecha debe ser YYYY-MM.'
                else:
                    try:
                        year, month = map(int, str(tarjeta_vencimiento).split('-'))
                        from datetime import date
                        today = date.today()
                        if year < today.year or (year == today.year and month < today.month):
                            errors['tarjeta_vencimiento'] = 'No puedes seleccionar un mes o año anterior al actual.'
                    except Exception:
                        errors['tarjeta_vencimiento'] = 'Fecha de vencimiento inválida.'
        elif tipo == PaymentTypeEnum.CHEQUE.value:
            for field in ['cheque_numero', 'cheque_banco', 'cheque_cuenta', 'cheque_orden', 'cheque_beneficiario', 'cheque_monto', 'cheque_moneda', 'cheque_fecha_emision']:
                if not cleaned_data.get(field):
                    errors[field] = 'Este campo es obligatorio para cheque.'
            # Validar número de cheque (solo números, mínimo 4 dígitos)
            cheque_numero = cleaned_data.get('cheque_numero')
            if cheque_numero and not re.match(r'^\d{4,}$', cheque_numero):
                errors['cheque_numero'] = 'El número de cheque debe tener al menos 4 dígitos y solo contener números.'
            # Validar banco (letras, números, espacios, puntos, guiones y tildes)
            cheque_banco = cleaned_data.get('cheque_banco')
            if cheque_banco and not re.match(r'^[A-Za-zÁÉÍÓÚáéíóúÑñ0-9 .\-]+$', cheque_banco):
                errors['cheque_banco'] = 'El nombre del banco solo puede contener letras, números, espacios, puntos y guiones.'
            # Validar cuenta (solo números, mínimo 6 dígitos)
            cheque_cuenta = cleaned_data.get('cheque_cuenta')
            if cheque_cuenta and not re.match(r'^\d{6,}$', cheque_cuenta):
                errors['cheque_cuenta'] = 'El número de cuenta debe tener al menos 6 dígitos y solo contener números.'
            # Validar monto (positivo)
            cheque_monto = cleaned_data.get('cheque_monto')
            if cheque_monto is not None and cheque_monto <= 0:
                errors['cheque_monto'] = 'El monto debe ser mayor a cero.'
            # Validar moneda (solo letras y espacios)
            cheque_moneda = cleaned_data.get('cheque_moneda')
            if cheque_moneda and not re.match(r'^[A-Za-zÁÉÍÓÚáéíóúÑñ ]+$', cheque_moneda):
                errors['cheque_moneda'] = 'La moneda solo puede contener letras y espacios.'
            # Validar fecha de emisión (no puede ser anterior a hoy)
            cheque_fecha_emision = cleaned_data.get('cheque_fecha_emision')
            if cheque_fecha_emision:
                from datetime import date
                if cheque_fecha_emision < date.today():
                    errors['cheque_fecha_emision'] = 'La fecha de emisión no puede ser anterior a hoy.'
        if errors:
            raise forms.ValidationError(errors)
        return cleaned_data




