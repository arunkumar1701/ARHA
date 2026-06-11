"""Render cron worker for public, non-login discovery.

This worker intentionally does not import resume/profile/application data. It only
checks public career URLs and writes a public JSON index for downstream review.
"""

import asyncio
import json
from pathlib import Path

from .jobs import PUBLIC_SOURCE_SEEDS, verify_url


async def main() -> None:
    output = []
    for seed in PUBLIC_SOURCE_SEEDS:
        verification = await verify_url(seed["apply_url"])
        output.append({**seed, "verification": verification})
    Path("public-opportunity-index.json").write_text(json.dumps(output, indent=2), encoding="utf-8")


if __name__ == "__main__":
    asyncio.run(main())
