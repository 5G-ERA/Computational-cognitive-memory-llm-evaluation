# Validador independiente — qué tienes que hacer

Guía rápida en castellano. El detalle técnico está en `SPEC.md` (en inglés, porque es el
documento que verá Renxi). Si algo se contradice, manda `SPEC.md`.

---

## Qué es esto y por qué importa

El protocolo de auditoría exige que **dos personas distintas programen la misma auditoría por
separado** y que las dos saquen exactamente los mismos resultados. Si coinciden, es que la
especificación está bien escrita y los números no dependen de quién los programó. Si no coinciden,
hemos encontrado un agujero en la especificación — que también es un resultado útil.

Yo ya he escrito una. Tú escribes la otra. Por eso este paquete **no** contiene mi código.

---

## La única regla que de verdad importa

**No abras** `audit_extension/scripts/`, `audit_extension/results/`,
`audit_extension/validation/` ni `PROPOSED_AMENDMENTS.md`.

Si miras cómo lo resolví yo, la prueba deja de valer y habremos perdido el tiempo los dos.

Si algo de este paquete te parece ambiguo o mal explicado: **eso es un hallazgo**. Apúntalo y
pregúntame. Una pregunta tuya vale más para el proyecto que un número que coincida porque
miraste.

Hay una segunda regla, distinta: tu programa **no puede leer los ficheros que contienen la
respuesta correcta**. Están listados en
`mappings/v0_5_1_qa1c_to_audit_schema.json`, apartado `ORACLE_QUARANTINE`. Los principales son
`scoring_records.jsonl`, todo lo que hay bajo `hidden/`, y dos CSV de contexto que llevan la
columna del oráculo. Ponle esa protección al programa desde el principio, no al final.

---

## Los pasos

### 1. Coloca el paquete

Descomprímelo en una carpeta **fuera** de `audit_extension/`. Por ejemplo
`~/validador_independiente/`.

### 2. Lee, en este orden

| # | fichero | para qué |
|---|---|---|
| 1 | `protocol/experiment1_audit_protocol_source.pdf` | La norma. Secciones 4 a 13, y la 17. |
| 2 | `contracts/error_ontology.yaml` | Los 40 códigos de error: gravedad, alcance y qué le hace cada uno al estado del caso. |
| 3 | `contracts/agreement_contract.json` | **Léelo antes de escribir código.** Fija las convenciones que si no te inventarías tú, y dice exactamente qué se compara y qué no. |
| 4 | `contracts/level1_io_contract.json` | La lista literal de comprobaciones del Nivel 1. |
| 5 | `contracts/m0_prospective_contract.json` y `contracts/b1_resolved_contract.json` | Lo mismo para el Nivel 2. |
| 6 | `DECISIONS_2026-08-22.json` | Las 18 decisiones de Renxi del 22 de agosto y en qué contrato aterrizó cada una. |

### 3. Qué tiene que hacer tu programa

Lee, de la release congelada:

- `prompts/model_calls_v0_5_1.jsonl` — lo que se le enseñó al modelo en cada llamada
- `public/response_schema.json` y `public/rule_vocabulary.json`
- `data_v0_5_1/historical_events.jsonl` y `data_v0_5_1/current_events.jsonl` — el registro de eventos
- `data_v0_5_1/rendering_map.csv` — **el único** mapa de contexto sin oráculo
- `data_v0_5_1/split_manifest.csv`

Y de una carpeta de ejecución (`bedrock_terra/out/dev_terra` o `.../dev_qwen3`):

- `responses_raw.jsonl`, `responses_parsed.jsonl`, `call_registry.jsonl`, `run_manifest.json`

Escribe **dos ficheros y nada más**:

- `audit_errors.jsonl` — una línea por hallazgo, con la forma de `schemas/audit_error.schema.json`
- `audit_case_summaries.jsonl` — una línea por (caso, nivel, lectura), con la forma de
  `schemas/audit_case_summary.schema.json`

Ni informes, ni CSV, ni intervalos de confianza. Eso no se compara.

### 4. Pruébate primero con las fixturas

`fixtures_blind/` tiene **15 casos completos y autocontenidos**: un registro de eventos pequeño,
un payload, una respuesta y una fila de manifiesto. Les he quitado las respuestas esperadas, así
que te examinan en vez de chivártelas. Cada una dice en `audit_level` qué nivel hay que correrle.

Saca las 15 antes de tocar los datos reales. Te va a ahorrar mucho tiempo.

### 5. Luego los dos runs de verdad

360 llamadas cada uno, 8 grupos de memoria. Si tu programa dice otra cosa que 360, algo falla en
cómo estás filtrando el split.

### 6. Comparar — solo al final

```bash
python3 ~/dca_v051/audit_extension/scripts/compare_implementations.py \
    --reference ~/dca_v051/audit_extension/results/dev_terra --candidate <lo_tuyo>/dev_terra \
    --reference ~/dca_v051/audit_extension/results/dev_qwen3 --candidate <lo_tuyo>/dev_qwen3 \
    --validator "Adrian Lendinez Ibanez, independent implementation" \
    --report ~/dca_v051/audit_extension/validation/implementation_agreement.json
```

Compara cuatro cosas: los códigos de error, si el caso es crítico, el estado del caso, y los
totales. Te nombra los casos donde discrepamos. **No** da por buena mi versión: si discrepamos,
decidimos entre los dos quién está mal.

Córrelo cuando hayas terminado del todo. Leer su salida a medio camino convierte tu programa en
una copia del mío.

---

## Dónde es probable que discrepemos

No son pistas — son los sitios donde el contrato está haciendo más trabajo, y donde una
discrepancia de verdad sería más informativa:

- cómo se pliegan las filas `BOTH` en las dos lecturas, y si un código inerte en esta release
  sigue apareciendo en la vista `LITERAL`;
- si una comprobación que encuentra tres identificadores malos emite una fila o tres;
- qué pasa cuando un registro se retira del payload: choca `E0_INPUT_TRUNCATED` con
  `E1_CITATION_NOT_VISIBLE`, y la precedencia de la sección 10 decide el estado;
- si `E4_REVIEW_DEFER_CONFLATED` puede saltar sin que salte también
  `E4_RULE_OUTCOME_INCONSISTENT`, dado que cada regla admite una sola reacción;
- `E5_VERSION_AMBIGUOUS` frente a `E5_PROSPECTIVE_REWRITE` cuando la relación prospectiva difiere
  y hay un sucesor declarado;
- si la exención `UNRESOLVED_BY_CONDITION_DESIGN` tapa solo `E3_CONSTITUTIVE_LINK_MISSING` o
  también las comprobaciones de pertenencia y visibilidad que vienen detrás.

Si tu lectura del contrato difiere de la mía en alguno de estos, **dímelo antes de comparar**. Esa
es la discrepancia que merece la pena tener.

---

## Si te atascas

Pregúntame lo que quieras sobre el protocolo, los contratos o los datos. Lo único que no te voy a
enseñar es cómo lo resolví yo. También te puedo montar el esqueleto — solo la carga de ficheros y
la escritura de la salida, sin nada de la lógica de comprobación — si prefieres saltarte la
fontanería. Dímelo y te lo hago.
