import test from 'node:test';
import assert from 'node:assert/strict';
import { config, MODEL_NAME } from '../src/config.mjs';

test('llama.cpp configuration is CPU-only and uses the requested GGUF', () => {
  assert.equal(MODEL_NAME, 'Qwen3.5-2B-Q4_K_M.gguf');
  assert.equal(config.context, 4096);
  assert.equal(config.gpuLayers, 0);
  assert.match(config.model, /Qwen3\.5-2B-Q4_K_M\.gguf$/);
});
