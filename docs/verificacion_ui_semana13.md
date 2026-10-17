# Verificación UI — Semana 13 (checklist manual)

> Este checklist cumple el papel de `verificacion_ui_semana13.md` (plan
> F6). El agente deja este checklist — además de `npm run lint` (0),
> `npm run build` (152 módulos) y la suite de backend **220/220 en
> verde** (`manage.py check` 0 issues, `makemigrations --check` sin
> cambios) — y el responsable lo ejecuta en navegador y anota el
> resultado.
> Pantallas de la semana: **`/auditoria`** (HU-105..HU-111), el botón
> **«Ver historial»** de las fichas de productor, parcela y usuario
> (HU-110) y **`/cambiar-clave`** con toda la marca
> `debe_cambiar_clave` (HU-112..HU-113).
> Ver también: `decisiones_semana13.md`, `api_auditoria.md`,
> `api_cambio_clave.md`.

## Preparación

```bash
# Terminal 1 — backend (puerto 8000)
cd backend && venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000 --noreload

# Terminal 2 — frontend (puerto 5173)
cd frontend && npm run dev
```

- Abrir `http://localhost:5173` en **Chrome** y en **Edge** (los mismos
  pasos en ambos).
- Usuarios (de `.credenciales`): `admin` / `SigpaGA2026!`,
  `coordinador` / `Coordinador2026!`, `tecnico` / `Tecnico2026!`.
- Para la prueba de la marca de cambio: con `admin`, crea (o usa) un
  usuario de prueba (p. ej. rol Cualquiera) y **restablece su
  contraseña** desde su ficha («Restablecer contraseña»); anota la
  contraseña temporal que devuelve la acción. Ese usuario es el que
  entrará con la marca activa.
- No usar datos reales (decisión 22); `.credenciales` solo en local.

## 1. Chrome — escritorio 1366×768

### Pantalla `/auditoria` (HU-105..HU-111)

- [ ] Con `admin`, la opción **«Auditoría»** del menú abre
      `/auditoria` (título «Auditoría» + «N evento(s) — registro
      inmutable de acciones»); con un usuario **sin `auditoria.ver`**
      (Técnico o Coordinador) la ruta muestra **Acceso denegado** y la
      opción no está en el menú.
- [ ] El listado muestra eventos reales de la sesión (p. ej. los
      LOGOUT/LOGIN y CREAR/MODIFICAR que dejen las acciones de prueba)
      ordenados de más reciente a más antiguo.
- [ ] La tabla (`Tabla`) tiene las 8 columnas: **Fecha** (fecha+hora en
      es-PE), **Usuario** (código, o «—» si el evento no tiene cuenta),
      **Acción** (chip: Entrar, Salir, Crear, Modificar, Activar,
      Desactivar, Anular, Reactivar, Asignar, Desasignar, Bloquear,
      Desbloquear, Restablecer clave, Cambiar clave), **Módulo**,
      **Tabla**, **Registro**, **Detalle** (JSON en `<code>` o «—») y
      **IP**.
- [ ] Filtros: **Buscar** (placeholder «Módulo, acción o tabla»),
      **Módulo** (placeholder «p. ej. productores»), **Acción**
      (desplegable «Todas» + las 15 etiquetas), **Desde**/**Hasta**
      (fechas), botones **«Aplicar»** y **«Limpiar»**; los filtros viven
      en la URL y la paginación respeta la página (20 por página).
- [ ] Filtrar por acción «Entrar» (LOGIN) y módulo «usuarios» reduce el
      listado a accesos; «Limpiar» lo restaura todo.
- [ ] Con filtros imposibles (p. ej. módulo «zzz») aparece el panel
      «No hay eventos que coincidan con los filtros.» con la nota de
      que las lecturas no dejan eventos.
- [ ] El botón **«Actualizar»** recarga el listado (estado
      «refrescando» de la tabla mientras llega la respuesta).
- [ ] No hay ningún formulario de alta/edición en la pantalla (la
      auditoría es solo lectura; no existe botón que abra un modal).

### «Ver historial» en las fichas (HU-110)

- [ ] En la ficha de un **productor** (con `admin`), el botón
      **«Ver historial»** lleva a `/auditoria?tabla=productores&registro={id}`
      y la pantalla muestra solo los eventos de ese productor, con el
      chip **«Quitar historial de Productor #{id}»** en la cabecera.
- [ ] Lo mismo en la ficha de una **parcela** (`tabla=parcelas`) y en
      **`/usuarios` → ficha de usuario** (`tabla=usuarios`).
- [ ] «Quitar historial» devuelve al listado completo y quita el chip.
- [ ] El botón «Ver historial» **no aparece** en las fichas con un
      usuario sin `auditoria.ver` (p. ej. Técnico en su productor).

### Pantalla `/cambiar-clave` (HU-112..HU-113)

- [ ] Con la sesión del usuario de prueba **sin marca**, entrar a
      `/cambiar-clave` a mano funciona (pantalla tipo login: aside
      SIGPA-GA + panel «Cambiar contraseña») con el lema «Actualiza tu
      contraseña para seguir trabajando con seguridad.».
- [ ] **Ciclo de la marca** (con `admin` restablece → con el usuario de
      prueba entra con la contraseña temporal):
      - [ ] Tras el login, la interfaz **redirige sola** a
            `/cambiar-clave` (menú y rutas no disponibles; el lema del
            aside dice «Tu cuenta tiene una contraseña provisional…»).
      - [ ] Intentar ir a otra ruta (p. ej. `/productores`) vuelve a
            mandar a `/cambiar-clave`.
      - [ ] En otra pestaña abierta con la sesión previa, cualquier
            llamada a la API responde 403/401 (no se navega).
- [ ] **Contraseña actual incorrecta**: el error «La contraseña actual
      no es correcta.» aparece junto al campo y no se cierra la sesión.
- [ ] **Validadores de la nueva**: repetir el username, «1234» o una
      contraseña común muestran el error del servidor junto a
      «Contraseña nueva»; si la nueva no coincide con la repetición, el
      aviso «Las dos contraseñas nuevas no coinciden.» es del cliente.
- [ ] **Éxito**: con la contraseña actual correcta y una nueva válida,
      el botón muestra la rueda «Guardando…», aparece el toast
      «Contraseña actualizada. Tus sesiones anteriores quedaron
      cerradas.» y la interfaz queda **dentro** (pantalla de inicio,
      menú completo) **sin volver a entrar**.
- [ ] Con esa misma cuenta, reintentar `/auditoria` (o cualquier ruta)
      funciona sin marca; en `/usuarios` su ficha ya no obliga a nada.
- [ ] En `/auditoria` filtrando por usuario y acción «Cambiar clave»
      aparece el evento CAMBIAR_CLAVE del cambio recién hecho (detalle
      `{}` e IP).
- [ ] **Reintentos**: con la marca activa, fallar la contraseña actual
      **6 veces** seguidas muestra «Demasiados intentos…» (429) junto
      al botón/cabecera; un cambio exitoso deja los intentos limpios.
- [ ] Tras cambiar, la contraseña **anterior ya no entra** en un
      `login` nuevo (y la temporal del restablecimiento tampoco).
- [ ] **`logout`** con la marca activa funciona (la puerta no lo corta)
      y vuelve a la pantalla de entrada.

## 2. Edge — escritorio 1024×768

- [ ] Repetir los apartados principales de §1 (`/auditoria` con filtros
      e historial, y el ciclo de marca + `/cambiar-clave`); sin scroll
      horizontal y sin solapes.

## 3. Móvil — 360×780 (y 768 px de ancho)

- [ ] La tabla de `/auditoria` se convierte en **tarjetas**
      (`data-rotulo`) con las 8 etiquetas legibles y la paginación
      pulsable (áreas ≥ 44 px).
- [ ] Los filtros de `/auditoria` se apilan sin desbordes y «Aplicar»/
      «Limpiar» quedan visibles.
- [ ] `/cambiar-clave` ocupa el ancho completo (el aside marca se
      oculta o apila como en login) y el botón «Guardar contraseña» no
      queda cortado.
- [ ] El menú de la entrada **«Auditoría»** y la navegación a
      `/auditoria` funcionan con táctil.

## 4. Comprobaciones transversales

- [ ] `npm run lint` y `npm run build` en 0 problemas; backend
      **220/220** (`manage.py test`, `check`, `makemigrations --check`).
- [ ] Ninguna acción asíncrona queda sin rueda dentro de su botón
      (Aplicar filtros, Actualizar, Guardar contraseña).
- [ ] Sin datos reales en las pruebas manuales (decisión 22);
      `.credenciales` no se pega en la colección ni en los tickets.
- [ ] La auditoría **no se puede editar ni borrar** desde la UI (no hay
      acciones de escritura) y un `PATCH`/`DELETE` manual a la API
      responde 405 (la inmutabilidad del trigger se prueba con
      `manage.py shell` o psql: `UPDATE auditoria SET detalle = '{}'`
      debe fallar).
