from django.db.models.signals import post_save
from django.dispatch import receiver
from transaccion.models import Transaccion
from .services import ServicioFacturacion
from .models import FacturaElectronica
import threading
import time

@receiver(post_save, sender=Transaccion)
def generar_factura_automatica(sender, instance, created, **kwargs):
    """
    Genera factura automáticamente cuando una transacción se marca como COMPLETADA
    y no tiene factura asociada
    """
    if instance.estado == 'COMPLETADA' and not hasattr(instance, 'factura_electronica'):
        def generar_async():
            # Pequeña espera para asegurar commit de la transacción
            time.sleep(3)
            try:
                servicio = ServicioFacturacion()
                servicio.generar_factura(instance)
                print(f"Factura generada para transacción {instance.codigo_verificacion}")
            except Exception as e:
                print(f"Error al generar factura automática: {e}")
        
        # Ejecutar en hilo separado para no bloquear
        thread = threading.Thread(target=generar_async)
        thread.daemon = True
        thread.start()