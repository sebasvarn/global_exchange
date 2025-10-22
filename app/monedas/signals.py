from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from .models import PrecioBaseComision, TasaCambio


# Guardar los valores originales antes de guardar
@receiver(pre_save, sender=PrecioBaseComision)
def guardar_valores_antes_de_guardar(sender, instance, **kwargs):
    if instance.pk:
        try:
            old = sender.objects.get(pk=instance.pk)
            instance._old_precio_base = old.precio_base
            instance._old_comision_compra = old.comision_compra
            instance._old_comision_venta = old.comision_venta
        except sender.DoesNotExist:
            instance._old_precio_base = None
            instance._old_comision_compra = None
            instance._old_comision_venta = None
    else:
        instance._old_precio_base = None
        instance._old_comision_compra = None
        instance._old_comision_venta = None

# Crear registro en TasaCambio solo si hubo cambio
@receiver(post_save, sender=PrecioBaseComision)
def crear_tasacambio_al_editar_precio_base(sender, instance, created, **kwargs):
    compra = instance.precio_base - instance.comision_compra
    venta = instance.precio_base + instance.comision_venta
    if created:
        TasaCambio.objects.create(
            moneda=instance.moneda,
            compra=compra,
            venta=venta,
            fuente='BCP',
            es_automatica=True,
            activa=True
        )
    else:
        old_precio_base = getattr(instance, '_old_precio_base', None)
        old_comision_compra = getattr(instance, '_old_comision_compra', None)
        old_comision_venta = getattr(instance, '_old_comision_venta', None)
        if (
            old_precio_base is not None and (
                old_precio_base != instance.precio_base or
                old_comision_compra != instance.comision_compra or
                old_comision_venta != instance.comision_venta
            )
        ):
            TasaCambio.objects.create(
                moneda=instance.moneda,
                compra=compra,
                venta=venta,
                fuente='BCP',
                es_automatica=True,
                activa=True
            )
