# Decisiones — Semana 3: ubicación y productores

> Sprint 2, semana del 19 al 25 de octubre. Documento análogo a
> `decisiones_seguridad.md`: recoge lo acordado con el responsable y las
> reglas que guían la implementación de esta semana.
> Estado: **propuestas aprobadas en el plan de la semana**. Las marcadas
> con ⚠️ están pendientes de confirmación formal del responsable.

## 1. Tabla de decisiones

| # | Decisión | Qué queda anotado |
|---|----------|--------------------|
| 1 | **Datos de ubicación** | ⚠️ El responsable aún **no entregó** la lista de provincias, distritos y comunidades de trabajo. Mientras tanto se usa una **lista de datos de prueba** inventada y claramente marcada (`datos/ejemplo_ubicaciones.csv`), **fuera de las migraciones**. Cuando llegue la lista real, se carga con el mismo comando sin tocar código. |
| 2 | **Cómo se cargan** | Con el comando `python manage.py cargar_ubicacion --archivo <ruta>` (acepta `.csv` y `.xlsx`), **no con una migración de datos**: la lista la aporta el proyecto y puede cambiar. El comando es **idempotente** (se puede repetir sin duplicar) e informa de cuántas filas creó, cuántas ya existían y cuáles fallaron. |
| 3 | **Qué pasa al desactivar una ubicación** | Al poner `activo = false` deja de aparecer en los **desplegables** (`?activo=true`), pero **los productores que ya la tienen la conservan** (el vínculo no se toca). El listado administrativo por defecto muestra todas —incluidas las inactivas— para poder reactivarlas. |
| 4 | **Quién ve DNI y teléfono completos** | ⚠️ **Propuesta** (pendiente de confirmación del responsable, RNF de protección de datos personales): **Administrador** y **Técnico de campo** los ven **completos**; el **Coordinador** los ve **enmascarados** (DNI `****5678`, teléfono `****789`). Si el responsable cambia la regla, se ajusta en una única constante del serializador. |
| 5 | **Qué hace el Técnico antes de tener asignaciones** | La tabla `asignaciones_tecnico` llega en la **semana 4**. Hasta entonces el filtro «solo mis productores» queda como **punto de extensión sin activar** (anotado en la API, sin implementar). Se prueba con Administrador y Coordinador. **Pregunta abierta para la semana 4:** ¿el productor que registra un técnico se le asigna automáticamente? |
| 6 | **Borrado** | **Nada se borra**: productores y ubicaciones solo se **desactivan/reactivan**. La API **no ofrece** el método DELETE (responde `405`). A nivel de base de datos, las FK son `PROTECT` (diseño `ON DELETE RESTRICT`): no se puede borrar una provincia con distritos ni una comunidad con productores. |
| 7 | **Formato de listados** | **Paginados** (20 por página, `API_PAGE_SIZE` en el `.env`), **orden por apellidos** y un **parámetro de búsqueda general** (`?busqueda=`) además de filtros por jerarquía y estado. |

## 2. Preguntas abiertas

| # | Pregunta | Para cuándo |
|---|----------|-------------|
| A | ¿Entregó el responsable la lista real de ubicaciones? | Al recibirla: cargar con `cargar_ubicacion` y retirar `datos/ejemplo_ubicaciones.csv` del repositorio |
| B | Confirmar la regla de **enmascarado de DNI/teléfono** por rol (decisión 4) | Esta semana; hasta entonces rige la propuesta |
| C | ¿El productor que registra un técnico **se le asigna automáticamente**? | Semana 4 (antes de activar el filtro «solo mis productores») |

## 3. Notas de contexto

- Datos personales: en el repositorio **solo hay datos inventados** (CSV de ejemplo y ejemplos de documentación). No se commitean DNI ni nombres reales.
- Numeración de códigos `PROD-000N`: la secuencia **no se reinicia** entre pruebas; si hay saltos tras un fallo es comportamiento normal de las secuencias y **no se corrige**.
- Hasta la semana 4, un Técnico **ve todos los productores** (no existe aún el filtro por asignación). Todo el trabajo de la semana 3 está en desarrollo, sin datos reales.
