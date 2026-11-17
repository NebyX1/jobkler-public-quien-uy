# Comparación Qwen3.5 0.8B vs 2B

Fecha: 2026-09-20. Equipo: AMD Ryzen 5 5500, 12 procesadores lógicos, 16 GB RAM. Runtime llama.cpp b11052, CPU-only (`-ngl 0`), contexto 4096, batch 512, ubatch 512, un slot y `--no-cache-prompt`.

El benchmark histórico del 0.8B está preservado en [benchmark-qwen35-08b-final.md](benchmark-qwen35-08b-final.md). Ambos modelos fueron medidos realmente en este equipo; no se infieren resultados.

## Rendimiento

| Métrica | Qwen3.5-0.8B Q4_K_M | Qwen3.5-2B Q4_K_M |
|---|---:|---:|
| Tamaño GGUF | 527.502.816 bytes | 1.270.808.032 bytes |
| Mejor threads de generación | 6 | 4 |
| llama-bench prompt processing pp512 | 370,32 tok/s (12 hilos) | 171,04 tok/s (12 hilos) |
| llama-bench generation tg128 | 56,65 tok/s (6 hilos) | 26,82 tok/s (4 hilos) |
| TTFT E2E Flask promedio, 3 prompts | 226,0 ms | 523,4 ms |
| Tiempo total E2E promedio, 3 prompts | 2.807,1 ms | 6.353,4 ms |
| RSS después de la batería de prompts | 0,94–0,98 GB | 1,95–2,03 GB |
| RAM estable en 10 requests | 1.147,6 MB | 2.494,6 MB |

El `llama-bench` de prompt processing y generación se muestra con el mejor valor observado en cada métrica; los threads óptimos pueden ser distintos.

### Penalización de velocidad

Con la fórmula solicitada:

```text
generation_speed_change = 26,819616 / 56,651221 = 0,4734
```

El 2B conserva el **47,34%** de la velocidad de generación del 0.8B, con una penalización de **52,66%**. Para prompt processing, el mejor 2B conserva 171,038133 / 370,320276 = **46,19%**, una penalización de **53,81%**.

## Calidad y capacidades

| Prueba | Qwen3.5-0.8B | Qwen3.5-2B |
|---|---|---|
| Memoria conversacional “frutilla” | PASS: recuperó “La frutilla.” | PASS: recuperó “Frutilla” |
| JSON Lucía, 29, Minas | PASS, JSON parseable | PASS, JSON parseable |
| Clasificación esperada `tributos` | FAIL: respondió `otra` | FAIL: respondió `obras` |
| Tool routing — 3 casos | PASS: JSON válido, herramientas correctas | PASS: JSON válido, herramientas y argumentos correctos |
| Streaming | PASS | PASS |
| 10 generaciones consecutivas | PASS, sin crash; +38,5 MB iniciales y plateau | PASS, sin crash; +38,5 MB iniciales y plateau |

El 2B dio argumentos concretos en tool routing (`Villa Serrana`, `345 * 29`, ID `583`) mientras el 0.8B seleccionó correctamente las herramientas pero dejó argumentos vacíos. En estas pruebas acotadas no mejoró la clasificación municipal: ambos fallaron la categoría exacta.

## Prompts comparables E2E

Los tres prompts fueron enviados desde un cliente real a Flask `/api/chat/stream`, y TTFT se midió desde el inicio de la petición hasta el primer delta SSE.

| Test | 0.8B TTFT / total / chars | 2B TTFT / total / chars |
|---:|---:|---:|
| Base relacional | 223,1 / 2709,7 ms / 581 | 626,4 / 7238,7 ms / 608 |
| SQL vs NoSQL | 242,7 / 2690,2 ms / 506 | 489,5 / 6136,5 ms / 559 |
| Búsqueda de texto | 212,2 / 3021,3 ms / 533 | 454,3 / 5684,8 ms / 548 |

## Conclusión

Para este equipo y este proyecto, el 2B mejora la calidad observable en tool routing y conserva memoria/JSON, pero es aproximadamente 2,1× más lento en TTFT E2E, 2,3× más lento en tiempo total medio y usa aproximadamente 2,2× la RAM estable. La ganancia de capacidad **no justifica la pérdida de velocidad para el chat interactivo actual**, salvo que se prioricen respuestas más estructuradas y argumentos de herramientas por encima de la latencia. La configuración final queda en 4 threads, el mejor punto medido para generación y tiempo total del 2B.
