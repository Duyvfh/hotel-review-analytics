"""Validate scraper extraction logic against mock Google Maps review HTML."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pandas as pd
from playwright.async_api import async_playwright

from schemas import RAW_REVIEW_COLUMNS
from scraper import append_reviews, extract_reviews

MOCK_HTML = """
<!DOCTYPE html>
<html>
  <body>
    <div role="main">
      <div class="jftiEf" data-review-id="r1">
        <button class="WEBjve">Alice Nguyen</button>
        <span class="rsqaWe">2 weeks ago</span>
        <span role="img" aria-label="4 stars"></span>
        <span class="wiI7pd">Great location near the subway, but the room was noisy at night.</span>
      </div>
      <div class="jftiEf" data-review-id="r2">
        <button class="WEBjve">Bob Tran</button>
        <span class="rsqaWe">1 month ago</span>
        <span role="img" aria-label="5 stars"></span>
        <span class="wiI7pd">Spotless rooms and friendly staff. Would stay again.</span>
      </div>
      <div class="jftiEf" data-review-id="r3">
        <button class="WEBjve">Carol Lee</button>
        <span class="rsqaWe">3 months ago</span>
        <span role="img" aria-label="2 stars"></span>
        <span class="wiI7pd"></span>
      </div>
    </div>
  </body>
</html>
"""


async def run_mock_extraction_test() -> None:
    async with async_playwright() as playwright:
        browser = await playwright.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.set_content(MOCK_HTML)
        reviews = await extract_reviews(page, "Hotel Example 1")
        await browser.close()

    assert len(reviews) == 2, f"Expected 2 text reviews, got {len(reviews)}"
    assert reviews[0].reviewer_name == "Alice Nguyen"
    assert reviews[0].rating == 4
    assert "noisy" in reviews[0].review_text

    output = Path("raw_reviews.csv")
    if output.exists():
        output.unlink()
    append_reviews(reviews, output)

    df = pd.read_csv(output)
    assert list(df.columns) == RAW_REVIEW_COLUMNS
    assert len(df) == 2
    print("Mock scraper test passed:", len(df), "rows written to raw_reviews.csv")


if __name__ == "__main__":
    asyncio.run(run_mock_extraction_test())
