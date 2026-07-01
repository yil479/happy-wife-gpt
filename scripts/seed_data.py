"""Ingest the mock files under data/experiences and data/advice into the running backend.

Usage:
    python scripts/seed_data.py [--base-url http://localhost:8000] [--api-key KEY]

Requires the backend to already be running (see CLAUDE.md Key Commands).
"""
import argparse
import sys
from pathlib import Path

import httpx

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
COLLECTIONS = ("experiences", "advice")


def seed(base_url: str, api_key: str) -> None:
    headers = {"X-API-Key": api_key} if api_key else {}

    with httpx.Client(base_url=base_url, headers=headers, timeout=60.0) as client:
        for collection in COLLECTIONS:
            folder = DATA_DIR / collection
            files = sorted(p for p in folder.glob("*") if p.is_file())
            if not files:
                print(f"no files found in {folder}, skipping")
                continue

            for path in files:
                with open(path, "rb") as f:
                    resp = client.post(
                        "/ingest",
                        params={"collection": collection},
                        files={"file": (path.name, f, "text/markdown")},
                    )
                if resp.status_code != 200:
                    print(f"FAILED {collection}/{path.name}: {resp.status_code} {resp.text}")
                    continue
                data = resp.json()
                print(f"ingested {collection}/{path.name} -> {data['chunks_stored']} chunks")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--api-key", default="")
    args = parser.parse_args()

    try:
        seed(args.base_url, args.api_key)
    except httpx.ConnectError:
        print(f"Could not connect to {args.base_url} — is the backend running?", file=sys.stderr)
        sys.exit(1)
