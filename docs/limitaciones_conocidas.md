# Limitaciones conocidas — Entrega 1 (Semana 19 → 22)

Este documento declara, para transparencia y trazabilidad, las brechas de
cobertura donde una regla de negocio vive **solo en una capa** (API o base
de datos) o carece de defensa en BD. Se basa en la *Matriz de reglas de
calidad* (§3) y complementa `requerimientos.tex` **v1.5** (sección
«Limitaciones conocidas»); la §5 añade los límites del Machine Learning
de la Semana 22 (decisiones 243-244).

---

## 1. Reglas con cobertura parcial (solo API)

| Regla | Capa que la impone | Capa que NO la defiende | Pruebas que la cubren | Impacto |
|-------|-------------------|------------------------|----------------------|---------|
| **Sin fechas futuras** (hora de Lima) en actividades, usos, incidencias, etapas y clima | API (`seguimiento/serializers.py`) | BD (`fn_validar_fecha_campania` valida estado y período, no «hoy») | `test_89`, `test_141`, `test_157`, `test_185` | Un INSERT crudo con fecha futura entraría; solo la API la rechaza. |
| **Revisión pendiente bloquea el cierre** | API (`campanias/views.py:394`) | BD (`fn_validar_campania` solo exige «producción registrada») | `M240`, `test_115` | Un UPDATE crudo de estado podría cerrar con revisión pendiente. |
| **Requisitos de `revisar` (nota + incluir_en_entrenamiento)** | Regla de interfaz (API) | BD (ninguna) | `M240`, `test_115` | Un UPDATE crudo podría quitar la marca sin nota. |
| **Una etapa por campaña + cronología + etapa del cultivo** | API + `uq_seguimiento_etapa` + `fn_validar_etapa` (OK en BD para unicidad y orden) | — | `test_173`–`test_179` | Cubierta en ambas capas; listada por completitud. |

---

## 2. Alertas (Semana 15) — sin triggers en BD

La lógica completa de alertas (generación por incidencia severa, gracia tras
atención manual, cierre automático al cambiar de estado, barrido diario de
atraso) reside **exclusivamente en la aplicación**:

- 13 ganchos `transaction.on_commit` en `alertas/signals.py`.
- Comando `evaluar_alertas` para barrido programado (cron/worker).
- Endpoint `/alertas/evaluacion/` devuelve aviso de atraso si no se ejecuta
  en 36 h.

La tabla `alertas` **no tiene triggers** por decisión explícita
(`decisiones_semana15.md` §1.1). Su red en BD se limita a CHECKs e índices
únicos.

**Riesgo aceptado**: si el worker/cron no corre, las alertas no se generan
ni cierran. La mitigación es el aviso de atraso de 36 h y la monitorización
del proceso.

---

## 3. Fechas de cosecha futuras

Admitidas por diseño (pregunta H pendiente del responsable). Declaradas en
`decisiones_semana*.md`. No hay validación de «fecha de cosecha ≤ hoy».

---

## 4. Reglas **sin ninguna implementación**: NINGUNA

Las 16 RN-01…RN-16 del documento tienen al menos una red viva (API y/o BD)
y al menos una prueba automatizada que la dispara. La matriz de calidad
(M236–M241) confirma la cobertura completa.

---

## 5. Machine Learning (Semana 22) — límites declarados

| Limitación | Detalle | Dónde se declara |
|---|---|---|
| **Momento de la predicción** | La predicción es **al planificar el ciclo** (plan de manejo): solo entra lo registrado hasta ese momento. El clima del ciclo (monitoreo) **no alimenta al modelo**, aunque el seguimiento esté implementado. | `decisiones_semana22.md` U, `.tex` v1.5 |
| **Sin intervalo de confianza** | Se devuelve un punto (kg/ha) con MAE, sin intervalo inferior/superior; los campos existen pero quedan `null`. | `decisiones_semana22.md` 231 |
| **Tamaño de los datos** | 13 campañas aptas en la BD de desarrollo: por debajo del tramo «≥ 30» del criterio, la confiabilidad es **BAJA**. Con datos reales escasos el criterio puede no elegir ningún modelo (no se activa nada). | `decisiones_semana22.md` 207, J |
| **Origen de los datos de la demo** | El modelo activo de la demostración se entrenó con **datos inventados** (semilla 42, `datos_ml_demostracion`): banner «DATOS DE DEMOSTRACIÓN» en API y pantallas, marca `datos_demostracion` en la ficha. **Ninguna cifra es un resultado de tesis.** | `decisiones_semana22.md` 247, 231, 240 |
| **Modelo estático** | El modelo es un archivo `.joblib` versionado: se reentrena con comandos (`entrenar_modelos`, `registrar_modelo`), **no desde la interfaz**. No hay reentrenamiento automático ni vigencia temporal. | `manual_tecnico.md` §6 |
| **Despliegue pendiente** | El barrido de alertas depende de un cron/worker (§2); no hay despliegue en la nube ni proceso programado de reentrenamiento. | §2, `decisiones_semana22.md` 244 |

### Fuera de alcance (mejoras futuras — decisión 244)

Búsqueda de hiperparámetros · logaritmo del rendimiento · segundo
conjunto de entrenamiento con clima integrado · intervalo de
predicción · reportes de ML en Excel/PDF · alerta de rendimiento bajo
· tarjeta del dashboard · reentrenar desde la interfaz · despliegue en
la nube · predicciones en escenarios sin campaña · mapa de parcelas.

---

## 6. Referencias cruzadas

- `docs/matriz_reglas_calidad.md` — §3 (huecos) y §2 (agregados).
- `requerimientos.tex` v1.5 — secciones «Reglas adicionales implementadas» y «Limitaciones conocidas».
- `docs/decisiones_semana15.md` §1.1 — decisión de no triggers en alertas.
- `docs/decisiones_semana22.md` — decisiones 202-248 (Machine Learning).
- `backend/sistema/tests_calidad.py` — pruebas M236–M241 (matriz de calidad).