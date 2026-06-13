#!/usr/bin/env python3
import argparse
import asyncio
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from time import monotonic
from typing import Any

import httpx


@dataclass(frozen=True)
class RequestCase:
    label: str
    method: str
    path: str
    headers: dict[str, str]
    json_body: dict[str, Any] | None


@dataclass(frozen=True)
class RequestResult:
    label: str
    status_code: int | None
    elapsed_ms: float
    error: str | None = None
    response_excerpt: str | None = None


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a small concurrent load smoke against API endpoints."
    )
    parser.add_argument("--base-url", required=True, help="API base URL, e.g. https://api-test.paced.coach")
    parser.add_argument(
        "--scenario",
        choices=("analysis", "daily", "coach", "custom"),
        default="coach",
        help="Preset scenario to run.",
    )
    parser.add_argument("--token", help="Bearer token for a single test user.")
    parser.add_argument("--token-file", help="Path to a file with one bearer token per line.")
    parser.add_argument("--requests", type=int, help="Total requests to send.")
    parser.add_argument("--concurrency", type=int, default=3, help="Maximum in-flight requests.")
    parser.add_argument("--timeout-seconds", type=float, default=180.0, help="Per-request timeout.")
    parser.add_argument(
        "--allow-duplicates",
        action="store_true",
        help="Allow reuse of the same token for analysis/daily scenarios.",
    )
    parser.add_argument(
        "--coach-message",
        default="Quick training check-in for load smoke.",
        help="Message payload for the coach scenario.",
    )
    parser.add_argument(
        "--coach-thread-id",
        help="Optional thread id for the coach scenario. Omit to create/use the default flow.",
    )
    parser.add_argument(
        "--coach-sse",
        action="store_true",
        help="Request the coach endpoint as text/event-stream instead of JSON.",
    )
    parser.add_argument("--path", help="Custom request path when using --scenario custom.")
    parser.add_argument(
        "--method",
        default="POST",
        choices=("GET", "POST"),
        help="HTTP method for --scenario custom.",
    )
    parser.add_argument("--json-body", help="Inline JSON body for --scenario custom.")
    parser.add_argument("--json-file", help="Path to a JSON file for --scenario custom.")
    return parser.parse_args()


def _load_tokens(args: argparse.Namespace) -> list[str]:
    tokens: list[str] = []
    if args.token:
        tokens.append(args.token.strip())
    if args.token_file:
        for line in Path(args.token_file).read_text(encoding="utf-8").splitlines():
            token = line.strip()
            if token:
                tokens.append(token)
    deduped = list(dict.fromkeys(tokens))
    if not deduped:
        raise SystemExit("Provide --token or --token-file.")
    return deduped


def _load_custom_json(args: argparse.Namespace) -> dict[str, Any] | None:
    if args.json_body and args.json_file:
        raise SystemExit("Use either --json-body or --json-file, not both.")
    if args.json_body:
        payload = json.loads(args.json_body)
    elif args.json_file:
        payload = json.loads(Path(args.json_file).read_text(encoding="utf-8"))
    else:
        return None
    if not isinstance(payload, dict):
        raise SystemExit("Custom JSON payload must be a JSON object.")
    return payload


def _scenario_request_count(args: argparse.Namespace, token_count: int) -> int:
    if args.requests is not None:
        return args.requests
    if args.scenario in {"analysis", "daily"}:
        return token_count
    return max(token_count, 1)


def _build_auth_headers(args: argparse.Namespace, tokens: list[str], index: int) -> dict[str, str]:
    token = tokens[index % len(tokens)]
    return {"Authorization": f"Bearer {token}"}


def _build_cases(args: argparse.Namespace, tokens: list[str]) -> list[RequestCase]:
    request_count = _scenario_request_count(args, len(tokens))
    if request_count <= 0:
        raise SystemExit("--requests must be greater than zero.")
    if args.concurrency <= 0:
        raise SystemExit("--concurrency must be greater than zero.")

    if args.scenario in {"analysis", "daily"} and request_count > len(tokens) and not args.allow_duplicates:
        raise SystemExit(
            f"{args.scenario} is user-stateful. Provide at least {request_count} tokens or pass --allow-duplicates."
        )

    custom_payload = _load_custom_json(args)
    cases: list[RequestCase] = []

    for index in range(request_count):
        headers = _build_auth_headers(args, tokens, index)
        json_body: dict[str, Any] | None

        if args.scenario == "analysis":
            method = "POST"
            path = "/api/analysis/run"
            json_body = {}
        elif args.scenario == "daily":
            method = "POST"
            path = "/api/daily/run"
            json_body = None
        elif args.scenario == "coach":
            method = "POST"
            path = "/api/coach/turn"
            headers["Accept"] = "text/event-stream" if args.coach_sse else "application/json"
            json_body = {
                "action": "text",
                "message": args.coach_message,
                "idempotency_key": f"manual-smoke-{index + 1}",
            }
            if args.coach_thread_id:
                json_body["thread_id"] = args.coach_thread_id
        else:
            if not args.path:
                raise SystemExit("--path is required for --scenario custom.")
            method = args.method
            path = args.path
            json_body = custom_payload

        cases.append(
            RequestCase(
                label=f"{args.scenario}-{index + 1}",
                method=method,
                path=path,
                headers=headers,
                json_body=json_body,
            )
        )

    return cases


def _percentile(values: list[float], percentile: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, round((len(ordered) - 1) * percentile)))
    return ordered[index]


async def _send_case(
    client: httpx.AsyncClient,
    base_url: str,
    case: RequestCase,
) -> RequestResult:
    started_at = monotonic()
    try:
        response = await client.request(
            case.method,
            f"{base_url.rstrip('/')}{case.path}",
            headers=case.headers,
            json=case.json_body,
        )
        if "text/event-stream" in response.headers.get("content-type", ""):
            await response.aread()
        elapsed_ms = (monotonic() - started_at) * 1000
        excerpt = None
        if response.status_code >= 400:
            excerpt = response.text[:300]
        return RequestResult(
            label=case.label,
            status_code=response.status_code,
            elapsed_ms=elapsed_ms,
            response_excerpt=excerpt,
        )
    except Exception as exc:
        elapsed_ms = (monotonic() - started_at) * 1000
        return RequestResult(
            label=case.label,
            status_code=None,
            elapsed_ms=elapsed_ms,
            error=f"{type(exc).__name__}: {exc}",
        )


async def _run_cases(args: argparse.Namespace, cases: list[RequestCase]) -> list[RequestResult]:
    semaphore = asyncio.Semaphore(args.concurrency)
    results: list[RequestResult] = []
    timeout = httpx.Timeout(args.timeout_seconds)
    limits = httpx.Limits(max_keepalive_connections=args.concurrency, max_connections=args.concurrency)

    async with httpx.AsyncClient(timeout=timeout, limits=limits) as client:
        async def _runner(case: RequestCase) -> None:
            async with semaphore:
                results.append(await _send_case(client, args.base_url, case))

        await asyncio.gather(*(_runner(case) for case in cases))

    return results


def _print_summary(args: argparse.Namespace, results: list[RequestResult], total_elapsed_s: float) -> int:
    status_counts: dict[str, int] = {}
    failures: list[RequestResult] = []
    latencies = [result.elapsed_ms for result in results]

    for result in results:
        key = str(result.status_code) if result.status_code is not None else "error"
        status_counts[key] = status_counts.get(key, 0) + 1
        if result.status_code is None or result.status_code >= 400:
            failures.append(result)

    avg_ms = sum(latencies) / len(latencies) if latencies else 0.0
    rps = len(results) / total_elapsed_s if total_elapsed_s > 0 else 0.0

    print(f"Scenario: {args.scenario}")
    print(f"Requests: {len(results)}")
    print(f"Concurrency: {args.concurrency}")
    print(f"Elapsed: {total_elapsed_s:.2f}s")
    print(f"Approx RPS: {rps:.2f}")
    print("Status counts:")
    for key in sorted(status_counts):
        print(f"  {key}: {status_counts[key]}")
    print("Latency ms:")
    print(f"  min: {_percentile(latencies, 0.0):.1f}")
    print(f"  p50: {_percentile(latencies, 0.5):.1f}")
    print(f"  p95: {_percentile(latencies, 0.95):.1f}")
    print(f"  max: {_percentile(latencies, 1.0):.1f}")
    print(f"  avg: {avg_ms:.1f}")

    if failures:
        print("Failures:")
        for failure in failures[:10]:
            detail = failure.error or failure.response_excerpt or "unknown failure"
            print(f"  {failure.label}: {detail}")
        return 1

    if any(result.status_code is None or not 200 <= result.status_code < 300 for result in results):
        return 1
    return 0


async def _async_main(args: argparse.Namespace) -> int:
    tokens = _load_tokens(args)
    cases = _build_cases(args, tokens)
    started_at = monotonic()
    results = await _run_cases(args, cases)
    total_elapsed_s = monotonic() - started_at
    return _print_summary(args, results, total_elapsed_s)


def main() -> int:
    args = _parse_args()
    return asyncio.run(_async_main(args))


if __name__ == "__main__":
    sys.exit(main())
