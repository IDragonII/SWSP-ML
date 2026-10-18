# Matriz de reglas de calidad (HU-121 / HU-122) — Semana 14

Cruce de cada **RN-01…RN-16** de `requerimientos.tex` (v1.1, sección «Reglas
de negocio y validaciones») con los puntos donde la regla se impone de verdad:
**API** (validación de serializer/vista, con su mensaje), **BD** (CHECK,
índice o trigger del diseño en `DB_sql/`, con su nombre) y **prueba(s)** del
repositorio que las ejecutan.

Cómo leerla:

- ✅ = impuesta en API **y** en BD (doble red de seguridad).
- ⚠ API / ⚠ BD = impuesta solo en una capa (ver §4, huecos).
- **M236–M241** = pruebas de matriz de esta semana (`backend/sistema/tests_calidad.py`),
  que confirman que ambas redes siguen vivas; **las pruebas pormenorizadas de
  cada semana** siguen siendo la especificación ejecutable de cada caso.
- Todas las pruebas de esta matriz pasan en la suite completa: **262/262 OK**
  (recuento vigente desde la Semana 15; las 6 pruebas M236–M241 siguen
  incluidas y en verde).

---

## 1. Matriz RN-01 … RN-16

| Regla | API (validación y mensaje clave) | BD (restricción) | Pruebas |
|---|---|---|---|
| **RN-01** Superficie de parcela, sembrada y cosechada > 0 | Parcela: `productores/serializers.py:658` «La superficie debe ser mayor que 0.» · Sembrada: `campanias/serializers.py:499` · Cosechada: `produccion/serializers.py:256` | CHECK `superficie_ha > 0` en `parcelas` (`01_tablas.sql:217`, `ck_parcelas_superficie`); `ck_campania_superficie` (`:243`); `ck_produccion_superficie` (`:360`) | ✅ **M236**, `test_39`, `test_71`, `test_106` |
| **RN-02** Sembrada ≤ parcela; cosechada ≤ sembrada | «no puede superar la superficie de la parcela (X ha)» `campanias/serializers.py:590` · «no puede superar la sembrada (X ha)» `produccion/serializers.py:354` | Trigger `fn_validar_campania` (`02_reglas_y_vista.sql:106`) y `fn_validar_produccion` (`:297`) con los dos valores en el mensaje | ✅ **M236**, `test_71`, `test_84` (SQL directo), `test_106` (`_sql_debe_fallar`) |
| **RN-03** Producción total ≥ 0 | «La cantidad producida no puede ser negativa.» `produccion/serializers.py:263` | CHECK `cantidad_producida >= 0` y `produccion_kg >= 0` (`01:361/363`) | ✅ `test_103`, `test_106`; 0 kg con marca en **M240**, `test_107` |
| **RN-04** Precipitación ≥ 0; humedad 0–100 % | «La precipitación no puede ser negativa.» · «La humedad debe estar entre 0 y 100 %.» `seguimiento/serializers.py:1141-1153` | CHECK `ck_clima_precipitacion` y `ck_clima_humedad` (`01:340-341`) | ✅ **M239**, `test_140`, `test_151` (ORM → DatabaseError) |
| **RN-05** Temperatura −30…45 °C y mín ≤ máx | «entre -30 y 45 °C» (`seguimiento/serializers.py:1120-1139`), «La temperatura mínima no puede ser mayor que la máxima» (`:1241`), «promedio debe estar entre la mínima y la máxima» (`:1250`) | CHECKs de rango (`01:337-339`) + CONSTRAINT `ck_clima_temp` (`01:350`) | ✅ **M239**, `test_139`, `test_140`, `test_151` |
| **RN-06** Latitud −90…90; longitud −180…180 | «La latitud/longitud debe estar entre…» y «Indica latitud y longitud, o déjalas las dos vacías.» `productores/serializers.py:670-697` | CHECKs de rango (`01:219-220`) + `ck_parcela_coordenadas` «las dos o ninguna» (`01:230`) | ✅ **M239**, `test_39` (rangos y dos-o-ninguna) |
| **RN-07** Cosecha ≥ fecha de siembra | «no tiene siembra registrada: registra la actividad de siembra…» `produccion/serializers.py:225` · «La fecha de cosecha no puede ser anterior a la fecha de siembra (X)» (`:334`) · «…no anterior al inicio de la campaña» (`:343`) | Trigger `fn_validar_produccion`: «La fecha de cosecha (%) es anterior a la fecha de siembra (%)» (`02:301`) | ✅ **M237**, `test_108` |
| **RN-08** Toda actividad dentro del período de la campaña | «La fecha X está fuera del período de la campaña (a b)» (actividades `seguimiento/serializers.py:448`, usos `:799`, incidencias `:1743`, etapas `:2025`) | Trigger `fn_validar_fecha_campania` (`02:139`) disparado por `trg_actividades_fecha`, `trg_uso_recursos_fecha`, `trg_incidencias_fecha`, `trg_seguimiento_fecha` (`02:162-169`) | ✅ **M237**, `test_88`, `test_126`, `test_157`, `test_176` |
| **RN-09** No hay cosecha sin campaña activa | `validate_campania` solo admite `EN_PRODUCCION`/`COSECHADA`: «La campaña está {estado} y no admite nuevos registros.» `produccion/serializers.py:217` | `fn_validar_produccion`: «No se puede registrar la cosecha: la campaña no está activa (estado %)» (`02:294`) | ✅ **M237**, `test_109` (API y SQL directo), `test_115` |
| **RN-10** Una campaña activa por parcela; un solo cultivo por campaña | «Ya existe una campaña de {cultivo} en esta parcela para el período {periodo} (id N)» y «Ya existe una campaña activa en esta parcela (id N, período, cultivo)» `campanias/serializers.py:632-663` (y la vista lo repite si la base rechaza: `views.py:252-290`) | Índice único parcial `uq_campania_activa_por_parcela` (`01:478`, `WHERE estado IN ('PLANIFICADA','EN_PRODUCCION','COSECHADA')`) y `uq_campania_parcela_periodo` (`01:483`, excluye CANCELADA) | ✅ **M238**, `test_72`, `test_73`, `test_84` |
| **RN-11** DNI único y 8 dígitos | «El DNI debe tener exactamente 8 dígitos numéricos.» y «Ya existe un productor con ese DNI.» `productores/serializers.py:288-324` | `dni CHAR(8) NOT NULL UNIQUE CHECK (dni ~ '^[0-9]{8}$')` (`01:171`, `ck_productores_dni`) | ✅ **M238**, `test_23`, `test_24` |
| **RN-12** Superficie afectada de la incidencia ≤ superficie (sembrada) | «La superficie afectada (X ha) supera la sembrada (Y ha).» y «…no puede ser negativa» `seguimiento/serializers.py:1664-1726` | CHECK `ck_incidencia_superficie >= 0` (`01:322`) + trigger `fn_validar_incidencia` contra la superficie **sembrada** de la campaña (`02:197`) | ✅ **M236**, `test_159`, `test_172` |
| **RN-13** Cerrar solo con producción registrada | «Solo se puede cerrar una campaña cosechada.», «…no tiene producción registrada.» y «…la producción requiere revisión pendiente. Revísala antes de cerrar.» `campanias/views.py:371-403` | `fn_validar_campania` al pasar a CERRADA: «…no tiene producción registrada» (`02:125`) | ✅ **M240**, `test_115` |
| **RN-14** Rendimiento = kg/ha, calculado por el sistema | `produccion_kg` y `rendimiento_kg_ha` son solo lectura (`produccion/serializers.py:109-118/201-212`); el cliente no los escribe | Trigger `fn_validar_produccion` recalcula siempre: `round(kg / superficie, 2)` (`02:313`) — un UPDATE crudo también lo recalcula | ✅ **M240** (recalculo por SQL directo), `test_103`, `test_104`, `test_111` |
| **RN-15** Rendimiento atípico solo con marca de revisión; el administrador decide la inclusión | El cliente no puede forzar `requiere_revision`; acción `revisar` con `nota` e `incluir_en_entrenamiento` obligatorios (`produccion/views.py:239-283`) | `fn_validar_produccion` lee `parametros_sistema` (`rendimiento_min/max_plausible` = 100/5000) y marca «Rendimiento atípico: X kg/ha» (`02:316-331`) | ✅ **M240** (0 kg), `test_107`, `test_112`, `test_113` |
| **RN-16** Productores, parcelas y campañas con historial no se eliminan; se desactivan | **Ningún viewset expone DELETE** (405 en todas las rutas); los estados INACTIVA/CANCELADA/CERRADA son la vía de baja | `ON DELETE RESTRICT/CASCADE` en las FK; la auditoria además es inmutable (`02:364`) | ✅ **M241** (barrido de todas las rutas, lista de excepciones vacía), `test_41`, `test_64`, `test_102`, `test_148`, `test_163`, `test_181`, `test_196`, `test_207/208` |

### Notas de fidelidad entre el texto del documento y la implementación

1. **RN-10** («un solo cultivo por campaña»): en los datos es imposible
   tener dos cultivos en la misma fila de campaña; lo que el sistema
   realmente garantiza es **un cultivo por parcela y período** y **una
   campaña activa por parcela** (`uq_campania_parcela_periodo` +
   `uq_campania_activa_por_parcela`). La red del documento se cumple y la
   de la red de seguridad es más precisa.
2. **RN-12** («no puede superar la superficie de la parcela»): la
   implementación es **más estricta** — compara contra la superficie
   *sembrada* de la campaña, que a su vez nunca supera la de la parcela
   (RN-02), así que la regla del documento se cumple siempre.
3. **RN-06** en el documento fija los rangos; además el sistema exige
   «latitud y longitud, las dos o ninguna» (`ck_parcela_coordenadas`),
   que es una precisión del diseño, no una contradicción.

---

## 2. Reglas implementadas que conviene incorporar al documento (agregados)

Están vivas en el sistema y conviene proponerlas en el capítulo de
requisitos (o como notas de diseño) para que la trazabilidad sea completa:

| Regla | Imposición | Prueba |
|---|---|---|
| Sin fechas futuras (hora de Lima) en actividades, usos, incidencias, etapas y clima | ⚠ API (`seguimiento/serializers.py:342/697/1656/1928`) — la BD no las rechaza | `test_89`, `test_141`, `test_157`, `test_185` |
| Una campaña **CERRADA/CANCELADA** no admite ningún registro nuevo | ✅ API + BD (`fn_validar_fecha_campania`, `02:152`) | **M237**, `test_90`, `test_124`, `test_126` |
| La revisión pendiente bloquea el cierre de campaña | ⚠ API (`campanias/views.py:394`) | **M240**, `test_115` |
| La campaña cerrada no admite cambios en su producción | ⚠ API (`produccion/serializers.py:302`) | `test_115` |
| Un solo registro de clima por parcela y día | ✅ API + `uq_clima_parcela_fecha` (`01:349`) | `test_143` |
| Una etapa por campaña + cronología + etapa correspondiente al cultivo | ✅ API + `uq_seguimiento_etapa` (`01:272`) + `fn_validar_etapa` (`02:172`) | `test_173`–`test_179` |
| La unidad de un uso de recurso debe ser compatible con el recurso | ✅ API + `fn_uso_recurso` (`02:213`) | `test_123` |
| La variedad debe pertenecer al cultivo elegido | ✅ API + FK compuesta `fk_campania_variedad_cultivo` (`01:252`) | `test_68` |
| Anulaciones con motivo obligatorio (actividades, usos, incidencias) | ✅ API + CHECK (`01:293/312/330`) | `test_96`, `test_128`, `test_162` |
| La densidad de siembra va con valor y unidad, y solo en siembras | ✅ API + `ck_actividad_densidad` (`01:292`) | `test_91`, `test_92` |
| Coherencia del clima: promedio entre mínima y máxima, helada coherente | ✅ API + CHECKs | **M239**, `test_139`, `test_140` |

---

## 3. Huecos de cobertura (una sola capa)

Para transparencia del capítulo 4; no son errores, son decisiones de
diseño, pero conviene declararlas:

| Regla | Solo API (la BD no la defiende) | Impacto |
|---|---|---|
| Fecha futura | `fn_validar_fecha_campania` valida estado y período, no el «hoy» | Un INSERT crudo con fecha futura entraría; solo la API la rechaza |
| Revisión pendiente al cerrar | `fn_validar_campania` solo exige «producción registrada» | Un UPDATE crudo de estado podría cerrar con revisión pendiente |
| Requisitos de `revisar` (nota + incluir_en_entrenamiento) | Regla de interfaz | Un UPDATE crudo podría quitar la marca sin nota |
| Un cultivo por parcela y período (el texto habla de «por campaña») | Índices cubren parcela+período; el texto es trivialmente cierto | Ninguno: ambas capas coinciden |
| Fechas de cosecha futuras | Admitidas por diseño (pregunta H pendiente del responsable) | Declarado en `decisiones_semana*.md` |

No hay reglas del documento **sin** implementación alguna: las 16 tienen
al menos una red viva y una prueba que la dispara.

- **Alertas (Semana 15, adyacente a la RN-16/supuesto de 30 días):** su
  lógica — generación por incidencia severa, cierre automático al cambiar
  de estado, gracia tras la atención manual y barrido diario — vive **solo
  en la aplicación** (13 ganchos `transaction.on_commit` + comando
  `evaluar_alertas`); la tabla `alertas` **no tiene triggers** por decisión
  (`decisiones_semana15.md` §1.1) y su red en BD se limita a CHECKs e
  índices únicos. Si el proceso no corre (p. ej. sin workers), la única
  defensa es el aviso de atraso de 36 h de `/alertas/evaluacion/`.

---

## 4. Controles de completitud del modelo ML (HU-122)

- La vista `vw_dataset_entrenamiento` (`02_reglas_y_vista.sql:388`) solo
  devuelve campañas **CERRADA** con producción (`:464`) y
  `incluir_en_entrenamiento = TRUE` — la decisión del administrador de la
  RN-15 es el filtro de entrada al entrenamiento.
- `requiere_revision` queda en `FALSE` obligatoriamente: ninguna fila sin
  revisar entra al dataset (se revisa en `test_113` y en el bloque `inc_c`
  de `seguimiento/tests.py`).
- Los umbrales `rendimiento_min_plausible` / `rendimiento_max_plausible`
  de `parametros_sistema` (semilla: 100 / 5000 kg/ha) son los que marcan
  lo atípico; cambiarlos por la API cambia el marcado sin tocar código.
- Cobertura de la matriz en pruebas: **M236** (superficies), **M237**
  (fechas y estados), **M238** (unicidades), **M239** (rangos),
  **M240** (rendimiento/marcas/cierre), **M241** (borrado físico: ninguna
  ruta DELETE).

---

*Semana 14 (4–10 ene). Suite completa: **241/241 OK** (824 s).*

*Actualizado en la Semana 15 (11–17 ene): la matriz RN-01…RN-16 no cambia;
la suite completa pasó a **262/262** con las 21 pruebas de alertas
(242–262) y se documentó el hueco de cobertura de las alertas (§3).*
