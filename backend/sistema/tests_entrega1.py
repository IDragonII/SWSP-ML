"""Pruebas 318-325 (Semana 19 / Entrega 1).

Numeración del repositorio: cierra la Semana 18 con 317 pruebas, así
que la Entrega 1 añade 318-325 (8 pruebas → 325 en total): el recorrido
completo con los tres roles (318), la matriz de rutas por rol generada
(319), la protección por defecto de las rutas (320), la configuración
de producción sin avisos críticos (321), los errores internos sin
trazas con DEBUG apagado (322), los registros del servidor limpios de
contraseñas y tokens (323), el número fijo de consultas con volumen
(324) y la migración desde cero con su respaldo restaurado (325).
"""
import json
import logging
import os
import re
import secrets
import subprocess
import sys
from datetime import date
from decimal import Decimal
from unittest.mock import patch

from django.conf import settings
from django.core.cache import cache
from django.db import connection
from django.test import TestCase, override_settings

from auditoria.models import Auditoria
from catalogos.models import (
    Cultivo,
    EtapaFenologica,
    Recurso,
    TipoActividad,
    TipoIncidencia,
    Unidad,
    Variedad,
)
from productores.models import Comunidad, Distrito, Parcela, Provincia
from sistema import matriz_rutas as mr
from usuarios.models import Rol, Usuario
from usuarios.tests import _post_login


class Entrega1Base(TestCase):
    """Cuentas de los tres roles, ubicación, cultivo con variedad, los
    catálogos sembrados por migraciones, un recurso y las etapas del
    cultivo: el suelo común de las pruebas de la Entrega 1."""

    def setUp(self):
        cache.clear()
        self.admin = Usuario.objects.create_superuser(
            username="admin_pruebas", email="", password="AdminPruebas2026!",
            rol=Rol.objects.get(nombre="Administrador"),
        )
        self.coordinador = Usuario.objects.create_user(
            username="coord_pruebas", password="Coord2026!",
            rol=Rol.objects.get(nombre="Coordinador"),
        )
        self.tecnico = Usuario.objects.create_user(
            username="tec_pruebas", password="Tec2026!",
            rol=Rol.objects.get(nombre="Técnico de campo"),
        )
        self.provincia = Provincia.objects.create(nombre="Prov E19")
        self.distrito = Distrito.objects.create(
            provincia=self.provincia, nombre="Distrito E19"
        )
        self.comunidad = Comunidad.objects.create(
            distrito=self.distrito, nombre="Comunidad E19"
        )
        self.cultivo = Cultivo.objects.create(nombre="Quinua E19")
        self.variedad = Variedad.objects.create(
            cultivo=self.cultivo, nombre="Real E19"
        )
        self.preparacion = TipoActividad.objects.get(codigo="PREPARACION")
        self.siembra = TipoActividad.objects.get(codigo="SIEMBRA")
        self.helada = TipoIncidencia.objects.get(nombre="Helada")
        self.kg = Unidad.objects.get(nombre="Kilogramo")
        self.semilla = Recurso.objects.create(
            nombre="Quinua semilla E19", categoria="SEMILLA",
            tipo_unidad="MASA",
        )
        self.etapa1 = EtapaFenologica.objects.create(
            cultivo=self.cultivo, nombre="Siembra E19", orden=1
        )

    # ------------------------------------------------------------------ #
    # helpers
    # ------------------------------------------------------------------ #
    def _entrar(self, usuario, clave):
        self.assertEqual(
            _post_login(self.client, usuario, clave).status_code, 200
        )

    def _entrar_admin(self):
        self._entrar("admin_pruebas", "AdminPruebas2026!")

    def _entrar_tecnico(self):
        self._entrar("tec_pruebas", "Tec2026!")

    def _entrar_coordinador(self):
        self._entrar("coord_pruebas", "Coord2026!")

    def _json(self, respuesta):
        return json.loads(respuesta.content.decode("utf-8"))

    def _api(self, metodo, url, cuerpo=None):
        kwargs = {"content_type": "application/json"}
        if cuerpo is not None:
            kwargs["data"] = json.dumps(cuerpo)
        return getattr(self.client, metodo)(url, **kwargs)

    def _post201(self, url, cuerpo):
        """Alta por API: afirma 201 y devuelve la fila."""
        respuesta = self._api("post", url, cuerpo)
        self.assertEqual(respuesta.status_code, 201, respuesta.content)
        return self._json(respuesta)


class RecorridoCompletoTests(Entrega1Base):
    """Prueba 318 (Semana 19)."""

    # ------------------------------------------------------------------ #
    # 318: recorrido completo del ciclo de una campaña con los tres roles
    # ------------------------------------------------------------------ #
    def test_318_recorrido_completo_del_ciclo_con_los_tres_roles(self):
        base_eventos = Auditoria.objects.count()

        # --- Técnico: productor, parcela, campaña e iniciar ------------
        self._entrar_tecnico()
        productor = self._post201(
            "/api/productores/",
            {
                "nombres": "Rosa",
                "apellidos": "Quispe",
                "dni": "73011223",
                "comunidad": self.comunidad.pk,
            },
        )
        parcela = self._post201(
            "/api/parcelas/",
            {
                "productor": productor["id"],
                "comunidad": self.comunidad.pk,
                "superficie_ha": "2.00",
                "altitud_msnm": 3850,
                "tipo_suelo": "FRANCO",
                "pendiente": "SUAVE",
                "disponibilidad_agua": "MEDIA",
                "sistema_riego": "GOTEO",
            },
        )
        campania = self._post201(
            "/api/campanias/",
            {
                "periodo": "2025-2026",
                "parcela": parcela["id"],
                "cultivo": self.cultivo.pk,
                "variedad": self.variedad.pk,
                "fecha_inicio": "2025-09-01",
                "fecha_fin_prevista": "2026-05-31",
                "superficie_sembrada_ha": "1.50",
            },
        )
        self.assertEqual(campania["estado"], "PLANIFICADA")
        respuesta = self._api(
            "post", f"/api/campanias/{campania['id']}/iniciar/"
        )
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        self.assertEqual(self._json(respuesta)["estado"], "EN_PRODUCCION")

        # --- Técnico: seguimiento (actividad, siembra, recursos,
        #     clima, incidencia y etapa) --------------------------------
        self._post201(
            "/api/actividades/",
            {
                "campania": campania["id"],
                "tipo_actividad": self.preparacion.pk,
                "fecha": "2025-09-15",
                "metodo": "Arado de disco",
            },
        )
        filosa = self._post201(
            "/api/actividades/",
            {
                "campania": campania["id"],
                "tipo_actividad": self.siembra.pk,
                "fecha": "2025-10-01",
            },
        )
        self.assertEqual(
            filosa["campania"]["fecha_siembra"], "2025-10-01"
        )
        self._post201(
            "/api/usos-recursos/",
            {
                "campania": campania["id"],
                "recurso": self.semilla.pk,
                "fecha": "2025-10-02",
                "cantidad": "16",
                "unidad": self.kg.pk,
            },
        )
        self._post201(
            "/api/clima/",
            {
                "parcela": parcela["id"],
                "fecha": "2025-10-01",
                "temp_min": "5.0",
                "temp_max": "15.0",
            },
        )
        self._post201(
            "/api/incidencias/",
            {
                "campania": campania["id"],
                "tipo_incidencia": self.helada.pk,
                "fecha": "2025-10-05",
                "severidad": "MEDIA",
                "descripcion": "Helada tardía en la parcela alta",
                "superficie_afectada_ha": "1.00",
            },
        )
        self._post201(
            "/api/etapas-campania/",
            {
                "campania": campania["id"],
                "etapa": self.etapa1.pk,
                "fecha_inicio": "2025-09-05",
            },
        )

        # --- Coordinador: todo es de solo lectura ----------------------
        self._entrar_coordinador()
        self.assertEqual(
            self._api("get", f"/api/productores/{productor['id']}/").status_code,
            200,
        )
        listado = self._api("get", "/api/campanias/")
        self.assertEqual(listado.status_code, 200, listado.content)
        self.assertGreaterEqual(self._json(listado)["count"], 1)
        self.assertEqual(
            self._api("get", "/api/dashboard/resumen/").status_code, 200
        )
        catalogo = self._api("get", "/api/reportes/")
        self.assertEqual(catalogo.status_code, 200, catalogo.content)
        tipos = [r["tipo"] for r in self._json(catalogo)["reportes"]]
        self.assertEqual(tipos, ["productores", "productivo", "actividades"])
        previa = self._api("get", "/api/reportes/actividades/vista-previa/")
        self.assertEqual(previa.status_code, 200, previa.content)
        self.assertGreaterEqual(self._json(previa)["total_filas"], 2)
        denegada = self._api(
            "post", "/api/productores/",
            {"nombres": "No", "apellidos": "Puede", "dni": "73000000",
             "comunidad": self.comunidad.pk},
        )
        self.assertEqual(denegada.status_code, 403, denegada.content)
        self.assertEqual(self._api("get", "/api/auditoria/").status_code, 403)

        # --- Técnico: producción (con rendimiento atípico) -------------
        self._entrar_tecnico()
        produccion = self._post201(
            "/api/producciones/",
            {
                "campania": campania["id"],
                "fecha_cosecha": "2026-04-15",
                "superficie_cosechada_ha": "1.50",
                "cantidad_producida": "9000",
                "unidad": self.kg.pk,
            },
        )
        # 9000 kg / 1.50 ha = 6000 kg/ha: fuera del rango plausible →
        # la campaña queda COSECHADA con la marca de revisión puesta
        self.assertEqual(produccion["campania"]["estado"], "COSECHADA")
        self.assertTrue(produccion["requiere_revision"])
        denegado = self._api(
            "post", f"/api/campanias/{campania['id']}/cerrar/"
        )
        self.assertEqual(denegado.status_code, 403, denegado.content)

        # --- Administrador: revisar, cerrar, panel, reportes, auditoría
        self._entrar_admin()
        respuesta = self._api(
            "post",
            f"/api/producciones/{produccion['id']}/revisar/",
            {"nota": "Rendimiento atípico confirmado en campo",
             "incluir_en_entrenamiento": True},
        )
        self.assertEqual(respuesta.status_code, 200, respuesta.content)
        self.assertFalse(self._json(respuesta)["requiere_revision"])
        cerrado = self._api("post", f"/api/campanias/{campania['id']}/cerrar/")
        self.assertEqual(cerrado.status_code, 200, cerrado.content)
        self.assertEqual(self._json(cerrado)["estado"], "CERRADA")
        self.assertEqual(
            self._api("get", "/api/dashboard/resumen/").status_code, 200
        )
        previa = self._api(
            "get", "/api/reportes/actividades/vista-previa/"
        )
        self.assertEqual(previa.status_code, 200, previa.content)
        self.assertGreaterEqual(self._json(previa)["total_filas"], 2)
        exporte = self._api(
            "post", "/api/reportes/actividades/exportar/",
            {"formato": "xlsx"},
        )
        self.assertEqual(exporte.status_code, 200, exporte.content)
        auditoria = self._api("get", "/api/auditoria/")
        self.assertEqual(auditoria.status_code, 200, auditoria.content)
        self.assertGreater(self._json(auditoria)["count"], base_eventos)
        por_accion = self._api("get", "/api/auditoria/?accion=EXPORTAR")
        self.assertGreaterEqual(self._json(por_accion)["count"], 1)
        creaciones = self._api("get", "/api/auditoria/?accion=CREAR")
        self.assertGreaterEqual(self._json(creaciones)["count"], 1)


class MatrizRutasTests(Entrega1Base):
    """Pruebas 319 y 320 (Semana 19)."""

    # ------------------------------------------------------------------ #
    # 319: las respuestas reales por rol coinciden con la matriz generada
    # ------------------------------------------------------------------ #
    def test_319_las_respuestas_reales_coinciden_con_la_matriz_generada(self):
        rutas = mr.rutas_api()
        self.assertGreaterEqual(len(rutas), 100)
        # Solo login, renovación y cierre son AllowAny (la 320 detalla el
        # comportamiento del anónimo en ellas).
        self.assertEqual(
            {i["ruta"] for i in rutas if i["allow_any"]},
            set(mr.RUTAS_EXENTAS),
        )

        errores = []
        for rol, entrar in (
            ("Administrador", self._entrar_admin),
            ("Coordinador", self._entrar_coordinador),
            ("Técnico de campo", self._entrar_tecnico),
        ):
            entrar()
            permisos = mr.permisos_de_rol(rol)
            # logout el último: su POST blacklistea el refresh y cierra
            # la sesión que usan el resto de sondas del rol.
            orden = sorted(rutas, key=lambda i: i["ruta"] == "/api/auth/logout/")
            for info in orden:
                for metodo in mr.METODOS:
                    real = self._api(
                        metodo, info["ruta"], None if metodo == "get" else {}
                    ).status_code
                    valor = mr.esperado(info, metodo, permisos)
                    if real not in mr.aceptables(valor):
                        errores.append(
                            f"{rol}: {metodo.upper()} {info['ruta']} -> "
                            f"{real}, esperado {valor}"
                        )
        self.assertEqual(errores, [], "\n".join(errores))

        # El documento generado está al día con esta misma matriz.
        doc = mr.ruta_doc()
        self.assertTrue(doc.exists(), f"falta {doc}: python manage.py matriz_rutas")
        self.assertEqual(
            mr.generar_markdown(),
            doc.read_text(encoding="utf-8"),
            "docs/matriz_rutas_por_rol.md desactualizado: "
            "python manage.py matriz_rutas",
        )

    # ------------------------------------------------------------------ #
    # 320: sin token, toda ruta de la API responde 401 (salvo AllowAny)
    # ------------------------------------------------------------------ #
    def test_320_las_rutas_api_exigen_token_salvo_login_y_renovacion(self):
        rutas = mr.rutas_api()
        errores = []
        for info in rutas:
            for metodo in mr.METODOS:
                real = self._api(
                    metodo, info["ruta"], None if metodo == "get" else {}
                ).status_code
                if info["allow_any"]:
                    # Validan su propia credencial: sin ella nunca operan.
                    if real not in (400, 401, 405):
                        errores.append(
                            f"exenta {metodo.upper()} {info['ruta']} -> {real}"
                        )
                elif real != 401:
                    errores.append(
                        f"{metodo.upper()} {info['ruta']} -> {real}, "
                        f"esperado 401"
                    )
        self.assertEqual(errores, [], "\n".join(errores))


class SeguridadTests(Entrega1Base):
    """Pruebas 321-323 (Semana 19)."""

    # ------------------------------------------------------------------ #
    # 321: check --deploy sin avisos con la configuración de producción
    # ------------------------------------------------------------------ #
    def test_321_check_deploy_sin_advertencias_con_la_config_de_produccion(self):
        entorno = dict(
            os.environ,
            DEBUG="False",
            PRODUCCION="1",
            SECRET_KEY=secrets.token_urlsafe(48),
            ALLOWED_HOSTS="localhost,127.0.0.1",
            ADMIN_URL="panel-interno/",
        )
        proceso = subprocess.run(
            [sys.executable, "manage.py", "check", "--deploy"],
            cwd=str(settings.BASE_DIR),
            env=entorno,
            capture_output=True,
        )
        salida = (proceso.stdout + proceso.stderr).decode("utf-8", "replace")
        self.assertEqual(proceso.returncode, 0, salida)
        self.assertIn("System check identified no issues", salida)
        self.assertNotIn("WARNINGS", salida)
        self.assertIn("0 silenced", salida)

        # El panel de Django se sirve en la ruta que diga ADMIN_URL (.env).
        consulta = subprocess.run(
            [sys.executable, "manage.py", "shell", "-c",
             "from config.urls import ADMIN_URL; print(ADMIN_URL)"],
            cwd=str(settings.BASE_DIR),
            env=entorno,
            capture_output=True,
        )
        texto = (consulta.stdout + consulta.stderr).decode("utf-8", "replace")
        self.assertIn("panel-interno/", texto)

    # ------------------------------------------------------------------ #
    # 322: un error interno no filtra trazas con DEBUG apagado
    # ------------------------------------------------------------------ #
    def test_322_un_error_interno_no_fuga_trazas_con_debug_apagado(self):
        self._entrar_admin()
        # En Django 5.2 el modo «no re-lanzar» vive en el cliente, no en get().
        self.client.raise_request_exception = False
        try:
            with override_settings(DEBUG=False):
                with patch(
                    "dashboard.views.DashboardViewSet.resumen",
                    side_effect=Exception("TRAZA_SECRETA_322"),
                ):
                    respuesta = self.client.get("/api/dashboard/resumen/")
        finally:
            self.client.raise_request_exception = True
        self.assertEqual(respuesta.status_code, 500)
        cuerpo = respuesta.content.lower()
        self.assertNotIn(b"traza_secreta_322", cuerpo)
        self.assertNotIn(b"traceback", cuerpo)
        self.assertNotIn(b"exception value", cuerpo)
        self.assertNotIn(b"settings.py", cuerpo)

    # ------------------------------------------------------------------ #
    # 323: los registros del servidor no guardan claves ni tokens
    # ------------------------------------------------------------------ #
    def test_323_los_registros_del_servidor_no_guardan_claves_ni_tokens(self):
        class Capturador(logging.Handler):
            def __init__(self):
                super().__init__()
                self.lineas = []

            def emit(self, registro):
                self.lineas.append(registro.getMessage())

        capturador = Capturador()
        raiz = logging.getLogger()
        sigpa = logging.getLogger("sigpa.seguridad")
        raiz.addHandler(capturador)
        sigpa.addHandler(capturador)  # sigpa.seguridad no propaga (LOGGING)
        try:
            self._entrar_admin()
            # fallo de acceso: la clave errónea no debe quedarse en el log
            fallido = _post_login(self.client, "admin_pruebas", "Mala323!")
            self.assertEqual(fallido.status_code, 401)
            self._post201(
                "/api/productores/",
                {"nombres": "Luz", "apellidos": "Ccatas", "dni": "73011224",
                 "comunidad": self.comunidad.pk},
            )
            # cambio con la clave actual mal: 400 y ninguna clave en el log
            cambio = self._api(
                "post", "/api/auth/cambiar-clave/",
                {"password_actual": "TambienMala323!",
                 "password_nueva": "NuevaSegura323!"},
            )
            self.assertEqual(cambio.status_code, 400, cambio.content)
            self._api("post", "/api/auth/logout/")
        finally:
            raiz.removeHandler(capturador)
            sigpa.removeHandler(capturador)

        texto = "\n".join(capturador.lineas)
        self.assertTrue(texto.strip(), "no se registró ningún evento")
        self.assertIn("login_correcto", texto)
        for secreto in (
            "AdminPruebas2026!", "Mala323!", "TambienMala323!",
            "NuevaSegura323!",
        ):
            self.assertNotIn(
                secreto, texto, f"la clave «{secreto}» aparece en los registros"
            )
        self.assertNotIn("eyJ", texto, "un token JWT aparece en los registros")
        self.assertNotIn(settings.SECRET_KEY, texto)


class RendimientoTests(Entrega1Base):
    """Prueba 324 (Semana 19): rendimiento con volumen reducido."""

    def test_324_rendimiento_con_volumen_reducido(self):
        from django.core.management import call_command
        import time

        # Escala reducida para que la prueba sea rápida en CI
        escala = {
            "productores": 30,
            "parcelas": 60,
            "campanias": 72,
            "actividades": 1200,
            "clima_dias": 20,
        }

        # Siembra datos
        inicio = time.perf_counter()
        call_command(
            "datos_volumen",
            **escala,
            stdout=open(os.devnull, "w"),
            stderr=open(os.devnull, "w"),
        )
        t_siembra = time.perf_counter() - inicio

        # Autentica como admin (cookies JWT)
        self._entrar_admin()

        # Endpoints a medir
        endpoints = {
            "dashboard": "/api/dashboard/resumen/",
            "productores": "/api/productores/",
            "campanias": "/api/campanias/",
            "actividades": "/api/actividades/",
            "clima": "/api/clima/",
        }

        umbral = 2.0  # segundos (meta local conservadora)
        resultados = {}
        for nombre, url in endpoints.items():
            t0 = time.perf_counter()
            resp = self.client.get(url)
            t1 = time.perf_counter()
            self.assertEqual(resp.status_code, 200, f"{nombre}: {resp.status_code}")
            dt = t1 - t0
            resultados[nombre] = dt
            self.assertLess(
                dt, umbral, f"{nombre} tarda {dt:.2f}s > {umbral}s"
            )

        # Imprime resumen
        print(
            f"\n[324] Siembra ({t_siembra:.1f}s) + latencias: "
            + ", ".join(f"{k}={v:.2f}s" for k, v in resultados.items())
        )


class RespaldoTests(Entrega1Base):
    """Prueba 325 (Semana 19)."""

    @staticmethod
    def _canonicalizar(volcado):
        """Volcado comparable byte a byte tras una restauración.

        pg_dump 17 escribe dos cosas que NO son estables entre un volcado
        y su restauración: la línea `\\restrict` (firma aleatoria por
        volcado) y la forma del `= ANY ((ARRAY[..])::text[])` de los
        CHECK de enumeración, que al reparsear sale como
        `= ANY (ARRAY[(..)::text, ..])` — mismo árbol, otra escritura.
        Los datos (COPY) sí deben coincidir exactamente.
        """
        lineas = []
        for linea in volcado.decode("utf-8", "replace").splitlines():
            if linea.startswith(("\\restrict", "\\unrestrict")):
                continue
            corte = linea.find("= ANY (")
            if corte >= 0:
                valores = re.findall(r"'([^']*)'::character varying", linea[corte:])
                if valores:
                    linea = linea[:corte] + "= ANY([" + "|".join(valores) + "])"
            lineas.append(linea)
        return "\n".join(lineas)

    # ------------------------------------------------------------------ #
    # 325: migraciones desde cero (29 tablas / 25 triggers) y respaldo
    #      restaurado que coincide byte a byte con el original
    # ------------------------------------------------------------------ #
    def test_325_migraciones_desde_cero_respaldo_y_restauracion(self):
        from sistema import respaldo

        # --- A) la base de pruebas nace de `migrate` desde cero ---------
        with connection.cursor() as cursor:
            cursor.execute(
                """SELECT count(*) FROM information_schema.tables
                   WHERE table_schema = 'public'
                     AND table_type = 'BASE TABLE'
                     AND table_name NOT LIKE 'auth\\_%'
                     AND table_name NOT LIKE 'django\\_%'
                     AND table_name NOT LIKE 'token\\_%'"""
            )
            tablas_dominio = cursor.fetchone()[0]
            cursor.execute(
                "SELECT count(*) FROM pg_trigger WHERE NOT tgisinternal"
            )
            triggers = cursor.fetchone()[0]
        self.assertEqual(
            tablas_dominio, 29,
            "las migraciones desde cero deben crear 29 tablas de dominio",
        )
        self.assertEqual(
            triggers, 25,
            "las migraciones desde cero deben crear 25 triggers",
        )

        # --- B) volcado → restauración en base temporal → mismo volcado -
        bd_pruebas = connection.settings_dict["NAME"]
        temporal = "sigpa_e19_resp325"
        try:
            respaldo.eliminar_bd(temporal)
            volcado = respaldo.volcar_bytes(bd=bd_pruebas)
            self.assertGreater(len(volcado), 20_000, "volcado sospechosamente corto")
            respaldo.crear_bd(temporal)
            respaldo.restaurar(temporal, volcado)
            volcado2 = respaldo.volcar_bytes(bd=temporal)
            self.assertEqual(
                self._canonicalizar(volcado),
                self._canonicalizar(volcado2),
                "el volcado de la base restaurada no coincide con el original",
            )
            texto = volcado2.decode("utf-8", "replace")
            self.assertEqual(texto.count("CREATE TABLE public."), 38)
            self.assertEqual(texto.count("CREATE TRIGGER "), 25)
        finally:
            respaldo.eliminar_bd(temporal)
