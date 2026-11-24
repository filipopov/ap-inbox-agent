"""The chat agent: a tool-calling loop over the read-only inbox database.

Model access goes through OpenAI-compatible endpoints, so free providers are interchangeable.
Free tiers have small per-model limits, so each request walks a fallback chain of (provider, model);
if every model is rate-limited the user gets an explicit message instead of a silent failure.
"""
import os
import time
from pathlib import Path

from openai import APIConnectionError, APIStatusError, OpenAI

from agent.tools import SCHEMAS, call_tool

SYSTEM = (Path(__file__).parent / "AGENTS.md").read_text()
MAX_TOOL_ROUNDS = 8
HISTORY_TURNS = 4  # earlier user/assistant turns kept (tool chatter dropped) to stay inside free token limits

PROVIDERS = {
    "groq": ("https://api.groq.com/openai/v1", "GROQ_API_KEY"),
    "gemini": ("https://generativelanguage.googleapis.com/v1beta/openai/", "GEMINI_API_KEY"),
}
CHAIN = [(p.split(":", 1)[0], p.split(":", 1)[1]) for p in os.environ.get(
    "CHAT_MODELS",
    "gemini:gemini-3.1-flash-lite,groq:openai/gpt-oss-120b,groq:qwen/qwen3.8-27b",
).split(",")]


class AllModelsBusy(Exception):
    pass


def _clients():
    out = {}
    for name, (url, env) in PROVIDERS.items():
        if os.environ.get(env):
            out[name] = OpenAI(base_url=url, api_key=os.environ[env], max_retries=0, timeout=60)
    return out


CLIENTS = _clients()


def _retry_after(e):
    try:
        return float(e.response.headers.get("retry-after"))
    except Exception:  # header missing or not a number -> no wait hint
        return None


def _flatten(messages):
    """Turn tool-call history into plain text, so a different model can continue it
    (providers reject tool calls in history that they did not produce themselves)."""
    out = []
    for m in messages:
        if m["role"] == "assistant" and m.get("tool_calls"):
            calls = ", ".join(f"{t['function']['name']}({t['function']['arguments']})" for t in m["tool_calls"])
            out.append({"role": "assistant", "content": f"{m.get('content') or ''}\n[I called tools: {calls}]"})
        elif m["role"] == "tool":
            out.append({"role": "user", "content": f"[tool result]\n{m['content']}"})
        else:
            out.append(m)
    return out


def _complete(messages, start=0, origin=None):
    """One model call, walking the fallback chain. Returns (message, index of the model that answered).
    origin: index of the model that made the earlier tool calls in this question (None if none yet)."""
    errors = []
    for i in range(start, len(CHAIN)):
        msgs = messages if origin in (None, i) else _flatten(messages)
        provider, model = CHAIN[i]
        if provider not in CLIENTS:
            errors.append(f"{provider}: no API key")
            continue
        extra = {"reasoning_effort": "low"} if "gpt-oss" in model else {}
        for attempt in range(2):  # a per-minute limit with a short retry-after: waiting once beats a weaker model
            try:
                r = CLIENTS[provider].chat.completions.create(
                    model=model, messages=msgs, tools=SCHEMAS, temperature=0, max_tokens=1500, extra_body=extra)
                return r.choices[0].message, i
            except (APIStatusError, APIConnectionError) as e:
                status = getattr(e, "status_code", "connection")
                wait = _retry_after(e)
                if attempt == 0 and status == 429 and wait is not None and wait <= 20:
                    time.sleep(wait + 0.5)
                    continue
                errors.append(f"{model}: {status}")
                break
    raise AllModelsBusy("; ".join(errors))


def answer(question, history=()):
    """Run the agent on one question. Returns (answer_text, trace) where trace lists the tool calls made."""
    messages = [{"role": "system", "content": SYSTEM}]
    for turn in list(history)[-HISTORY_TURNS * 2:]:
        messages.append({"role": turn["role"], "content": turn["content"]})
    messages.append({"role": "user", "content": question})
    trace, model_idx, origin = [], 0, None
    try:
        for _ in range(MAX_TOOL_ROUNDS):
            msg, model_idx = _complete(messages, model_idx, origin)
            if origin is not None and model_idx != origin:  # switched model: continue in plain-text form
                messages, origin = _flatten(messages), None
            if not msg.tool_calls:
                return (msg.content or "(the model returned an empty answer)"), trace + [f"model: {CHAIN[model_idx][1]}"]
            origin = model_idx
            messages.append({"role": "assistant", "content": msg.content or "",
                             "tool_calls": [tc.model_dump(exclude_none=True) for tc in msg.tool_calls]})
            for tc in msg.tool_calls:
                result = call_tool(tc.function.name, tc.function.arguments)
                trace.append(f"{tc.function.name}({tc.function.arguments})")
                messages.append({"role": "tool", "tool_call_id": tc.id, "content": result})
        return ("I stopped after the maximum number of tool steps without a final answer. "
                "Please ask a narrower question."), trace
    except AllModelsBusy as e:
        return ("All free AI models are rate-limited right now (free tier: ~8k tokens per minute per model). "
                f"Please try again in a minute. Details: {e}"), trace
