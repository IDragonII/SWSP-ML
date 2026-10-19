"""Validación agrupada por productor (Semana 21).

Regla anti-fuga más dura que la del catálogo: un productor NO puede
estar en entrenamiento y en prueba al mismo tiempo — sus parcelas se
parecen entre sí y el modelo las memorizaría. GroupKFold reparte los
grupos de productor_id de forma que cada productor cae entero en un
lado, y con la SEMILLA fija de la semana el corte sale siempre igual:
cualquiera que repita el notebook obtiene los mismos pliegues
(pruebas 360 y 361).

Solo define CÓMO se parten los datos: aquí no se entrena ningún modelo.
"""
from sklearn.model_selection import GroupKFold

from ml.exportacion import SEMILLA

GRUPO = "productor_id"


def grupos_de(datos):
    """Grupos por fila como array posicional (productor de cada fila)."""
    if GRUPO not in datos.columns:
        raise ValueError(
            f"Falta «{GRUPO}»: sin el productor no se puede validar por "
            "grupos."
        )
    return datos[GRUPO].to_numpy()


def particiones(datos, n_pliegues=5, semilla=SEMILLA):
    """[(índices_entrenamiento, Índices_prueba)] con grupos completos.

    Los índices son POSICIONALES (0..n-1), listos para .iloc[...]. Cada
    productor aparece entero en un solo lado de cada corte, y todo el
    conjunto pasa por prueba exactamente una vez.
    """
    grupos = grupos_de(datos)
    n_grupos = len(set(grupos))
    if n_grupos < n_pliegues:
        raise ValueError(
            f"Hay {n_grupos} productores y se pidieron {n_pliegues} "
            "pliegues: cada pliegue necesita al menos un productor de "
            "prueba completo."
        )
    corte = GroupKFold(
        n_splits=n_pliegues, shuffle=True, random_state=semilla
    )
    return [
        (entrenamiento, prueba)
        for entrenamiento, prueba in corte.split(datos, None, grupos)
    ]
