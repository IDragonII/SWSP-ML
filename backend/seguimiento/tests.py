"""Pruebas de la Semana 7: actividades productivas (HU-47 a HU-55).

Numeración del repositorio 87-102 (16 pruebas nuevas → 102 en total ≥ 100;
el repositorio llegaba a 86 al cerrar la Semana 6).
"""
import json
from datetime import date, datetime, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.core.cache import cache
from django.test import TestCase

from campanias.models import Campania
from catalogos.models import Cultivo, TipoActividad, Variedad
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
