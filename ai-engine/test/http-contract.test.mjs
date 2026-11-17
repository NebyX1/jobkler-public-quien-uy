import test from 'node:test';
import assert from 'node:assert/strict';

test('llama.cpp exposes the OpenAI-compatible endpoint used by Flask', async () => {
  if (process.env.RUN_LLM_TESTS !== '1') return;
  const url = process.env.LLM_URL || 'http://127.0.0.1:8081';
  const denied = await fetch(`${url}/v1/models`);
  assert.equal(denied.status, 401);
  assert.ok(process.env.LLM_API_KEY, 'Provide LLM_API_KEY for the live contract test');
  const allowed = await fetch(`${url}/v1/models`, { headers: { Authorization: `Bearer ${process.env.LLM_API_KEY}` } });
  assert.equal(allowed.status, 200);
  assert.ok((await allowed.json()).data.length > 0);
});
