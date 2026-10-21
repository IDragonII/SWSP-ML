"""Serializadores de la API de Machine Learning (Sprint 14, S22, S23).

La lista de predicciones trae campaña (período, cultivo, parcela y
productor), modelo (algoritmo y versión), fecha, resultado y la
comparación con lo real cuando existe; la ficha añade las variables de
entrada con sus avisos y confiabilidad (229), el texto de estimación y
el MAE del modelo (231). creado_por lo pone el servidor (el servicio
registra a quién se le predijo) y se OCULTA a los roles con
limita_a_asignados (233); jamás se expone DNI ni teléfono (decisión
233). El de escritura solo acepta campaña y los cuatro valores
planificados (228): modelo, resultados, errores y creador los pone el
servidor y no existen en este serializer (232). Una campaña ajena o
inexistente responde 404 — el MISMO que en el detalle (227).
"""
from decimal import Decimal

from rest_framework import serializers
from rest_framework.exceptions import NotFound

from campanias.models import Campania
from productores.views import filtrar_asignados

from .models import EntrenamientoML, ModeloML, Prediccion, TareaEntrenamiento
from .servicio import TEXTO_ESTIMACION


def _mini_campania(campania):
    return {
        "id": campania.id,
        "periodo": campania.periodo,
        "estado": campania.estado,
        "cultivo": {
            "id": campania.cultivo_id,
            "nombre": campania.cultivo.nombre,
        },
        "parcela": {
            "id": campania.parcela_id,
            "codigo": campania.parcela.codigo,
            "productor": {
                "id": campania.parcela.productor_id,
                "nombre_completo": (
                    f"{campania.parcela.productor.apellidos}, "
                    f"{campania.parcela.productor.nombres}"
                ),
            },
        },
    }


def _demostracion(entrenamiento):
    """La marca de demostración se lee del entrenamiento (231)."""
    origen = (entrenamiento.variables_usadas or {}).get("origen_datos") or ""
    return "demostr" in str(origen).lower()


def _variables(obj):
    return obj.variables_entrada or {}


class PrediccionListaSerializer(serializers.ModelSerializer):
    """Fila del historial: campaña, modelo, fecha, resultado y
    comparación con lo real cuando la campaña ya se cosechó."""

    campania = serializers.SerializerMethodField()
    modelo = serializers.SerializerMethodField()
    confiabilidad = serializers.SerializerMethodField()
    datos_demostracion = serializers.SerializerMethodField()

    class Meta:
        model = Prediccion
        fields = (
            "id",
            "fecha",
            "campania",
            "modelo",
            "dias_ciclo",
            "rendimiento_predicho",
            "produccion_estimada_kg",
            "confiabilidad",
            "datos_demostracion",
            "rendimiento_real",
            "error_abs",
            "error_pct",
        )

    def get_campania(self, obj):
        return _mini_campania(obj.campania)

    def get_modelo(self, obj):
        return {
            "algoritmo": obj.modelo.algoritmo,
            "version": obj.modelo.version,
        }

    def get_confiabilidad(self, obj):
        return _variables(obj).get("confiabilidad")

    def get_datos_demostracion(self, obj):
        return _demostracion(obj.modelo.entrenamiento)


class PrediccionDetalleSerializer(serializers.ModelSerializer):
    """Ficha completa (HU-173/HU-177): variables con avisos y
    confiabilidad, marca de demostración con el texto fijo y el MAE
    (231); creado_por se omite de la respuesta para los roles con
    limita_a_asignados (233)."""

    campania = serializers.SerializerMethodField()
    modelo = serializers.SerializerMethodField()
    confiabilidad = serializers.SerializerMethodField()
    avisos = serializers.SerializerMethodField()
    negativo_ajustado = serializers.SerializerMethodField()
    datos_demostracion = serializers.SerializerMethodField()
    texto_estimacion = serializers.SerializerMethodField()
    creado_por = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Prediccion
        fields = (
            "id",
            "fecha",
            "campania",
            "modelo",
            "dias_ciclo",
            "rendimiento_predicho",
            "produccion_estimada_kg",
            "intervalo_inferior",
            "intervalo_superior",
            "confiabilidad",
            "avisos",
            "negativo_ajustado",
            "datos_demostracion",
            "texto_estimacion",
            "rendimiento_real",
            "error_abs",
            "error_pct",
            "variables_entrada",
            "creado_por",
        )

    def get_campania(self, obj):
        return _mini_campania(obj.campania)

    def get_modelo(self, obj):
        return {
            "id": obj.modelo_id,
            "algoritmo": obj.modelo.algoritmo,
            "version": obj.modelo.version,
            "activo": obj.modelo.activo,
            "mae": str(obj.modelo.mae),
            "rmse": str(obj.modelo.rmse),
        }

    def get_confiabilidad(self, obj):
        return _variables(obj).get("confiabilidad")

    def get_avisos(self, obj):
        return _variables(obj).get("avisos") or []

    def get_negativo_ajustado(self, obj):
        return bool(_variables(obj).get("negativo_ajustado"))

    def get_datos_demostracion(self, obj):
        return _demostracion(obj.modelo.entrenamiento)

    def get_texto_estimacion(self, obj):
        return TEXTO_ESTIMACION

    def to_representation(self, instance):
        datos = super().to_representation(instance)
        request = self.context.get("request")
        rol = getattr(getattr(request, "user", None), "rol", None)
        if rol is not None and rol.limita_a_asignados:
            datos.pop("creado_por", None)
        return datos


def _planificado(etiqueta):
    """Campo decimal ≥ 0 de los valores planificados (228)."""
    return serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        min_value=Decimal("0"),
        required=False,
        allow_null=True,
        error_messages={
            "invalid": f"El valor de {etiqueta} debe ser un número.",
            "max_digits": (
                f"El valor de {etiqueta} admite como máximo 8 dígitos "
                "enteros y 2 decimales."
            ),
            "max_decimal_places": (
                f"El valor de {etiqueta} admite como máximo 2 decimales."
            ),
            "min_value": f"El valor de {etiqueta} no puede ser negativo.",
        },
    )


class PrediccionEscrituraSerializer(serializers.Serializer):
    """Alta desde la pantalla Predicción (HU-173): campaña y los cuatro
    valores planificados de la decisión 228. Los campos que el cliente
    no controla (modelo, rendimiento, errores, creador) no existen aquí
    (232); el estado elegible y el modelo activo los resuelve el
    servicio (227)."""

    campania = serializers.IntegerField(
        error_messages={
            "required": "La campaña es obligatoria.",
            "invalid": "La campaña debe ser un id numérico.",
        }
    )
    semilla = _planificado("la semilla")
    fertilizante = _planificado("el fertilizante")
    mano_de_obra = _planificado("la mano de obra")
    agua = _planificado("el agua")

    def validate_campania(self, valor):
        """Ajena o inexistente → 404 «No encontrado.» (decisión 227)."""
        request = self.context.get("request")
        alcance = filtrar_asignados(
            Campania.objects.filter(pk=valor),
            getattr(request, "user", None),
            campo="parcela__productor_id",
        )
        if not alcance.exists():
            raise NotFound()
        return alcance.select_related(
            "parcela", "parcela__productor", "cultivo", "variedad"
        ).get()


class ModeloListaSerializer(serializers.ModelSerializer):
    """Ficha del modelo con sus métricas, el origen de los datos del
    entrenamiento (223) y la marca de demostración para el banner de la
    pantalla Modelos (239). Solo la ven los roles con ml.ver_modelos.
    Con la S23 (decisión 263) añade las columnas de la BD: `huella`,
    `versiones_librerias` y `en_bd` (el binario JAMÁS sale por la API;
    solo su presencia y su huella)."""

    entrenamiento = serializers.SerializerMethodField()
    datos_demostracion = serializers.SerializerMethodField()
    en_bd = serializers.SerializerMethodField()

    class Meta:
        model = ModeloML
        fields = (
            "id",
            "algoritmo",
            "version",
            "mae",
            "rmse",
            "r2",
            "activo",
            "archivo",
            "huella",
            "versiones_librerias",
            "en_bd",
            "creado_en",
            "entrenamiento",
            "datos_demostracion",
        )

    def get_entrenamiento(self, obj):
        usadas = obj.entrenamiento.variables_usadas or {}
        return {
            "id": obj.entrenamiento_id,
            "fecha": obj.entrenamiento.fecha,
            "n_registros": obj.entrenamiento.n_registros,
            "origen_datos": usadas.get("origen_datos"),
            "semilla": usadas.get("semilla"),
        }

    def get_datos_demostracion(self, obj):
        return _demostracion(obj.entrenamiento)

    def get_en_bd(self, obj):
        return obj.contenido is not None


class CampaniaPredecibleSerializer(serializers.ModelSerializer):
    """Selector de la pantalla Predicción (HU-173): solo estado, fechas
    y a qué parcela y productor pertenece cada campaña."""

    cultivo = serializers.StringRelatedField()
    variedad = serializers.StringRelatedField()
    parcela = serializers.SerializerMethodField()

    class Meta:
        model = Campania
        fields = (
            "id",
            "periodo",
            "estado",
            "fecha_inicio",
            "fecha_siembra",
            "superficie_sembrada_ha",
            "cultivo",
            "variedad",
            "parcela",
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


class TareaEntrenamientoSerializer(serializers.ModelSerializer):
    """Fila del historial y del polling cada 5 s (decisión 263): estado,
    progreso, latido y, al terminar, el enlace al resultado. Todo
    read-only: el cliente solo pide el alta y la cancelación."""

    usuario = serializers.StringRelatedField()

    class Meta:
        model = TareaEntrenamiento
        fields = (
            "id",
            "estado",
            "progreso",
            "latido",
            "observacion",
            "error",
            "resultado",
            "usuario",
            "creado_en",
        )
        read_only_fields = fields


class ResultadoEntrenamientoSerializer(serializers.ModelSerializer):
    """La pantalla de resultados (decisión 264): los 3 candidatos con
    sus métricas, el veredicto del criterio y la marca de
    demostración. El binario del modelo no sale nunca."""

    modelos = serializers.SerializerMethodField()
    criterio = serializers.SerializerMethodField()
    datos_demostracion = serializers.SerializerMethodField()

    class Meta:
        model = EntrenamientoML
        fields = (
            "id",
            "fecha",
            "n_registros",
            "n_entrenamiento",
            "n_prueba",
            "criterio",
            "modelos",
            "datos_demostracion",
        )

    def get_modelos(self, obj):
        return [
            {
                "id": modelo.id,
                "algoritmo": modelo.algoritmo,
                "version": modelo.version,
                "mae": str(modelo.mae),
                "rmse": str(modelo.rmse),
                "r2": str(modelo.r2),
                "activo": modelo.activo,
                "en_bd": modelo.contenido is not None,
                "huella": modelo.huella,
            }
            for modelo in obj.modelos.order_by("algoritmo")
        ]

    def get_criterio(self, obj):
        """El veredicto escrito (elegido, motivo y sigma); si el
        entrenamiento viejo no lo guarda, devuelve el vacío."""
        usadas = obj.variables_usadas or {}
        criterio = usadas.get("criterio") or {}
        return {
            "elegido": criterio.get("elegido"),
            "motivo": criterio.get("motivo"),
            "sigma": criterio.get("sigma"),
        }

    def get_datos_demostracion(self, obj):
        return _demostracion(obj)
