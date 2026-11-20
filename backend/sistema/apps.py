from django.apps import AppConfig


class SistemaConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "sistema"
    verbose_name = "Configuración del sistema"

    def ready(self):
        # Despliegue gratuito (S24): con TRABAJADOR_EN_WEB=1 el bucle de
        # entrenamientos corre en un hilo de este proceso; sin la bandera
        # (local, pruebas) no arranca nada. Ver sistema/trabajador_web.py.
        from sistema import trabajador_web

        trabajador_web.iniciar()
