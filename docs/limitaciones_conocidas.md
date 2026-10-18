# Limitaciones conocidas — Entrega 1 (Semana 19)

Este documento declara, para transparencia y trazabilidad, las brechas de
cobertura donde una regla de negocio vive **solo en una capa** (API o base
de datos) o carece de defensa en BD. Se basa en la *Matriz de reglas de
calidad* (§3) y complementa `requerimientos.tex` v1.3 (sección
«Limitaciones conocidas»).

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

## 5. Referencias cruzadas

- `docs/matriz_reglas_calidad.md` — §3 (huecos) y §2 (agregados).
- `requerimientos.tex` v1.3 — secciones «Reglas adicionales implementadas» y «Limitaciones conocidas».
- `docs/decisiones_semana15.md` §1.1 — decisión de no triggers en alertas.
- `backend/sistema/tests_calidad.py` — pruebas M236–M241 (matriz de calidad).