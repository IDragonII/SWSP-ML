# Manual de usuario - SIGPA-GA

Manual por rol del Sistema Integrado de Gestión de Productores
Agropecuarios. Cada rol ve solo lo que sus permisos permiten (la matriz
completa está en `docs/matriz_rutas_por_rol.md`). Las contraseñas de
prueba del entorno de desarrollo están en `.credenciales` (nunca se
suben a Git).

---

## 1. Entrar al sistema

1. Abrir la aplicación (en desarrollo: `http://127.0.0.1:8000/`).
2. Introducir usuario y contraseña. Tras 5 intentos fallidos la cuenta
   se bloquea 15 minutos (el Administrador la puede desbloquear).
3. Si la contraseña es la inicial, el sistema obliga a cambiarla antes
   de continuar (HU-112).
4. La sesión se cierra sola tras 30 minutos sin actividad; el enlace
   «Salir» la cierra antes.

---

## 2. Administrador

Tiene todo el menú (55 permisos) más el panel de Django en `/admin/`.

| Sección | Qué hace |
|---|---|
| **Panel** | Tarjetas de productores, campañas, producción y alertas; series del período. |
| **Productores** | Alta/edición en ventana modal, búsqueda, ficha con parcelas; puede desactivar (nunca borrar). |
| **Campañas** | Ciclo completo: planificar, iniciar producción, registrar etapas fenológicas y actividades, incidencias, cosechar y cerrar. |
| **Seguimiento** | Clima manual o desde la API (Open-Meteo) por parcela; recursos de la campaña. |
| **Producción** | Registro de cosecha por campaña; al registrarla el sistema compara el rendimiento real con la predicción y calcula el error. |
| **Alertas** | Listado con filtros; «Evaluar ahora» dispara el barrido (también puede correrse con `manage.py evaluar_alertas`). |
| **Reportes** | Catálogo con vista previa y exportación a Excel/PDF; el reporte de auditoría está marcado «datos sensibles». |
| **Usuarios / Roles / Auditoría** | Gestión de cuentas, permisos por rol y bitácora con filtros. |
| **Predicción** (ML) | Ver sección 5. |
| **Historial de predicciones** (ML) | Ver sección 5. |
| **Modelos** (ML) | Ver sección 5. |

---

## 3. Coordinador

Solo lectura (14 permisos): Panel, productores, campañas, seguimiento,
producción, alertas (ver), reportes (ver y exportar) e **historial de
predicciones**. No crea ni edita; no ve usuarios, roles ni auditoría; no
ve modelos ni puede predecir (recibe «No tienes permiso para realizar
esta acción»).

---

## 4. Técnico de campo

Crea y edita en campo sobre **sus productores asignados** (32
permisos): productores y parcelas asignados, campañas, etapas,
actividades, incidencias, clima y recursos; reportes de actividades (sin
la columna «Responsable») y alertas de sus asignados.

- Lo que no le pertenece responde **«No encontrado.»** (igual que un id
  inexistente: su alcance no se filtra).
- Puede **predecir** y ver su historial (las predicciones ajenas
  también son «No encontrado.»); no ve ni activa modelos.

---

## 5. Machine Learning (las tres pantallas)

> Las tres muestran el banner **«DATOS DE DEMOSTRACIÓN»** mientras el
> modelo activo se haya entrenado con datos inventados
> (`datos_ml_demostracion`). Ninguna cifra de estas pantallas es un
> resultado de tesis: es una estimación de plan, no una medición.

### 5.1 Predicción (`/predicción`) — Administrador y Técnico

1. Elegir una campaña del selector (solo PLANIFICADA o EN_PRODUCCION; el
   Técnico solo ve las de sus productores).
2. Introducir los valores planificados del manejo (semilla, fertilizante,
   mano de obra y agua, en kg/ha o m³/ha, ≥ 0 y hasta 2 decimales).
3. Pulsar **Predecir**. El resultado grande muestra el rendimiento
   predicho (kg/ha), la producción estimada de la campaña, la
   confiabilidad (ALTA/BAJA), el MAE del modelo y los avisos (valores
   imputados, fuera del rango de entrenamiento, etc.).
4. Si el modelo activo es de demostración aparece también el texto:
   «Es una estimación basada en datos históricos, no una medición».

La campaña elegida queda en la dirección (compartible); hay límite de
30 predicciones por hora y usuario.

### 5.2 Historial (`/predicciones`) — los tres roles

Pestañas **Pendientes** / **Comparadas** / **Todas** (también en la
dirección). Cada fila muestra el resultado predicho y, cuando la campaña
ya se cosechó, el rendimiento real y el error (absoluto y %). La ficha
completa (clic en una fila) añade las variables de entrada, los avisos y
quién predijo (oculto para el Técnico). No se puede editar ni borrar
una predicción desde la interfaz.

### 5.3 Modelos (`/modelos`) — solo Administrador

Tabla con los modelos entrenados: algoritmo, versión, MAE, RMSE, R²,
estado (activo) y el origen de los datos del entrenamiento. El botón
**Activar** (con confirmación) cambia el modelo vigente: un solo modelo
puede estar activo a la vez y la activación queda en la auditoría.

---

## 6. Dudas frecuentes

| Pregunta | Respuesta |
|---|---|
| «No encontré un productor/campaña» | Si eres Técnico, probablemente no está asignado: pide asignación al Administrador. |
| «La predicción dice confiabilidad BAJA» | Faltan 2 o más de los 4 valores de manejo: completa el formulario. |
| «No puedo predecir en la campaña» | Solo se puede predecir con campañas PLANIFICADA o EN_PRODUCCION, y mientras haya modelo activo. |
| «Demasiadas solicitudes» | Límite de 30 predicciones por hora; espera o pide al Administrador que revise. |
| «La alerta no se generó» | El barrido puede estar atrasado (>36 h): el sistema avisa en la pantalla de alertas. |
