"""Serializadores de la API de ubicación y productores (Semana 3) y de
parcelas (Semana 4).

Los de lectura anidan el nivel superior (jerarquía completa para el
desplegable en cascada); los de escritura reciben el id del padre.

DNI y teléfono se enmascaran por rol (decisión 4 de
docs/decisiones_semana3.md; pendiente de confirmación del responsable):
Administrador y Técnico de campo los ven completos, el Coordinador
ve ****5678 y ****789.
"""
import re
from decimal import Decimal

from django.core.exceptions import ObjectDoesNotExist
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from campanias.models import Campania
from usuarios.models import Usuario

from .models import AsignacionTecnico, Comunidad, Distrito, Parcela, Productor, Provincia

ROLES_CON_DATOS_COMPLETOS = ("Administrador", "Técnico de campo")
_MENSAJE_REQUERIDO = "Este campo es obligatorio."


def _campanias_de_productor(obj):
    """Bloque de campañas de la ficha del productor (HU-44, Semana 6).

    Sin creado_por ni datos de otros usuarios (decisión de la Semana 6):
    solo período, cultivo, variedad, parcela, estado y (Semana 8) el
    bloque de producción si ya hay cosecha registrada."""
    campanias = (
        Campania.objects.filter(parcela__productor=obj)
        .select_related("cultivo", "variedad", "parcela", "produccion")
        .order_by("-periodo", "id")
    )
    resultado = []
    for c in campanias:
        resultado.append(
            {
                "id": c.id,
                "periodo": c.periodo,
                "cultivo": {"id": c.cultivo_id, "nombre": c.cultivo.nombre},
                "variedad": {"id": c.variedad_id, "nombre": c.variedad.nombre},
                "parcela": {"id": c.parcela_id, "codigo": c.parcela.codigo},
                "estado": c.estado,
                "produccion": _mini_produccion(c),
            }
        )
    return resultado


def _mini_produccion(c):
    """Producción de la campaña o None (HU-62, Semana 8)."""
    try:
        p = c.produccion
    except ObjectDoesNotExist:
        return None
    return {
        "produccion_kg": p.produccion_kg,
        "rendimiento_kg_ha": p.rendimiento_kg_ha,
        "requiere_revision": p.requiere_revision,
    }


def _rol_enmascara(context):
    """True si el usuario de la petición no ve datos personales completos."""
    request = (context or {}).get("request")
    user = getattr(request, "user", None)
    rol = getattr(user, "rol", None)
    nombre = getattr(rol, "nombre", None)
    return nombre is not None and nombre not in ROLES_CON_DATOS_COMPLETOS


def _mascara(valor, ultimos):
    if not valor:
        return valor
    return "****" + valor[-ultimos:]


class ProvinciaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Provincia
        fields = ("id", "nombre", "activo")


class DistritoSerializer(serializers.ModelSerializer):
    provincia = ProvinciaSerializer(read_only=True)

    class Meta:
        model = Distrito
        fields = ("id", "nombre", "activo", "provincia")


class DistritoEscrituraSerializer(serializers.ModelSerializer):
    class Meta:
        model = Distrito
        fields = ("nombre", "activo", "provincia")


class ComunidadSerializer(serializers.ModelSerializer):
    distrito = DistritoSerializer(read_only=True)

    class Meta:
        model = Comunidad
        fields = ("id", "nombre", "activo", "distrito")


class ComunidadEscrituraSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comunidad
        fields = ("nombre", "activo", "distrito")


class ProductorListaSerializer(serializers.ModelSerializer):
    """Fila del listado: código, nombre completo, ubicación, estado y DNI
    enmascarado o completo según el rol."""

    nombre_completo = serializers.SerializerMethodField()
    dni = serializers.SerializerMethodField()
    comunidad = serializers.SerializerMethodField()
    distrito = serializers.SerializerMethodField()
    provincia = serializers.SerializerMethodField()

    class Meta:
        model = Productor
        fields = (
            "id",
            "codigo",
            "nombre_completo",
            "comunidad",
            "distrito",
            "provincia",
            "estado",
            "dni",
        )

    def get_nombre_completo(self, obj):
        return f"{obj.apellidos}, {obj.nombres}"

    def get_dni(self, obj):
        if _rol_enmascara(self.context):
            return _mascara(obj.dni, 4)
        return obj.dni

    def get_comunidad(self, obj):
        return {"id": obj.comunidad_id, "nombre": obj.comunidad.nombre}

    def get_distrito(self, obj):
        distrito = obj.comunidad.distrito
        return {"id": distrito.id, "nombre": distrito.nombre}

    def get_provincia(self, obj):
        provincia = obj.comunidad.distrito.provincia
        return {"id": provincia.id, "nombre": provincia.nombre}


class ProductorDesplegableSerializer(serializers.ModelSerializer):
    """?desplegable=1 (Semana 7): selector de productores para los filtros
    de actividades — código y nombre (sin DNI ni ubicación). Solo activos;
    para el Técnico, solo sus asignados (lo garantiza el queryset)."""

    nombre_completo = serializers.SerializerMethodField()

    class Meta:
        model = Productor
        fields = ("id", "codigo", "nombre_completo")

    def get_nombre_completo(self, obj):
        return f"{obj.apellidos}, {obj.nombres}"


class ProductorDetalleSerializer(serializers.ModelSerializer):
    """Ficha completa (HU-22): datos, ubicación, parcelas con resumen y
    técnicos asignados. El campo tecnicos_asignados solo lo reciben
    Administrador y Coordinador (decisión 7: el Técnico no lo recibe)."""

    dni = serializers.SerializerMethodField()
    telefono = serializers.SerializerMethodField()
    creado_por = serializers.StringRelatedField(read_only=True)
    parcelas = serializers.SerializerMethodField()
    resumen = serializers.SerializerMethodField()
    tecnicos_asignados = serializers.SerializerMethodField()
    campanias = serializers.SerializerMethodField()

    class Meta:
        model = Productor
        fields = (
            "id",
            "codigo",
            "nombres",
            "apellidos",
            "dni",
            "telefono",
            "comunidad",
            "referencia_ubicacion",
            "fecha_incorporacion",
            "estado",
            "parcelas",
            "resumen",
            "tecnicos_asignados",
            "campanias",
            "creado_por",
            "creado_en",
            "actualizado_en",
        )
        read_only_fields = ("codigo", "creado_por", "creado_en", "actualizado_en")

    def get_dni(self, obj):
        if _rol_enmascara(self.context):
            return _mascara(obj.dni, 4)
        return obj.dni

    def get_telefono(self, obj):
        if _rol_enmascara(self.context):
            return _mascara(obj.telefono, 3)
        return obj.telefono

    def get_parcelas(self, obj):
        return [
            {
                "id": p.id,
                "codigo": p.codigo,
                "superficie_ha": p.superficie_ha,
                "estado": p.estado,
            }
            for p in obj.parcelas.order_by("codigo")
        ]

    def get_resumen(self, obj):
        parcelas = list(obj.parcelas.all())
        return {
            "parcelas_activas": sum(
                1 for p in parcelas if p.estado == Parcela.ESTADO_ACTIVA
            ),
            "superficie_total_ha": sum(
                (p.superficie_ha for p in parcelas), Decimal("0")
            ),
            "campanias_activas": Campania.objects.filter(
                parcela__productor=obj, estado__in=Campania.ESTADOS_ACTIVOS
            ).count(),
        }

    def get_campanias(self, obj):
        return _campanias_de_productor(obj)

    def get_tecnicos_asignados(self, obj):
        return [
            {
                "id": a.tecnico_id,
                "username": a.tecnico.username,
                "nombre_completo": a.tecnico.get_full_name() or a.tecnico.username,
                "fecha_asignacion": a.fecha_asignacion.isoformat(),
            }
            for a in obj.asignaciones_tecnico.select_related("tecnico").filter(
                activo=True
            )
        ]

    def to_representation(self, instance):
        data = super().to_representation(instance)
        # Decisión 7: el Técnico no recibe el campo tecnicos_asignados
        request = self.context.get("request")
        rol = getattr(getattr(request, "user", None), "rol", None)
        if rol is not None and rol.limita_a_asignados:
            data.pop("tecnicos_asignados", None)
        return data


class ProductorEscrituraSerializer(serializers.ModelSerializer):
    """Alta y edición: sin código (lo genera la BD), sin creado_por (lo
    pone el servidor) y sin estado (se cambia con /estado/)."""

    dni = serializers.CharField(
        validators=[
            UniqueValidator(
                queryset=Productor.objects.all(),
                message="Ya existe un productor con ese DNI.",
            )
        ],
        error_messages={"required": _MENSAJE_REQUERIDO},
    )
    comunidad = serializers.PrimaryKeyRelatedField(
        queryset=Comunidad.objects.all(),
        error_messages={
            "required": "La comunidad es obligatoria.",
            "does_not_exist": "La comunidad indicada no existe.",
        },
    )
    nombres = serializers.CharField(error_messages={"required": _MENSAJE_REQUERIDO})
    apellidos = serializers.CharField(error_messages={"required": _MENSAJE_REQUERIDO})

    class Meta:
        model = Productor
        fields = (
            "nombres",
            "apellidos",
            "dni",
            "telefono",
            "comunidad",
            "referencia_ubicacion",
            "fecha_incorporacion",
        )

    def validate_dni(self, valor):
        if not re.fullmatch(r"\d{8}", valor or ""):
            raise serializers.ValidationError(
                "El DNI debe tener exactamente 8 dígitos numéricos."
            )
        return valor

    def validate_comunidad(self, valor):
        if not valor.activo:
            raise serializers.ValidationError(
                "La comunidad indicada no existe o está inactiva."
            )
        return valor

    def validate_telefono(self, valor):
        return valor or None


class ParcelaListaSerializer(serializers.ModelSerializer):
    """Fila del listado: código, productor, ubicación jerárquica y estado."""

    productor = serializers.SerializerMethodField()
    comunidad = serializers.SerializerMethodField()
    distrito = serializers.SerializerMethodField()
    provincia = serializers.SerializerMethodField()

    class Meta:
        model = Parcela
        fields = (
            "id",
            "codigo",
            "productor",
            "comunidad",
            "distrito",
            "provincia",
            "superficie_ha",
            "altitud_msnm",
            "estado",
        )

    def get_productor(self, obj):
        return {
            "id": obj.productor_id,
            "codigo": obj.productor.codigo,
            "nombre_completo": f"{obj.productor.apellidos}, {obj.productor.nombres}",
        }

    def get_comunidad(self, obj):
        return {"id": obj.comunidad_id, "nombre": obj.comunidad.nombre}

    def get_distrito(self, obj):
        distrito = obj.comunidad.distrito
        return {"id": distrito.id, "nombre": distrito.nombre}

    def get_provincia(self, obj):
        provincia = obj.comunidad.distrito.provincia
        return {"id": provincia.id, "nombre": provincia.nombre}


class ParcelaDesplegableSerializer(serializers.ModelSerializer):
    """?desplegable=1 (Semana 6): selector de parcelas para el formulario
    de campañas — código, productor y superficie (la superficie sembrada
    propone la de la parcela). Solo activas; para el Técnico, solo las de
    sus productores (lo garantiza el queryset de la vista)."""

    productor = serializers.SerializerMethodField()

    class Meta:
        model = Parcela
        fields = ("id", "codigo", "productor", "superficie_ha")

    def get_productor(self, obj):
        return {
            "id": obj.productor_id,
            "codigo": obj.productor.codigo,
            "nombre_completo": f"{obj.productor.apellidos}, {obj.productor.nombres}",
        }


class ParcelaDetalleSerializer(serializers.ModelSerializer):
    """Ficha completa de la parcela. codigo, creado_por y fechas son de
    sólo lectura (los rellena la base de datos); el productor se muestra
    anidado y no se puede cambiar al editar. Desde la Semana 6 incluye
    sus campañas (HU-44)."""

    productor = serializers.SerializerMethodField()
    comunidad = ComunidadSerializer(read_only=True)
    creado_por = serializers.StringRelatedField(read_only=True)
    campanias = serializers.SerializerMethodField()

    class Meta:
        model = Parcela
        fields = (
            "id",
            "codigo",
            "productor",
            "comunidad",
            "referencia_ubicacion",
            "superficie_ha",
            "altitud_msnm",
            "latitud",
            "longitud",
            "tipo_suelo",
            "pendiente",
            "disponibilidad_agua",
            "sistema_riego",
            "estado",
            "campanias",
            "creado_por",
            "creado_en",
            "actualizado_en",
        )
        read_only_fields = ("codigo", "creado_por", "creado_en", "actualizado_en")

    def get_productor(self, obj):
        return {
            "id": obj.productor_id,
            "codigo": obj.productor.codigo,
            "nombre_completo": f"{obj.productor.apellidos}, {obj.productor.nombres}",
        }

    def get_campanias(self, obj):
        campanias = (
            obj.campanias.select_related("cultivo", "variedad", "produccion")
            .order_by("-periodo", "id")
        )
        return [
            {
                "id": c.id,
                "periodo": c.periodo,
                "cultivo": {"id": c.cultivo_id, "nombre": c.cultivo.nombre},
                "variedad": {"id": c.variedad_id, "nombre": c.variedad.nombre},
                "fecha_inicio": c.fecha_inicio.isoformat(),
                "fecha_fin_prevista": c.fecha_fin_prevista.isoformat(),
                "superficie_sembrada_ha": c.superficie_sembrada_ha,
                "estado": c.estado,
                "produccion": _mini_produccion(c),
            }
            for c in campanias
        ]


class ParcelaEscrituraSerializer(serializers.ModelSerializer):
    """Alta y edición: sin código (lo genera la BD), sin estado (se cambia
    con /estado/) y sin creado_por/fechas (los pone el servidor). El
    productor es obligatorio en el alta pero no se puede cambiar al editar
    (la vista lo descarta de validated_data)."""

    productor = serializers.PrimaryKeyRelatedField(
        queryset=Productor.objects.all(),
        error_messages={
            "required": "El productor es obligatorio.",
            "does_not_exist": "El productor indicado no existe.",
        },
    )
    comunidad = serializers.PrimaryKeyRelatedField(
        queryset=Comunidad.objects.all(),
        error_messages={
            "required": "La comunidad es obligatoria.",
            "does_not_exist": "La comunidad indicada no existe.",
        },
    )
    superficie_ha = serializers.DecimalField(
        max_digits=8,
        decimal_places=2,
        error_messages={
            "required": "La superficie es obligatoria.",
            "invalid": "La superficie debe ser un número.",
            "max_digits": "La superficie admite como máximo 6 dígitos enteros y 2 decimales.",
            "max_decimal_places": "La superficie admite como máximo 2 decimales.",
        },
    )
    altitud_msnm = serializers.IntegerField(
        error_messages={
            "required": "La altitud es obligatoria.",
            "invalid": "La altitud debe ser un número entero.",
        }
    )
    latitud = serializers.DecimalField(
        max_digits=9,
        decimal_places=6,
        required=False,
        allow_null=True,
        error_messages={"invalid": "La latitud debe ser un número."},
    )
    longitud = serializers.DecimalField(
        max_digits=9,
        decimal_places=6,
        required=False,
        allow_null=True,
        error_messages={"invalid": "La longitud debe ser un número."},
    )
    tipo_suelo = serializers.ChoiceField(
        choices=Parcela.TIPOS_SUELO,
        required=False,
        allow_null=True,
        error_messages={"invalid_choice": "Valor no permitido para el tipo de suelo."},
    )
    pendiente = serializers.ChoiceField(
        choices=Parcela.PENDIENTES,
        required=False,
        allow_null=True,
        error_messages={"invalid_choice": "Valor no permitido para la pendiente."},
    )
    disponibilidad_agua = serializers.ChoiceField(
        choices=Parcela.DISPONIBILIDADES_AGUA,
        required=False,
        allow_null=True,
        error_messages={"invalid_choice": "Valor no permitido para la disponibilidad de agua."},
    )
    sistema_riego = serializers.ChoiceField(
        choices=Parcela.SISTEMAS_RIEGO,
        required=False,
        allow_null=True,
        error_messages={"invalid_choice": "Valor no permitido para el sistema de riego."},
    )

    class Meta:
        model = Parcela
        fields = (
            "productor",
            "comunidad",
            "referencia_ubicacion",
            "superficie_ha",
            "altitud_msnm",
            "latitud",
            "longitud",
            "tipo_suelo",
            "pendiente",
            "disponibilidad_agua",
            "sistema_riego",
        )

    def validate_productor(self, valor):
        if valor.estado != Productor.ESTADO_ACTIVO:
            raise serializers.ValidationError(
                "El productor indicado está inactivo: no admite parcelas nuevas."
            )
        # El técnico solo puede dar de alta parcelas de SUS productores
        # (decisión 6: como no existe, se responde «no existe o no está
        # asignado a ti» y no se filtra la existencia real)
        request = self.context.get("request")
        rol = getattr(getattr(request, "user", None), "rol", None)
        if rol is not None and rol.limita_a_asignados:
            asignado = AsignacionTecnico.objects.filter(
                tecnico=request.user, productor=valor, activo=True
            ).exists()
            if not asignado:
                raise serializers.ValidationError(
                    "El productor indicado no existe o no está asignado a ti."
                )
        return valor

    def validate_comunidad(self, valor):
        if not valor.activo:
            raise serializers.ValidationError(
                "La comunidad indicada no existe o está inactiva."
            )
        return valor

    def validate_superficie_ha(self, valor):
        if valor is not None and valor <= 0:
            raise serializers.ValidationError("La superficie debe ser mayor que 0.")
        return valor

    def validate_altitud_msnm(self, valor):
        if valor is not None and not 0 <= valor <= 6500:
            raise serializers.ValidationError(
                "La altitud debe estar entre 0 y 6500 msnm."
            )
        return valor

    def validate_latitud(self, valor):
        if valor is not None and not -90 <= valor <= 90:
            raise serializers.ValidationError(
                "La latitud debe estar entre -90 y 90."
            )
        return valor

    def validate_longitud(self, valor):
        if valor is not None and not -180 <= valor <= 180:
            raise serializers.ValidationError(
                "La longitud debe estar entre -180 y 180."
            )
        return valor

    def validate(self, attrs):
        # Las dos coordenadas o ninguna (ck_parcela_coordenadas)
        instancia = self.instance
        latitud = attrs.get(
            "latitud", getattr(instancia, "latitud", None) if instancia else None
        )
        longitud = attrs.get(
            "longitud", getattr(instancia, "longitud", None) if instancia else None
        )
        if (latitud is None) != (longitud is None):
            raise serializers.ValidationError(
                "Indica latitud y longitud, o déjalas las dos vacías."
            )
        return attrs

    def update(self, instance, validated_data):
        # El productor no se puede cambiar al editar la parcela
        validated_data.pop("productor", None)
        return super().update(instance, validated_data)


class AsignacionSerializer(serializers.ModelSerializer):
    """Fila del listado de asignaciones: técnicos y productores anidados."""

    tecnico = serializers.SerializerMethodField()
    productor = serializers.SerializerMethodField()

    class Meta:
        model = AsignacionTecnico
        fields = ("id", "tecnico", "productor", "fecha_asignacion", "activo")

    def get_tecnico(self, obj):
        return {
            "id": obj.tecnico_id,
            "username": obj.tecnico.username,
            "nombre_completo": obj.tecnico.get_full_name() or obj.tecnico.username,
        }

    def get_productor(self, obj):
        return {
            "id": obj.productor_id,
            "codigo": obj.productor.codigo,
            "nombre_completo": f"{obj.productor.apellidos}, {obj.productor.nombres}",
        }


class AsignacionEscrituraSerializer(serializers.ModelSerializer):
    """Alta de asignación: valida ANTES que el trigger (decisión 8): rol
    con limita_a_asignados, usuario activo y no duplicada. El estado se
    cambia con /estado/ (activo true|false); no hay PUT/PATCH completos
    (reasignar = desactivar + crear otra)."""

    tecnico = serializers.PrimaryKeyRelatedField(
        queryset=Usuario.objects.all(),
        error_messages={
            "required": "El técnico es obligatorio.",
            "does_not_exist": "El usuario indicado no existe.",
        },
    )
    productor = serializers.PrimaryKeyRelatedField(
        queryset=Productor.objects.all(),
        error_messages={
            "required": "El productor es obligatorio.",
            "does_not_exist": "El productor indicado no existe.",
        },
    )

    class Meta:
        model = AsignacionTecnico
        fields = ("tecnico", "productor")
        # Sin el validador automático de uq_asignacion: validate() explica la
        # unicidad con el mensaje en español (reactivar en vez de duplicar)
        validators = []

    def validate_tecnico(self, valor):
        if not valor.is_active:
            raise serializers.ValidationError("El usuario indicado está inactivo.")
        rol = valor.rol
        if rol is None or not rol.limita_a_asignados:
            raise serializers.ValidationError(
                "El usuario indicado no tiene un rol que trabaje con productores asignados."
            )
        return valor

    def validate(self, attrs):
        duplicada = AsignacionTecnico.objects.filter(
            tecnico=attrs["tecnico"], productor=attrs["productor"]
        ).exists()
        if duplicada:
            # Sin rutas ni verbos HTTP en el mensaje (seguridad: no se
            # revela la superficie de la API en errores de usuario).
            raise serializers.ValidationError(
                "Esa asignación ya existe (activa o desactivada): "
                "ve a la ficha del productor y reactiva la existente."
            )
        return attrs
