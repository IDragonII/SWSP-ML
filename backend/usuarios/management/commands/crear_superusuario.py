import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from usuarios.models import Rol


class Command(BaseCommand):
    help = (
        "Crea el superusuario inicial a partir de ADMIN_USERNAME y "
        "ADMIN_PASSWORD del .env (idempotente; no toca un usuario "
        "existente ni duplica si ya hay un superusuario). La cuenta "
        "nace con debe_cambiar_credenciales: el primer ingreso obliga "
        "a elegir usuario y contraseña propios (S24)."
    )

    def handle(self, *args, **options):
        username = os.getenv("ADMIN_USERNAME")
        password = os.getenv("ADMIN_PASSWORD")
        if not username or not password:
            raise CommandError("Falta ADMIN_USERNAME o ADMIN_PASSWORD en el .env.")

        Usuario = get_user_model()
        if Usuario.objects.filter(username=username).exists():
            self.stdout.write(f"El usuario '{username}' ya existe; no se modifica.")
            return
        # El superusuario puede haber renombrado su cuenta en el primer
        # ingreso: no crear otro desde el env (el env solo hace de
        # bootstrap, una vez)
        if Usuario.objects.filter(is_superuser=True).exists():
            self.stdout.write(
                "Ya existe un superusuario con otro nombre; no se crea otro."
            )
            return

        try:
            rol = Rol.objects.get(nombre="Administrador")
        except Rol.DoesNotExist:
            raise CommandError("No existe el rol 'Administrador'; ejecuta primero migrate.")

        Usuario.objects.create_superuser(
            username=username,
            email="",
            password=password,
            rol=rol,
            debe_cambiar_credenciales=True,
        )
        self.stdout.write(
            self.style.SUCCESS(f"Superusuario '{username}' creado con rol Administrador.")
        )
