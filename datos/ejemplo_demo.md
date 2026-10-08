# datos de ejemplo para la demostración (Semana 4)

> **Todo inventado.** Ni DNI ni teléfonos ni coordenadas reales: son datos de
> demostración para teclear en la interfaz siguiendo el guion
> `docs/demo_sprint2.md` (decisión 13 de `docs/decisiones_semana4.md`).
> No se cargan con ningún comando: se crean **por la interfaz**.

## Requisito previo: ubicación

Cargar primero la ubicación de ejemplo (la usan las comunidades de abajo):

```
python manage.py cargar_ubicacion --archivo datos/ejemplo_ubicaciones.csv
```

## Productores (alta con la cuenta `admin`)

| Apellidos | Nombres | DNI (inventado) | Teléfono | Comunidad | Referencia | Estado |
|-----------|---------|-----------------|----------|-----------|------------|--------|
| Mamani Quispe | Juan Carlos | 44556677 | 951234567 | Comunidad Demo N1-1 | Al costado de la escuela | ACTIVO |
| Flores Huanca | Rosa Elena | 55667788 | 952345678 | Comunidad Demo S1-1 | Camino al mercado | ACTIVO |
| Condori Ticona | Luis Alberto | 66778899 | — | Comunidad Demo N2-1 | Junto al pozo | ACTIVO |
| Choque Ramos | María Elena | 77889900 | 953456789 | Comunidad Demo N1-2 | — | INACTIVO (se desactiva al final del guion) |

## Parcelas (alta con la cuenta `admin` o `tecnico`)

Coordenadas **inventadas**: no corresponden a ningún terreno real.

| Código | Productor | Superficie | Altitud | Latitud | Longitud | Suelo | Pendiente | Agua | Riego | Estado |
|--------|-----------|------------|---------|---------|----------|-------|-----------|------|-------|--------|
| P-001 (auto) | Mamani Quispe | 2.00 ha | 3850 | -15.123456 | -70.987654 | FRANCO | SUAVE | MEDIA | GOTEO | ACTIVA |
| P-002 (auto) | Mamani Quispe | 1.50 ha | 3862 | *(sin coordenadas — ejemplo de «las dos o ninguna»)* | | ARCILLOSO | MODERADA | ESCASA | GRAVEDAD | ACTIVA |
| P-003 (auto) | Flores Huanca | 3.20 ha | 3910 | -15.234567 | -70.876543 | ARENOSO | PLANA | ABUNDANTE | ASPERSION | ACTIVA |
| P-004 (auto) | Condori Ticona | 0.80 ha | 4010 | — | | OTRO | FUERTE | ESCASA | SECANO | INACTIVA (se desactiva en el guion) |

Notas del guion:

- El **código `P-00N` no se teclea**: lo genera la base de datos.
- Altitud obligatoria (0-6500); superficie > 0 con 2 decimales.
- P-002 se da de alta **sin latitud ni longitud** para comprobar la regla
  «las dos coordenadas o ninguna».
- Para el productor **INACTIVO** (Choque) la interfaz debe **impedir** el alta
  de parcelas nuevas (decisión 1 de `decisiones_semana4.md`).

## Asignaciones (alta con la cuenta `admin`, pantalla de la ficha)

| Técnico (cuenta) | Productor | activo |
|------------------|-----------|--------|
| `tecnico` | Mamani Quispe | true |
| `tecnico` | Condori Ticona | true |

Con esto la demo cubre los tres casos del filtro:

- **Mamani / P-001, P-002** → el técnico los ve (asignado).
- **Flores / P-003** → el técnico **no** los ve → detalle responde **404**.
- **Choque (INACTIVO)** → conserva sus datos; si tiene parcela, es visible
  para admin/coordinador.

## Cuentas de la demo

| Cuenta | Rol | Qué permite ver en la demo |
|--------|-----|----------------------------|
| `admin` | Administrador | Todo: altas, edición, asignaciones, técnicos asignados en la ficha |
| `coordinador` | Coordinador | Solo lectura (incluye `tecnicos_asignados`), **sin** crear/editar |
| `tecnico` | Técnico de campo | Solo **sus** productores y parcelas; 404 en los ajenos; **no** recibe el campo `tecnicos_asignados`; 403 al entrar en asignaciones |

Credenciales: ver `.credenciales` (no está en el repositorio).
