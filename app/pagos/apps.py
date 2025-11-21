from django.apps import AppConfig


class PagosConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'pagos'
    verbose_name = 'Procesamiento de Pagos'
    
    def ready(self):
        """Importar signals cuando la app esté lista"""
        try:
            import pagos.signals  # noqa
        except ImportError:
            pass
