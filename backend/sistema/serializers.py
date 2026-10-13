"""Serializadores de la API de parámetros del sistema (Semana 8).

La lista muestra clave, valor, descripción y trazabilidad; el de escritura
solo admite el valor (la clave es fija, cargada por la migración 0001) y
valida que sea un número mayor que 0 y que el par de umbrales de
rendimiento siga coherente (mínimo menor que máximo).
"""
from decimal import Decimal, InvalidOperation

from rest_framework import serializers

from .models import ParametroSistema


class ParametroSerializer(serializers.ModelSerializer):
    """Lectura: clave, valor, descripción y actualizado_en."""

    class Meta:
        model = ParametroSistema
        fields = ("clave", "valor", "descripcion", "actualizado_en")
        read_only_fields = ("clave", "descripcion", "actualizado_en")


class ParametroEscrituraSerializer(serializers.ModelSerializer):
    """Edición por clave: solo el valor cambia."""

    valor = serializers.CharField(
        error_messages={"required": "El valor es obligatorio."}
    )

    class Meta:
        model = ParametroSistema
        fields = ("valor",)

    def validate_valor(self, valor):
        valor = (valor or "").strip()
        try:
            numero = Decimal(valor)
        except InvalidOperation:
            raise serializers.ValidationError(
                "El valor debe ser un número mayor que 0."
            )
        if numero <= 0:
            raise serializers.ValidationError(
                "El valor debe ser un número mayor que 0."
            )
        return valor

    def validate(self, attrs):
        instancia = self.instance
        clave = instancia.clave if instancia is not None else None
        numero = Decimal(attrs["valor"])
        # El par de umbrales de revisión debe seguir coherente: al mover el
        # mínimo se compara con el máximo vigente y viceversa
        if clave == "rendimiento_min_plausible":
            maximo = ParametroSistema.objects.filter(
                clave="rendimiento_max_plausible"
            ).first()
            if maximo is not None and numero >= Decimal(maximo.valor):
                raise serializers.ValidationError(
                    {"valor": "El rendimiento mínimo debe ser menor que el máximo."}
                )
        elif clave == "rendimiento_max_plausible":
            minimo = ParametroSistema.objects.filter(
                clave="rendimiento_min_plausible"
            ).first()
            if minimo is not None and numero <= Decimal(minimo.valor):
                raise serializers.ValidationError(
                    {"valor": "El rendimiento mínimo debe ser menor que el máximo."}
                )
        return attrs
