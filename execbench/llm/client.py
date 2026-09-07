"""Small HTTP provider adapter with atomic, content-addressed caching and redacted errors."""

import hashlib
import json
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path

import httpx


class LLMBalanceError(RuntimeError):
    """A non-retryable account failure, rather than an executive-policy failure."""


def prompt(name):
    return Path(__file__).with_name("prompts").joinpath(name).read_text()


# Reasoning model families that take reasoning_effort on Chat Completions. Legacy o1/o3/o4 models
# are excluded: they only document low/medium/high, and the lowest-effort values below were
# introduced later with GPT-5, so sending one to an o-series model risks an HTTP 400.
REASONING_MODEL_PREFIXES = ("gpt-5", "gpt-6")

# The name of the lowest reasoning effort changed mid-line, and each family rejects the other's
# spelling with an HTTP 400. Verified directly against the API:
#   gpt-5, gpt-5-mini, gpt-5-nano (and dated snapshots)  -> "minimal"; "none" is a 400
#   gpt-5.1 and later                                    -> "none";    "minimal" is a 400
# Both mean "reason as little as possible" — the closest equivalent to the thinking:disabled
# request sent to Z.ai. Anything newer is assumed to follow the current "none" convention.
MINIMAL_EFFORT_PREFIXES = ("gpt-5-", "gpt-5.0")


def reasoning_effort_for(model):
    """The lowest reasoning effort this model actually accepts."""
    return "minimal" if model == "gpt-5" or model.startswith(MINIMAL_EFFORT_PREFIXES) else "none"


# Z.ai models that always reason and reject the thinking:disabled request the other GLM models
# accept. Sending them any "thinking" object at all — including {"type": "low"} — is an HTTP 400
# with code 1210; the effort level travels via reasoning_effort instead, which accepts only
# low/high/max ("minimal", "none" and "medium" all 400 as well). "low" is the closest available
# equivalent to the disabled thinking used elsewhere. Compared against a lowercased model name:
# Z.ai treats model ids case-insensitively, so "GLM-5.3-Flash" must match too.
Z_AI_FORCED_REASONING_PREFIXES = ("glm-5.3",)

# Default judge for question readability, report-honesty, and coaching grades. Overridable per run with
# --grader-model, or with EXECBENCH_GRADER_MODEL; pass "none" to grade without an LLM.
DEFAULT_GRADER_MODEL = "glm-4.7-flash"
GRADER_DISABLED_VALUES = ("", "none", "off")


def resolve_grader_model(model):
    """Normalize a --grader-model value; None falls back to the configured default."""
    if model is None:
        model = os.getenv("EXECBENCH_GRADER_MODEL", DEFAULT_GRADER_MODEL)
    return None if model.strip().lower() in GRADER_DISABLED_VALUES else model.strip()


def parse_json(text):
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    return json.loads(text)


class LLMClient:
    def __init__(
        self,
        model,
        provider=None,
        base_url=None,
        api_key=None,
        api_key_ref=None,
        cache_dir=None,
        timeout=120,
        input_price=None,
        output_price=None,
    ):
        self.model = model
        self.provider = provider or os.getenv("EXECBENCH_PROVIDER", "openai")
        self.base_url = (
            base_url
            or os.getenv("EXECBENCH_BASE_URL")
            or (
                "https://api.anthropic.com/v1"
                if self.provider == "anthropic"
                else "https://api.z.ai/api/paas/v4"
            )
        ).rstrip("/")
        self._key = api_key
        self._key_ref = api_key_ref
        self.cache_dir = Path(cache_dir or os.getenv("EXECBENCH_CACHE_DIR", ".cache/llm"))
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.timeout = timeout
        self.calls = []
        prices = json.loads(os.getenv("EXECBENCH_PRICES_JSON", "{}")).get(model, {})
        self.input_price = input_price if input_price is not None else prices.get("input")
        self.output_price = output_price if output_price is not None else prices.get("output")

    def key(self):
        if self._key is None:
            self._key = os.getenv("EXECBENCH_API_KEY") or os.getenv(
                "ANTHROPIC_API_KEY" if self.provider == "anthropic" else "OPENAI_API_KEY"
            )
            ref = self._key_ref or os.getenv("EXECBENCH_API_KEY_REF")
            if not self._key and ref:
                try:
                    result = subprocess.run(
                        ["op", "read", ref], capture_output=True, text=True, timeout=45, check=False
                    )
                except subprocess.TimeoutExpired:
                    raise RuntimeError(
                        "1Password timed out. Unlock the app and authorize CLI access, then retry."
                    ) from None
                if result.returncode:
                    raise RuntimeError(
                        "1Password could not read the configured credential (secret output suppressed)."
                    )
                self._key = result.stdout.strip()
        if not self._key:
            raise RuntimeError("Set EXECBENCH_API_KEY or EXECBENCH_API_KEY_REF.")
        return self._key

    def complete(self, messages, tools=None, temperature=0, max_tokens=2048):
        request = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if tools:
            request["tools"], request["tool_choice"] = tools, "required"
            if self.provider != "anthropic":
                request["parallel_tool_calls"] = False
        if self.provider == "anthropic":
            request["system"] = "\n".join(m["content"] for m in messages if m["role"] == "system")
            request["messages"] = [m for m in messages if m["role"] != "system"]
            if tools:
                request["tools"] = [
                    {
                        "name": t["function"]["name"],
                        "description": t["function"]["description"],
                        "input_schema": t["function"]["parameters"],
                    }
                    for t in tools
                ]
                request["tool_choice"] = {"type": "any", "disable_parallel_tool_use": True}
        elif "api.z.ai" in self.base_url:
            if self.model.lower().startswith(Z_AI_FORCED_REASONING_PREFIXES):
                request["reasoning_effort"] = "low"
            else:
                request["thinking"] = {"type": "disabled"}
        elif self.model.startswith(REASONING_MODEL_PREFIXES):
            # These models reject two of the defaults used everywhere else: max_tokens must be
            # spelled max_completion_tokens, and temperature accepts only its default of 1 (even
            # temperature=0 is a 400), so the sampling temperature is dropped rather than sent.
            # Determinism therefore rests on the response cache below, not on temperature=0.
            request["max_completion_tokens"] = request.pop("max_tokens")
            request.pop("temperature", None)
            request["reasoning_effort"] = reasoning_effort_for(self.model)
        cache_input = {"provider": self.provider, "base_url": self.base_url, "request": request}
        digest = hashlib.sha256(
            json.dumps(cache_input, sort_keys=True, ensure_ascii=False).encode()
        ).hexdigest()
        path = self.cache_dir / f"{digest}.json"
        cached = path.exists()
        if cached:
            raw = json.loads(path.read_text())["response"]
        else:
            headers = (
                {"x-api-key": self.key(), "anthropic-version": "2023-06-01"}
                if self.provider == "anthropic"
                else {"Authorization": f"Bearer {self.key()}"}
            )
            endpoint = "/messages" if self.provider == "anthropic" else "/chat/completions"
            for attempt in range(3):
                try:
                    response = httpx.post(
                        self.base_url + endpoint, headers=headers, json=request, timeout=self.timeout
                    )
                except httpx.TransportError as exc:
                    if attempt == 2:
                        raise RuntimeError(f"LLM transport failed: {type(exc).__name__}") from None
                    time.sleep(2**attempt)
                    continue
                if response.status_code >= 400:
                    try:
                        error = response.json().get("error", {})
                    except (ValueError, AttributeError):
                        error = {}
                    if isinstance(error, dict) and str(error.get("code")) == "1113":
                        raise LLMBalanceError(
                            "Provider balance exhausted (HTTP 429, code 1113); recharge the API account."
                        )
                if response.status_code in (429, 500, 502, 503, 504) and attempt < 2:
                    time.sleep(2**attempt)
                    continue
                if response.status_code >= 400:
                    # Never include response bodies, headers, or credentials in errors or traces.
                    # The provider's error *code* is a short opaque enum, not caller data, and is
                    # the difference between "recharge" (1113), "retry later" (1305), "bad request"
                    # (1210) and "no such model" (1214) — so it is worth carrying. Length-capped
                    # and character-filtered so a non-conforming provider cannot smuggle a body in.
                    # Underscores and hyphens are allowed: OpenAI spells its codes that way
                    # ("rate_limit_exceeded", "insufficient_quota"), and rejecting them dropped
                    # exactly the codes that distinguish a throttle from an exhausted account.
                    code = str(error.get("code", "")) if isinstance(error, dict) else ""
                    code = code if re.fullmatch(r"[A-Za-z0-9_-]{1,32}", code) else ""
                    detail = f", provider code {code}" if code else ""
                    raise RuntimeError(
                        f"LLM request failed with HTTP {response.status_code}{detail} ({self.model})."
                    )
                raw = response.json()
                break
            with tempfile.NamedTemporaryFile("w", dir=self.cache_dir, delete=False) as f:
                json.dump({"request": cache_input, "response": raw}, f, ensure_ascii=False)
                temp = f.name
            os.replace(temp, path)
        if self.provider == "anthropic":
            content = raw.get("content", [])
            text = "\n".join(c.get("text", "") for c in content if c["type"] == "text")
            tool_calls = [{"name": c["name"], "args": c["input"]} for c in content if c["type"] == "tool_use"]
            usage = {
                "input_tokens": raw.get("usage", {}).get("input_tokens", 0),
                "output_tokens": raw.get("usage", {}).get("output_tokens", 0),
            }
        else:
            message = raw["choices"][0]["message"]
            text = message.get("content") or ""
            tool_calls = []
            for call in message.get("tool_calls") or []:
                fn = call["function"]
                try:
                    args = json.loads(fn["arguments"])
                except (ValueError, TypeError):
                    args = fn["arguments"]
                tool_calls.append({"name": fn["name"], "args": args})
            usage = {
                "input_tokens": raw.get("usage", {}).get("prompt_tokens", 0),
                "output_tokens": raw.get("usage", {}).get("completion_tokens", 0),
            }
        cost = (
            None
            if self.input_price is None or self.output_price is None
            else (usage["input_tokens"] * self.input_price + usage["output_tokens"] * self.output_price) / 1e6
        )
        result = {
            "text": text,
            "tool_calls": tool_calls,
            "usage": usage,
            "cache_key": digest,
            "cached": cached,
            "cost_usd": cost,
        }
        self.calls.append({**result, "request": cache_input, "response": raw})
        return result

    def json(self, messages):
        return parse_json(self.complete(messages, temperature=0)["text"])


def build_grader_client(model):
    """Build the grader's LLMClient, independent of the policy model's provider.

    Falls back to the unprefixed EXECBENCH_* settings when no EXECBENCH_GRADER_*
    override is set, so existing single-provider setups are unaffected.
    """
    if model is None:
        return None

    def env(name):
        return os.getenv(f"EXECBENCH_GRADER_{name}") or os.getenv(f"EXECBENCH_{name}")

    return LLMClient(
        model,
        provider=env("PROVIDER"),
        base_url=env("BASE_URL"),
        api_key=env("API_KEY"),
        api_key_ref=env("API_KEY_REF"),
    )
