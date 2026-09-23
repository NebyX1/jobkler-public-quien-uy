import asyncio
import json
import threading
import time

import httpx
from pydantic import ValidationError

from .contracts import SearchIntent
from .text import contains_phrase

_INFERENCE_SLOT = threading.BoundedSemaphore(1)


class InferenceUnavailable(RuntimeError):
    pass


class InferenceBusy(RuntimeError):
    pass


SYSTEM_PROMPT = """Interpretá una consulta de búsqueda de servicios locales en Uruguay.
Respondé únicamente el objeto JSON solicitado. El esquema limita las claves y longitudes.
search_text describe solo el servicio, sin la ubicación. profession_text se completa solo si
el usuario pidió explícitamente un oficio. action_text y object_text preservan palabras de la
consulta. location_text preserva una ubicación escrita por el usuario; nunca inventes nombres,
IDs ni coordenadas. related_terms son sinónimos de búsqueda acotados, no equivalencias de
prestaciones. No infieras que todo sanitario repara termofones. No cambies instalar por reparar.
Usá status=ambiguous si hay dos interpretaciones igualmente probables que cambian el servicio;
unsupported solo si la solicitud no busca un proveedor/servicio. Una consulta sin lugar es válida.

Ejemplos:
Entrada: "¿Hay alguien que arregle termofones en Minas?"
Salida: {"status":"ok","search_text":"arreglar termofones","profession_text":null,"action_text":"arregle","object_text":"termofones","location_text":"Minas","related_terms":["calefón"],"excluded_terms":[]}
Entrada: "Necesito un carpintero en Minas"
Salida: {"status":"ok","search_text":"carpintero","profession_text":"carpintero","action_text":null,"object_text":null,"location_text":"Minas","related_terms":[],"excluded_terms":[]}
Entrada: "Necesito reparar una puerta de madera"
Salida: {"status":"ok","search_text":"reparar puerta de madera","profession_text":null,"action_text":"reparar","object_text":"puerta de madera","location_text":null,"related_terms":[],"excluded_terms":[]}
Entrada: "Busco alguien en Minas que instale o repare un calefón"
Salida: {"status":"ambiguous","search_text":"instalar o reparar calefón","profession_text":null,"action_text":null,"object_text":"calefón","location_text":"Minas","related_terms":[],"excluded_terms":[]}"""


def _intent_schema():
    schema = SearchIntent.model_json_schema()
    schema.pop("title", None)
    schema.pop("$schema", None)
    return schema


async def _request_intent(query, *, base_url, model, timeout_seconds, connect_timeout_seconds):
    deadline = time.monotonic() + timeout_seconds
    remaining = max(0.05, deadline - time.monotonic())
    timeout = httpx.Timeout(
        timeout=remaining,
        connect=min(connect_timeout_seconds, remaining),
        read=remaining,
        write=remaining,
        pool=min(connect_timeout_seconds, remaining),
    )
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps({"query": query}, ensure_ascii=False)},
        ],
        "response_format": {"type": "json_schema", "schema": _intent_schema()},
        "chat_template_kwargs": {"enable_thinking": False},
        "temperature": 0.1,
        "top_p": 0.9,
        "max_tokens": 256,
        "stream": False,
    }
    async with httpx.AsyncClient(timeout=timeout, trust_env=False) as client:
        response = await asyncio.wait_for(
            client.post(f"{base_url.rstrip('/')}/chat/completions", json=body),
            timeout=remaining,
        )
    response.raise_for_status()
    data = response.json()
    choice = (data.get("choices") or [None])[0]
    if not isinstance(choice, dict):
        raise InferenceUnavailable("El motor local no devolvió una opción JSON.")
    if choice.get("finish_reason") == "length":
        raise InferenceUnavailable("La salida de interpretación quedó truncada.")
    content = (choice.get("message") or {}).get("content")
    if not isinstance(content, str) or not content.strip():
        raise InferenceUnavailable("El motor local no devolvió contenido JSON.")
    try:
        intent = SearchIntent.model_validate_json(content)
    except ValidationError as exc:
        raise InferenceUnavailable("La interpretación no respetó el esquema validado.") from exc

    # The model may normalize conjugations, but must not invent a place or an explicit job title.
    for field in ("profession_text", "location_text"):
        value = getattr(intent, field)
        if value and not contains_phrase(query, value):
            raise InferenceUnavailable(f"La interpretación cambió el campo {field}.")
    if intent.status == "ok" and not intent.search_text:
        raise InferenceUnavailable("La interpretación no identificó qué servicio se busca.")
    return intent


def extract_intent(query, *, base_url, model, timeout_seconds=20, connect_timeout_seconds=2, queue_wait_seconds=0.15):
    if not _INFERENCE_SLOT.acquire(timeout=queue_wait_seconds):
        raise InferenceBusy("El motor local está atendiendo otra búsqueda.")
    try:
        return asyncio.run(_request_intent(
            query,
            base_url=base_url,
            model=model,
            timeout_seconds=timeout_seconds,
            connect_timeout_seconds=connect_timeout_seconds,
        ))
    except (httpx.HTTPError, asyncio.TimeoutError, ValueError, KeyError, TypeError) as exc:
        if isinstance(exc, InferenceUnavailable):
            raise
        raise InferenceUnavailable("No se pudo interpretar la búsqueda con Qwen local.") from exc
    finally:
        _INFERENCE_SLOT.release()
