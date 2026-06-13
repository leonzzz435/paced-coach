from __future__ import annotations

from collections.abc import Mapping

_CANONICAL_PROVIDER_ORDER = ("strava", "whoop")


def extract_daily_sync_sources(prefetched_recovery_readiness: object) -> list[str]:
    if not isinstance(prefetched_recovery_readiness, Mapping):
        return []

    raw_sources = prefetched_recovery_readiness.get("sources")
    if not isinstance(raw_sources, Mapping):
        return []

    sources_used: list[str] = []
    seen_provider_names: set[str] = set()
    for provider_name in _CANONICAL_PROVIDER_ORDER:
        provider_payload = raw_sources.get(provider_name)
        if isinstance(provider_payload, Mapping):
            sources_used.append(provider_name)
            seen_provider_names.add(provider_name)

    for provider_name, provider_payload in raw_sources.items():
        if not isinstance(provider_name, str) or provider_name in seen_provider_names:
            continue
        if isinstance(provider_payload, Mapping):
            sources_used.append(provider_name)

    return sources_used
