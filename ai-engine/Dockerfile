FROM ghcr.io/ggml-org/llama.cpp:server-b10524
COPY docker-start.sh /app/docker-start.sh
RUN chmod +x /app/docker-start.sh
ENTRYPOINT ["/app/docker-start.sh"]
EXPOSE 8081
HEALTHCHECK --interval=10s --timeout=3s --start-period=120s --retries=3 CMD curl -fsS "http://127.0.0.1:${LLM_PORT:-8081}/health" >/dev/null || exit 1
