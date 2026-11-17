#!/bin/sh
set -eu
: "${LLM_API_KEY:?Set LLM_API_KEY to the same secret as the backend}"
if [ "${#LLM_API_KEY}" -lt 32 ]; then echo 'LLM_API_KEY must be at least 32 characters' >&2; exit 1; fi
export LLAMA_API_KEY="$LLM_API_KEY"
exec /app/llama-server \
    -m "${LLM_MODEL:-/models/Qwen3.5-2B-Q4_K_M.gguf}" \
    --alias "${LLM_MODEL_ALIAS:-Qwen3.5-2B-Q4_K_M.gguf}" \
    --host "${LLM_HOST:-0.0.0.0}" --port "${LLM_PORT:-8081}" \
    -c "${LLM_CONTEXT:-4096}" -np 1 \
    -t "${LLM_THREADS:-4}" -tb "${LLM_THREADS:-4}" \
    -ngl "${LLM_GPU_LAYERS:-0}" \
    --no-cache-prompt --reasoning off --metrics
