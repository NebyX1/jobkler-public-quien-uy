const url = process.env.LLM_URL || 'http://127.0.0.1:8081';
const prompt = process.argv.slice(2).join(' ') || 'Explicá en una frase por qué los zorros se adaptan a distintos ambientes.';
if (!process.env.LLM_API_KEY) throw new Error('Configurá LLM_API_KEY en el entorno para ejecutar el benchmark.');
const body = { model: 'Qwen3.5-2B-Q4_K_M.gguf', messages: [{ role: 'user', content: prompt }], stream: true, max_tokens: 128, temperature: 0.2, top_p: 0.9, chat_template_kwargs: { enable_thinking: false } };
const started = performance.now();
const response = await fetch(`${url}/v1/chat/completions`, { method: 'POST', headers: { 'content-type': 'application/json', Authorization: `Bearer ${process.env.LLM_API_KEY}` }, body: JSON.stringify(body) });
if (!response.ok) throw new Error(`llama.cpp returned ${response.status}: ${await response.text()}`);
const reader = response.body.getReader();
const decoder = new TextDecoder();
let buffer = '', answer = '', firstToken = null, chunks = 0;
for (;;) {
  const { done, value } = await reader.read();
  if (done) break;
  buffer += decoder.decode(value, { stream: true });
  const blocks = buffer.split('\n\n');
  buffer = blocks.pop() || '';
  for (const block of blocks) {
    const line = block.split('\n').find(item => item.startsWith('data:'));
    if (!line || line.slice(5).trim() === '[DONE]') continue;
    const item = JSON.parse(line.slice(5).trim());
    const delta = item.choices?.[0]?.delta?.content || '';
    if (delta) { if (firstToken === null) firstToken = performance.now(); answer += delta; chunks += 1; }
  }
}
const finished = performance.now();
console.log(JSON.stringify({ prompt, answer, chunks, ttft_ms: firstToken === null ? null : firstToken - started, total_ms: finished - started, chars: answer.length }));
