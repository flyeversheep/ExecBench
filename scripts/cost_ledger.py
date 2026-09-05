"""Estimate unique cached request costs, including calls from interrupted episodes."""

import argparse
import json
from collections import defaultdict
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", default="results/live-demo-resumed")
    parser.add_argument("--cache", default=".cache/llm")
    parser.add_argument("--out", default="results/live-demo-resumed/cost-ledger.json")
    parser.add_argument(
        "--cached-input-prices", default="{}", help="JSON model-to-USD-per-million cached-input rates"
    )
    args = parser.parse_args()
    cached_prices = json.loads(args.cached_input_prices)
    prices = json.loads((Path(args.results) / "manifest.json").read_text())["pricing"]
    ledger = defaultdict(
        lambda: {
            "unique_cached_responses": 0,
            "input_tokens": 0,
            "output_tokens": 0,
            "provider_cached_input_tokens": 0,
            "full_input_price_estimate_usd": 0.0,
            "cache_adjusted_estimate_usd": 0.0,
        }
    )
    for path in Path(args.cache).glob("*.json"):
        data = json.loads(path.read_text())
        model = data["request"]["request"]["model"]
        if model not in prices:
            continue
        usage = data["response"].get("usage", {})
        inputs = usage.get("prompt_tokens", usage.get("input_tokens", 0))
        outputs = usage.get("completion_tokens", usage.get("output_tokens", 0))
        row = ledger[model]
        row["unique_cached_responses"] += 1
        row["input_tokens"] += inputs
        row["output_tokens"] += outputs
        cached = usage.get("prompt_tokens_details", {}).get("cached_tokens", 0)
        row["provider_cached_input_tokens"] += cached
        row["full_input_price_estimate_usd"] += (
            inputs * prices[model]["input"] + outputs * prices[model]["output"]
        ) / 1e6
        row["cache_adjusted_estimate_usd"] += (
            (inputs - cached) * prices[model]["input"]
            + cached * cached_prices.get(model, prices[model]["input"])
            + outputs * prices[model]["output"]
        ) / 1e6
    result = {
        "source": "Unique request hashes in the local response cache, including previous attempts and unfinished episodes.",
        "caveat": "Estimates, not an invoice. Cache-adjusted totals use reported cached-token counts and explicitly supplied rates; missing rates use full input prices. Interrupted or duplicate in-flight requests may be omitted.",
        "prices_usd_per_million": prices,
        "cached_input_prices_usd_per_million": cached_prices,
        "models": dict(ledger),
        "total_full_input_price_estimate_usd": sum(
            r["full_input_price_estimate_usd"] for r in ledger.values()
        ),
        "total_cache_adjusted_estimate_usd": sum(r["cache_adjusted_estimate_usd"] for r in ledger.values()),
    }
    path = Path(args.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
