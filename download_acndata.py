from __future__ import annotations

import argparse
import getpass
import hashlib
import json
import os
import sys
import time
from collections import Counter
from datetime import datetime, timezone
from email.utils import format_datetime, parsedate_to_datetime
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

try:
    import requests
except ImportError:
    print(
        "Missing dependency: requests\n"
        "Install it with: py -m pip install requests",
        file=sys.stderr,
    )
    raise SystemExit(2)


API_BASE_URL = "https://ev.caltech.edu/api/v1/"
DEFAULT_SITES = ("caltech", "jpl")
VALID_SITES = ("caltech", "jpl", "office001")
TOKEN_ENV_VAR = "[TOKEN HERE]"


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def parse_connection_time(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    try:
        parsed = parsedate_to_datetime(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def preserve_old_partial(path: Path) -> None:
    if not path.exists():
        return
    backup = path.with_name(f"{path.name}.{utc_timestamp()}.bak")
    path.rename(backup)
    print(f"Preserved previous partial file as: {backup.name}")


def response_json_with_retries(
    session: requests.Session,
    url: str,
    *,
    params: dict[str, str] | None,
    max_attempts: int = 6,
) -> dict[str, Any]:
    last_error: Exception | None = None

    for attempt in range(1, max_attempts + 1):
        try:
            response = session.get(url, params=params, timeout=(15, 90))

            if response.status_code == 401:
                raise RuntimeError(
                    "ACN rejected the token (HTTP 401). Retrieve a current key "
                    "from your ACN account and try again."
                )

            if response.status_code == 429 or 500 <= response.status_code < 600:
                retry_after = response.headers.get("Retry-After", "")
                wait_seconds = (
                    float(retry_after)
                    if retry_after.replace(".", "", 1).isdigit()
                    else min(2 ** (attempt - 1), 30)
                )
                raise requests.HTTPError(
                    f"Temporary API response {response.status_code}; "
                    f"retrying in {wait_seconds:.1f}s",
                    response=response,
                )

            response.raise_for_status()
            payload = response.json()
            if not isinstance(payload, dict):
                raise RuntimeError("The API returned JSON in an unexpected format.")
            return payload

        except RuntimeError:
            raise
        except (requests.RequestException, ValueError) as exc:
            last_error = exc
            if attempt == max_attempts:
                break

            retry_after = ""
            if isinstance(exc, requests.HTTPError) and exc.response is not None:
                retry_after = exc.response.headers.get("Retry-After", "")
            wait_seconds = (
                float(retry_after)
                if retry_after.replace(".", "", 1).isdigit()
                else min(2 ** (attempt - 1), 30)
            )
            print(
                f"Request failed (attempt {attempt}/{max_attempts}): {exc}\n"
                f"Retrying in {wait_seconds:.1f} seconds...",
                file=sys.stderr,
            )
            time.sleep(wait_seconds)

    raise RuntimeError(f"API request failed after {max_attempts} attempts: {last_error}")


def next_page_url(payload: dict[str, Any]) -> str | None:
    next_link = payload.get("_links", {}).get("next")
    if isinstance(next_link, dict):
        href = next_link.get("href")
    elif isinstance(next_link, str):
        href = next_link
    else:
        href = None

    if not isinstance(href, str) or not href.strip():
        return None
    return urljoin(API_BASE_URL, href)


def download_site(
    session: requests.Session,
    site: str,
    output_dir: Path,
    cutoff: datetime,
    delay_seconds: float,
) -> dict[str, Any]:
    final_path = output_dir / f"acndata_{site}_sessions.jsonl"
    partial_path = output_dir / f"acndata_{site}_sessions.jsonl.part"

    if final_path.exists():
        raise FileExistsError(
            f"{final_path} already exists. Move or rename it before downloading "
            "the same site again."
        )
    preserve_old_partial(partial_path)

    cutoff_rfc = format_datetime(cutoff, usegmt=True)
    first_url = urljoin(API_BASE_URL, f"sessions/{site}")
    params: dict[str, str] | None = {
        "where": f'connectionTime<="{cutoff_rfc}"',
        "sort": "-connectionTime",
    }

    downloaded = 0
    expected_total: int | None = None
    earliest: datetime | None = None
    latest: datetime | None = None
    year_counts: Counter[str] = Counter()
    record_ids: set[str] = set()
    duplicate_ids = 0
    missing_connection_time = 0
    seen_page_urls: set[str] = set()
    url: str | None = first_url

    print(f"\nDownloading {site} sessions through {cutoff_rfc}...")

    try:
        with partial_path.open("w", encoding="utf-8", newline="\n") as output:
            while url is not None:
                page_key = requests.Request("GET", url, params=params).prepare().url or url
                if page_key in seen_page_urls:
                    raise RuntimeError(f"Pagination loop detected at {page_key}")
                seen_page_urls.add(page_key)

                payload = response_json_with_retries(session, url, params=params)
                params = None

                meta = payload.get("_meta", {})
                if expected_total is None and isinstance(meta.get("total"), int):
                    expected_total = meta["total"]
                    print(f"API reports {expected_total:,} sessions for {site}.")

                items = payload.get("_items")
                if not isinstance(items, list):
                    raise RuntimeError("API response is missing the _items list.")

                for item in items:
                    if not isinstance(item, dict):
                        raise RuntimeError("API returned a non-object session record.")

                    output.write(json.dumps(item, ensure_ascii=False, separators=(",", ":")))
                    output.write("\n")
                    downloaded += 1

                    record_id = item.get("sessionID") or item.get("_id")
                    if isinstance(record_id, str):
                        if record_id in record_ids:
                            duplicate_ids += 1
                        else:
                            record_ids.add(record_id)

                    connected_at = parse_connection_time(item.get("connectionTime"))
                    if connected_at is None:
                        missing_connection_time += 1
                    else:
                        earliest = connected_at if earliest is None else min(earliest, connected_at)
                        latest = connected_at if latest is None else max(latest, connected_at)
                        year_counts[str(connected_at.year)] += 1

                if downloaded and downloaded % 250 < len(items):
                    total_text = f"/{expected_total:,}" if expected_total is not None else ""
                    print(f"  Retrieved {downloaded:,}{total_text} sessions...")
                    output.flush()

                url = next_page_url(payload)
                if url is not None and delay_seconds > 0:
                    time.sleep(delay_seconds)

        if expected_total is not None and downloaded != expected_total:
            raise RuntimeError(
                f"Completeness check failed for {site}: downloaded {downloaded:,}, "
                f"but the API reported {expected_total:,}. The partial file was kept."
            )

        partial_path.rename(final_path)

    except Exception:
        print(f"Partial data, if any, remains at: {partial_path}", file=sys.stderr)
        raise

    result = {
        "site": site,
        "file": final_path.name,
        "downloaded_sessions": downloaded,
        "api_reported_sessions": expected_total,
        "earliest_connection_time_utc": earliest.isoformat() if earliest else None,
        "latest_connection_time_utc": latest.isoformat() if latest else None,
        "sessions_by_year": dict(sorted(year_counts.items())),
        "duplicate_record_ids_observed": duplicate_ids,
        "missing_connection_time": missing_connection_time,
        "sha256": sha256_file(final_path),
    }

    print(
        f"Completed {site}: {downloaded:,} sessions\n"
        f"  Earliest: {result['earliest_connection_time_utc']}\n"
        f"  Latest:   {result['latest_connection_time_utc']}\n"
        f"  Saved:    {final_path}"
    )
    return result


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Download complete session-level ACN-Data records through the "
            "official paginated API."
        )
    )
    parser.add_argument(
        "--sites",
        nargs="+",
        choices=VALID_SITES,
        default=list(DEFAULT_SITES),
        help="Sites to download (default: caltech jpl).",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parent / "acndata_download",
        help="Output directory (default: acndata_download beside this script).",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.10,
        help="Courtesy delay between API pages in seconds (default: 0.10).",
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if args.delay < 0:
        print("--delay cannot be negative.", file=sys.stderr)
        return 2

    token = os.environ.get(TOKEN_ENV_VAR, "").strip()
    if not token:
        token = getpass.getpass("Enter your ACN API token (input hidden): ").strip()
    if not token:
        print("No API token was provided.", file=sys.stderr)
        return 2

    output_dir: Path = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    cutoff = datetime.now(timezone.utc).replace(microsecond=0)
    session = requests.Session()
    session.auth = (token, "")
    session.headers.update(
        {
            "Accept": "application/json",
            "User-Agent": "ACN-Thesis-Data-Collector/1.0",
        }
    )

    results: list[dict[str, Any]] = []
    failures: list[dict[str, str]] = []

    try:
        for site in args.sites:
            try:
                results.append(
                    download_site(
                        session,
                        site,
                        output_dir,
                        cutoff,
                        args.delay,
                    )
                )
            except Exception as exc:
                failures.append({"site": site, "error": str(exc)})
                print(f"Failed to complete {site}: {exc}", file=sys.stderr)
    finally:
        session.close()

    summary = {
        "download_started_cutoff_utc": cutoff.isoformat(),
        "api_base_url": API_BASE_URL,
        "timeseries_requested": False,
        "sites_requested": list(args.sites),
        "successful_sites": results,
        "failures": failures,
    }
    summary_path = output_dir / f"acndata_download_summary_{utc_timestamp()}.json"
    with summary_path.open("w", encoding="utf-8") as output:
        json.dump(summary, output, indent=2, ensure_ascii=False)
        output.write("\n")

    print(f"\nDownload summary: {summary_path}")
    if failures:
        print("One or more sites did not complete. See the summary above.", file=sys.stderr)
        return 1

    print("All requested sites downloaded and passed the completeness check.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
