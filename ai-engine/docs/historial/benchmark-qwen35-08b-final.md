# Benchmark final — Qwen3.5 0.8B GGUF Q4_K_M

Este documento preserva la última medición real del 0.8B antes de sustituirlo. Fecha: 2026-09-20. Host: AMD Ryzen 5 5500, 12 procesadores lógicos, 16 GB RAM. llama.cpp b11052, CPU-only, contexto 4096, 6 threads para la prueba end-to-end, `-np 1`, batch 512, ubatch 512, `--no-cache-prompt`, `--reasoning off`.

## llama-bench pp512 / tg128

Comando: `llama-bench -m llm/models/Qwen3.5-0.8B-Q4_K_M.gguf -p 512 -n 128 -b 512 -ub 512 -t 4,6,8,12 -ngl 0 -r 1 -o json`.

| Threads | Prompt processing | Generation |
|---:|---:|---:|
| 4 | 248,57 tok/s | 54,83 tok/s |
| 6 | 342,84 tok/s | 56,65 tok/s |
| 8 | 362,34 tok/s | 51,81 tok/s |
| 12 | 370,32 tok/s | 46,07 tok/s |

Mejor configuración de generación: 6 threads.

## Prompts comparables

Se enviaron los tres prompts definidos para la comparación, desde el cliente streaming real contra Flask y llama-server:

| Test | TTFT | Tiempo total | Longitud | RSS final | CPU proceso |
|---:|---:|---:|---:|---:|---:|
| 1 — base relacional | 204,5 ms | 2768,1 ms | 639 caracteres | 894,8 MB | 16,484 s |
| 2 — SQL vs NoSQL | 180,3 ms | 2652,5 ms | 518 caracteres | 935,5 MB | 16,094 s |
| 3 — búsqueda de texto | 213,1 ms | 2697,8 ms | 576 caracteres | 977,0 MB | 16,312 s |

## Pruebas de calidad

- Memoria conversacional con “frutilla”: PASS. Recuperó “La frutilla.”
- JSON Lucía/29/Minas: PASS y parseable.
- Clasificación esperada `tributos`: FAIL; respondió `otra`.
- Tool routing: PASS en los tres casos: `search_text`, `calculate` y `get_document`; las tres respuestas fueron JSON válido.

## Carga

Diez generaciones consecutivas reales: PASS, sin crash ni bloqueo. Con `--no-cache-prompt`, el RSS pasó de 1109,1 MB a 1147,6 MB y se estabilizó; crecimiento final observado: +38,5 MB.

Este archivo es histórico y se conserva para la comparación 0.8B vs 2B. El modelo físico 0.8B se elimina sólo después de verificar que este registro está guardado.
