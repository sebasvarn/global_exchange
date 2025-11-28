from django.db.models.signals import post_save
from django.dispatch import receiver
from django.db import transaction
from transaccion.models import Transaccion
from .services import ServicioFacturacion
import logging
import threading
import time

logger = logging.getLogger(__name__)

@receiver(post_save, sender=Transaccion)
def generar_factura_automatica(sender, instance, created, **kwargs):
    """
    Genera la factura automáticamente cuando la transacción pasa a COMPLETADA.
    Evita duplicados, respeta la facturación manual desde Tauser y garantiza
    que la transacción esté totalmente disponible en la BD.
    """

    # 1. Solo si está COMPLETADA
    if instance.estado != 'COMPLETADA':
        return

    # 2. Evitar duplicados
    if hasattr(instance, 'factura_electronica'):
        return

    # 3. Evitar facturación desde Tauser
    if getattr(instance, '_generando_factura_desde_tauser', False):
        return

    # 4. (Opcional) Si no requiere factura automática
    if hasattr(instance, 'facturar_automaticamente'):
        if not instance.facturar_automaticamente:
            return

    def generar_async():
        try:
            # Asegurar que el commit del save haya finalizado
            time.sleep(0.5)

            logger.info(
                f"[SIGNAL] Generando FE automática para transacción {instance.codigo_verificacion}"
            )

            servicio = ServicioFacturacion()
            resultado = servicio.generar_factura(instance)

            if resultado['success']:
                logger.info(
                    f"[SIGNAL] ✓ Factura generada para transacción {instance.codigo_verificacion}"
                )
            else:
                logger.error(
                    f"[SIGNAL] ✗ Error al generar FE para {instance.codigo_verificacion}: {resultado['error']}"
                )

        except Exception as e:
            logger.error(f"[SIGNAL] Excepción en facturación automática: {e}", exc_info=True)

    # Ejecutar todo en hilo aparte
    threading.Thread(target=generar_async, daemon=True).start()
