import asyncio
import json
import os
import sys
import torch
from dotenv import load_dotenv
from guardrails import Guard, OnFailAction
from guardrails.hub import DetectJailbreak, RestrictToTopic
from openai import OpenAI

from homework.mcp_manager import MCPManager  

load_dotenv()

LLM_MODEL = os.environ.get("LLM_MODEL", "google/gemini-3.5-flash")
LLM_BASE_URL = os.environ.get("LLM_BASE_URL", "https://openrouter.ai/api/v1")
OPENWEATHER_MCP_URL = os.environ.get("OPENWEATHER_MCP_URL", "http://localhost:8010/mcp")

SYSTEM_PROMPT = """You are a helpful trip planning assistant.

Your job is to help users plan trips: destinations, timing, weather, activities, packing, and travel logistics.

Rules:
- Only answer questions related to trip planning and travel.
- If the user asks about unrelated topics (coding, homework, politics, etc.), politely refuse and steer back to trip planning.
- Use tools when you need weather data or up-to-date travel information about places.
- For weather within 16 days, use get_daily_forecast.
- For trips farther than 16 days out, use get_monthly_weather_statistics.
- Use Tavily search tools to find attractions, events, visa rules, or practical travel tips.
- Be concise but helpful. Ask clarifying questions when the trip details are unclear.
"""

TRIP_TOPICS = [
    "travel",
    "trip planning",
    "vacation",
    "tourism",
    "weather",
    "flights",
    "hotels",
    "destinations",
    "itinerary",
    "packing",
    "sightseeing",
    "transportation",
]


def _guardrail_device() -> str:
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def _build_guards() -> tuple[Guard, Guard]:
    device = _guardrail_device()
    input_guard = Guard().use(
        DetectJailbreak(
            use_local=True,
            device=device,
            on_fail=OnFailAction.EXCEPTION,
        )
    )
    output_guard = Guard().use(
        RestrictToTopic(
            valid_topics=TRIP_TOPICS,
            disable_classifier=False,
            disable_llm=True,
            use_local=True,
            on_fail=OnFailAction.EXCEPTION,
        )
    )
    return input_guard, output_guard


def _tavily_mcp_url() -> str:
    api_key = os.environ.get("TAVILY_API_KEY", "").strip()
    if api_key:
        return f"https://mcp.tavily.com/mcp/?tavilyApiKey={api_key}"
    return "https://mcp.tavily.com/mcp/"


def _mcp_servers() -> dict[str, str]:
    return {
        "openweather": OPENWEATHER_MCP_URL,
        "tavily": _tavily_mcp_url(),
    }


def _openai_client() -> OpenAI:
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        raise ValueError("OPENROUTER_API_KEY is not set")
    return OpenAI(api_key=api_key, base_url=LLM_BASE_URL)


async def _run_tool_loop(
    client: OpenAI,
    mcp: MCPManager,
    messages: list[dict],
) -> str:
    for _ in range(12):
        response = client.chat.completions.create(
            model=LLM_MODEL,
            messages=messages,
            tools=mcp.tools,
            tool_choice="auto",
            max_completion_tokens=1500,
            reasoning_effort="low",
        )
        assistant_message = response.choices[0].message
        if not assistant_message.tool_calls:
            return (assistant_message.content or "").strip()

        messages.append(assistant_message.model_dump(exclude_none=True))
        for tool_call in assistant_message.tool_calls:
            func_name = tool_call.function.name
            func_args = json.loads(tool_call.function.arguments)
            print(f"[tool] {func_name}({json.dumps(func_args, ensure_ascii=False)})")
            tool_result = await mcp.call_tool(func_name, func_args)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": func_name,
                    "content": tool_result,
                }
            )

    return "I could not finish the request within the tool-call limit."


async def chat() -> None:
    input_guard, output_guard = _build_guards()
    client = _openai_client()
    messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]

    print("Trip Planning Assistant")
    print("Uses OpenRouter + MCP (OpenWeatherMap, Tavily). Type 'quit' to exit.\n")

    async with MCPManager(_mcp_servers()) as mcp:
        print(f"Loaded tools: {[tool['function']['name'] for tool in mcp.tools]}\n")

        while True:
            user_input = input("You: ").strip()
            if not user_input:
                continue
            if user_input.lower() in {"quit", "exit", "q"}:
                print("Goodbye!")
                break

            try:
                input_guard.validate(user_input)
            except Exception as exc:
                print(f"Assistant: Sorry, I cannot help with that. ({exc})\n")
                continue

            messages.append({"role": "user", "content": user_input})

            try:
                reply = await _run_tool_loop(client, mcp, messages)
                output_guard.validate(reply)
            except Exception as exc:
                reply = (
                    "I can only help with trip planning. "
                    f"Please ask about destinations, weather, or travel logistics. ({exc})"
                )

            messages.append({"role": "assistant", "content": reply})
            print(f"\nAssistant: {reply}\n")


def main() -> None:
    try:
        asyncio.run(chat())
    except KeyboardInterrupt:
        print("\nGoodbye!")
        sys.exit(0)


if __name__ == "__main__":
    main()
