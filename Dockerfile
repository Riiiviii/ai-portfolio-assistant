FROM python:3.12-slim-bookworm
COPY --from=docker.io/astral/uv:0.11.6 /uv /uvx /bin/
WORKDIR /app

COPY pyproject.toml ./
COPY uv.lock ./
RUN uv sync --frozen --no-install-project

COPY . .
RUN uv sync --frozen
EXPOSE 8000

RUN chmod +x ./entrypoint.sh
RUN useradd -m ai-chatbot
RUN mkdir -p /data && chown ai-chatbot:ai-chatbot /data
USER ai-chatbot

CMD ["./entrypoint.sh"]
