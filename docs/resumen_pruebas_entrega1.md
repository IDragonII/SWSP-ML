# Resumen de pruebas — Entrega 1 (Semana 19)

La Entrega 1 añade **8 pruebas** (318–325) a la suite existente (cerraba
Semana 18 con 317 → total **325**). Todas deben pasar en verde para la
entrega.

| Nº | Nombre | Qué verifica | Estado |
|----|--------|--------------|--------|
| **318** | `RecorridoCompletoTests.test_318_recorrido_completo_tres_roles` | Ciclo E2E de una campaña con los 3 roles (Administrador, Coordinador, Técnico de campo): alta productor/parcela, campaña, actividades, clima, incidencia, producción, cierre, predicción, reporte. | ✅ |
| **319** | `MatrizRutasTests.test_319_matriz_rutas_por_rol` | La matriz generada por `matriz_rutas.py` (107 rutas × 5 métodos × 3 roles) coincide con las respuestas reales del servidor; no hay rutas sin documentar; `RUTAS_EXENTAS` = `AllowAny`. | ✅ |
| **320** | `SeguridadTests.test_320_anonimo_sin_acceso` | Usuario anónimo recibe **401** en todas las 107 rutas API × 5 métodos (salvo `/auth/login/`, `/auth/refresh/`, `/auth/logout/` que son `AllowAny`). Nunca 2xx. | ✅ |
| **321** | `SeguridadTests.test_321_check_deploy_cero_avisos` | `manage.py check --deploy` con `DEBUG=False`, `PRODUCCION=1`, `SECRET_KEY` ≥50 chars, `ADMIN_URL` no default → **0 avisos**. ADMIN_URL fluye al URLconf. | ✅ |
| **322** | `SeguridadTests.test_322_error_500_sin_trazas` | Excepción interna en vista (`DEBUG=False`) → 500 **sin trazas** en la respuesta (body sin `TRAZA_SECRETA_322`). | ✅ |
| **323** | `SeguridadTests.test_323_registros_limpios` | Logger `sigpa.seguridad` (handlers `consola_seguridad`) no registra contraseñas, tokens JWT (`eyJ`), ni `SECRET_KEY`; sí registra `login_correcto`. | ✅ |
| **324** | `RendimientoTests.test_324_rendimiento_con_volumen_reducido` | Siembra volumen reducido (30 prod, 60 parc, 72 camp, 1200 act, 20 días clima) → mide latencias de 5 endpoints; todos **< 2 s**. | ✅ |
| **325** | `RespaldoTests.test_325_migraciones_desde_cero_respaldo_y_restauracion` | Migraciones desde cero crean **28 tablas de dominio** + **25 triggers**. Volcado pg_dump → restauración en BD temporal → segundo volcado coincide **byte a byte** (tras canonizar `\restrict` y forma `= ANY` de CHECKs). | ✅ |

---

## Ejecución completa

```bash
cd backend
python manage.py test sistema.tests_entrega1 --noinput
# 325 tests, ~8 min (incluye siembra de volumen en test 324)
```

---

## Métricas de la suite Entrega 1

- **Total pruebas**: 325 (317 previas + 8 nuevas)
- **Tiempo total**: ~8 min (CI local, SSD, 8 GB RAM)
- **Cobertura**: recorrido E2E (3 roles), matriz de rutas, seguridad (deploy, errores, logs), rendimiento, respaldo/restauración
- **Dependencias**: `cargar_ubicacion`, `cargar_catalogos` previos; BD limpia por prueba (Django `TestCase`)

---

## Referencias

- Código: `backend/sistema/tests_entrega1.py` (clases `RecorridoCompletoTests`, `MatrizRutasTests`, `SeguridadTests`, `RendimientoTests`, `RespaldoTests`)
- Matriz de rutas: `docs/matriz_rutas_por_rol.md` (generada por `manage.py matriz_rutas`)
- Seguridad: `docs/seguridad_entrega1.md`
- Rendimiento: `docs/rendimiento_entrega1.md`
- Respaldo: `backend/sistema/respaldo.py`, `backend/sistema/management/commands/respaldo_bd.py`