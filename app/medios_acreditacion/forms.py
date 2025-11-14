from django import forms
from .models import MedioAcreditacion
from commons.enums import TipoMedioAcreditacionEnum

class MedioAcreditacionForm(forms.ModelForm):
    """
    Formulario para crear o editar medios de acreditación.

    Muestra dinámicamente campos según el tipo de medio seleccionado:
    - Cuenta bancaria: muestra campos relacionados con la cuenta.
    - Billetera digital: muestra campos relacionados con la billetera.

    :param forms.ModelForm: Hereda de ModelForm de Django para enlace con el modelo MedioAcreditacion.
    """


    TIPO_CUENTA_CHOICES = [
        ('caja_ahorro', 'Caja de Ahorro'),
        ('cuenta_corriente', 'Cuenta Corriente'),
    ]
    BANCO_CHOICES = [
        ('banco_nacional_de_fomento', 'Banco Nacional de Fomento'),
        ('banco_continental', 'Banco Continental'),
        ('ueno_bank', 'Ueno Bank'),
        ('banco_itau', 'Banco Itaú'),
        ('banco_familiar', 'Banco Familiar'),
        ('banco_atlas', 'Banco Atlas'),
        ('zeta_bank', 'Zeta Bank'),
        ('interfisa_banco', 'Interfisa Banco'),
        ('financiera_paraguayo_japonesa', 'Financiera Paraguayo Japonesa'),
    ]

    tipo_cuenta = forms.ChoiceField(choices=[('', '---------')] + TIPO_CUENTA_CHOICES, widget=forms.Select(attrs={'class': 'form-select'}), required=False)
    banco = forms.ChoiceField(choices=[('', '---------')] + BANCO_CHOICES, widget=forms.Select(attrs={'class': 'form-select'}), required=False)

    class Meta:
        model = MedioAcreditacion
        fields = [
            'tipo_medio',
            # Cuenta bancaria
            'titular_cuenta', 'tipo_cuenta', 'banco', 'numero_cuenta',
            # Billetera
            'proveedor_billetera', 'billetera_email_telefono', 'billetera_titular',
        ]
        widgets = {
            'tipo_medio': forms.Select(attrs={'class': 'form-select'}),
            'titular_cuenta': forms.TextInput(attrs={'class': 'form-control'}),
            'numero_cuenta': forms.TextInput(attrs={'class': 'form-control'}),
            'proveedor_billetera': forms.TextInput(attrs={'class': 'form-control'}),
            'billetera_email_telefono': forms.TextInput(attrs={'class': 'form-control'}),
            'billetera_titular': forms.TextInput(attrs={'class': 'form-control'}),
        }

    def clean(self):
        """
        Valida los campos según el tipo de medio de acreditación seleccionado, pero sin validar tipo_cuenta ni banco.
        """
        import re

        cleaned_data = super().clean()
        tipo = cleaned_data.get('tipo_medio')
        errors = {}

        if tipo == TipoMedioAcreditacionEnum.CUENTA_BANCARIA.value:
            # Validar campos obligatorios (excepto tipo_cuenta y banco)
            for field in ['titular_cuenta', 'numero_cuenta']:
                if not cleaned_data.get(field):
                    errors[field] = 'Este campo es obligatorio para cuenta bancaria.'
            # Validaciones específicas solo para titular_cuenta y numero_cuenta
            titular = cleaned_data.get('titular_cuenta')
            if titular and not re.match(r'^[A-Za-zÁÉÍÓÚáéíóúÑñ ]+$', titular):
                errors['titular_cuenta'] = 'El nombre del titular solo puede contener letras y espacios.'
            numero_cuenta = cleaned_data.get('numero_cuenta')
            if numero_cuenta and not re.match(r'^\d{6,}$', numero_cuenta):
                errors['numero_cuenta'] = 'El número de cuenta debe tener al menos 6 dígitos y solo contener números.'

        elif tipo == TipoMedioAcreditacionEnum.BILLETERA.value:
            for field in ['proveedor_billetera', 'billetera_email_telefono']:
                if not cleaned_data.get(field):
                    errors[field] = 'Este campo es obligatorio para billetera digital.'
            proveedor = cleaned_data.get('proveedor_billetera')
            if proveedor and not re.match(r'^[A-Za-zÁÉÍÓÚáéíóúÑñ ]+$', proveedor):
                errors['proveedor_billetera'] = 'El proveedor solo puede contener letras y espacios.'
            billetera_titular = cleaned_data.get('billetera_titular')
            if billetera_titular and not re.match(r'^[A-Za-zÁÉÍÓÚáéíóúÑñ ]+$', billetera_titular):
                errors['billetera_titular'] = 'El nombre del titular solo puede contener letras y espacios.'
            billetera_email_telefono = cleaned_data.get('billetera_email_telefono')
            if billetera_email_telefono:
                if billetera_email_telefono.isdigit():
                    if not re.match(r'^09\d{8}$', billetera_email_telefono):
                        errors['billetera_email_telefono'] = 'El número debe empezar con 09 y tener exactamente 10 dígitos.'
                else:
                    if not billetera_email_telefono.endswith('@gmail.com'):
                        errors['billetera_email_telefono'] = 'El email debe terminar en @gmail.com.'

        if errors:
            raise forms.ValidationError(errors)

        return cleaned_data
