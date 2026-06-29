# Homework — Trip Planning Assistant

Terminal chat app using **OpenRouter** (`google/gemini-3.5-flash`) instead of local vLLM — suitable for macOS.

## Components

| File | Purpose |
|------|---------|
| `openweather_mcp.py` | MCP server: daily forecast (16 days) + monthly weather statistics |
| `chat.py` | Terminal chat with MCP tools, system prompt, and Guardrails |
| `mcp_manager.py` | Connects to local OpenWeather MCP + remote Tavily MCP |
| `docker-compose.yml` | Runs the full stack |

## API keys

Copy `.env.example` to the **project root** as `.env`:

```bash
cp homework/.env.example .env
```

Required keys:

- `OPENROUTER_API_KEY` — [openrouter.ai](https://openrouter.ai)
- `OPENWEATHERMAP_API_KEY` — [openweathermap.org](https://openweathermap.org/api)
- `TAVILY_API_KEY` — [tavily.com](https://tavily.com) (optional; keyless Tavily MCP works for basic search)

Guardrails hub validators (install once from project root):

```bash
guardrails configure
guardrails hub install hub://guardrails/detect_jailbreak
guardrails hub install hub://tryolabs/restricttotopic
```

## Local run (macOS)

Terminal 1 — OpenWeather MCP:

```bash
uv run python homework/openweather_mcp.py
```

Terminal 2 — chat:

```bash
uv run python -m homework.chat
```

## Docker Compose

From `homework/` directory (with `.env` in project root):

```bash
cd homework
docker compose up --build
```

Attach to the chat container:

```bash
docker compose run --rm chat
```

## Security

- **System prompt** — refuses non–trip-planning questions
- **DetectJailbreak** — blocks jailbreak attempts on user input (local models, `use_local=True`)
- **RestrictToTopic** — output must stay on travel/trip topics

## Screenshots for submission

Save terminal conversation screenshots in `homework/screenshots/`, e.g.:

1. Normal trip planning (weather + attractions)
2. Off-topic question refused
3. Long-range trip using monthly weather stats
