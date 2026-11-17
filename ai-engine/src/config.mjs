import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');

export const config = Object.freeze({
  root,
  host: process.env.LLM_HOST || '127.0.0.1',
  port: Number(process.env.LLM_PORT || 8081),
  model: path.resolve(root, process.env.LLM_MODEL || 'models/Qwen3.5-2B-Q4_K_M.gguf'),
  context: Number(process.env.LLM_CONTEXT || 4096),
  threads: Number(process.env.LLM_THREADS || 4),
  gpuLayers: Number(process.env.LLM_GPU_LAYERS || 0),
});

export const MODEL_NAME = 'Qwen3.5-2B-Q4_K_M.gguf';
