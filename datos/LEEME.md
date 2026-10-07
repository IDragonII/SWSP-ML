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
