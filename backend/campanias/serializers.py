"""Serializadores de la API de campañas (Semana 6).

La lista muestra productor, parcela, cultivo, variedad, período y estado
(sin DNI ni teléfono, decisión de docs/decisiones_semana6.md); la ficha
añade fechas, superficie, observaciones, trazabilidad y (Semana 8) el
bloque de producción. El de escritura no acepta estado, fecha de siembra
ni creador (son de solo lectura: el estado solo cambia con
iniciar/cancelar/cerrar y la siembra la llena el Sprint 4) y valida ANTES
que la base: período, fechas dentro del período, superficie y las dos
reglas únicas nombrando la campaña existente. El estado del request
(edición según estado) también se controla aquí: en cosechada se bloquean
los mismos campos que en producción y en cerrada no se admite nada.
"""
import re
from datetime import date

from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Max
from rest_framework import serializers

from catalogos.models import Cultivo, Variedad
from productores.models import AsignacionTecnico, Parcela, Productor

from .models import Campania

_MENSAJE_REQUERIDO = "Este campo es obligatorio."

# Campos que quedan bloqueados al iniciar la campaña: definen la fila del
# dataset y las etapas; para corregirlos se cancela y se crea otra nueva.
_BLOQUEADOS_EN_PRODUCCION = (
    "parcela",
    "cultivo",
    "variedad",
    "periodo",
    "fecha_inicio",
)


def _mini_cultivo(obj):
    return {"id": obj.cultivo_id, "nombre": obj.cultivo.nombre}


def _mini_variedad(obj):
    return {"id": obj.variedad_id, "nombre": obj.variedad.nombre}


def _mini_parcela(obj):
    """Parcela anidada con su productor (código y nombre, sin DNI)."""
    return {
        "id": obj.parcela_id,
        "codigo": obj.parcela.codigo,
        "superficie_ha": obj.parcela.superficie_ha,
        "productor": {
            "id": obj.parcela.productor_id,
            "codigo": obj.parcela.productor.codigo,
            "nombre_completo": (
                f"{obj.parcela.productor.apellidos}, {obj.parcela.productor.nombres}"
            ),
        },
    }


class CampaniaListaSerializer(serializers.ModelSerializer):
    """Fila del listado: productor, parcela, cultivo, variedad, período y
    estado (HU-42). El orden por defecto es período descendente."""

    parcela = serializers.SerializerMethodField()
    cultivo = serializers.SerializerMethodField()
    variedad = serializers.SerializerMethodField()

    class Meta:
        model = Campania
        fields = ("id", "periodo", "parcela", "cultivo", "variedad", "estado")

    def get_parcela(self, obj):
        return _mini_parcela(obj)

    def get_cultivo(self, obj):
        return _mini_cultivo(obj)

    def get_variedad(self, obj):
        return _mini_variedad(obj)


class CampaniaDetalleSerializer(serializers.ModelSerializer):
    """Ficha completa. creado_por sale como nombre de usuario
    (StringRelatedField, igual que parcelas y productores). La Semana 7
    añade el resumen de actividades: cuántas activas quedan y la última
    fecha registrada (ambas excluyen anuladas)."""

    parcela = serializers.SerializerMethodField()
    cultivo = serializers.SerializerMethodField()
    variedad = serializers.SerializerMethodField()
    creado_por = serializers.StringRelatedField(read_only=True)
    actividades_activas = serializers.SerializerMethodField()
    fecha_ultima_actividad = serializers.SerializerMethodField()
    produccion = serializers.SerializerMethodField()

    class Meta:
        model = Campania
        fields = (
            "id",
            "periodo",
            "parcela",
            "cultivo",
            "variedad",
            "fecha_inicio",
            "fecha_fin_prevista",
            "fecha_siembra",
            "superficie_sembrada_ha",
            "estado",
            "observaciones",
            "actividades_activas",
            "fecha_ultima_actividad",
            "produccion",
            "creado_por",
            "creado_en",
            "actualizado_en",
        )
        read_only_fields = (
            "estado",
            "fecha_siembra",
            "actividades_activas",
            "fecha_ultima_actividad",
            "produccion",
            "creado_por",
            "creado_en",
            "actualizado_en",
        )

    def get_parcela(self, obj):
        return _mini_parcela(obj)

    def get_cultivo(self, obj):
        return _mini_cultivo(obj)

    def get_variedad(self, obj):
        return _mini_variedad(obj)

    def get_actividades_activas(self, obj):
        # Lazy: solo se consulta en ficha (la lista usa CampaniaListaSerializer)
        return obj.actividades.filter(anulada=False).count()

    def get_fecha_ultima_actividad(self, obj):
        ultima = obj.actividades.filter(anulada=False).aggregate(u=Max("fecha"))["u"]
        return ultima

    def get_produccion(self, obj):
        """Bloque de producción (HU-62, Semana 8): null si la campaña aún
        no tiene cosecha registrada."""
        try:
            p = obj.produccion
        except ObjectDoesNotExist:
            return None
        return {
            "id": p.id,
            "fecha_cosecha": p.fecha_cosecha.isoformat(),
            "produccion_kg": p.produccion_kg,
            "rendimiento_kg_ha": p.rendimiento_kg_ha,
            "requiere_revision": p.requiere_revision,
            "incluir_en_entrenamiento": p.incluir_en_entrenamiento,
        }


class CampaniaEscrituraSerializer(serializers.ModelSerializer):
    """Alta y edición. estado, fecha_siembra y creado_por no están en
    fields: el cliente no puede forzarlos (prueba 83)."""

    periodo = serializers.CharField(
        error_messages={"required": _MENSAJE_REQUERIDO}
    )
    parcela = serializers.PrimaryKeyRelatedField(
        queryset=Parcela.objects.select_related("productor"),
        error_messages={
            "required": "La parcela es obligatoria.",
            "does_not_exist": "La parcela indicada no existe.",
        },
    )
    cultivo = serializers.PrimaryKeyRelatedField(
        queryset=Cultivo.objects.all(),
        error_messages={
            "required": "El cultivo es obligatorio.",
            "does_not_exist": "El cultivo indicado no existe.",
        },
    )
    variedad = serializers.PrimaryKeyRelatedField(
        queryset=Variedad.objects.all(),
        error_messages={
            "required": "La variedad es obligatoria.",
            "does_not_exist": "La variedad indicada no existe.",
        },
    )
    fecha_inicio = serializers.DateField(
        error_messages={
            "required": "La fecha de inicio es obligatoria.",
            "invalid": "La fecha de inicio no es válida: usa el formato AAAA-MM-DD.",
        }
    )
    fecha_fin_prevista = serializers.DateField(
        error_messages={
            "required": "La fecha de fin prevista es obligatoria.",
            "invalid": (
                "La fecha de fin prevista no es válida: usa el formato AAAA-MM-DD."
            ),
        }
    )
    superficie_sembrada_ha = serializers.DecimalField(
        max_digits=8,
        decimal_places=2,
        required=False,
        error_messages={
            "invalid": "La superficie sembrada debe ser un número.",
            "max_digits": (
                "La superficie admite como máximo 6 dígitos enteros y 2 decimales."
            ),
            "max_decimal_places": "La superficie admite como máximo 2 decimales.",
        },
    )
    observaciones = serializers.CharField(
        required=False, allow_null=True, allow_blank=True, default=""
    )

    class Meta:
        model = Campania
        fields = (
            "periodo",
            "parcela",
            "cultivo",
            "variedad",
            "fecha_inicio",
            "fecha_fin_prevista",
            "superficie_sembrada_ha",
            "observaciones",
        )

    # ------------------------------------------------------------------ #
    # validaciones por campo
    # ------------------------------------------------------------------ #
    def validate_parcela(self, valor):
        if valor.estado != Parcela.ESTADO_ACTIVA:
            raise serializers.ValidationError(
                "La parcela indicada no existe o está inactiva."
            )
        if valor.productor.estado != Productor.ESTADO_ACTIVO:
            raise serializers.ValidationError(
                "El productor de la parcela está inactivo: no admite campañas nuevas."
            )
        # El técnico solo puede usar parcelas de SUS productores asignados:
        # si no le corresponde, el mismo mensaje que si no existiera
        request = self.context.get("request")
        rol = getattr(getattr(request, "user", None), "rol", None)
        if rol is not None and rol.limita_a_asignados:
            asignado = AsignacionTecnico.objects.filter(
                tecnico=request.user, productor=valor.productor, activo=True
            ).exists()
            if not asignado:
                raise serializers.ValidationError("La parcela indicada no existe.")
        return valor

    def validate_cultivo(self, valor):
        if not valor.activo:
            raise serializers.ValidationError(
                "El cultivo indicado no existe o está inactivo."
            )
        return valor

    def validate_variedad(self, valor):
        if not valor.activo:
            raise serializers.ValidationError(
                "La variedad indicada no existe o está inactiva."
            )
        return valor

    def validate_periodo(self, valor):
        valor = (valor or "").strip()
        if not re.fullmatch(r"\d{4}-\d{4}", valor):
            raise serializers.ValidationError(
                "El período debe tener el formato AAAA-AAAA (por ejemplo 2025-2026)."
            )
        anio_1, anio_2 = int(valor[:4]), int(valor[5:])
        if anio_2 != anio_1 + 1:
            raise serializers.ValidationError(
                "El segundo año del período debe ser uno más que el primero "
                "(por ejemplo 2025-2026)."
            )
        return valor

    def validate_fecha_inicio(self, valor):
        return valor

    def validate_superficie_sembrada_ha(self, valor):
        if valor is not None and valor <= 0:
            raise serializers.ValidationError(
                "La superficie sembrada debe ser mayor que 0."
            )
        return valor

    # ------------------------------------------------------------------ #
    # validaciones cruzadas (fechas, superficie, estado y duplicados)
    # ------------------------------------------------------------------ #
    def validate(self, attrs):
        # Primero la edición según el estado: en producción los campos
        # bloqueados se rechazan aunque el valor enviado sea «válido»
        if self.instance is not None:
            self._validar_edicion_por_estado(attrs)

        instancia = self.instance

        periodo = attrs.get(
            "periodo", getattr(instancia, "periodo", None) if instancia else None
        )
        parcela = attrs.get(
            "parcela", getattr(instancia, "parcela", None) if instancia else None
        )
        cultivo = attrs.get(
            "cultivo", getattr(instancia, "cultivo", None) if instancia else None
        )
        variedad = attrs.get(
            "variedad", getattr(instancia, "variedad", None) if instancia else None
        )
        inicio = attrs.get(
            "fecha_inicio",
            getattr(instancia, "fecha_inicio", None) if instancia else None,
        )
        fin = attrs.get(
            "fecha_fin_prevista",
            getattr(instancia, "fecha_fin_prevista", None) if instancia else None,
        )

        # La variedad debe pertenecer al cultivo (la clave compuesta de la
        # base sería la red de seguridad; aquí se responde 400 en español)
        if cultivo is not None and variedad is not None:
            if variedad.cultivo_id != cultivo.pk:
                raise serializers.ValidationError(
                    {"variedad": "La variedad indicada no pertenece al cultivo elegido."}
                )

        # La superficie por defecto es la de la parcela (solo en el alta)
        if instancia is None and attrs.get("superficie_sembrada_ha") is None:
            if parcela is not None:
                attrs["superficie_sembrada_ha"] = parcela.superficie_ha
        superficie = attrs.get("superficie_sembrada_ha")

        # fin prevista >= inicio
        if inicio is not None and fin is not None and fin < inicio:
            raise serializers.ValidationError(
                {
                    "fecha_fin_prevista": (
                        "La fecha de fin prevista no puede ser anterior a la "
                        "fecha de inicio."
                    )
                }
            )

        # Ambas fechas dentro del período (supuesto del responsable, solo en
        # la API: pendiente de confirmar; decisión en decisiones_semana6.md)
        if periodo is not None and (inicio is not None or fin is not None):
            anio_1, anio_2 = int(periodo[:4]), int(periodo[5:])
            minima = date(anio_1, 1, 1)
            maxima = date(anio_2, 12, 31)
            rango = f"entre el 1 de enero de {anio_1} y el 31 de diciembre de {anio_2}"
            if inicio is not None and not minima <= inicio <= maxima:
                raise serializers.ValidationError(
                    {
                        "fecha_inicio": (
                            f"La fecha de inicio debe caer dentro del período "
                            f"{periodo}: {rango}."
                        )
                    }
                )
            if fin is not None and not minima <= fin <= maxima:
                raise serializers.ValidationError(
                    {
                        "fecha_fin_prevista": (
                            f"La fecha de fin prevista debe caer dentro del "
                            f"período {periodo}: {rango}."
                        )
                    }
                )

        # Superficie sembrada nunca mayor que la de la parcela
        if superficie is not None and parcela is not None:
            if superficie > parcela.superficie_ha:
                raise serializers.ValidationError(
                    {
                        "superficie_sembrada_ha": (
                            f"La superficie sembrada no puede superar la "
                            f"superficie de la parcela ({parcela.superficie_ha} ha)."
                        )
                    }
                )

        self._validar_duplicados(attrs, parcela, periodo, cultivo)
        return attrs

    def _validar_edicion_por_estado(self, attrs):
        """Edición según el estado (HU-41 y Semana 8): planificada todo
        salvo estado y siembra (ya no escribibles); en producción y en
        cosechada solo fin prevista, superficie y observaciones; cerrada y
        cancelada nada."""
        estado = self.instance.estado
        if estado == Campania.ESTADO_CANCELADA and attrs:
            raise serializers.ValidationError(
                "Una campaña cancelada no admite cambios."
            )
        if estado == Campania.ESTADO_CERRADA and attrs:
            raise serializers.ValidationError(
                "Una campaña cerrada no admite cambios."
            )
        if estado in (Campania.ESTADO_EN_PRODUCCION, Campania.ESTADO_COSECHADA):
            presentes = [c for c in _BLOQUEADOS_EN_PRODUCCION if c in self.initial_data]
            if presentes:
                campo = presentes[0]
                raise serializers.ValidationError(
                    {
                        campo: (
                            f"El campo «{campo}» está bloqueado al iniciar la "
                            "campaña: para corregirlo, cancela esta campaña y "
                            "crea otra nueva."
                        )
                    }
                )

    def _validar_duplicados(self, attrs, parcela, periodo, cultivo):
        """Las dos reglas únicas, ANTES de guardar y con el nombre de la
        campaña que ya existe (el índice parcial es la red de seguridad y la
        vista traduce su choque a un 400 igual)."""
        if parcela is None or periodo is None:
            return
        excluido = self.instance.pk if self.instance is not None else None
        existente = self._duplicada_periodo(parcela, periodo, excluido)
        if existente is not None:
            raise serializers.ValidationError(
                {
                    "parcela": (
                        f"Ya existe una campaña de {existente.cultivo.nombre} "
                        f"en esta parcela para el período {existente.periodo} "
                        f"(id {existente.pk})."
                    ),
                    "campania_existente": str(existente.pk),
                }
            )
        if self.instance is None or self.instance.estado in Campania.ESTADOS_ACTIVOS:
            existente = self._duplicada_activa(parcela, excluido)
            if existente is not None:
                raise serializers.ValidationError(
                    {
                        "parcela": (
                            f"Ya existe una campaña activa en esta parcela "
                            f"(id {existente.pk}, {existente.periodo}, "
                            f"{existente.cultivo.nombre})."
                        ),
                        "campania_existente": str(existente.pk),
                    }
                )

    # Estas dos consultas son las que la vista repite si la base rechaza el
    # INSERT/UPDATE (carrera entre la validación y el guardado): se pueden
    # parchear en las pruebas 72 y 73 para forzar ese camino.
    def _duplicada_periodo(self, parcela, periodo, excluido):
        consulta = Campania.objects.filter(
            parcela=parcela, periodo=periodo
        ).exclude(estado=Campania.ESTADO_CANCELADA)
        if excluido is not None:
            consulta = consulta.exclude(pk=excluido)
        return consulta.select_related("cultivo").first()

    def _duplicada_activa(self, parcela, excluido):
        consulta = Campania.objects.filter(
            parcela=parcela, estado__in=Campania.ESTADOS_ACTIVOS
        )
        if excluido is not None:
            consulta = consulta.exclude(pk=excluido)
        return consulta.select_related("cultivo").first()


class CampaniaDesplegableSerializer(serializers.ModelSerializer):
    """?desplegable=1 (Semana 7): selector de campañas para el formulario y
    los filtros de actividades — periodo, estado, productor, parcela,
    cultivo y el rango del período (para validar la fecha antes de enviar).
    Solo estados que admiten registros (ESTADOS_ACTIVOS); para el Técnico,
    solo las de sus productores (lo garantiza el queryset de la vista)."""

    parcela = serializers.SerializerMethodField()
    cultivo = serializers.SerializerMethodField()

    class Meta:
        model = Campania
        fields = (
            "id",
            "periodo",
            "estado",
            "parcela",
            "cultivo",
            "fecha_inicio",
            "fecha_fin_prevista",
            "fecha_siembra",
        )

    def get_parcela(self, obj):
        return {
            "id": obj.parcela_id,
            "codigo": obj.parcela.codigo,
            "productor": {
                "id": obj.parcela.productor_id,
                "nombre_completo": (
                    f"{obj.parcela.productor.apellidos}, "
                    f"{obj.parcela.productor.nombres}"
                ),
            },
        }

    def get_cultivo(self, obj):
        return _mini_cultivo(obj)
