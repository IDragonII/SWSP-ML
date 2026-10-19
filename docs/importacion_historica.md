# Importación de datos históricos (RF-49 / RF-50)

Guía de uso del comando `importar_historico` (Semana 20). Carga datos
históricos de **productores**, **parcelas** y **campañas con su
producción** desde un CSV o un Excel `.xlsx`, validando cada fila con las
mismas reglas que la API y dejando un informe de errores por fila.

Comandos relacionados: `--plantilla` (genera el Excel en blanco),
`--dry-run` (prueba sin escribir), `--forzar` (libera una importación
interrumpida). Decisiones completas en `decisiones_semana20.md` (117–147).

---

## 1. Requisitos previos

1. **Permisos**: el usuario debe existir, estar activo y su rol tener el
   permiso **`importacion.ejecutar`** (sembrado en `usuarios.0002`; sin
   él, el comando aborta con un error claro).
2. **Catálogos existentes**: comunidades, cultivos y variedades que
   aparezcan en el archivo **deben estar dadas de alta antes**; el
   importador **nunca los crea** y sugiere el más parecido si hay una
   confusión (p. ej. «Quinu» → *«¿Quizá quiso decir **Quinua**?»*).
3. **Orden de carga**: primero `productores`, luego `parcelas` y al final
   `campanias` (las claves naturales de cada tipo dependen del anterior).
4. **Ubicaciones**: `cargar_ubicacion` (productores) necesita
   `datos/ejemplo_ubicaciones.csv` si el archivo no trae comunidad.

---

## 2. Generar la plantilla

```bash
python manage.py importar_historico --plantilla parcelas --salida D:\imp\parcelas.xlsx
```

La plantilla tiene **fila 1 = encabezados** (columna `marca` + columnas
de datos) y **fila 2 = EJEMPLO** con `marca=EJEMPLO`: esa fila se ignora
siempre, así no se puede importar el ejemplo sin borrarlo. La columna
`marca` es **opcional** en los archivos reales.

## 3. Columnas por tipo

**productores**: `nombres`, `apellidos`, `dni`, `telefono`, `comunidad`,
`referencia_ubicacion`, `fecha_incorporacion`.

**parcelas**: `dni_productor`, `comunidad`, `referencia_ubicacion`,
`superficie_ha`, `altitud_msnm`, `latitud`, `longitud`, `tipo_suelo`
(ARENOSO/FRANCO/ARCILLOSO/OTRO), `pendiente`
(PLANA/SUAVE/MODERADA/FUERTE), `disponibilidad_agua`
(ESCASA/MEDIA/ABUNDANTE), `sistema_riego` (SECANO/GRAVEDAD/ASPERSION/GOTEO).

**campanias**: `dni_productor`, `referencia_parcela`, `cultivo`,
`variedad`, `periodo` (p. ej. 2024-2025), `fecha_inicio`,
`fecha_fin_prevista`, `fecha_siembra`, `superficie_sembrada_ha`,
`fecha_cosecha`, `superficie_cosechada_ha`, `produccion_kg`,
`semilla_kg`, `fertilizante_kg`, `jornales`, `agua_m3`, `observaciones`.

Los 4 últimos son los **totales de recursos** de la campaña (vacío/0 =
sin uso, negativo = error); se graban con `fecha = fecha_siembra` y la
unidad base de cada tipo.

### Formato del archivo

- **CSV**: delimitador `,` o `;` (se detecta solos), UTF-8 con o sin BOM.
- **Excel**: `.xlsx` (no `.xls`), una sola hoja, encabezados en la fila 1.
- **Límites**: máx **5 MB** y **5000 filas** de datos.
- **Fechas**: exactamente `dd/mm/aaaa` o `aaaa-mm-dd` (10 caracteres);
  cualquier otra forma (p. ej. `1/2/2020`) es error.
- **DNI**: 7 dígitos se normalizan a 8 anteponiendo `0`; debe tener 8.

Ejemplos listos para probar: `docs/ejemplos_importacion/*.csv`.

## 4. Ejecutar

```bash
# Prueba sin escribir nada (recomendada siempre primero)
python manage.py importar_historico --tipo productores --archivo prod.csv --usuario ana --dry-run

# Importación real
python manage.py importar_historico --tipo productores --archivo prod.csv --usuario ana
```

Salida resumen: filas de datos, creadas, ya existían (se **omitieron sin
actualizar**: la re-ejecución es idempotente) y con error, una por línea
con `Fila N [columna]: mensaje`.

Al terminar, cada ejecución real deja:

- **1 registro** en la tabla `importaciones` (EN_PROCESO → COMPLETADA o
  CON_ERRORES, con `detalle_errores` en JSONB);
- **1 informe CSV** en `IMPORTACION_DIR` (.env, fuera del repo) con
  cabecera `fila,columna,mensaje` y **sin datos personales** (el DNI va
  enmascarado: `******` + 2 últimos);
- **1 evento de auditoría** (`modulo=importaciones`, `accion=CREAR`);
- **una pasada de alertas** (`evaluar_todo()`), una sola vez.

## 5. Errores frecuentes

| Mensaje | Qué hacer |
|---------|-----------|
| `Faltan argumentos obligatorios: --tipo …` | Indicar los tres (`--tipo`, `--archivo`, `--usuario`) o usar `--plantilla --salida`. |
| `El usuario «x» no tiene el permiso importacion.ejecutar` | Asignar el permiso al rol o ejecutar con otro usuario. |
| `Ya hay una importación EN_PROCESO (id …)` | Terminar la otra consola; si quedó interrumpida, repetir con `--forzar`. |
| `No existe la comunidad «X». ¿Quizá quiso decir «Y»?` | Corregir el nombre en el archivo; los catálogos no se crean desde aquí. |
| `IMPORTACION_DIR no está definido` | Añadir la variable al `.env`; el informe no se escribe pero los errores siguen en consola y en el registro. |
| Archivo rechazado por tamaño/filas | Partir en varios archivos de ≤5 MB y ≤5000 filas. |

**Atípicas**: si el rendimiento queda fuera de los umbrales, la campaña
queda **COSECHADA con `requiere_revision`** (no entra al dataset hasta
que alguien la revise y cierre); el resto de campañas importadas pasan a
**CERRADA** y al dataset con `origen=IMPORTADA`.

## 6. Ejemplo completo (campañas)

```bash
python manage.py importar_historico --plantilla campanias --salida D:\imp\campanias.xlsx
# ... editar D:\imp\campanias.xlsx (borrar la fila EJEMPLO si se copia) ...
python manage.py importar_historico --tipo campanias --archivo D:\imp\campanias.csv --usuario ana --dry-run
python manage.py importar_historico --tipo campanias --archivo D:\imp\campanias.csv --usuario ana
```
