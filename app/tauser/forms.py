from django import forms
from .models import Tauser, TauserStock, Denominacion
from monedas.models import Moneda
import json
import os


class TauserForm(forms.ModelForm):
    class Meta:
        model = Tauser
        fields = ['ubicacion', 'estado']
        widgets = {
            'ubicacion': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Ubicación'}),
            'estado': forms.Select(attrs={'class': 'form-select'}),
        }



class TauserStockForm(forms.Form):
    tauser = forms.ModelChoiceField(queryset=Tauser.objects.all(), label="TAUser", widget=forms.Select(attrs={'class': 'form-select'}))
    moneda = forms.ModelChoiceField(queryset=Moneda.objects.all(), label="Moneda", widget=forms.Select(attrs={'class': 'form-select', 'onchange': 'this.form.submit();'}))
    operacion = forms.ChoiceField(
        choices=[('agregar', 'Agregar'), ('descontar', 'Descontar')],
        label="Operación",
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    def __init__(self, *args, **kwargs):
        denominaciones = kwargs.pop('denominaciones', None)
        super().__init__(*args, **kwargs)
        # Si hay denominaciones, agregarlas dinámicamente
        if denominaciones:
            for d in denominaciones:
                field_name = f"den_{d['type']}_{str(d['value']).replace('.', '_')}"
                self.fields[field_name] = forms.IntegerField(
                    label=f"{d['type'].capitalize()} {d['value']}",
                    min_value=0,
                    required=False,
                    widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': 'Cantidad'})
                )
