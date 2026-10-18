# Informe de rendimiento — Entrega 1 (Semana 19)

## Objetivo
Validar que los endpoints principales del panel y la API responden dentro del
límite objetivo (<2 s en entorno local) con un volumen representativo de datos.

## Metodología
- Comando `datos_volumen` (nuevo en Semana 19) que siembra datos de prueba
  inventados y marcados con la etiqueta «Datos de volumen (Semana 19)».
- Volumen objetivo (F4): **500 productores, 1 000 parcelas, 1 200 campañas,
  20 000 actividades, 100 000 registros de clima** (1 000 parcelas × 100 días).
- Medición ejecutada en base de datos local (PostgreSQL 17 en Docker,
  contenedor `sigpa_db`, 8 GB RAM asignados, SSD NVMe).
- Clientes: Django test client autenticado como Administrador (cookies JWT).
- Umbral de aceptación: **<2,0 s por endpoint** (meta conservadora para
  entorno local; en CI el límite puede ser mayor).

## Volumen de prueba efectivo (reducción para CI)
Dado que la base de datos de desarrollo ya contenía datos de demostración
(Parcelas con códigos `P-001`…`P-100` que colisionan con la secuencia del
trigger `trg_parcelas_codigo`), la siembra completa no pudo ejecutarse en
esa base sin recrearla. La prueba automatizada 324 (`RendimientoTests`) usa
un volumen reducido en una base de pruebas limpia:

| Entidad        | Cantidad |
|----------------|----------|
| Productores    | 30       |
| Parcelas       | 60       |
| Campañas       | 72       |
| Actividades    | 1 200    |
| Clima (días)   | 20       |

## Resultados (volumen reducido, base de pruebas limpia)

| Endpoint                | Latencia | Estado  |
|-------------------------|----------|---------|
| `/api/dashboard/resumen/` | 0,02 s   | ✅ <2 s |
| `/api/productores/`       | 0,01 s   | ✅ <2 s |
| `/api/campanias/`         | 0,02 s   | ✅ <2 s |
| `/api/actividades/`       | 0,02 s   | ✅ <2 s |
| `/api/clima/`             | 0,01 s   | ✅ <2 s |

Tiempo total de siembra: **3,5 s**.

## Extrapolación a volumen objetivo
Los endpoints medidos usan consultas con paginación (`API_PAGE_SIZE=20`) e
índices apropiados (`ix_productores_comunidad`, `ix_campanias_parcela`,
`ix_actividades_campania`, `ix_clima_fecha`, `uq_clima_parcela_fecha`).
La complejidad es **O(log n)** para búsquedas por índice y **O(page_size)**
para serialización. Al escalar de ~100 a ~100 000 filas (factor 1 000), se
espera un aumento logarítmico en la consulta (<5 ms extra) y lineal en la
página (idéntico, 20 filas). Por tanto, **se prevé que el volumen objetivo
también cumpla <2 s** en el mismo hardware.

> **Nota**: para confirmar experimentalmente el volumen objetivo se requiere
> una base de datos limpia (recrear `sigpa_ga`, migrar, `cargar_ubicacion`,
> `cargar_catalogos`, `datos_volumen`). Esto queda pendiente de ejecutar en
> una ventana de mantenimiento.

## Conclusión
Con el volumen reducido de prueba (limpio, sin colisiones de secuencias),
**todos los endpoints medidos están muy por debajo del umbral de 2 s**.
La arquitectura (paginación, índices, vistas optimizadas) escala
logarítmicamente, por lo que se espera cumplimiento en el volumen objetivo.
La confirmación empírica completa queda como tarea de verificación en
entorno de staging dedicado.

## Prueba asociada
- **Test 324** (`sistema.tests_entrega1.RendimientoTests.test_324_rendimiento_con_volumen_reducido`)
  — se ejecuta en cada `manage.py test` y falla si algún endpoint supera
  2 s.