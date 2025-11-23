from django.contrib import admin
from .models import PagoPasarela


@admin.register(PagoPasarela)
class PagoPasarelaAdmin(admin.ModelAdmin):
    """Administración de pagos de pasarela"""
    
    list_display = [
        'id_pago_externo',
        'transaccion',
        'metodo_pasarela',
        'monto',
        'moneda',
        'estado',
        'fecha_creacion'
    ]
    
    list_filter = [
        'estado',
        'metodo_pasarela',
        'moneda',
        'fecha_creacion'
    ]
    
    search_fields = [
        'id_pago_externo',
        'transaccion__id_transaccion',
        'mensaje_error'
    ]
    
    readonly_fields = [
        'id_pago_externo',
        'transaccion',
        'fecha_creacion',
        'fecha_actualizacion',
        'fecha_procesamiento',
        'respuesta_pasarela',
        'datos_pago'
    ]
    
    fieldsets = (
        ('Información Principal', {
            'fields': (
                'transaccion',
                'id_pago_externo',
                'estado',
            )
        }),
        ('Detalles del Pago', {
            'fields': (
                'monto',
                'moneda',
                'metodo_pasarela',
            )
        }),
        ('Datos Técnicos', {
            'fields': (
                'datos_pago',
                'respuesta_pasarela',
            ),
            'classes': ('collapse',)
        }),
        ('Fechas', {
            'fields': (
                'fecha_creacion',
                'fecha_actualizacion',
                'fecha_procesamiento',
            )
        }),
        ('Errores', {
            'fields': ('mensaje_error',),
            'classes': ('collapse',)
        }),
    )
    
    def has_add_permission(self, request):
        """No permitir crear pagos manualmente"""
        return False
    
    def has_delete_permission(self, request, obj=None):
        """No permitir eliminar pagos"""
        return False
