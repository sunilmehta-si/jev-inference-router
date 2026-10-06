"""Small synthetic routing benchmark, not a general capability claim."""

import argparse
import asyncio
import json
import platform
import statistics
import sys
import time
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from jev_router.config import Settings  # noqa: E402
from jev_router.decision import (  # noqa: E402
    OPTIONS,
    DecisionUnavailable,
    DemoDecider,
    JevDecider,
    effective_route,
    rule_route,
)
from jev_router.generation import LocalGenerator  # noqa: E402
from jev_router.retrieval import Knowledge  # noqa: E402


def percentile(values, p):
    if not values:
        return None
    values = sorted(values)
    index = (len(values) - 1) * p
    low = int(index)
    high = min(low + 1, len(values) - 1)
    return round(values[low] + (values[high] - values[low]) * (index - low), 2)


def summarize(rows, predicted="route", latency="duration_ms"):
    valid = [r for r in rows if r.get(predicted) is not None]
    confusion = {truth: {guess: 0 for guess in OPTIONS} for truth in OPTIONS}
    for row in valid:
        confusion[row["expected"]][row[predicted]] += 1
    times = [r[latency] for r in valid if r.get(latency) is not None]
    return {
        "cases": len(rows),
        "successful_requests": len(valid),
        "correct": sum(r[predicted] == r["expected"] for r in valid),
        "accuracy_over_all_cases": round(
            sum(r[predicted] == r["expected"] for r in valid) / len(rows), 4
        ),
        "latency_p50_ms": percentile(times, 0.5),
        "latency_p95_ms": percentile(times, 0.95),
        "confusion_matrix": confusion,
    }


async def run(args):
    cases = json.loads(Path("evaluations/cases.json").read_text())
    settings = Settings.from_env() if args.mode == "live" else Settings()
    decider = JevDecider(settings) if args.mode == "live" else DemoDecider()
    generator = LocalGenerator(settings) if args.include_qwen else None
    knowledge = Knowledge()
    rows, baseline, qwen_rows = [], [], []
    tokens, reverse_tokens, disagreements = 0, 0, 0
    try:
        for case in cases:
            question = case["question"]
            docs = knowledge.search(question)
            row = {"id": case["id"], "expected": case["expected"]}
            start = time.perf_counter()
            baseline.append(row | {"route": rule_route(question), "duration_ms": 0})
            try:
                d = await decider.decide(question, docs)
                route, reason, _ = effective_route(d, docs, settings.confidence_min)
                row |= {
                    "route": route,
                    "selected_route": d.selected_route,
                    "policy_reason": reason,
                    "model": d.model,
                    "confidence": d.confidence,
                    "probabilities": d.probabilities,
                    "needs_context": d.needs_context,
                    "duration_ms": round(d.duration_ms, 2),
                    "input_tokens": d.input_tokens,
                }
                tokens += d.input_tokens
                if args.reverse_options:
                    other = await decider.decide(question, docs, reverse=True)
                    reverse_tokens += other.input_tokens
                    disagrees = d.selected_route != other.selected_route
                    disagreements += int(disagrees)
                    row["reversed_selected_route"] = other.selected_route
                    row["option_order_disagreement"] = disagrees
            except DecisionUnavailable:
                row |= {
                    "route": None,
                    "error": "decision_unavailable",
                    "duration_ms": round((time.perf_counter() - start) * 1000, 2),
                }
            rows.append(row)
            if generator:
                started = time.perf_counter()
                qrow = {"id": case["id"], "expected": case["expected"]}
                try:
                    # Same route rubric and candidate documents; no probability comparison.
                    prompt = (
                        "Classify the question into exactly one routing label.\n"
                        + json.dumps(OPTIONS)
                        + "\nFor this application, commands to execute changes require clarify. "
                        "General explanations use local_llm; project facts use retrieve. "
                        'Respond ONLY with JSON: {"route": "label"}.\nQuestion: '
                        + question
                        + "\nCandidate project passages: "
                        + json.dumps(docs)
                    )
                    answer = await generator.answer(prompt, [], 64)
                    answer = answer.strip()
                    if answer.startswith("```"):
                        answer = answer.split("\n", 1)[1].rsplit("```", 1)[0].strip()
                    route = json.loads(answer)["route"]
                    if route not in OPTIONS:
                        raise ValueError("Invalid route")
                    qrow["route"] = route
                except Exception:
                    # Do not publish upstream bodies, generated raw content, or secrets.
                    qrow |= {"route": None, "error": "generation_or_parse_failure"}
                qrow["duration_ms"] = round((time.perf_counter() - started) * 1000, 2)
                qwen_rows.append(qrow)
            print(f"{case['id']}: {row.get('route')} ({len(rows)}/{len(cases)})", flush=True)
    finally:
        await decider.close()
        if generator:
            await generator.close()
    accepted = [
        r for r in rows if r.get("policy_reason") == "accepted" and r.get("route") != "clarify"
    ]
    report = {
        "created_utc": datetime.now(UTC).isoformat(),
        "mode": args.mode,
        "dataset": "24 manually labeled synthetic examples; demonstration suite only",
        "python": platform.python_version(),
        "typesafe_sdk": version("typesafe-sdk"),
        "confidence_threshold": settings.confidence_min,
        "jev_or_demo": summarize(rows),
        "rules": summarize(baseline),
        "accepted_nonclarify_count": len(accepted),
        "accepted_nonclarify_accuracy": round(
            statistics.mean(r["route"] == r["expected"] for r in accepted), 4
        )
        if accepted
        else None,
        "measured_input_tokens": tokens,
        "reversed_input_tokens": reverse_tokens,
        "estimated_jev_cost_usd": round((tokens + reverse_tokens) * 0.042 / 1_000_000, 8),
        "pricing_note": "Estimate $0.042/M input tokens; retries and account pricing excluded",
        "option_order_checks": sum("option_order_disagreement" in r for r in rows),
        "option_order_disagreements": disagreements,
        "results": rows,
    }
    if qwen_rows:
        report |= {
            "local_qwen": summarize(qwen_rows),
            "qwen_model": settings.llm_model,
            "qwen_results": qwen_rows,
            "comparison_note": (
                "Qwen emits JSON labels; Jev emits distributions and gates. "
                "Different tasks; no universal speed claim."
            ),
        }
    path = Path(args.output or f"evaluations/{args.mode}-results.json")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2) + "\n")
    print(
        json.dumps(
            {k: report[k] for k in ("jev_or_demo", "rules", "estimated_jev_cost_usd")}, indent=2
        )
    )
    return 0 if report["jev_or_demo"]["successful_requests"] == len(cases) else 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--mode", choices=["demo", "live"], default="demo")
    parser.add_argument("--include-qwen", action="store_true")
    parser.add_argument("--reverse-options", action="store_true")
    parser.add_argument("--output")
    options = parser.parse_args()
    if options.mode == "demo" and (options.include_qwen or options.reverse_options):
        parser.error("Live comparison options require --mode live")
    sys.exit(asyncio.run(run(options)))
