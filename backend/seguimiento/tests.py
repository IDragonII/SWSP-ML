"""Pruebas de las Semanas 7, 9 y 10: actividades productivas (HU-47 a
HU-55), usos de recursos (HU-67 a HU-75) y registro de clima (HU-76 a
HU-83).

Numeración del repositorio: 87-102 (Semana 7, 16 pruebas), 121-137
(Semana 9, 17 pruebas) y 138-151 y 155 (Semana 10, API de clima; la
Semana 10 añade además 152-154 con la consulta a la API meteorológica
y cierra con 155 pruebas). El repositorio llegaba a 120 al cerrar la
Semana 8 y a 137 al cerrar la Semana 9.
"""
import importlib
import json
from datetime import date, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch
from urllib.error import URLError
from zoneinfo import ZoneInfo

from django.core.cache import cache
from django.db import DatabaseError, IntegrityError, connection, transaction
from django.test import TestCase

from campanias.models import Campania
from catalogos.models import Cultivo, Recurso, TipoActividad, Unidad, Variedad
from productores.models import (
    AsignacionTecnico,
    Comunidad,
    Distrito,
    Parcela,
    Productor,
    Provincia,
)
from usuarios.models import Rol, Usuario
from usuarios.tests import _post_login

from .models import Clima
from .servicio_meteorologico import CLAVES_SALIDA, ErrorServicioMeteorologico


class Semana7Base(TestCase):
    """Datos comunes: las 3 cuentas, ubicación, cultivo con variedad, los
    tipos de actividad sembrados, dos productores (el primero asignado al
    técnico), sus parcelas y una campaña planificada."""

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
        self.provincia = Provincia.objects.create(nombre="Prov S7")
        self.distrito = Distrito.objects.create(
            provincia=self.provincia, nombre="Distrito S7"
        )
        self.comunidad = Comunidad.objects.create(
            distrito=self.distrito, nombre="Comunidad S7"
        )
        self.cultivo = Cultivo.objects.create(nombre="Quinua S7")
        self.cultivo_b = Cultivo.objects.create(nombre="Maíz S7")
        self.variedad = Variedad.objects.create(cultivo=self.cultivo, nombre="Real S7")
        self.variedad_b = Variedad.objects.create(
            cultivo=self.cultivo_b, nombre="Blanca S7"
        )
        self.preparacion = TipoActividad.objects.get(codigo="PREPARACION")
        self.siembra = TipoActividad.objects.get(codigo="SIEMBRA")
        self.riego = TipoActividad.objects.get(codigo="RIEGO")
        self.p1 = Productor.objects.create(
            nombres="Uno", apellidos="Alfa", dni="71000001",
            comunidad=self.comunidad, creado_por=self.admin,
        )
        self.p2 = Productor.objects.create(
            nombres="Dos", apellidos="Beta", dni="71000002",
            comunidad=self.comunidad, creado_por=self.admin,
        )
        self.p1.refresh_from_db()
        self.p2.refresh_from_db()
        self.parcela = self._parcela_bd(self.p1, "2.00")
        self.parcela_b = self._parcela_bd(self.p2, "3.00")
        AsignacionTecnico.objects.create(tecnico=self.tecnico, productor=self.p1)
        self.campania = self._campania_bd(self.parcela, self.cultivo, self.variedad)

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

    def _parcela_bd(self, productor, superficie):
        parcela = Parcela.objects.create(
            productor=productor,
            comunidad=self.comunidad,
            superficie_ha=superficie,
            altitud_msnm=3850,
            tipo_suelo="FRANCO",
            pendiente="SUAVE",
            disponibilidad_agua="MEDIA",
            sistema_riego="GOTEO",
        )
        parcela.refresh_from_db()
        return parcela

    def _campania_bd(self, parcela, cultivo, variedad, **extra):
        datos = {
            "periodo": "2025-2026",
            "parcela": parcela,
            "cultivo": cultivo,
            "variedad": variedad,
            "fecha_inicio": date(2025, 9, 1),
            "fecha_fin_prevista": date(2026, 5, 31),
            "superficie_sembrada_ha": Decimal("1.50"),
        }
        datos.update(extra)
        return Campania.objects.create(**datos)

    def _datos(self, **extra):
        datos = {
            "campania": self.campania.pk,
            "tipo_actividad": self.preparacion.pk,
            "fecha": "2025-10-01",
            "metodo": "Arado de disco",
        }
        datos.update(extra)
        return datos

    def _crear(self, **extra):
        return self._api("post", "/api/actividades/", self._datos(**extra))

    def _hoy_lima(self):
        return datetime.now(ZoneInfo("America/Lima")).date()


class ActividadApiTests(Semana7Base):
    """Pruebas 87-102."""

    # ------------------------------------------------------------------ #
    # 87: alta válida y trazabilidad (registrado por, campaña anidada y
    #     resumen de la campaña)
    # ------------------------------------------------------------------ #
    def test_87_alta_valida_registra_y_expone_trazabilidad(self):
        self._entrar_admin()
        respuesta = self._crear()
        self.assertEqual(respuesta.status_code, 201)
        fila = self._json(respuesta)
        self.assertEqual(fila["fecha"], "2025-10-01")
        self.assertEqual(fila["tipo_actividad"]["codigo"], "PREPARACION")
        self.assertEqual(fila["campania"]["estado"], "PLANIFICADA")
        self.assertEqual(fila["campania"]["parcela"]["productor"]["id"], self.p1.pk)
        self.assertFalse(fila["anulada"])
        self.assertIsNone(fila["motivo_anulacion"])
        self.assertEqual(fila["registrado_por"], "admin_pruebas")
        self.assertIn("creado_en", fila)
        self.assertIn("actualizado_en", fila)

        ficha = self._json(self._api("get", f"/api/campanias/{self.campania.pk}/"))
        self.assertEqual(ficha["actividades_activas"], 1)
        self.assertEqual(ficha["fecha_ultima_actividad"], "2025-10-01")

    # ------------------------------------------------------------------ #
    # 88: la fecha debe caer dentro del período de la campaña
    # ------------------------------------------------------------------ #
    def test_88_fecha_fuera_del_periodo_se_rechaza(self):
        self._entrar_admin()
        antes = self._json(self._crear(fecha="2025-08-31"))
        self.assertIn("fecha", antes)
        self.assertIn("fuera del período", antes["fecha"][0])
        despues = self._json(self._crear(fecha="2026-06-01"))
        self.assertIn("fecha", despues)
        self.assertIn("fuera del período", despues["fecha"][0])

    # ------------------------------------------------------------------ #
    # 89: no se aceptan fechas futuras (hora de Lima; pregunta H)
    # ------------------------------------------------------------------ #
    def test_89_fecha_futura_se_rechaza(self):
        self._entrar_admin()
        futura = self._hoy_lima() + timedelta(days=3)
        anio = futura.year
        campania_futura = self._campania_bd(
            self.parcela_b,
            self.cultivo_b,
            self.variedad_b,
            periodo=f"{anio - 1}-{anio}",
            fecha_inicio=date(anio - 1, 1, 1),
            fecha_fin_prevista=date(anio, 12, 31),
            superficie_sembrada_ha=Decimal("2.00"),
        )
        rechazo = self._json(
            self._crear(
                campania=campania_futura.pk,
                fecha=futura.isoformat(),
            )
        )
        self.assertIn("fecha", rechazo)
        self.assertIn("no puede ser futura", rechazo["fecha"][0])
        # Una fecha pasada dentro del período sigue admitiéndose
        pasada = futura - timedelta(days=10)
        ok = self._crear(campania=campania_futura.pk, fecha=pasada.isoformat())
        self.assertEqual(ok.status_code, 201)

    # ------------------------------------------------------------------ #
    # 90: la campaña cancelada no admite registros
    # ------------------------------------------------------------------ #
    def test_90_campania_cancelada_no_admite_actividades(self):
        self._entrar_admin()
        self.assertEqual(
            self._api(
                "post",
                f"/api/campanias/{self.campania.pk}/cancelar/",
                {"motivo": "Sin presupuesto"},
            ).status_code,
            200,
        )
        rechazo = self._json(self._crear())
        self.assertIn("campania", rechazo)
        self.assertIn("CANCELADA", rechazo["campania"][0])
        self.assertIn("no admite nuevos registros", rechazo["campania"][0])

    # ------------------------------------------------------------------ #
    # 91: la densidad lleva valor y unidad juntos
    # ------------------------------------------------------------------ #
    def test_91_densidad_requiere_valor_y_unidad_juntos(self):
        self._entrar_admin()
        sin_unidad = self._json(
            self._crear(tipo_actividad=self.siembra.pk, densidad_siembra="80")
        )
        self.assertIn("densidad_siembra", sin_unidad)
        self.assertIn("deben ir juntas", sin_unidad["densidad_siembra"][0])
        sin_valor = self._json(
            self._crear(tipo_actividad=self.siembra.pk, densidad_unidad="KG_HA")
        )
        self.assertIn("densidad_siembra", sin_valor)
        self.assertIn("deben ir juntas", sin_valor["densidad_siembra"][0])
        completa = self._crear(
            tipo_actividad=self.siembra.pk,
            densidad_siembra="80",
            densidad_unidad="KG_HA",
        )
        self.assertEqual(completa.status_code, 201)
        fila = self._json(completa)
        self.assertEqual(fila["densidad_siembra"], "80.00")
        self.assertEqual(fila["densidad_unidad"], "KG_HA")

    # ------------------------------------------------------------------ #
    # 92: la densidad solo aplica a siembras y la unidad es válida
    # ------------------------------------------------------------------ #
    def test_92_densidad_solo_en_siembra_y_unidad_valida(self):
        self._entrar_admin()
        en_riego = self._json(
            self._crear(
                tipo_actividad=self.riego.pk,
                densidad_siembra="10",
                densidad_unidad="KG_HA",
            )
        )
        self.assertIn("densidad_siembra", en_riego)
        self.assertIn("solo aplica", en_riego["densidad_siembra"][0])
        unidad_mala = self._json(
            self._crear(
                tipo_actividad=self.siembra.pk,
                densidad_siembra="10",
                densidad_unidad="LITROS",
            )
        )
        self.assertIn("densidad_unidad", unidad_mala)
        self.assertIn("KG_HA o PLANTAS_M2", unidad_mala["densidad_unidad"][0])

    # ------------------------------------------------------------------ #
    # 93: densidad > 0, horas y costo no negativos
    # ------------------------------------------------------------------ #
    def test_93_densidad_horas_costo_no_negativos(self):
        self._entrar_admin()
        densidad = self._json(
            self._crear(
                tipo_actividad=self.siembra.pk,
                densidad_siembra="0",
                densidad_unidad="KG_HA",
            )
        )
        self.assertIn("mayor que 0", densidad["densidad_siembra"][0])
        horas = self._json(self._crear(horas="-1"))
        self.assertIn("horas", horas)
        self.assertIn("negativas", horas["horas"][0])
        costo = self._json(self._crear(costo="-0.01"))
        self.assertIn("costo", costo)
        self.assertIn("negativo", costo["costo"][0])
        ok = self._crear(horas="7.5", costo="120.50")
        self.assertEqual(ok.status_code, 201)

    # ------------------------------------------------------------------ #
    # 94: campaña y tipo no cambian al editar; registrado_por es del servidor
    # ------------------------------------------------------------------ #
    def test_94_campos_protegidos_y_registrado_por_del_servidor(self):
        self._entrar_admin()
        fila = self._json(self._crear())
        campania_b = self._campania_bd(
            self.parcela_b, self.cultivo_b, self.variedad_b
        )
        campania = self._json(
            self._api(
                "patch",
                f"/api/actividades/{fila['id']}/",
                {"campania": campania_b.pk},
            )
        )
        self.assertIn("campania", campania)
        self.assertIn("no se puede cambiar", str(campania["campania"]))
        tipo = self._json(
            self._api(
                "patch",
                f"/api/actividades/{fila['id']}/",
                {"tipo_actividad": self.siembra.pk},
            )
        )
        self.assertIn("tipo_actividad", tipo)
        self.assertIn("no se puede cambiar", str(tipo["tipo_actividad"]))
        # registrado_por lo pone el servidor: el enviado se ignora
        otro = self._json(
            self._crear(registrado_por=self.coordinador.pk)
        )
        self.assertEqual(otro["registrado_por"], "admin_pruebas")

    # ------------------------------------------------------------------ #
    # 95: la siembra cambia la campaña a EN_PRODUCCION y fija la fecha;
    #     una segunda siembra recalcula la mínima
    # ------------------------------------------------------------------ #
    def test_95_siembra_cambia_campania_y_segunda_recalcula_fecha(self):
        self._entrar_admin()
        primera = self._json(
            self._crear(tipo_actividad=self.siembra.pk, fecha="2025-11-05")
        )
        self.assertEqual(primera["campania"]["estado"], "EN_PRODUCCION")
        self.assertEqual(primera["campania"]["fecha_siembra"], "2025-11-05")
        segunda = self._json(
            self._crear(tipo_actividad=self.siembra.pk, fecha="2025-10-20")
        )
        self.assertEqual(segunda["campania"]["fecha_siembra"], "2025-10-20")
        ficha = self._json(self._api("get", f"/api/campanias/{self.campania.pk}/"))
        self.assertEqual(ficha["fecha_siembra"], "2025-10-20")
        self.assertEqual(ficha["estado"], "EN_PRODUCCION")
        self.assertEqual(ficha["actividades_activas"], 2)
        self.assertEqual(ficha["fecha_ultima_actividad"], "2025-11-05")

    # ------------------------------------------------------------------ #
    # 96: anular exige motivo, no se anula dos veces y recalcula la siembra
    # ------------------------------------------------------------------ #
    def test_96_anular_requiere_motivo_y_recalcula_siembra(self):
        self._entrar_admin()
        siembra = self._json(
            self._crear(tipo_actividad=self.siembra.pk, fecha="2025-11-05")
        )
        sin_motivo = self._json(
            self._api("post", f"/api/actividades/{siembra['id']}/anular/", {})
        )
        self.assertIn("motivo", sin_motivo)
        self.assertIn("obligatorio", str(sin_motivo["motivo"]))
        anulada = self._json(
            self._api(
                "post",
                f"/api/actividades/{siembra['id']}/anular/",
                {"motivo": "Se registró por error"},
            )
        )
        self.assertTrue(anulada["anulada"])
        self.assertEqual(anulada["motivo_anulacion"], "Se registró por error")
        # La única siembra anulada deja la fecha vacía; la campaña NO
        # vuelve a PLANIFICADA
        self.assertIsNone(anulada["campania"]["fecha_siembra"])
        self.assertEqual(anulada["campania"]["estado"], "EN_PRODUCCION")
        otra_vez = self._json(
            self._api(
                "post",
                f"/api/actividades/{siembra['id']}/anular/",
                {"motivo": "Otra vez"},
            )
        )
        self.assertIn("estado", otra_vez)
        self.assertIn("ya está anulada", str(otra_vez["estado"]))

    # ------------------------------------------------------------------ #
    # 97: reactivar restaura la siembra y respeta la campaña cancelada
    # ------------------------------------------------------------------ #
    def test_97_reactivar_restaura_siembra_y_respeta_campania_cerrada(self):
        self._entrar_admin()
        siembra = self._json(
            self._crear(tipo_actividad=self.siembra.pk, fecha="2025-11-05")
        )
        self._api(
            "post",
            f"/api/actividades/{siembra['id']}/anular/",
            {"motivo": "Error de captura"},
        )
        reactivada = self._json(
            self._api("post", f"/api/actividades/{siembra['id']}/reactivar/", {})
        )
        self.assertFalse(reactivada["anulada"])
        self.assertIsNone(reactivada["motivo_anulacion"])
        self.assertEqual(reactivada["campania"]["fecha_siembra"], "2025-11-05")
        # reactivar una actividad que no está anulada
        otra = self._json(
            self._api("post", f"/api/actividades/{siembra['id']}/reactivar/", {})
        )
        self.assertIn("no está anulada", str(otra["estado"]))
        # una campaña cancelada no admite reactivar
        actividad = self._json(self._crear())
        self._api(
            "post",
            f"/api/actividades/{actividad['id']}/anular/",
            {"motivo": "Temporada mala"},
        )
        self._api(
            "post",
            f"/api/campanias/{self.campania.pk}/cancelar/",
            {"motivo": "Lluvias tardías"},
        )
        cancelada = self._json(
            self._api("post", f"/api/actividades/{actividad['id']}/reactivar/", {})
        )
        self.assertIn("estado", cancelada)
        self.assertIn("CANCELADA", str(cancelada["estado"]))

    # ------------------------------------------------------------------ #
    # 98: búsqueda general y filtros (campaña, tipo, fechas y estado)
    # ------------------------------------------------------------------ #
    def test_98_busqueda_y_filtros(self):
        self._entrar_admin()
        self._crear(fecha="2025-10-01")
        self._crear(tipo_actividad=self.riego.pk, fecha="2025-11-02")
        campania_b = self._campania_bd(
            self.parcela_b, self.cultivo_b, self.variedad_b
        )
        tercera = self._json(
            self._crear(campania=campania_b.pk, fecha="2025-10-15")
        )
        self._api(
            "post",
            f"/api/actividades/{tercera['id']}/anular/",
            {"motivo": "Registro duplicado"},
        )

        por_parcela = self._json(self.client.get(f"/api/actividades/?busqueda={self.parcela.codigo}"))
        self.assertEqual(len(por_parcela["results"]), 2)
        por_productor = self._json(self.client.get("/api/actividades/?busqueda=Alfa"))
        self.assertEqual(len(por_productor["results"]), 2)
        por_tipo = self._json(self.client.get(f"/api/actividades/?tipo={self.riego.pk}"))
        self.assertEqual(len(por_tipo["results"]), 1)
        por_campania = self._json(self.client.get(f"/api/actividades/?campania={campania_b.pk}"))
        self.assertEqual(len(por_campania["results"]), 1)
        rango = self._json(self.client.get("/api/actividades/?fecha_desde=2025-10-15&fecha_hasta=2025-11-02"))
        self.assertEqual(len(rango["results"]), 2)
        activas = self._json(self.client.get("/api/actividades/?estado=ACTIVA"))
        self.assertEqual(len(activas["results"]), 2)
        anuladas = self._json(self.client.get("/api/actividades/?estado=ANULADA"))
        self.assertEqual(len(anuladas["results"]), 1)
        invalido = self._json(self.client.get("/api/actividades/?estado=OTRO"))
        self.assertIn("estado", invalido)
        self.assertIn("Use ACTIVA o ANULADA", str(invalido["estado"]))
        por_productor_filtro = self._json(
            self.client.get(f"/api/actividades/?productor={self.p1.pk}")
        )
        self.assertEqual(len(por_productor_filtro["results"]), 2)

    # ------------------------------------------------------------------ #
    # 99: el técnico solo ve y registra actividades de SUS productores
    # ------------------------------------------------------------------ #
    def test_99_ambito_del_tecnico_y_registrado_por_oculto(self):
        self._entrar_admin()
        ajena = self._json(
            self._crear(
                campania=self._campania_bd(
                    self.parcela_b, self.cultivo_b, self.variedad_b
                ).pk
            )
        )
        propia = self._json(self._crear())
        self._entrar_tecnico()
        listado = self._json(self.client.get("/api/actividades/"))
        self.assertEqual(len(listado["results"]), 1)
        self.assertEqual(listado["results"][0]["id"], propia["id"])
        # registrado_por se oculta a los roles con limita_a_asignados
        self.assertNotIn("registrado_por", listado["results"][0])
        detalle_ajeno = self.client.get(f"/api/actividades/{ajena['id']}/")
        self.assertEqual(detalle_ajeno.status_code, 404)
        crear_ajena = self._json(
            self._api(
                "post",
                "/api/actividades/",
                self._datos(campania=self.campania.pk)
                | {"campania": ajena["campania"]["id"]},
            )
        )
        self.assertIn("campania", crear_ajena)
        self.assertIn("no existe", crear_ajena["campania"][0])
        propia_ok = self._crear(campania=self.campania.pk)
        self.assertEqual(propia_ok.status_code, 201)

    # ------------------------------------------------------------------ #
    # 100: permisos por rol (coordinador solo ve; anular es desactivar)
    # ------------------------------------------------------------------ #
    def test_100_permisos_por_rol(self):
        self._entrar_admin()
        fila = self._json(self._crear())
        self._entrar_coordinador()
        listado = self.client.get("/api/actividades/")
        self.assertEqual(listado.status_code, 200)
        crear = self._api("post", "/api/actividades/", self._datos())
        self.assertEqual(crear.status_code, 403)
        anular = self._api(
            "post", f"/api/actividades/{fila['id']}/anular/", {"motivo": "x"}
        )
        self.assertEqual(anular.status_code, 403)
        self._entrar_tecnico()
        anular_tecnico = self._api(
            "post", f"/api/actividades/{fila['id']}/anular/", {"motivo": "x"}
        )
        self.assertEqual(anular_tecnico.status_code, 403)
        editar_tecnico = self._api(
            "patch", f"/api/actividades/{fila['id']}/", {"observaciones": "Ok"}
        )
        self.assertEqual(editar_tecnico.status_code, 200)

    # ------------------------------------------------------------------ #
    # 101: desplegables de campañas y productores para la pantalla
    # ------------------------------------------------------------------ #
    def test_101_desplegables_de_campanias_y_productores(self):
        self._entrar_admin()
        cancelada = self._campania_bd(
            self.parcela_b, self.cultivo_b, self.variedad_b, periodo="2024-2025"
        )
        cancelada.estado = Campania.ESTADO_CANCELADA
        cancelada.save(update_fields=("estado",))

        campanias = self._json(self.client.get("/api/campanias/?desplegable=1"))
        self.assertIsInstance(campanias, list)
        ids = {c["id"] for c in campanias}
        self.assertIn(self.campania.pk, ids)
        self.assertNotIn(cancelada.pk, ids)
        self.assertIn("fecha_inicio", campanias[0])
        self.assertIn("fecha_fin_prevista", campanias[0])

        # El desplegable de productores solo ofrece activos
        self.p2.estado = Productor.ESTADO_INACTIVO
        self.p2.save(update_fields=("estado",))
        productores = self._json(self.client.get("/api/productores/?desplegable=1"))
        self.assertIsInstance(productores, list)
        self.assertEqual([p["id"] for p in productores], [self.p1.pk])
        self.assertIn("nombre_completo", productores[0])

        # El técnico en su desplegable solo ve sus asignados
        self._entrar_tecnico()
        tec_campanias = self._json(self.client.get("/api/campanias/?desplegable=1"))
        self.assertEqual([c["id"] for c in tec_campanias], [self.campania.pk])
        tec_productores = self._json(self.client.get("/api/productores/?desplegable=1"))
        self.assertEqual([p["id"] for p in tec_productores], [self.p1.pk])

    # ------------------------------------------------------------------ #
    # 102: 401 sin sesión, DELETE 405 y edición de los campos editables
    # ------------------------------------------------------------------ #
    def test_102_sin_sesion_delete_405_y_edicion(self):
        self._entrar_admin()
        fila = self._json(self._crear())
        self.client.cookies.clear()
        sin_sesion = self.client.get("/api/actividades/")
        self.assertEqual(sin_sesion.status_code, 401)
        self._entrar_admin()
        borrar = self._api("delete", f"/api/actividades/{fila['id']}/")
        self.assertEqual(borrar.status_code, 405)
        editar = self._json(
            self._api(
                "patch",
                f"/api/actividades/{fila['id']}/",
                {"metodo": "Arado y rastreo", "observaciones": "Terreno seco"},
            )
        )
        self.assertEqual(editar["metodo"], "Arado y rastreo")
        self.assertEqual(editar["observaciones"], "Terreno seco")
        # la fecha cambia si sigue dentro del período (el trigger la valida)
        mover = self._json(
            self._api(
                "patch", f"/api/actividades/{fila['id']}/", {"fecha": "2025-10-05"}
            )
        )
        self.assertEqual(mover["fecha"], "2025-10-05")
        # una PREPARACION no admite densidad ni al editar
        denegar = self._json(
            self._api(
                "patch",
                f"/api/actividades/{fila['id']}/",
                {"densidad_siembra": "5", "densidad_unidad": "KG_HA"},
            )
        )
        self.assertIn("densidad_siembra", denegar)
        self.assertIn("solo aplica", denegar["densidad_siembra"][0])


class Semana9Base(Semana7Base):
    """Datos comunes de la Semana 9: la base de la Semana 7 más las
    unidades (con quintal a 46 kg creado aquí), recursos de cada
    categoría y una segunda campaña (p2, sin asignar al técnico)."""

    def setUp(self):
        super().setUp()
        self.kg = Unidad.objects.get(nombre="Kilogramo")
        self.gramo = Unidad.objects.get(nombre="Gramo")
        self.tonelada = Unidad.objects.get(nombre="Tonelada")
        self.m3 = Unidad.objects.get(nombre="Metro cúbico")
        self.litro = Unidad.objects.get(nombre="Litro")
        self.jornal = Unidad.objects.get(nombre="Jornal")
        self.hora = Unidad.objects.get(nombre="Hora")
        self.quintal = Unidad.objects.create(
            nombre="Quintal", simbolo="qq", tipo="MASA",
            factor_a_base=Decimal("46"), es_base=False,
        )

        self.semilla = Recurso.objects.create(
            nombre="Quinua semilla S9", categoria="SEMILLA", tipo_unidad="MASA"
        )
        self.urea = Recurso.objects.create(
            nombre="Urea S9", categoria="FERTILIZANTE", tipo_unidad="MASA"
        )
        self.manobra = Recurso.objects.create(
            nombre="Jornal S9", categoria="MANO_OBRA", tipo_unidad="LABOR"
        )
        self.combustible = Recurso.objects.create(
            nombre="Diésel S9", categoria="COMBUSTIBLE", tipo_unidad="VOLUMEN"
        )
        self.agua = Recurso.objects.create(
            nombre="Agua S9", categoria="AGUA", tipo_unidad="VOLUMEN"
        )
        self.tratamiento = Recurso.objects.create(
            nombre="Herbicida S9", categoria="FITOSANITARIO", tipo_unidad="VOLUMEN"
        )

        self.campania_b = self._campania_bd(
            self.parcela_b,
            self.cultivo_b,
            self.variedad_b,
            periodo="2025-2026",
            fecha_inicio=date(2025, 1, 1),
            fecha_fin_prevista=date(2026, 12, 31),
            superficie_sembrada_ha=Decimal("3.00"),
        )
        self.fertilizacion = TipoActividad.objects.get(codigo="FERTILIZACION")

    # ------------------------------------------------------------------ #
    # helpers
    # ------------------------------------------------------------------ #
    def _datos_uso(self, **extra):
        datos = {
            "campania": self.campania.pk,
            "recurso": self.semilla.pk,
            "fecha": "2025-10-02",
            "cantidad": "16",
            "unidad": self.kg.pk,
        }
        datos.update(extra)
        return datos

    def _crear_uso(self, **extra):
        return self._api("post", "/api/usos-recursos/", self._datos_uso(**extra))

    def _anular_uso(self, uso_id, motivo="Registro duplicado"):
        return self._api(
            "post", f"/api/usos-recursos/{uso_id}/anular/", {"motivo": motivo}
        )

    def _sql(self, consulta, parametros=None):
        with connection.cursor() as cursor:
            if parametros:
                cursor.execute(consulta, parametros)
            else:
                cursor.execute(consulta)

    def _consulta(self, consulta, parametros=None):
        with connection.cursor() as cursor:
            if parametros:
                cursor.execute(consulta, parametros)
            else:
                cursor.execute(consulta)
            return cursor.fetchall()


class UsoRecursoApiTests(Semana9Base):
    """Pruebas 121-137."""

    # ------------------------------------------------------------------ #
    # 121: alta válida — la base la calcula el trigger y la ficha de la
    #     campaña ya muestra el resumen por categoría
    # ------------------------------------------------------------------ #
    def test_121_alta_valida_calcula_la_base_y_alimenta_el_resumen(self):
        self._entrar_admin()
        respuesta = self._crear_uso()
        self.assertEqual(respuesta.status_code, 201)
        fila = self._json(respuesta)
        self.assertEqual(fila["fecha"], "2025-10-02")
        self.assertEqual(fila["recurso"]["nombre"], "Quinua semilla S9")
        self.assertEqual(fila["recurso"]["categoria"], "SEMILLA")
        self.assertEqual(fila["recurso"]["tipo_unidad"], "MASA")
        self.assertEqual(fila["cantidad"], "16.000")
        self.assertEqual(fila["unidad"]["simbolo"], "kg")
        self.assertEqual(fila["cantidad_base"], "16.000")
        self.assertEqual(fila["campania"]["estado"], "PLANIFICADA")
        self.assertEqual(fila["campania"]["parcela"]["productor"]["id"], self.p1.pk)
        self.assertIsNone(fila["actividad"])
        self.assertFalse(fila["anulada"])
        self.assertEqual(fila["registrado_por"], "admin_pruebas")

        ficha = self._json(self._api("get", f"/api/campanias/{self.campania.pk}/"))
        self.assertEqual(
            ficha["resumen_recursos"],
            [
                {
                    "categoria": "SEMILLA",
                    "total": 16.0,
                    "unidad": "kg",
                    "total_ha": 10.67,
                    "registros": 1,
                }
            ],
        )

    # ------------------------------------------------------------------ #
    # 122: cantidad_base, anulada, motivo y registrado_por no los manda
    #     el cliente; la respuesta trae la base calculada
    # ------------------------------------------------------------------ #
    def test_122_campos_protegidos_no_los_acepta_el_cliente(self):
        self._entrar_admin()
        respuesta = self._crear_uso(
            cantidad_base="999",
            anulada=True,
            motivo_anulacion="del cliente",
            registrado_por="otro",
        )
        self.assertEqual(respuesta.status_code, 201)
        fila = self._json(respuesta)
        self.assertEqual(fila["cantidad_base"], "16.000")
        self.assertFalse(fila["anulada"])
        self.assertIsNone(fila["motivo_anulacion"])
        self.assertEqual(fila["registrado_por"], "admin_pruebas")

    # ------------------------------------------------------------------ #
    # 123: cantidad > 0, costo ≥ 0, recurso y unidad activos y la
    #     unidad del mismo tipo que el recurso (nombrando las válidas)
    # ------------------------------------------------------------------ #
    def test_123_validaciones_de_cantidad_costo_recurso_y_unidad(self):
        self._entrar_admin()
        cantidad = self._json(self._crear_uso(cantidad="0"))
        self.assertIn("La cantidad debe ser mayor que 0.", str(cantidad["cantidad"]))

        costo = self._json(self._crear_uso(costo="-5"))
        self.assertIn("El costo no puede ser negativo.", str(costo["costo"]))

        unidad_mala = self._json(self._crear_uso(unidad=self.litro.pk))
        self.assertIn(
            "Esta unidad no sirve para este recurso: use g, kg, qq o t.",
            str(unidad_mala["unidad"]),
        )

        inactivo = Recurso.objects.create(
            nombre="Abono inactivo S9", categoria="ABONO", tipo_unidad="MASA",
            activo=False,
        )
        recurso_malo = self._json(self._crear_uso(recurso=inactivo.pk))
        self.assertIn(
            "El recurso indicado no existe o está inactivo.", str(recurso_malo["recurso"])
        )

        self.gramo.activo = False
        self.gramo.save(update_fields=("activo",))
        unidad_inactiva = self._json(self._crear_uso(unidad=self.gramo.pk))
        self.assertIn(
            "La unidad indicada no existe o está inactiva.", str(unidad_inactiva["unidad"])
        )

    # ------------------------------------------------------------------ #
    # 124: campaña cerrada — no admite altas, ediciones ni anulaciones
    # ------------------------------------------------------------------ #
    def test_124_campania_cancelada_no_admite_nada(self):
        self._entrar_admin()
        uso = self._json(self._crear_uso())
        self._api(
            "post",
            f"/api/campanias/{self.campania.pk}/cancelar/",
            {"motivo": "Lluvias tardías"},
        )

        alta = self._json(self._crear_uso())
        self.assertIn(
            "La campaña está CANCELADA y no admite nuevos registros.",
            str(alta["campania"]),
        )
        edicion = self._json(
            self._api(
                "patch", f"/api/usos-recursos/{uso['id']}/", {"cantidad": "32"}
            )
        )
        self.assertIn(
            "La campaña está CANCELADA y no admite nuevos registros.", str(edicion)
        )
        anular = self._json(self._anular_uso(uso["id"]))
        self.assertIn(
            "La campaña está CANCELADA y no admite nuevos registros.",
            str(anular["estado"]),
        )

    # ------------------------------------------------------------------ #
    # 125: la actividad es opcional; si se elige, es de la campaña y la
    #     fecha debe coincidir con la de la actividad
    # ------------------------------------------------------------------ #
    def test_125_actividad_opcional_coherente_con_la_campania(self):
        self._entrar_admin()
        actividad = self._json(
            self._api(
                "post",
                "/api/actividades/",
                {
                    "campania": self.campania.pk,
                    "tipo_actividad": self.fertilizacion.pk,
                    "fecha": "2025-10-02",
                },
            )
        )
        ok = self._json(
            self._crear_uso(
                actividad=actividad["id"], recurso=self.urea.pk,
                cantidad="2", unidad=self.quintal.pk,
            )
        )
        self.assertEqual(ok["actividad"]["id"], actividad["id"])
        self.assertEqual(ok["actividad"]["tipo"]["nombre"], "Fertilización")
        self.assertEqual(ok["cantidad_base"], "92.000")

        otro_dia = self._json(
            self._crear_uso(actividad=actividad["id"], fecha="2025-10-03")
        )
        self.assertIn(
            "La fecha debe coincidir con la de la actividad indicada.",
            str(otro_dia["fecha"]),
        )

        ajena = self._json(
            self._api(
                "post",
                "/api/actividades/",
                {
                    "campania": self.campania_b.pk,
                    "tipo_actividad": self.preparacion.pk,
                    "fecha": "2025-10-02",
                },
            )
        )
        no_pertenece = self._json(self._crear_uso(actividad=ajena["id"]))
        self.assertIn(
            "La actividad indicada no pertenece a esta campaña.",
            str(no_pertenece["actividad"]),
        )

    # ------------------------------------------------------------------ #
    # 126: fecha fuera del período y fecha futura (hora de Lima, H)
    # ------------------------------------------------------------------ #
    def test_126_fechas_fuera_del_periodo_y_futuras(self):
        self._entrar_admin()
        antes = self._json(self._crear_uso(fecha="2024-08-31"))
        self.assertIn("fuera del período", str(antes["fecha"]))
        despues = self._json(self._crear_uso(fecha="2026-06-15"))
        self.assertIn("fuera del período", str(despues["fecha"]))
        futura = datetime.now(ZoneInfo("America/Lima")).date() + timedelta(days=3)
        mala = self._json(
            self._crear_uso(campania=self.campania_b.pk, fecha=futura.isoformat())
        )
        self.assertIn("La fecha no puede ser futura.", str(mala["fecha"]))

    # ------------------------------------------------------------------ #
    # 127: la campaña no cambia al editar; cantidad y recurso+unidad sí
    #     y la base se recalcula
    # ------------------------------------------------------------------ #
    def test_127_edicion_bloquea_campania_y_recalcula_la_base(self):
        self._entrar_admin()
        uso = self._json(self._crear_uso())
        cambio = self._json(
            self._api(
                "patch",
                f"/api/usos-recursos/{uso['id']}/",
                {"campania": self.campania_b.pk},
            )
        )
        self.assertIn(
            "La campaña de un uso de recurso no se puede cambiar: anula y "
            "registra otro uso.",
            str(cambio["campania"]),
        )
        doble = self._json(
            self._api(
                "patch", f"/api/usos-recursos/{uso['id']}/", {"cantidad": "32"}
            )
        )
        self.assertEqual(doble["cantidad_base"], "32.000")
        otro = self._json(
            self._api(
                "patch",
                f"/api/usos-recursos/{uso['id']}/",
                {
                    "recurso": self.urea.pk,
                    "unidad": self.quintal.pk,
                    "cantidad": "2",
                },
            )
        )
        self.assertEqual(otro["recurso"]["nombre"], "Urea S9")
        self.assertEqual(otro["cantidad_base"], "92.000")

    # ------------------------------------------------------------------ #
    # 128: anular exige motivo y recursos.desactivar; ya anulada → 400
    # ------------------------------------------------------------------ #
    def test_128_anular_exige_motivo_y_permiso(self):
        self._entrar_admin()
        uso = self._json(self._crear_uso())
        sin_motivo = self._json(
            self._api("post", f"/api/usos-recursos/{uso['id']}/anular/", {})
        )
        self.assertIn(
            "El motivo de anulación es obligatorio.", str(sin_motivo["motivo"])
        )

        self._entrar_coordinador()
        coordinador = self._api(
            "post", f"/api/usos-recursos/{uso['id']}/anular/", {"motivo": "x"}
        )
        self.assertEqual(coordinador.status_code, 403)

        self._entrar_admin()
        anulado = self._json(self._anular_uso(uso["id"], "Se registró dos veces"))
        self.assertTrue(anulado["anulada"])
        self.assertEqual(anulado["motivo_anulacion"], "Se registró dos veces")
        otra_vez = self._json(self._anular_uso(uso["id"]))
        self.assertIn("El uso de recurso ya está anulado.", otra_vez["estado"])

    # ------------------------------------------------------------------ #
    # 129: reactivar solo si la campaña sigue abierta y la fecha válida
    # ------------------------------------------------------------------ #
    def test_129_reactivar_exige_campania_abierta_y_fecha_valida(self):
        self._entrar_admin()
        uso = self._json(self._crear_uso())
        activo = self._json(
            self._api("post", f"/api/usos-recursos/{uso['id']}/reactivar/", {})
        )
        self.assertIn("El uso de recurso no está anulado.", str(activo["estado"]))

        # Reactivar funciona mientras la campaña siga abierta y la fecha
        # siga dentro del período
        self._anular_uso(uso["id"])
        reactivado = self._json(
            self._api("post", f"/api/usos-recursos/{uso['id']}/reactivar/", {})
        )
        self.assertFalse(reactivado["anulada"])
        self.assertIsNone(reactivado["motivo_anulacion"])

        # La fecha queda fuera del período si la campaña se mueve
        self._anular_uso(uso["id"])
        self.campania.fecha_inicio = date(2025, 10, 5)
        self.campania.save(update_fields=("fecha_inicio",))
        fuera = self._json(
            self._api("post", f"/api/usos-recursos/{uso['id']}/reactivar/", {})
        )
        self.assertIn("fuera del período", str(fuera["fecha"]))
        self.campania.fecha_inicio = date(2025, 9, 1)
        self.campania.save(update_fields=("fecha_inicio",))

        # Una campaña cancelada no admite reactivar
        self._api(
            "post",
            f"/api/campanias/{self.campania.pk}/cancelar/",
            {"motivo": "Lluvias tardías"},
        )
        cancelada = self._json(
            self._api("post", f"/api/usos-recursos/{uso['id']}/reactivar/", {})
        )
        self.assertIn("CANCELADA", str(cancelada["estado"]))

    # ------------------------------------------------------------------ #
    # 130: anular una actividad anula sus usos activos en la misma
    #     transacción; reactivar la actividad no los reactiva
    # ------------------------------------------------------------------ #
    def test_130_anular_actividad_anula_sus_usos_atomicamente(self):
        self._entrar_admin()
        actividad = self._json(
            self._api(
                "post",
                "/api/actividades/",
                {
                    "campania": self.campania.pk,
                    "tipo_actividad": self.fertilizacion.pk,
                    "fecha": "2025-10-02",
                },
            )
        )
        uso_urea = self._json(
            self._crear_uso(
                actividad=actividad["id"], recurso=self.urea.pk,
                cantidad="2", unidad=self.quintal.pk,
            )
        )
        uso_jornales = self._json(
            self._crear_uso(
                actividad=actividad["id"], recurso=self.manobra.pk,
                cantidad="40", unidad=self.jornal.pk,
            )
        )
        uso_combustible = self._json(
            self._crear_uso(
                actividad=actividad["id"], recurso=self.combustible.pk,
                cantidad="10", unidad=self.litro.pk,
            )
        )
        self._anular_uso(uso_combustible["id"], "Original")

        respuesta = self._json(
            self._api(
                "post",
                f"/api/actividades/{actividad['id']}/anular/",
                {"motivo": "Se registró por error"},
            )
        )
        self.assertTrue(respuesta["anulada"])
        self.assertEqual(respuesta["recursos_anulados"], 2)

        urea = self._json(
            self._api("get", f"/api/usos-recursos/{uso_urea['id']}/")
        )
        self.assertTrue(urea["anulada"])
        self.assertEqual(urea["motivo_anulacion"], "Se registró por error")
        jornales = self._json(
            self._api("get", f"/api/usos-recursos/{uso_jornales['id']}/")
        )
        self.assertTrue(jornales["anulada"])
        combustible = self._json(
            self._api("get", f"/api/usos-recursos/{uso_combustible['id']}/")
        )
        self.assertEqual(combustible["motivo_anulacion"], "Original")

        self._api("post", f"/api/actividades/{actividad['id']}/reactivar/", {})
        urea_tras = self._json(
            self._api("get", f"/api/usos-recursos/{uso_urea['id']}/")
        )
        self.assertTrue(urea_tras["anulada"])

    # ------------------------------------------------------------------ #
    # 131: el resumen agrupa por categoría, convierte a base, divide
    #     entre la superficie sembrada y excluye anulados
    # ------------------------------------------------------------------ #
    def test_131_resumen_por_categoria_excluye_anulados(self):
        self._entrar_admin()
        self._crear_uso()
        self._crear_uso(
            recurso=self.urea.pk, cantidad="0.092", unidad=self.tonelada.pk
        )
        self._crear_uso(
            recurso=self.manobra.pk, cantidad="40", unidad=self.jornal.pk
        )
        extra = self._json(self._crear_uso(cantidad="8"))
        self._anular_uso(extra["id"])

        ficha = self._json(self._api("get", f"/api/campanias/{self.campania.pk}/"))
        por_categoria = {f["categoria"]: f for f in ficha["resumen_recursos"]}
        self.assertEqual(set(por_categoria), {"SEMILLA", "FERTILIZANTE", "MANO_OBRA"})
        self.assertEqual(por_categoria["SEMILLA"], {
            "categoria": "SEMILLA", "total": 16.0, "unidad": "kg",
            "total_ha": 10.67, "registros": 1,
        })
        self.assertEqual(por_categoria["FERTILIZANTE"], {
            "categoria": "FERTILIZANTE", "total": 92.0, "unidad": "kg",
            "total_ha": 61.33, "registros": 1,
        })
        self.assertEqual(por_categoria["MANO_OBRA"], {
            "categoria": "MANO_OBRA", "total": 40.0, "unidad": "jornal",
            "total_ha": 26.67, "registros": 1,
        })

    # ------------------------------------------------------------------ #
    # 132: el combustible se muestra en litros; sin usos, lista vacía
    # ------------------------------------------------------------------ #
    def test_132_combustible_en_litros_y_campania_sin_usos(self):
        self._entrar_admin()
        self._crear_uso(
            recurso=self.combustible.pk, cantidad="10", unidad=self.litro.pk
        )
        self._crear_uso(recurso=self.agua.pk, cantidad="2", unidad=self.m3.pk)

        ficha = self._json(self._api("get", f"/api/campanias/{self.campania.pk}/"))
        por_categoria = {f["categoria"]: f for f in ficha["resumen_recursos"]}
        self.assertEqual(por_categoria["COMBUSTIBLE"], {
            "categoria": "COMBUSTIBLE", "total": 10.0, "unidad": "L",
            "total_ha": 6.67, "registros": 1,
        })
        self.assertEqual(por_categoria["AGUA"]["unidad"], "m3")

        otra = self._json(self._api("get", f"/api/campanias/{self.campania_b.pk}/"))
        self.assertEqual(otra["resumen_recursos"], [])

    # ------------------------------------------------------------------ #
    # 133: permisos y ámbitos por rol (sin sesión 401, DELETE 405)
    # ------------------------------------------------------------------ #
    def test_133_permisos_y_ambitos_por_rol(self):
        self._entrar_admin()
        propio = self._json(self._crear_uso())
        ajeno = self._json(self._crear_uso(campania=self.campania_b.pk))

        self._entrar_tecnico()
        listado = self._json(self.client.get("/api/usos-recursos/"))
        self.assertEqual(
            [f["id"] for f in listado["results"]], [propio["id"]]
        )
        detalle_ajeno = self.client.get(f"/api/usos-recursos/{ajeno['id']}/")
        self.assertEqual(detalle_ajeno.status_code, 404)
        crear_ajena = self._json(self._crear_uso(campania=self.campania_b.pk))
        self.assertIn("La campaña indicada no existe.", crear_ajena["campania"][0])
        self.assertEqual(self._crear_uso().status_code, 201)
        anular_tecnico = self._api(
            "post", f"/api/usos-recursos/{propio['id']}/anular/", {"motivo": "x"}
        )
        self.assertEqual(anular_tecnico.status_code, 403)
        editar_tecnico = self._api(
            "patch", f"/api/usos-recursos/{propio['id']}/", {"observaciones": "Ok"}
        )
        self.assertEqual(editar_tecnico.status_code, 200)

        self._entrar_coordinador()
        self.assertEqual(self.client.get("/api/usos-recursos/").status_code, 200)
        crear_coord = self._api("post", "/api/usos-recursos/", self._datos_uso())
        self.assertEqual(crear_coord.status_code, 403)
        anular_coord = self._api(
            "post", f"/api/usos-recursos/{propio['id']}/anular/", {"motivo": "x"}
        )
        self.assertEqual(anular_coord.status_code, 403)

        self.client.cookies.clear()
        self.assertEqual(self.client.get("/api/usos-recursos/").status_code, 401)
        self._entrar_admin()
        borrar = self._api("delete", f"/api/usos-recursos/{propio['id']}/")
        self.assertEqual(borrar.status_code, 405)

    # ------------------------------------------------------------------ #
    # 134: filtros por campaña, actividad, recurso, categoría, fechas,
    #     productor, parcela, cultivo y estado, más la búsqueda
    # ------------------------------------------------------------------ #
    def test_134_filtros_y_busqueda(self):
        self._entrar_admin()
        actividad = self._json(
            self._api(
                "post",
                "/api/actividades/",
                {
                    "campania": self.campania.pk,
                    "tipo_actividad": self.fertilizacion.pk,
                    "fecha": "2025-10-02",
                },
            )
        )
        semilla = self._json(self._crear_uso())
        urea = self._json(
            self._crear_uso(
                actividad=actividad["id"], recurso=self.urea.pk,
                cantidad="2", unidad=self.quintal.pk,
            )
        )
        uso_b = self._json(
            self._crear_uso(campania=self.campania_b.pk, fecha="2025-01-15")
        )
        anulado = self._json(self._crear_uso(cantidad="8"))
        self._anular_uso(anulado["id"])

        por_campania = self._json(
            self.client.get(f"/api/usos-recursos/?campania={self.campania.pk}")
        )
        self.assertEqual(por_campania["count"], 3)
        por_actividad = self._json(
            self.client.get(f"/api/usos-recursos/?actividad={actividad['id']}")
        )
        self.assertEqual([f["id"] for f in por_actividad["results"]], [urea["id"]])
        por_recurso = self._json(
            self.client.get(f"/api/usos-recursos/?recurso={self.urea.pk}")
        )
        self.assertEqual([f["id"] for f in por_recurso["results"]], [urea["id"]])
        por_categoria = self._json(
            self.client.get("/api/usos-recursos/?categoria=SEMILLA")
        )
        self.assertEqual(por_categoria["count"], 3)
        por_fecha = self._json(
            self.client.get("/api/usos-recursos/?fecha_desde=2025-10-02")
        )
        self.assertEqual(por_fecha["count"], 3)
        por_productor = self._json(
            self.client.get(f"/api/usos-recursos/?productor={self.p2.pk}")
        )
        self.assertEqual(
            [f["id"] for f in por_productor["results"]], [uso_b["id"]]
        )
        por_parcela = self._json(
            self.client.get(f"/api/usos-recursos/?parcela={self.parcela_b.pk}")
        )
        self.assertEqual(por_parcela["count"], 1)
        por_cultivo = self._json(
            self.client.get(f"/api/usos-recursos/?cultivo={self.cultivo_b.pk}")
        )
        self.assertEqual(por_cultivo["count"], 1)
        anulados = self._json(self.client.get("/api/usos-recursos/?estado=ANULADA"))
        self.assertEqual([f["id"] for f in anulados["results"]], [anulado["id"]])
        activos = self._json(self.client.get("/api/usos-recursos/?estado=ACTIVA"))
        self.assertEqual(activos["count"], 3)

        estado_malo = self._json(self.client.get("/api/usos-recursos/?estado=RARA"))
        self.assertIn("estado", estado_malo)
        id_malo = self._json(self.client.get("/api/usos-recursos/?campania=abc"))
        self.assertIn("campania", id_malo)

        por_parcela_codigo = self._json(
            self.client.get(f"/api/usos-recursos/?busqueda={self.parcela.codigo}")
        )
        self.assertEqual(por_parcela_codigo["count"], 3)
        por_recurso_nombre = self._json(
            self.client.get("/api/usos-recursos/?busqueda=Urea")
        )
        self.assertEqual([f["id"] for f in por_recurso_nombre["results"]], [urea["id"]])
        self.assertIn("id", semilla)

    # ------------------------------------------------------------------ #
    # 135: regla de tipo de unidad por categoría y tipo fijo con usos
    # ------------------------------------------------------------------ #
    def test_135_regla_categoria_tipo_en_el_catalogo_de_recursos(self):
        self._entrar_admin()
        mala = self._json(
            self._api(
                "post",
                "/api/recursos/",
                {
                    "nombre": "Semilla en litros S9",
                    "categoria": "SEMILLA",
                    "tipo_unidad": "VOLUMEN",
                },
            )
        )
        self.assertIn(
            "Los recursos de la categoría semilla solo admiten unidades de "
            "tipo masa.",
            str(mala["tipo_unidad"]),
        )
        fito = self._api(
            "post",
            "/api/recursos/",
            {
                "nombre": "Fito en masa S9",
                "categoria": "FITOSANITARIO",
                "tipo_unidad": "MASA",
            },
        )
        self.assertEqual(fito.status_code, 201)

        # Un fitosanitario admite masa o volumen: la regla deja pasar el
        # cambio de tipo, pero lo bloquea la protección por usos
        self._crear_uso(
            recurso=self.tratamiento.pk, cantidad="5", unidad=self.litro.pk
        )
        cambio = self._json(
            self._api(
                "patch",
                f"/api/recursos/{self.tratamiento.pk}/",
                {"tipo_unidad": "MASA"},
            )
        )
        self.assertIn(
            "Este recurso ya tiene usos registrados: su tipo de unidad no se "
            "puede cambiar. Cree otro recurso.",
            str(cambio["tipo_unidad"]),
        )

    # ------------------------------------------------------------------ #
    # 136: factor y tipo de la unidad quedan fijos con usos; los
    #     desplegables ya traen la equivalencia y la categoría
    # ------------------------------------------------------------------ #
    def test_136_unidades_protegidas_y_desplegables_ampliados(self):
        self._entrar_admin()
        self._crear_uso(
            recurso=self.urea.pk, cantidad="2", unidad=self.quintal.pk
        )
        factor = self._json(
            self._api(
                "patch",
                f"/api/unidades/{self.quintal.pk}/",
                {"factor_a_base": "50"},
            )
        )
        self.assertIn(
            "Esta unidad ya tiene usos de recursos registrados: su factor no "
            "se puede cambiar. Cree otra unidad.",
            str(factor["factor_a_base"]),
        )
        tipo = self._json(
            self._api(
                "patch", f"/api/unidades/{self.quintal.pk}/", {"tipo": "VOLUMEN"}
            )
        )
        self.assertIn(
            "Esta unidad ya tiene usos de recursos registrados: su tipo no se "
            "puede cambiar. Cree otra unidad.",
            str(tipo["tipo"]),
        )

        unidades = self._json(self.client.get("/api/unidades/?desplegable=1"))
        qq = next(u for u in unidades if u["id"] == self.quintal.pk)
        self.assertEqual(qq["factor_a_base"], "46.000000")
        self.assertFalse(qq["es_base"])
        recursos = self._json(self.client.get("/api/recursos/?desplegable=1"))
        fila_semilla = next(r for r in recursos if r["id"] == self.semilla.pk)
        self.assertEqual(fila_semilla["categoria"], "SEMILLA")
        self.assertEqual(fila_semilla["tipo_unidad"], "MASA")

    # ------------------------------------------------------------------ #
    # 137: 18 triggers (los 3 de uso_recursos) y reversibilidad de 0004
    # ------------------------------------------------------------------ #
    def test_137_triggers_y_reversibilidad_de_las_migraciones(self):
        triggers = {
            fila[0]
            for fila in self._consulta(
                "SELECT tgname FROM pg_trigger "
                "WHERE NOT tgisinternal AND tgrelid IN (SELECT oid FROM pg_class "
                "WHERE relnamespace = 'public'::regnamespace)"
            )
        }
        self.assertEqual(len(triggers), 19)
        self.assertLessEqual(
            {
                "trg_uso_recursos_base",
                "trg_uso_recursos_fecha",
                "trg_uso_recursos_actualizado",
                "trg_clima_actualizado",
            },
            triggers,
        )

        prosrc = {
            fila[0]: fila[1]
            for fila in self._consulta(
                "SELECT proname, prosrc FROM pg_proc "
                "WHERE proname IN ('fn_uso_recurso')"
            )
        }
        self.assertIn("cantidad_base", prosrc["fn_uso_recurso"])
        self.assertIn("factor_a_base", prosrc["fn_uso_recurso"])
        self.assertIn("no pertenece a esta campaña", prosrc["fn_uso_recurso"])

        # Reversibilidad real: la reversión de 0004 quita los 3 triggers
        # y la función; el avance vuelve a instalarlos
        mig_uso = importlib.import_module(
            "seguimiento.migrations.0004_funciones_y_triggers_uso_recursos"
        )
        for consulta in mig_uso.Migration.operations[0].reverse_sql:
            self._sql(consulta)
        restantes = self._consulta(
            "SELECT count(*) FROM pg_trigger "
            "WHERE NOT tgisinternal AND tgrelid = 'uso_recursos'::regclass"
        )[0][0]
        self.assertEqual(restantes, 0)
        sin_fn = self._consulta(
            "SELECT count(*) FROM pg_proc WHERE proname = 'fn_uso_recurso'"
        )[0][0]
        self.assertEqual(sin_fn, 0)
        for consulta in mig_uso.Migration.operations[0].sql:
            self._sql(consulta)
        restaurados = {
            fila[0]
            for fila in self._consulta(
                "SELECT tgname FROM pg_trigger "
                "WHERE NOT tgisinternal AND tgrelid = 'uso_recursos'::regclass"
            )
        }
        self.assertEqual(
            restaurados,
            {
                "trg_uso_recursos_base",
                "trg_uso_recursos_fecha",
                "trg_uso_recursos_actualizado",
            },
        )


class Semana10Base(Semana7Base):
    """Datos comunes de la Semana 10: la base de la Semana 7 más la unidad
    de masa (para la cosecha del resumen climático) y los helpers de clima.
    _clima_bd crea registros con fuente API por la vía de la base, que es
    como los dejará la consulta a la API meteorológica (HU-84)."""

    def setUp(self):
        super().setUp()
        self.kg = Unidad.objects.get(nombre="Kilogramo")

    def _datos_clima(self, **extra):
        datos = {
            "parcela": self.parcela.pk,
            "fecha": "2025-10-01",
            "temp_min": "5.0",
            "temp_max": "15.0",
        }
        datos.update(extra)
        return datos

    def _crear_clima(self, **extra):
        return self._api("post", "/api/clima/", self._datos_clima(**extra))

    def _clima_bd(self, **extra):
        datos = {
            "parcela": self.parcela,
            "fecha": date(2025, 10, 2),
            "temp_min": Decimal("0.0"),
            "temp_max": Decimal("8.0"),
            "temp_prom": Decimal("4.0"),
            "fuente": Clima.FUENTE_API,
        }
        datos.update(extra)
        return Clima.objects.create(**datos)

    def _consulta(self, consulta, parametros=None):
        with connection.cursor() as cursor:
            if parametros:
                cursor.execute(consulta, parametros)
            else:
                cursor.execute(consulta)
            return cursor.fetchall()

    def _sql(self, consulta):
        with connection.cursor() as cursor:
            cursor.execute(consulta)

    def _consulta_cte_clima(self, campania_id):
        """Ejecuta el bloque clima_c de vw_dataset_entrenamiento con el
        TEXTO LITERAL del diseño (DB_sql/02_reglas_y_vista.sql:386-397).
        La vista completa aún no se puede materializar porque su CTE de
        incidencias depende de una tabla de una semana posterior; el
        bloque de clima es el que debe coincidir con el resumen de la
        ficha de campaña."""
        ruta = (
            Path(__file__).resolve().parents[2]
            / "DB_sql"
            / "02_reglas_y_vista.sql"
        )
        texto = ruta.read_text(encoding="utf-8", errors="replace")
        inicio = texto.index("clima_c AS (")
        fin = texto.index("inc_c AS (", inicio)
        bloque = texto[inicio:fin].strip().rstrip(",").strip()
        return self._consulta(
            f"WITH {bloque}\n"
            "SELECT precipitacion_acum_mm, ROUND(temp_prom_c, 1), "
            "ROUND(humedad_prom_pct, 1), n_heladas, dias_con_clima "
            "FROM clima_c WHERE campania_id = %s",
            [campania_id],
        )

    def _poner_coordenadas(self, latitud="-13.520000", longitud="-71.950000"):
        """La parcela base nace sin coordenadas (el modelo exige latitud y
        longitud juntas): la HU-84 las necesita para consultar."""
        self.parcela.latitud = Decimal(latitud)
        self.parcela.longitud = Decimal(longitud)
        self.parcela.save()

    def _datos_consulta_api(self, **extra):
        datos = {
            "parcela": self.parcela.pk,
            "fecha_desde": "2025-10-01",
            "fecha_hasta": "2025-10-03",
        }
        datos.update(extra)
        return datos

    def _consulta_api(self, **extra):
        return self._api(
            "post", "/api/clima/consulta-api/", self._datos_consulta_api(**extra)
        )

    def _dia_servicio(self, fecha, **medidas):
        """Un día como lo devuelve el adaptador de Open-Meteo simulado
        (lo que no se nombre llega None)."""
        datos = {clave: None for clave in CLAVES_SALIDA}
        datos["fecha"] = (
            date.fromisoformat(fecha) if isinstance(fecha, str) else fecha
        )
        datos.update(medidas)
        return datos


class ClimaApiTests(Semana10Base):
    """Pruebas 138-151 y 155."""

    # ------------------------------------------------------------------ #
    # 138: alta válida — el servidor calcula el promedio, deriva la helada
    #     del umbral y fija fuente y registrado por
    # ------------------------------------------------------------------ #
    def test_138_alta_valida_calcula_promedio_y_helada(self):
        self._entrar_admin()
        creado = self._json(self._crear_clima())
        self.assertEqual(creado["fecha"], "2025-10-01")
        self.assertEqual(creado["temp_prom"], "10.0")
        self.assertTrue(creado["temp_prom_calculado"])
        self.assertEqual(creado["fuente"], "MANUAL")
        self.assertEqual(creado["registrado_por"], "admin_pruebas")
        self.assertEqual(creado["parcela"]["codigo"], self.parcela.codigo)
        self.assertEqual(
            creado["parcela"]["productor"]["nombre_completo"], "Alfa, Uno"
        )
        self.assertEqual(creado["parcela"]["comunidad"]["nombre"], "Comunidad S7")
        self.assertFalse(creado["helada"])
        # Con mínima, la helada siempre la deriva el servidor (umbral 0 °C)
        self.assertTrue(creado["helada_calculada"])
        self.assertIn("creado_en", creado)

        fria = self._json(
            self._crear_clima(fecha="2025-10-02", temp_min="-1.5", temp_max="3.0")
        )
        # Punto medio con 1 decimal: (−1.5 + 3.0) / 2 = 0.75 → 0.8
        self.assertEqual(fria["temp_prom"], "0.8")
        self.assertTrue(fria["helada"])
        self.assertTrue(fria["helada_calculada"])

        # Y un registro que solo marca la helada, sin medidas
        solo_helada = self._json(
            self._crear_clima(
                fecha="2025-10-03",
                temp_min=None,
                temp_max=None,
                helada=True,
            )
        )
        self.assertTrue(solo_helada["helada"])
        self.assertFalse(solo_helada["helada_calculada"])
        self.assertFalse(solo_helada["temp_prom_calculado"])
        self.assertIsNone(solo_helada["temp_prom"])

    # ------------------------------------------------------------------ #
    # 139: al menos una medida o la helada; mínima ≤ máxima y el promedio
    #     entre ambas (400 claros, no un 500)
    # ------------------------------------------------------------------ #
    def test_139_medidas_obligatorias_y_coherencia_de_temperaturas(self):
        self._entrar_admin()
        vacio = self._json(
            self._crear_clima(temp_min=None, temp_max=None, temp_prom=None)
        )
        self.assertIn("helada", vacio)
        self.assertIn(
            "al menos una medida meteorológica", vacio["helada"][0]
        )

        invertidas = self._json(
            self._crear_clima(fecha="2025-10-04", temp_min="20.0", temp_max="10.0")
        )
        self.assertIn("temp_min", invertidas)
        self.assertIn("máxima", invertidas["temp_min"][0])

        promedio_alto = self._json(
            self._crear_clima(fecha="2025-10-05", temp_prom="25.0")
        )
        self.assertIn("temp_prom", promedio_alto)
        self.assertIn("entre la mínima", promedio_alto["temp_prom"][0])

        promedio_bajo = self._json(
            self._crear_clima(fecha="2025-10-06", temp_prom="1.0")
        )
        self.assertIn("temp_prom", promedio_bajo)
        self.assertIn("entre la mínima", promedio_bajo["temp_prom"][0])

    # ------------------------------------------------------------------ #
    # 140: rangos de cada medida (los CHECK de la base, traducidos a un
    #     400 con el nombre del campo)
    # ------------------------------------------------------------------ #
    def test_140_rangos_de_las_medidas(self):
        self._entrar_admin()
        minima = self._json(self._crear_clima(temp_min="50.0"))
        self.assertIn("entre -30 y 45", minima["temp_min"][0])
        maxima = self._json(
            self._crear_clima(fecha="2025-10-02", temp_max="-31.0")
        )
        self.assertIn("entre -30 y 45", maxima["temp_max"][0])
        precipitacion = self._json(
            self._crear_clima(fecha="2025-10-03", precipitacion_mm="-1")
        )
        self.assertIn("negativa", precipitacion["precipitacion_mm"][0])
        humedad = self._json(
            self._crear_clima(fecha="2025-10-04", humedad_pct="150")
        )
        self.assertIn("entre 0 y 100", humedad["humedad_pct"][0])
        viento = self._json(
            self._crear_clima(fecha="2025-10-05", viento_ms="-0.5")
        )
        self.assertIn("negativo", viento["viento_ms"][0])
        radiacion = self._json(
            self._crear_clima(fecha="2025-10-06", radiacion_mj="-1")
        )
        self.assertIn("negativa", radiacion["radiacion_mj"][0])
        # Ninguna de las anteriores llegó a guardarse
        self.assertEqual(Clima.objects.count(), 0)

    # ------------------------------------------------------------------ #
    # 141: fechas — ni futuras (hora de Lima) ni anteriores a 2000
    # ------------------------------------------------------------------ #
    def test_141_fechas_fuera_del_rango_se_rechazan(self):
        self._entrar_admin()
        futura = (self._hoy_lima() + timedelta(days=1)).isoformat()
        rechazo = self._json(self._crear_clima(fecha=futura))
        self.assertIn("no puede ser futura", rechazo["fecha"][0])
        vieja = self._json(self._crear_clima(fecha="1999-12-31"))
        self.assertIn(
            "anterior al 1 de enero de 2000", vieja["fecha"][0]
        )
        formato = self._json(self._crear_clima(fecha="ayer"))
        self.assertIn("AAAA-MM-DD", formato["fecha"][0])
        # La última fecha admitida es hoy mismo (hora de Lima)
        hoy = self._hoy_lima().isoformat()
        self.assertEqual(self._crear_clima(fecha=hoy).status_code, 201)

    # ------------------------------------------------------------------ #
    # 142: la parcela debe existir, estar activa y, para el técnico, ser
    #     de SUS productores (ahí se prueba en la 146)
    # ------------------------------------------------------------------ #
    def test_142_parcela_inexistente_o_inactiva(self):
        self._entrar_admin()
        inexistente = self._json(self._crear_clima(parcela=99999))
        self.assertIn(
            "La parcela indicada no existe.", inexistente["parcela"][0]
        )
        inactiva = self._parcela_bd(self.p1, "1.00")
        inactiva.estado = Parcela.ESTADO_INACTIVA
        inactiva.save(update_fields=("estado",))
        rechazo = self._json(self._crear_clima(parcela=inactiva.pk))
        self.assertIn("no existe o está inactiva", rechazo["parcela"][0])
        self.assertEqual(Clima.objects.count(), 0)

    # ------------------------------------------------------------------ #
    # 143: una fila por parcela y día — 400 antes de guardar y también si
    #     la carrera con la base llega a materializarse (nunca un 500)
    # ------------------------------------------------------------------ #
    def test_143_duplicado_de_parcela_y_fecha(self):
        from .serializers import ClimaEscrituraSerializer

        self._entrar_admin()
        self.assertEqual(self._crear_clima().status_code, 201)
        duplicado = self._json(self._crear_clima(temp_max="20.0"))
        self.assertIn("fecha", duplicado)
        self.assertIn(
            "Ya existe un registro de clima", duplicado["fecha"][0]
        )
        # Carrera: la validación no lo ve, pero la base lo rechaza
        with patch.object(
            ClimaEscrituraSerializer, "_existe_duplicado", return_value=False
        ):
            carrera = self._api("post", "/api/clima/", self._datos_clima())
        self.assertEqual(carrera.status_code, 400)
        self.assertIn("ya existe", str(self._json(carrera)))
        self.assertEqual(Clima.objects.count(), 1)

    # ------------------------------------------------------------------ #
    # 144: campos protegidos y cálculos que el cliente no puede forzar
    # ------------------------------------------------------------------ #
    def test_144_campos_protegidos_y_calculos_del_servidor(self):
        self._entrar_admin()
        creado = self._json(
            self._api(
                "post",
                "/api/clima/",
                {
                    "parcela": self.parcela.pk,
                    "fecha": "2025-10-07",
                    "temp_min": "5.0",
                    "temp_max": "15.0",
                    "temp_prom": "12.0",
                    "fuente": "API",
                    "registrado_por": 99999,
                    "creado_en": "2000-01-01T00:00:00Z",
                },
            )
        )
        # Un promedio propio, válido entre mínima y máxima, se respeta
        self.assertEqual(creado["temp_prom"], "12.0")
        self.assertFalse(creado["temp_prom_calculado"])
        # ...pero fuente, registrado por y fechas son del servidor
        self.assertEqual(creado["fuente"], "MANUAL")
        self.assertEqual(creado["registrado_por"], "admin_pruebas")

        # La helada la manda el servidor cuando hay mínima (umbral 0 °C)
        contraria = self._json(
            self._crear_clima(
                fecha="2025-10-08", temp_min="-2.0", temp_max="4.0", helada=False
            )
        )
        self.assertTrue(contraria["helada"])
        self.assertTrue(contraria["helada_calculada"])

        # Sin mínima, manda la marca del técnico
        manual = self._json(
            self._crear_clima(
                fecha="2025-10-09",
                temp_min=None,
                temp_max=None,
                helada=True,
            )
        )
        self.assertTrue(manual["helada"])
        self.assertFalse(manual["helada_calculada"])

        # Al editar sin enviar promedio, vuelve a calcularse el punto medio
        editado = self._json(
            self._api(
                "patch",
                f"/api/clima/{creado['id']}/",
                {"temp_min": "4.0", "temp_max": "8.0"},
            )
        )
        self.assertEqual(editado["temp_prom"], "6.0")
        self.assertTrue(editado["temp_prom_calculado"])

    # ------------------------------------------------------------------ #
    # 145: editar un registro que vino de la API exige confirmación y lo
    #     convierte en MANUAL; uno manual se edita sin más
    # ------------------------------------------------------------------ #
    def test_145_editar_registro_de_la_api_exige_confirmacion(self):
        self._entrar_admin()
        registro = self._clima_bd()
        sin_confirmar = self._json(
            self._api(
                "patch",
                f"/api/clima/{registro.pk}/",
                {"precipitacion_mm": "12.0"},
            )
        )
        self.assertIn("confirmar_reemplazo", sin_confirmar)
        self.assertIn(
            "API meteorológica", sin_confirmar["confirmar_reemplazo"][0]
        )
        registro.refresh_from_db()
        self.assertEqual(registro.fuente, Clima.FUENTE_API)
        self.assertIsNone(registro.precipitacion_mm)

        confirmado = self._json(
            self._api(
                "patch",
                f"/api/clima/{registro.pk}/",
                {"precipitacion_mm": "12.0", "confirmar_reemplazo": True},
            )
        )
        self.assertEqual(confirmado["fuente"], "MANUAL")
        self.assertEqual(confirmado["precipitacion_mm"], "12.0")
        self.assertEqual(confirmado["helada_calculada"], True)

        # Un registro MANUAL no pide nada
        manual = self._json(self._crear_clima(fecha="2025-10-10"))
        ok = self._json(
            self._api(
                "patch",
                f"/api/clima/{manual['id']}/",
                {"humedad_pct": "55.0"},
            )
        )
        self.assertEqual(ok["fuente"], "MANUAL")
        self.assertEqual(ok["humedad_pct"], "55.0")

    # ------------------------------------------------------------------ #
    # 146: permisos y ámbitos — el técnico solo ve y registra clima de SUS
    #     productores; el coordinador consulta; sin sesión, 401
    # ------------------------------------------------------------------ #
    def test_146_permisos_y_ambitos_por_rol(self):
        self._entrar_admin()
        propio = self._json(self._crear_clima())
        ajeno = self._json(
            self._crear_clima(parcela=self.parcela_b.pk, fecha="2025-10-02")
        )

        self._entrar_tecnico()
        listado = self._json(self.client.get("/api/clima/"))
        self.assertEqual(
            [f["id"] for f in listado["results"]], [propio["id"]]
        )
        detalle_ajeno = self.client.get(f"/api/clima/{ajeno['id']}/")
        self.assertEqual(detalle_ajeno.status_code, 404)
        crear_ajena = self._json(
            self._crear_clima(parcela=self.parcela_b.pk, fecha="2025-10-03")
        )
        self.assertIn(
            "La parcela indicada no existe.", crear_ajena["parcela"][0]
        )
        self.assertEqual(self._crear_clima(fecha="2025-10-04").status_code, 201)
        # registrado_por se oculta a los roles con limita_a_asignados
        detalle = self._json(self.client.get(f"/api/clima/{propio['id']}/"))
        self.assertNotIn("registrado_por", detalle)
        editar_tecnico = self._api(
            "patch", f"/api/clima/{propio['id']}/", {"humedad_pct": "60.0"}
        )
        self.assertEqual(editar_tecnico.status_code, 200)

        self._entrar_coordinador()
        self.assertEqual(self.client.get("/api/clima/").status_code, 200)
        crear_coord = self._api("post", "/api/clima/", self._datos_clima())
        self.assertEqual(crear_coord.status_code, 403)

        self.client.cookies.clear()
        self.assertEqual(self.client.get("/api/clima/").status_code, 401)

    # ------------------------------------------------------------------ #
    # 147: filtros (parcela, productor, comunidad, distrito, provincia,
    #     fechas, fuente y heladas), búsqueda, orden y paginación
    # ------------------------------------------------------------------ #
    def test_147_filtros_busqueda_orden_y_paginacion(self):
        self._entrar_admin()
        self._json(self._crear_clima(fecha="2025-10-01"))
        self._json(
            self._crear_clima(fecha="2025-10-02", temp_min="-3.0", temp_max="2.0")
        )
        self._json(
            self._crear_clima(
                parcela=self.parcela_b.pk,
                fecha="2025-10-03",
                temp_min=None,
                temp_max=None,
                precipitacion_mm="12.5",
            )
        )
        self._clima_bd(fecha=date(2025, 9, 20), helada=True)
        self._clima_bd(
            fecha=date(2025, 9, 18),
            parcela=self.parcela_b,
            fuente=Clima.FUENTE_MANUAL,
        )

        por_parcela = self._json(
            self.client.get(f"/api/clima/?parcela={self.parcela.pk}")
        )
        self.assertEqual(por_parcela["count"], 3)
        por_productor = self._json(
            self.client.get(f"/api/clima/?productor={self.p1.pk}")
        )
        self.assertEqual(por_productor["count"], 3)
        por_comunidad = self._json(
            self.client.get(f"/api/clima/?comunidad={self.comunidad.pk}")
        )
        self.assertEqual(por_comunidad["count"], 5)
        por_distrito = self._json(
            self.client.get(f"/api/clima/?distrito={self.distrito.pk}")
        )
        self.assertEqual(por_distrito["count"], 5)
        por_provincia = self._json(
            self.client.get(f"/api/clima/?provincia={self.provincia.pk}")
        )
        self.assertEqual(por_provincia["count"], 5)
        por_fechas = self._json(
            self.client.get(
                "/api/clima/?fecha_desde=2025-10-01&fecha_hasta=2025-10-02"
            )
        )
        self.assertEqual(por_fechas["count"], 2)
        por_fuente = self._json(self.client.get("/api/clima/?fuente=API"))
        self.assertEqual(por_fuente["count"], 1)
        manual = self._json(self.client.get("/api/clima/?fuente=MANUAL"))
        self.assertEqual(manual["count"], 4)
        con_heladas = self._json(self.client.get("/api/clima/?heladas=1"))
        self.assertEqual(con_heladas["count"], 2)
        sin_heladas = self._json(self.client.get("/api/clima/?heladas=0"))
        self.assertEqual(sin_heladas["count"], 3)
        fuente_mala = self._json(self.client.get("/api/clima/?fuente=X"))
        self.assertIn("fuente", fuente_mala)
        heladas_malas = self._json(self.client.get("/api/clima/?heladas=x"))
        self.assertIn("heladas", heladas_malas)

        # Búsqueda por código de parcela y por apellidos
        por_codigo = self._json(
            self.client.get(f"/api/clima/?busqueda={self.parcela.codigo}")
        )
        self.assertEqual(por_codigo["count"], 3)
        por_apellido = self._json(self.client.get("/api/clima/?busqueda=Beta"))
        self.assertEqual(por_apellido["count"], 2)

        # Orden por fecha descendente (el Meta del modelo)
        ordenado = self._json(self.client.get("/api/clima/"))
        fechas = [f["fecha"] for f in ordenado["results"]]
        self.assertEqual(fechas, sorted(fechas, reverse=True))

        # Paginación global de 20 por página
        Clima.objects.all().delete()
        Clima.objects.bulk_create(
            [
                Clima(
                    parcela=self.parcela,
                    fecha=date(2024, 1, 1) + timedelta(days=i),
                    temp_min=Decimal("1.0"),
                    temp_max=Decimal("9.0"),
                    temp_prom=Decimal("5.0"),
                )
                for i in range(21)
            ]
        )
        pagina1 = self._json(self.client.get("/api/clima/"))
        self.assertEqual(pagina1["count"], 21)
        self.assertEqual(len(pagina1["results"]), 20)
        self.assertEqual(pagina1["results"][0]["fecha"], "2024-01-21")
        pagina2 = self._json(self.client.get("/api/clima/?page=2"))
        self.assertEqual(len(pagina2["results"]), 1)
        self.assertEqual(pagina2["results"][0]["fecha"], "2024-01-01")

    # ------------------------------------------------------------------ #
    # 148: sin DELETE (405: un error se corrige editando), edición de las
    #     medidas y 401 sin sesión
    # ------------------------------------------------------------------ #
    def test_148_sin_delete_y_edicion_de_medidas(self):
        self._entrar_admin()
        creado = self._json(self._crear_clima())
        self.client.cookies.clear()
        self.assertEqual(self.client.get("/api/clima/").status_code, 401)
        self._entrar_admin()
        borrar = self._api("delete", f"/api/clima/{creado['id']}/")
        self.assertEqual(borrar.status_code, 405)

        editado = self._json(
            self._api(
                "patch",
                f"/api/clima/{creado['id']}/",
                {"temp_min": "3.0", "temp_max": "7.0", "precipitacion_mm": "4.5"},
            )
        )
        self.assertEqual(editado["temp_prom"], "5.0")
        self.assertTrue(editado["temp_prom_calculado"])
        self.assertEqual(editado["precipitacion_mm"], "4.5")

        # PUT completo también (la corrección es la edición, no el borrado)
        put = self._json(
            self._api(
                "put",
                f"/api/clima/{creado['id']}/",
                self._datos_clima(temp_min="1.0", temp_max="9.0"),
            )
        )
        self.assertEqual(put["temp_prom"], "5.0")
        self.assertEqual(put["parcela"]["id"], self.parcela.pk)

    # ------------------------------------------------------------------ #
    # 149: el resumen de la campaña coincide, cifra a cifra, con las
    #     columnas clima_c de vw_dataset_entrenamiento
    # ------------------------------------------------------------------ #
    def test_149_resumen_de_campania_igual_que_la_vista_del_dataset(self):
        self._entrar_admin()
        # La campaña pasa a producción con siembra y cosecha
        self.campania.estado = Campania.ESTADO_EN_PRODUCCION
        self.campania.fecha_siembra = date(2025, 9, 5)
        self.campania.save(update_fields=("estado", "fecha_siembra"))

        self._crear_clima(
            fecha="2025-09-10",
            temp_min="6.0",
            temp_max="14.0",
            precipitacion_mm="10.0",
            humedad_pct="70.0",
        )
        self._crear_clima(
            fecha="2025-11-20",
            temp_min="-2.0",
            temp_max="9.0",
            precipitacion_mm="25.5",
            humedad_pct="80.0",
        )
        # Después de la cosecha: fuera de la ventana, no cuenta
        self._crear_clima(
            fecha="2026-05-20", temp_min="8.0", temp_max="16.0",
            precipitacion_mm="99.9",
        )

        produccion = self._json(
            self._api(
                "post",
                "/api/producciones/",
                {
                    "campania": self.campania.pk,
                    "fecha_cosecha": "2026-04-15",
                    "superficie_cosechada_ha": "1.50",
                    "cantidad_producida": "7000",
                    "unidad": self.kg.pk,
                },
            )
        )
        self.assertTrue(produccion["incluir_en_entrenamiento"])
        self.assertEqual(
            self._api(
                "post", f"/api/campanias/{self.campania.pk}/cerrar/"
            ).status_code,
            200,
        )

        ficha = self._json(self._api("get", f"/api/campanias/{self.campania.pk}/"))
        resumen = ficha["resumen_clima"]
        vista = self._consulta_cte_clima(self.campania.pk)
        self.assertEqual(len(vista), 1)
        precip_vista, temp_vista, humedad_vista, heladas_vista, dias_vista = vista[0]
        self.assertEqual(
            float(resumen["precipitacion_acum_mm"]), float(precip_vista)
        )
        self.assertEqual(resumen["temp_prom_c"], float(temp_vista))
        self.assertEqual(resumen["humedad_prom_pct"], float(humedad_vista))
        self.assertEqual(resumen["n_heladas"], heladas_vista)
        self.assertEqual(resumen["dias_con_clima"], dias_vista)
        # ...y los valores esperados a mano
        self.assertEqual(resumen["precipitacion_acum_mm"], 35.5)
        self.assertEqual(resumen["temp_prom_c"], 6.8)
        self.assertEqual(resumen["humedad_prom_pct"], 75.0)
        self.assertEqual(resumen["n_heladas"], 1)
        self.assertEqual(resumen["dias_con_clima"], 2)
        self.assertEqual(resumen["desde"], "2025-09-05")
        self.assertEqual(resumen["hasta"], "2026-04-15")
        self.assertFalse(resumen["provisional"])
        self.assertEqual(
            resumen["dias_ventana"], (date(2026, 4, 15) - date(2025, 9, 5)).days + 1
        )
        self.assertIsNotNone(resumen["cobertura_pct"])

    # ------------------------------------------------------------------ #
    # 150: sin datos el resumen viene vacío (no error), la ventana en
    #     curso es provisional y el detalle de parcela cuenta su clima
    # ------------------------------------------------------------------ #
    def test_150_resumen_vacio_y_conteo_en_la_parcela(self):
        self._entrar_admin()
        vacio = self._json(self._api("get", f"/api/campanias/{self.campania.pk}/"))
        resumen = vacio["resumen_clima"]
        self.assertIsNone(resumen["precipitacion_acum_mm"])
        self.assertIsNone(resumen["temp_prom_c"])
        self.assertIsNone(resumen["humedad_prom_pct"])
        self.assertEqual(resumen["n_heladas"], 0)
        self.assertEqual(resumen["dias_con_clima"], 0)
        self.assertEqual(resumen["cobertura_pct"], 0)
        self.assertTrue(resumen["provisional"])
        # Sin siembra, la ventana arranca en la fecha de inicio
        self.assertEqual(resumen["desde"], "2025-09-01")
        # ...y sin cosecha, termina hoy (hora de Lima)
        self.assertEqual(resumen["hasta"], self._hoy_lima().isoformat())
        self.assertGreater(resumen["dias_ventana"], 0)

        self.assertEqual(self._crear_clima().status_code, 201)
        con_datos = self._json(
            self._api("get", f"/api/campanias/{self.campania.pk}/")
        )["resumen_clima"]
        self.assertEqual(con_datos["dias_con_clima"], 1)
        self.assertGreater(con_datos["cobertura_pct"], 0)

        parcela = self._json(
            self._api("get", f"/api/parcelas/{self.parcela.pk}/")
        )
        self.assertEqual(parcela["clima"]["registros"], 1)
        self.assertEqual(parcela["clima"]["ultimo_dia"], "2025-10-01")

    # ------------------------------------------------------------------ #
    # 151: la base es la última red de seguridad — los CHECK de rangos y
    #     la unicidad rechazan también a mano
    # ------------------------------------------------------------------ #
    def test_151_la_base_protege_rangos_y_unicidad(self):
        with self.assertRaises(DatabaseError):
            with transaction.atomic():
                Clima.objects.create(
                    parcela=self.parcela,
                    fecha=date(2025, 11, 1),
                    temp_min=Decimal("99.0"),
                )
        with self.assertRaises(DatabaseError):
            with transaction.atomic():
                Clima.objects.create(
                    parcela=self.parcela,
                    fecha=date(2025, 11, 2),
                    helada=True,
                    humedad_pct=Decimal("150.0"),
                )
        with self.assertRaises(DatabaseError):
            with transaction.atomic():
                Clima.objects.create(
                    parcela=self.parcela,
                    fecha=date(2025, 11, 3),
                    temp_min=Decimal("20.0"),
                    temp_max=Decimal("10.0"),
                )
        self._clima_bd(fecha=date(2025, 11, 4))
        with self.assertRaises(DatabaseError):
            with transaction.atomic():
                Clima.objects.create(
                    parcela=self.parcela,
                    fecha=date(2025, 11, 4),
                    temp_min=Decimal("5.0"),
                )
        self.assertEqual(Clima.objects.count(), 1)

    # ------------------------------------------------------------------ #
    # 155: umbral_helada_c — la quinta clave de parámetros, su rango y su
    #     efecto en las heladas que deriva el registro de clima
    # ------------------------------------------------------------------ #
    def test_155_umbral_helada_como_parametro_del_sistema(self):
        self._entrar_admin()
        listado = self._json(self.client.get("/api/parametros/"))
        self.assertEqual(listado["count"], 5)
        umbral = [
            p for p in listado["results"] if p["clave"] == "umbral_helada_c"
        ][0]
        self.assertEqual(umbral["valor"], "0")
        self.assertIn("helada", umbral["descripcion"].lower())

        fuera = self._json(
            self._api("patch", "/api/parametros/umbral_helada_c/", {"valor": "-11"})
        )
        self.assertIn("entre -10 y 5", fuera["valor"][0])
        fuera = self._json(
            self._api("patch", "/api/parametros/umbral_helada_c/", {"valor": "6"})
        )
        self.assertIn("entre -10 y 5", fuera["valor"][0])
        no_num = self._json(
            self._api("patch", "/api/parametros/umbral_helada_c/", {"valor": "abc"})
        )
        self.assertIn("número entre -10 y 5", no_num["valor"][0])
        ok = self._json(
            self._api("patch", "/api/parametros/umbral_helada_c/", {"valor": "-5"})
        )
        self.assertEqual(ok["valor"], "-5")

        # Con el umbral nuevo, −3 °C ya no es helada y −6 °C sí
        grieta = self._json(
            self._crear_clima(fecha="2025-10-11", temp_min="-3.0", temp_max="2.0")
        )
        self.assertFalse(grieta["helada"])
        mas_fria = self._json(
            self._crear_clima(fecha="2025-10-12", temp_min="-6.0", temp_max="1.0")
        )
        self.assertTrue(mas_fria["helada"])


class ClimaConsultaApiTests(Semana10Base):
    """Pruebas 152-154: la consulta a la API meteorológica (HU-84) con el
    servicio siempre simulado (sin internet en la suite)."""

    # ------------------------------------------------------------------ #
    # 152: permisos y reglas de la entrada — parcela con coordenadas,
    #     rango de hasta 92 días sin fechas futuras; el informe guarda los
    #     días válidos como fuente API con las reglas del servidor
    # ------------------------------------------------------------------ #
    def test_152_reglas_de_la_entrada_y_primer_guardado(self):
        self.assertEqual(self._consulta_api().status_code, 401)
        self._entrar_coordinador()
        self.assertEqual(self._consulta_api().status_code, 403)
        self.client.logout()

        self._entrar_tecnico()
        sin_coordenadas = self._json(self._consulta_api())
        self.assertIn("coordenadas", sin_coordenadas["parcela"][0])

        self._poner_coordenadas()
        ajena = self._json(self._consulta_api(parcela=self.parcela_b.pk))
        self.assertEqual(ajena["parcela"][0], "La parcela indicada no existe.")

        largo = self._json(
            self._consulta_api(fecha_desde="2025-01-01", fecha_hasta="2025-05-01")
        )
        self.assertIn("92 días", largo["fecha_hasta"][0])

        futuro = self._json(
            self._consulta_api(
                fecha_desde="2026-01-01",
                fecha_hasta=(self._hoy_lima() + timedelta(days=1)).isoformat(),
            )
        )
        self.assertEqual(
            futuro["fecha_hasta"][0], "La fecha final no puede ser futura."
        )

        invertido = self._json(
            self._consulta_api(fecha_desde="2025-10-05", fecha_hasta="2025-10-01")
        )
        self.assertIn("posterior", invertido["fecha_desde"][0])

        self.parcela.estado = Parcela.ESTADO_INACTIVA
        self.parcela.save()
        inactiva = self._json(self._consulta_api())
        self.assertIn("inactiva", inactiva["parcela"][0])
        self.parcela.estado = Parcela.ESTADO_ACTIVA
        self.parcela.save()

        with patch("seguimiento.views.consultar_dias") as servicio:
            servicio.return_value = [
                self._dia_servicio(
                    "2025-10-01", temp_min=-2.0, temp_max=9.0, precipitacion_mm=3.5
                ),
                self._dia_servicio("2025-10-02"),  # todo None
                self._dia_servicio("2025-10-03", humedad_pct=70.0),
            ]
            respuesta = self._consulta_api()
        self.assertEqual(respuesta.status_code, 200)
        informe = self._json(respuesta)
        self.assertEqual(informe["creados"], 2)
        self.assertEqual(informe["sin_datos"], 1)
        self.assertEqual(informe["actualizados"], 0)
        self.assertEqual(informe["omitidos_manual"], 0)
        self.assertEqual(informe["omitidos_api"], 0)
        self.assertEqual(informe["descartados"], 0)
        # El servicio se llamó con las coordenadas redondeadas a 2 decimales
        self.assertEqual(servicio.call_args[0][:2], (-13.52, -71.95))

        registro = Clima.objects.get(parcela=self.parcela, fecha=date(2025, 10, 1))
        self.assertEqual(registro.fuente, Clima.FUENTE_API)
        self.assertEqual(registro.temp_prom, Decimal("3.5"))
        self.assertTrue(registro.helada)
        self.assertEqual(registro.precipitacion_mm, Decimal("3.5"))
        self.assertEqual(registro.registrado_por, self.tecnico)
        solo_humedad = Clima.objects.get(parcela=self.parcela, fecha=date(2025, 10, 3))
        self.assertEqual(solo_humedad.humedad_pct, Decimal("70.0"))
        self.assertIsNone(solo_humedad.temp_min)
        self.assertFalse(solo_humedad.helada)
        self.assertFalse(Clima.objects.filter(fecha=date(2025, 10, 2)).exists())

    # ------------------------------------------------------------------ #
    # 153: convivencia — un manual nunca lo pisa la API, un registro de la
    #     API se refresca, los inválidos se descartan y la transacción es
    #     única (un choque a mitad de rango no deja nada a medias)
    # ------------------------------------------------------------------ #
    def test_153_no_pisa_manuales_y_es_transaccion_unica(self):
        self._entrar_tecnico()
        self._poner_coordenadas()
        manual = Clima.objects.create(
            parcela=self.parcela,
            fecha=date(2025, 10, 1),
            fuente=Clima.FUENTE_MANUAL,
            temp_min=Decimal("1.0"),
            temp_max=Decimal("5.0"),
            temp_prom=Decimal("3.0"),
            registrado_por=self.tecnico,
        )
        previo = self._clima_bd(
            fecha=date(2025, 10, 2),
            temp_min=Decimal("2.0"),
            temp_max=Decimal("6.0"),
            temp_prom=Decimal("4.0"),
        )
        conservado = self._clima_bd(fecha=date(2025, 10, 7))
        with patch("seguimiento.views.consultar_dias") as servicio:
            servicio.return_value = [
                self._dia_servicio("2025-10-01", temp_min=9.0, temp_max=19.0),
                self._dia_servicio(
                    "2025-10-02", temp_min=0.0, temp_max=12.0, precipitacion_mm=1.2
                ),
                self._dia_servicio("2025-10-03", temp_min=-40.0, temp_max=5.0),
                self._dia_servicio("2025-10-04", precipitacion_mm=2.0),
                self._dia_servicio("2025-10-06"),  # sin dato
                # 10-05 ni siquiera viene del servicio; 10-07 viene vacío
            ]
            respuesta = self._consulta_api(
                fecha_desde="2025-10-01", fecha_hasta="2025-10-07"
            )
        informe = self._json(respuesta)
        self.assertEqual(informe["creados"], 1)
        self.assertEqual(informe["actualizados"], 1)
        self.assertEqual(informe["omitidos_manual"], 1)
        self.assertEqual(informe["omitidos_api"], 1)
        self.assertEqual(informe["descartados"], 1)
        self.assertEqual(informe["sin_datos"], 2)

        manual.refresh_from_db()
        self.assertEqual(manual.fuente, Clima.FUENTE_MANUAL)
        self.assertEqual(manual.temp_min, Decimal("1.0"))
        self.assertEqual(manual.temp_prom, Decimal("3.0"))

        previo.refresh_from_db()
        self.assertEqual(previo.fuente, Clima.FUENTE_API)
        self.assertEqual(previo.temp_min, Decimal("0.0"))
        self.assertEqual(previo.temp_prom, Decimal("6.0"))
        self.assertEqual(previo.precipitacion_mm, Decimal("1.2"))
        self.assertEqual(previo.registrado_por, self.tecnico)

        conservado.refresh_from_db()
        self.assertEqual(conservado.temp_min, Decimal("0.0"))
        self.assertFalse(Clima.objects.filter(fecha=date(2025, 10, 3)).exists())
        self.assertEqual(Clima.objects.get(fecha=date(2025, 10, 4)).precipitacion_mm, Decimal("2.0"))

        # Transacción única: si un día chocha a mitad del rango, no queda
        # NADA del rango (el 10-08 se revierte junto con el que falló)
        with patch("seguimiento.views.consultar_dias") as servicio, patch(
            "seguimiento.serializers.ClimaEscrituraSerializer.save",
            side_effect=IntegrityError("carrera simulada"),
        ):
            servicio.return_value = [
                self._dia_servicio("2025-10-08", temp_min=3.0, temp_max=11.0),
                self._dia_servicio("2025-10-09", temp_min=4.0, temp_max=12.0),
            ]
            respuesta = self._consulta_api(
                fecha_desde="2025-10-08", fecha_hasta="2025-10-09"
            )
        self.assertEqual(respuesta.status_code, 400)
        self.assertFalse(
            Clima.objects.filter(
                fecha__in=[date(2025, 10, 8), date(2025, 10, 9)]
            ).exists()
        )

    # ------------------------------------------------------------------ #
    # 154: la red externa nunca rompe la API — 502 en español si el
    #     servicio no responde o contesta mal, y 10 consultas por usuario
    #     y hora
    # ------------------------------------------------------------------ #
    def test_154_servicio_caido_502_y_limite_de_consultas(self):
        self._entrar_tecnico()
        self._poner_coordenadas()
        with patch(
            "seguimiento.views.consultar_dias",
            side_effect=ErrorServicioMeteorologico(),
        ):
            respuesta = self._consulta_api()
        self.assertEqual(respuesta.status_code, 502)
        self.assertIn("servicio meteorológico", self._json(respuesta)["detail"])
        self.assertEqual(Clima.objects.count(), 0)

        with patch("seguimiento.servicio_meteorologico.urlopen") as urlopener:
            urlopener.return_value.__enter__.return_value.read.return_value = (
                b"no es json"
            )
            self.assertEqual(self._consulta_api().status_code, 502)

        with patch(
            "seguimiento.servicio_meteorologico.urlopen",
            side_effect=URLError("sin red"),
        ):
            self.assertEqual(self._consulta_api().status_code, 502)
        self.assertEqual(Clima.objects.count(), 0)

        # El adaptador cuantiza lo que venga del servicio a 1 decimal: un
        # 7.80 mm real no debe descartar el día entero por decimales
        json_diario = json.dumps(
            {
                "daily": {
                    "time": ["2025-10-01"],
                    "temperature_2m_min": [3.4],
                    "temperature_2m_max": [11.6],
                    "temperature_2m_mean": [7.5],
                    "precipitation_sum": [7.8],
                    "relative_humidity_2m_mean": [80],
                    "wind_speed_10m_max": [4.44],
                    "shortwave_radiation_sum": [17.19],
                }
            }
        ).encode("utf-8")
        with patch("seguimiento.servicio_meteorologico.urlopen") as urlopener:
            urlopener.return_value.__enter__.return_value.read.return_value = (
                json_diario
            )
            respuesta = self._consulta_api(
                fecha_desde="2025-10-01", fecha_hasta="2025-10-01"
            )
        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(self._json(respuesta)["creados"], 1)
        registro = Clima.objects.get(fecha=date(2025, 10, 1))
        self.assertEqual(registro.precipitacion_mm, Decimal("7.8"))
        self.assertEqual(registro.radiacion_mj, Decimal("17.2"))
        self.assertEqual(registro.viento_ms, Decimal("4.4"))
        self.assertEqual(registro.temp_prom, Decimal("7.5"))
        self.assertFalse(registro.helada)

        # 10 consultas por usuario y hora; la undécima se corta con 429
        # (la caché se limpia para que las anteriores no consuman cuota)
        cache.clear()
        with patch("seguimiento.views.consultar_dias", return_value=[]):
            for _ in range(10):
                self.assertEqual(self._consulta_api().status_code, 200)
            rechazada = self._json(self._consulta_api())
        self.assertTrue(rechazada["detail"].startswith("Demasiadas solicitudes"))
