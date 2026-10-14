"""Serializadores de la API de catálogos (Semana 5).

Los de lectura anidan el cultivo (variedades y etapas); los de
escritura reciben su id. La unicidad es normalizada a nivel de API:
mayúsculas y espacios dobles no crean duplicados (la base distingue
mayúsculas y por eso no se delega en ella). Todos los mensajes de
validación salen en español, incluidas las opciones de los campos con
lista cerrada.
"""
from rest_framework import serializers
from rest_framework.validators import UniqueValidator

from .models import (
    Agente,
    Cultivo,
    EtapaFenologica,
    Recurso,
    TipoActividad,
    TipoIncidencia,
    Unidad,
    Variedad,
)

_MENSAJE_REQUERIDO = "Este campo es obligatorio."
_MENSAJE_VACIO = "Este campo no puede quedar vacío."

# Regla de tipo de unidad por categoría (Semana 9, decisión 2): evita
# mezclar kg con litros en el mismo grupo del resumen por campaña.
_TIPOS_POR_CATEGORIA = {
    "SEMILLA": ("MASA",),
    "FERTILIZANTE": ("MASA",),
    "ABONO": ("MASA",),
    "FITOSANITARIO": ("MASA", "VOLUMEN"),
    "AGUA": ("VOLUMEN",),
    "COMBUSTIBLE": ("VOLUMEN",),
    "MANO_OBRA": ("LABOR",),
    "MAQUINARIA": ("TIEMPO",),
}


def _normalizar(valor):
    """Mayúsculas y espacios dobles no crean duplicados en la API."""
    return " ".join((valor or "").split()).casefold()


class EscrituraCatalogo(serializers.ModelSerializer):
    """Base de escritura: errores en español y sin los validadores
    únicos automáticos de DRF (responden en inglés y no normalizan)."""

    def get_validators(self):
        # La unicidad la resuelven validate_nombre/validate() en español
        return []

    def build_standard_field(self, field_name, model_field):
        campo, kwargs = super().build_standard_field(field_name, model_field)
        mensajes = dict(kwargs.get("error_messages") or {})
        mensajes.update(
            {"required": _MENSAJE_REQUERIDO, "blank": _MENSAJE_VACIO}
        )
        if issubclass(campo, serializers.ChoiceField):
            mensajes["invalid_choice"] = "«%(value)s» no es una opción válida."
        kwargs["error_messages"] = mensajes
        kwargs["validators"] = [
            v
            for v in (kwargs.get("validators") or [])
            if not isinstance(v, UniqueValidator)
        ]
        return campo, kwargs

    def build_relational_field(self, field_name, relation_info):
        campo, kwargs = super().build_relational_field(
            field_name, relation_info
        )
        mensajes = dict(kwargs.get("error_messages") or {})
        mensajes.update(
            {
                "required": _MENSAJE_REQUERIDO,
                "does_not_exist": "El registro indicado no existe.",
            }
        )
        kwargs["error_messages"] = mensajes
        kwargs["validators"] = [
            v
            for v in (kwargs.get("validators") or [])
            if not isinstance(v, UniqueValidator)
        ]
        return campo, kwargs


class NombreUnicoEscritura(EscrituraCatalogo):
    """Escritura con nombre único normalizado en español."""

    def _mensaje_duplicado(self):
        return "Ya existe un registro con ese nombre."

    def validate_nombre(self, valor):
        valor = " ".join(valor.split())
        consulta = self.Meta.model.objects.all()
        if self.instance is not None:
            consulta = consulta.exclude(pk=self.instance.pk)
        if any(
            _normalizar(objeto.nombre) == _normalizar(valor)
            for objeto in consulta
        ):
            raise serializers.ValidationError(self._mensaje_duplicado())
        return valor


class CultivoEscrituraSerializer(NombreUnicoEscritura):
    class Meta:
        model = Cultivo
        fields = ("nombre", "descripcion", "activo")

    def _mensaje_duplicado(self):
        return "Ya existe un cultivo con ese nombre."


class VariedadEscrituraSerializer(NombreUnicoEscritura):
    class Meta:
        model = Variedad
        fields = ("cultivo", "nombre", "descripcion", "activo")

    def validate_nombre(self, valor):
        # La unicidad es (cultivo, nombre): se comprueba en validate()
        return " ".join(valor.split())

    def validate(self, attrs):
        cultivo = attrs.get(
            "cultivo",
            self.instance.cultivo if self.instance is not None else None,
        )
        if "cultivo" in attrs and cultivo is not None and not cultivo.activo:
            raise serializers.ValidationError(
                {"cultivo": "El cultivo indicado no existe o está inactivo."}
            )
        nombre = attrs.get(
            "nombre",
            self.instance.nombre if self.instance is not None else None,
        )
        if cultivo is not None and nombre:
            consulta = Variedad.objects.filter(cultivo=cultivo)
            if self.instance is not None:
                consulta = consulta.exclude(pk=self.instance.pk)
            if any(
                _normalizar(variedad.nombre) == _normalizar(nombre)
                for variedad in consulta
            ):
                raise serializers.ValidationError(
                    {
                        "nombre": (
                            "Ya existe una variedad con ese nombre "
                            "para ese cultivo."
                        )
                    }
                )
        return attrs


class EtapaEscrituraSerializer(NombreUnicoEscritura):
    class Meta:
        model = EtapaFenologica
        fields = ("cultivo", "nombre", "orden")

    def validate_nombre(self, valor):
        # La unicidad es (cultivo, nombre): se comprueba en validate()
        return " ".join(valor.split())

    def validate_orden(self, valor):
        if not 1 <= valor <= 1000:
            raise serializers.ValidationError(
                "El orden debe ser un número entre 1 y 1000."
            )
        return valor

    def validate(self, attrs):
        cultivo = attrs.get(
            "cultivo",
            self.instance.cultivo if self.instance is not None else None,
        )
        if "cultivo" in attrs and cultivo is not None and not cultivo.activo:
            raise serializers.ValidationError(
                {"cultivo": "El cultivo indicado no existe o está inactivo."}
            )
        if cultivo is None:
            return attrs
        nombre = attrs.get(
            "nombre",
            self.instance.nombre if self.instance is not None else None,
        )
        orden = attrs.get(
            "orden",
            self.instance.orden if self.instance is not None else None,
        )
        consulta = EtapaFenologica.objects.filter(cultivo=cultivo)
        if self.instance is not None:
            consulta = consulta.exclude(pk=self.instance.pk)
        existentes = list(consulta)
        if nombre and any(
            _normalizar(etapa.nombre) == _normalizar(nombre)
            for etapa in existentes
        ):
            raise serializers.ValidationError(
                {
                    "nombre": (
                        "Ya existe una etapa con ese nombre "
                        "para ese cultivo."
                    )
                }
            )
        if orden is not None and any(etapa.orden == orden for etapa in existentes):
            raise serializers.ValidationError(
                {
                    "orden": (
                        "Ya existe otra etapa con el orden "
                        f"{orden} para ese cultivo."
                    )
                }
            )
        return attrs


class UnidadEscrituraSerializer(NombreUnicoEscritura):
    class Meta:
        model = Unidad
        fields = ("nombre", "simbolo", "tipo", "factor_a_base", "es_base", "activo")

    def _mensaje_duplicado(self):
        return "Ya existe una unidad con ese nombre."

    def validate(self, attrs):
        instancia = self.instance
        es_base = attrs.get(
            "es_base", instancia.es_base if instancia is not None else False
        )
        factor = attrs.get(
            "factor_a_base",
            instancia.factor_a_base if instancia is not None else None,
        )
        if factor is not None and factor <= 0:
            raise serializers.ValidationError(
                {"factor_a_base": "El factor debe ser mayor que 0."}
            )
        if es_base:
            if instancia is None:
                raise serializers.ValidationError(
                    {
                        "es_base": (
                            "No se pueden crear unidades base: "
                            "cada tipo ya tiene la suya."
                        )
                    }
                )
            if not instancia.es_base:
                raise serializers.ValidationError(
                    {
                        "es_base": (
                            "No se puede convertir una unidad existente "
                            "en base."
                        )
                    }
                )
            if factor is not None and factor != 1:
                raise serializers.ValidationError(
                    {"factor_a_base": "La unidad base debe tener factor 1."}
                )
            tipo = attrs.get("tipo", instancia.tipo)
            otras = Unidad.objects.filter(es_base=True, tipo=tipo).exclude(
                pk=instancia.pk
            )
            if otras.exists():
                raise serializers.ValidationError(
                    {"tipo": "Ya existe una unidad base para ese tipo."}
                )
        if "activo" in attrs and attrs["activo"] is False and es_base:
            raise serializers.ValidationError(
                {"activo": "Las unidades base no se pueden desactivar."}
            )
        return attrs


class TipoActividadEscrituraSerializer(EscrituraCatalogo):
    """Sin código: es fijo (los 7 sembrados) y no se admiten altas."""

    class Meta:
        model = TipoActividad
        fields = ("nombre", "activo")

    def validate(self, attrs):
        if (
            self.instance is not None
            and "activo" in attrs
            and attrs["activo"] is False
            and self.instance.codigo in ("SIEMBRA", "COSECHA")
        ):
            raise serializers.ValidationError(
                {"activo": "Siembra y Cosecha no se pueden desactivar."}
            )
        return attrs


class RecursoEscrituraSerializer(NombreUnicoEscritura):
    """Semana 9: cada categoría solo admite ciertos tipos de unidad (los
    fitosanitarios, masa o volumen) y el tipo de un recurso que ya tiene
    usos registrados no se puede cambiar (afectaría las cantidades base
    ya calculadas): hay que crear otro recurso."""

    class Meta:
        model = Recurso
        fields = ("nombre", "categoria", "tipo_unidad", "activo")

    def _mensaje_duplicado(self):
        return "Ya existe un recurso con ese nombre."

    def validate(self, attrs):
        instancia = self.instance
        categoria = attrs.get(
            "categoria", getattr(instancia, "categoria", None) if instancia else None
        )
        tipo = attrs.get(
            "tipo_unidad",
            getattr(instancia, "tipo_unidad", None) if instancia else None,
        )
        if categoria is not None and tipo is not None:
            permitidos = _TIPOS_POR_CATEGORIA.get(categoria, ())
            if tipo not in permitidos:
                raise serializers.ValidationError(
                    {
                        "tipo_unidad": (
                            f"Los recursos de la categoría {categoria.lower()} "
                            f"solo admiten unidades de tipo "
                            f"{', '.join(permitidos).lower()}."
                        )
                    }
                )
        # El tipo de unidad no cambia si el recurso ya tiene usos
        if instancia is not None:
            tipo_nuevo = attrs.get("tipo_unidad")
            if tipo_nuevo is not None and tipo_nuevo != instancia.tipo_unidad:
                if instancia.usos.exists():
                    raise serializers.ValidationError(
                        {
                            "tipo_unidad": (
                                "Este recurso ya tiene usos registrados: su "
                                "tipo de unidad no se puede cambiar. Cree "
                                "otro recurso."
                            )
                        }
                    )
        return attrs


class TipoIncidenciaEscrituraSerializer(NombreUnicoEscritura):
    class Meta:
        model = TipoIncidencia
        fields = ("nombre", "categoria", "activo")

    def _mensaje_duplicado(self):
        return "Ya existe un tipo de incidencia con ese nombre."


class AgenteEscrituraSerializer(NombreUnicoEscritura):
    class Meta:
        model = Agente
        fields = ("nombre", "tipo", "activo")

    def _mensaje_duplicado(self):
        return "Ya existe un agente con ese nombre."


class CultivoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cultivo
        fields = ("id", "nombre", "descripcion", "activo")


class VariedadSerializer(serializers.ModelSerializer):
    cultivo = serializers.SerializerMethodField()

    class Meta:
        model = Variedad
        fields = ("id", "cultivo", "nombre", "descripcion", "activo")

    def get_cultivo(self, obj):
        return {"id": obj.cultivo_id, "nombre": obj.cultivo.nombre}


class EtapaSerializer(serializers.ModelSerializer):
    cultivo = serializers.SerializerMethodField()

    class Meta:
        model = EtapaFenologica
        fields = ("id", "cultivo", "nombre", "orden")

    def get_cultivo(self, obj):
        return {"id": obj.cultivo_id, "nombre": obj.cultivo.nombre}


class UnidadSerializer(serializers.ModelSerializer):
    class Meta:
        model = Unidad
        fields = (
            "id",
            "nombre",
            "simbolo",
            "tipo",
            "factor_a_base",
            "es_base",
            "activo",
        )


class TipoActividadSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoActividad
        fields = ("id", "codigo", "nombre", "activo")


class RecursoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Recurso
        fields = ("id", "nombre", "categoria", "tipo_unidad", "activo")


class TipoIncidenciaSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoIncidencia
        fields = ("id", "nombre", "categoria", "activo")


class AgenteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Agente
        fields = ("id", "nombre", "tipo", "activo")


class CultivoDesplegableSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cultivo
        fields = ("id", "nombre")


class VariedadDesplegableSerializer(serializers.ModelSerializer):
    cultivo = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = Variedad
        fields = ("id", "nombre", "cultivo")


class EtapaDesplegableSerializer(serializers.ModelSerializer):
    cultivo = serializers.PrimaryKeyRelatedField(read_only=True)

    class Meta:
        model = EtapaFenologica
        fields = ("id", "nombre", "cultivo")


class UnidadDesplegableSerializer(serializers.ModelSerializer):
    """Semana 9: añade factor_a_base y es_base para mostrar en el
    formulario la equivalencia («1 quintal = 46 kg»)."""

    class Meta:
        model = Unidad
        fields = ("id", "nombre", "simbolo", "tipo", "factor_a_base", "es_base")


class TipoActividadDesplegableSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoActividad
        fields = ("id", "nombre")


class RecursoDesplegableSerializer(serializers.ModelSerializer):
    """Semana 9: añade categoría y tipo de unidad para agrupar por
    categoría en el formulario y filtrar las unidades compatibles."""

    class Meta:
        model = Recurso
        fields = ("id", "nombre", "categoria", "tipo_unidad")


class TipoIncidenciaDesplegableSerializer(serializers.ModelSerializer):
    class Meta:
        model = TipoIncidencia
        fields = ("id", "nombre")


class AgenteDesplegableSerializer(serializers.ModelSerializer):
    class Meta:
        model = Agente
        fields = ("id", "nombre")
