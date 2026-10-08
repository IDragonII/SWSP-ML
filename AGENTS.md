# Convenciones de UI — SIGPA-GA (frontend)

Reglas obligatorias al crear o modificar pantallas en `frontend/src`. Revisar
también `docs/verificacion_ui_semana4.md` (checklist de navegador) y la
decisión 14 (responsive siempre) de `docs/decisiones_semana4.md`.

## 1. Rueda de carga en toda operación en curso

Toda acción asíncrona con feedback (guardar, confirmar, entrar, asignar,
activar/desactivar) muestra la rueda **dentro del botón** que la dispara, con
el botón `disabled` mientras dure:

```jsx
import RuedaCarga from '../components/RuedaCarga.jsx'

<button className="boton-primario" type="submit" disabled={guardando}>
  {guardando ? (
    <>
      <RuedaCarga etiqueta="Guardando…" />
      Guardando…
    </>
  ) : (
    'Guardar'
  )}
</button>
```

- Textos según la acción: «Guardando…», «Procesando…», «Entrando…»,
  «Asignando…» (no dejar el texto de reposo mientras se espera).
- El `etiqueta` del `RuedaCarga` es el `aria-label` para lectores de pantalla.
- Las confirmaciones que pasan por `Modal` ya muestran la rueda solas (prop
  `ocupado` → «Procesando…»).
- Para cargas de pantalla completa se usa `components/Cargando.jsx` (con su
  prop `texto`, p. ej. `<Cargando texto="Cargando tu sesión…" />`).

## 2. Todo formulario vive en un modal

Todo alta/edición se construye con `components/Modal.jsx` (tamano
`formulario` o `ficha`), **nunca** como página/ruta nueva. El CRUD de
productores y parcelas es la referencia: rutas solo de listado, la operativa
completa en ventanas flotantes (decisión 19). Los permisos se muestran **en el
botón**: sin botón, sin modal.

## 3. Toda tabla usa el componente `Tabla`

Nunca escribir `<table>` a mano. Usar `components/Tabla.jsx` con su API
declarativa:

```jsx
<Tabla
  filas={datos}
  columnas={[
    { clave: 'codigo', etiqueta: 'Código' },
    { clave: 'estado', etiqueta: 'Estado', celda: (fila) => <Chip>{fila.estado}</Chip> },
    { clave: 'acciones', etiqueta: 'Acciones', acciones: true, celda: (fila) => (/* botones */) },
  ]}
/>
```

Trae gratis: `scope="col"`, `data-rotulo` para el paso a tarjetas en móvil
(≤860 px), clase `celda-acciones`, `key` por fila y el estado `refrescando`
de la paginación.
