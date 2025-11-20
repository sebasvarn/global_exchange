# transacciones/forms.py
from django import forms
from .models import Transaccion
from commons.enums import TipoTransaccionEnum


class TransaccionForm(forms.ModelForm):
    class Meta:
        model = Transaccion
        fields = ["cliente", "tipo", "moneda", "monto_operado", "medio_pago"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from clientes.models import Cliente
        from monedas.models import Moneda
        from payments.models import PaymentMethod

        self.fields["cliente"].queryset = Cliente.objects.all()
        # Excluir la moneda base (PYG) del select
        self.fields["moneda"].queryset = Moneda.objects.filter(activa=True, es_base=False)
        self.fields["medio_pago"].queryset = PaymentMethod.objects.none()

        if "cliente" in self.data:
            try:
                cliente_id = int(self.data.get("cliente"))
                self.fields["medio_pago"].queryset = PaymentMethod.objects.filter(cliente_id=cliente_id)
            except (ValueError, TypeError):
                pass
        elif self.instance.pk:
            self.fields["medio_pago"].queryset = self.instance.cliente.metodos_pago.all()
