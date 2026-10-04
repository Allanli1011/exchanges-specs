from __future__ import annotations

import argparse
import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
import yaml
from bs4 import BeautifulSoup


def normalize_html_text(content: bytes) -> bytes:
    soup = BeautifulSoup(content, "html.parser")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = " ".join(soup.stripped_strings)
    text = re.sub(r"\s+", " ", text).strip()
    return text.encode("utf-8")


def fingerprint(content: bytes, kind: str) -> tuple[str, int]:
    normalized = normalize_html_text(content) if kind == "html_text" else content
    return hashlib.sha256(normalized).hexdigest(), len(normalized)


def load_state(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def load_sources(path: Path) -> list[dict[str, str]]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    sources = payload.get("sources", [])
    if not isinstance(sources, list):
        raise ValueError("calendar source config must contain a list under 'sources'")
    return sources


def check_sources(
    sources: list[dict[str, str]],
    *,
    previous_state: dict[str, Any],
    timeout_seconds: float = 30.0,
) -> tuple[dict[str, Any], dict[str, Any]]:
    current: dict[str, Any] = {}
    changes: list[dict[str, Any]] = []

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 Chrome/131 Safari/537.36"
        )
    }
    with httpx.Client(
        timeout=timeout_seconds,
        follow_redirects=True,
        headers=headers,
        verify=False,
    ) as client:
        for source in sources:
            source_id = source["id"]
            url = source["url"]
            kind = source.get("kind", "binary")
            observed_at = datetime.now(timezone.utc).isoformat()

            try:
                response = client.get(url)
                response.raise_for_status()
                digest, normalized_size = fingerprint(response.content, kind)
                item = {
                    **source,
                    "sha256": digest,
                    "normalized_size": normalized_size,
                    "http_status": response.status_code,
                    "observed_at": observed_at,
                }
                current[source_id] = item

                previous = previous_state.get(source_id)
                if previous is None:
                    status = "new_baseline"
                elif previous.get("sha256") != digest:
                    status = "changed"
                else:
                    status = "unchanged"

                changes.append(
                    {
                        "id": source_id,
                        "exchange": source.get("exchange", ""),
                        "url": url,
                        "status": status,
                        "previous_sha256": previous.get("sha256") if previous else None,
                        "current_sha256": digest,
                        "normalized_size": normalized_size,
                    }
                )
            except Exception as exc:
                changes.append(
                    {
                        "id": source_id,
                        "exchange": source.get("exchange", ""),
                        "url": url,
                        "status": "error",
                        "error": str(exc),
                    }
                )

    report = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "changed_count": sum(item["status"] == "changed" for item in changes),
        "error_count": sum(item["status"] == "error" for item in changes),
        "sources": changes,
    }
    return current, report


def main() -> None:
    parser = argparse.ArgumentParser(description="Fingerprint official exchange calendar sources")
    parser.add_argument(
        "--config",
        default="config/calendar_sources.yaml",
    )
    parser.add_argument(
        "--state",
        default=".calendar-cache/source_state.json",
    )
    parser.add_argument(
        "--report",
        default="artifacts/calendar_source_watch.json",
    )
    args = parser.parse_args()

    config_path = Path(args.config)
    state_path = Path(args.state)
    report_path = Path(args.report)

    previous = load_state(state_path)
    sources = load_sources(config_path)
    current, report = check_sources(sources, previous_state=previous)

    state_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(
        json.dumps(current, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    report_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
