# datos/

- `ejemplo_ubicaciones.csv` — **datos de prueba inventados** para la carga de
  ubicación (decisión 1 de `docs/decisiones_semana3.md`). Columnas:
  `provincia,distrito,comunidad`; celdas vacías = crear solo los niveles
  superiores de la fila. Se carga con:

  ```
  python manage.py cargar_ubicacion --archivo datos/ejemplo_ubicaciones.csv
  ```

  No son la lista real del proyecto. Cuando el responsable entregue su lista,
  este archivo se retira del repositorio.

- `ejemplo_demo.md` — **hoja de datos inventados** para la demostración de la
  Semana 4 (decisión 13 de `docs/decisiones_semana4.md`): productores,
  parcelas y asignaciones que se dan de alta **por la interfaz** siguiendo el
  guion `docs/demo_sprint2.md`. No hay comando de carga: es una lista para
  teclear durante la demo.
