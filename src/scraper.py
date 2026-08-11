"""Google Maps hotel review scraper using Playwright."""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import random
import re
import time
from pathlib import Path
from urllib.parse import quote_plus, urlparse

import pandas as pd
from playwright.async_api import (
    BrowserContext,
    Page,
    TimeoutError as PlaywrightTimeoutError,
    async_playwright,
)

from schemas import RAW_REVIEW_COLUMNS, RawReview

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

COMPETITORS_FILE = Path("competitors.json")
OUTPUT_FILE = Path("raw_reviews.csv")
MAX_SCROLL_ITERATIONS = 50
SCROLL_STABLE_ROUNDS = 3
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)


def load_competitors(path: Path = COMPETITORS_FILE) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("competitors.json must contain a JSON array")
    return data


def normalize_maps_url(url: str, hotel_name: str) -> str:
    cleaned = url.strip()
    if cleaned:
        return cleaned
    return f"https://www.google.com/maps/search/{quote_plus(hotel_name)}"


def load_existing_keys(path: Path = OUTPUT_FILE) -> set[tuple[str, str, str, str]]:
    if not path.exists():
        return set()
    df = pd.read_csv(path)
    keys: set[tuple[str, str, str, str]] = set()
    for _, row in df.iterrows():
        keys.add(
            (
                str(row["hotel_name"]),
                str(row["reviewer_name"]),
                str(row["review_date"]),
                str(row["review_text"]),
            )
        )
    return keys


def append_reviews(reviews: list[RawReview], path: Path = OUTPUT_FILE) -> None:
    if not reviews:
        return
    rows = [review.model_dump() for review in reviews]
    df = pd.DataFrame(rows, columns=RAW_REVIEW_COLUMNS)
    write_header = not path.exists()
    df.to_csv(path, mode="a", index=False, header=write_header, encoding="utf-8")
    logger.info("Appended %d review(s) to %s", len(reviews), path)


async def random_delay(min_seconds: float, max_seconds: float) -> None:
    await asyncio.sleep(random.uniform(min_seconds, max_seconds))


async def apply_stealth(context: BrowserContext) -> None:
    await context.add_init_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined});"
    )


async def dismiss_dialogs(page: Page) -> None:
    selectors = [
        'button:has-text("Accept all")',
        'button:has-text("Reject all")',
        'button:has-text("Cancel")',
        'button[aria-label="Close"]',
    ]
    for selector in selectors:
        button = page.locator(selector).first
        try:
            if await button.count() > 0 and await button.is_visible():
                await button.click(timeout=2000)
                await random_delay(0.5, 1.0)
        except PlaywrightTimeoutError:
            continue


async def is_signed_in(page: Page) -> bool:
    try:
        await page.goto(
            "https://myaccount.google.com/",
            wait_until="domcontentloaded",
            timeout=60000,
        )
        await dismiss_dialogs(page)
        if await page.locator('input[type="email"]').count() > 0:
            return False
        if await page.locator('input[type="password"]').count() > 0:
            return False
        if await page.locator('text=Sign in').count() > 0:
            return False
        return True
    except PlaywrightTimeoutError:
        return False


async def sign_in_google(page: Page, email: str, password: str) -> bool:
    try:
        await page.goto(
            "https://accounts.google.com/ServiceLogin?hl=en&continue=https://www.google.com/maps",
            wait_until="domcontentloaded",
            timeout=60000,
        )
        await dismiss_dialogs(page)
        email_input = page.locator('input[type="email"]').first
        await email_input.fill(email, timeout=20000)
        await page.locator('button:has-text("Next")').first.click()
        await page.wait_for_selector('input[type="password"]', timeout=20000)
        await page.locator('input[type="password"]').first.fill(password, timeout=20000)
        await page.locator('button:has-text("Next")').first.click()
        await page.wait_for_load_state("networkidle", timeout=30000)
        await random_delay(2.0, 3.0)
        if "signin" in page.url or "challenge" in page.url:
            return False
        return await is_signed_in(page)
    except PlaywrightTimeoutError:
        return False


async def ensure_signed_in(
    page: Page, email: str | None, password: str | None
) -> bool:
    signed_in = await is_signed_in(page)
    if signed_in:
        logger.info("Already signed in to Google.")
        return True

    if not email or not password:
        logger.warning(
            "Google account is not signed in and no credentials were provided. "
            "Scraping may be limited."
        )
        return False

    logger.info("Signing in to Google with provided credentials.")
    success = await sign_in_google(page, email, password)
    if not success:
        logger.warning(
            "Google sign-in failed. Proceeding without an authenticated session may lead to limited or blocked results."
        )
    return success


async def is_limited_maps_view(page: Page) -> bool:
    try:
        return await page.locator("text=limited view of Google Maps").count() > 0
    except PlaywrightTimeoutError:
        return False


async def click_reviews_tab(page: Page) -> None:
    selectors = [
        'button[aria-label*="Reviews"]',
        'button[aria-label*="Review for"]',
        'button[aria-label*="Đánh giá"]',
        'button[data-tab-index="1"]',
        'button:has-text("Reviews")',
        'button:has-text("Đánh giá")',
    ]
    for selector in selectors:
        button = page.locator(selector).first
        try:
            if await button.count() > 0 and await button.is_visible():
                await button.click()
                await random_delay(1.0, 2.0)
                return
        except PlaywrightTimeoutError:
            continue

    rating_link = page.locator(
        'div.F7nice button, div.F7nice span[aria-label*="stars"], '
        'button[aria-label*="stars"]'
    ).first
    try:
        if await rating_link.count() > 0 and await rating_link.is_visible():
            await rating_link.click()
            await random_delay(1.0, 2.0)
    except PlaywrightTimeoutError:
        logger.warning("Reviews tab button not found; continuing with current view")


async def get_review_pane(page: Page):
    selectors = [
        'div[role="main"] div.m6QErb[tabindex="-1"]',
        'div[role="main"] div[aria-label*="Reviews for"]',
        'div[role="main"] div[aria-label*="Reviews"]',
        'div.section-scrollbox',
    ]
    for selector in selectors:
        pane = page.locator(selector).first
        if await pane.count() > 0:
            return pane
    return page.locator('div[role="main"]').first


async def expand_review_text(page: Page) -> None:
    selectors = [
        'button:has-text("More")',
        'button:has-text("Thêm")',
        'button[aria-label="See more"]',
        'button[aria-label="Xem thêm"]',
    ]
    for selector in selectors:
        buttons = page.locator(selector)
        count = await buttons.count()
        for index in range(count):
            button = buttons.nth(index)
            try:
                if await button.is_visible():
                    await button.click(timeout=2000)
                    await random_delay(0.5, 1.5)
            except PlaywrightTimeoutError:
                continue


async def scroll_review_pane(page: Page) -> int:
    pane = await get_review_pane(page)
    previous_count = await page.locator('div[data-review-id], div.jftiEf').count()
    try:
        await pane.evaluate("el => { el.scrollTop = el.scrollHeight; }")
    except PlaywrightTimeoutError:
        await page.mouse.wheel(0, 2500)
    await random_delay(1.5, 3.5)
    return await page.locator('div[data-review-id], div.jftiEf').count() - previous_count


def parse_rating(raw_value: str) -> int | None:
    match = re.search(r"(\d)", raw_value)
    if not match:
        return None
    rating = int(match.group(1))
    if 1 <= rating <= 5:
        return rating
    return None


async def extract_reviews(page: Page, hotel_name: str) -> list[RawReview]:
    cards = page.locator("div[data-review-id], div.jftiEf")
    count = await cards.count()
    reviews: list[RawReview] = []

    for index in range(count):
        card = cards.nth(index)
        try:
            reviewer_name = (
                await card.locator(".d4r55, button.WEBjve").first.inner_text(timeout=2000)
            ).strip()
            date_text = (
                await card.locator(".rsqaWe, span.xRkPPb").first.inner_text(timeout=2000)
            ).strip()
            rating_attr = await card.locator('span[role="img"]').first.get_attribute("aria-label")
            rating = parse_rating(rating_attr or "")
            review_text = (
                await card.locator(".wiI7pd, span.wiI7pd").first.inner_text(timeout=2000)
            ).strip()
        except PlaywrightTimeoutError:
            continue

        if not review_text:
            continue
        if rating is None:
            continue

        try:
            review = RawReview(
                hotel_name=hotel_name,
                reviewer_name=reviewer_name or "Unknown",
                rating=rating,
                review_date=date_text or "Unknown",
                review_text=review_text,
            )
            reviews.append(review)
        except Exception as exc:
            logger.debug("Skipped invalid review row: %s", exc)

    return reviews


async def scrape_hotel(
    page: Page,
    hotel_name: str,
    url: str,
    existing_keys: set[tuple[str, str, str, str]],
) -> int:
    logger.info("Scraping %s", hotel_name)
    target_url = normalize_maps_url(url, hotel_name)
    await page.goto(target_url, wait_until="domcontentloaded", timeout=60000)
    await random_delay(2.0, 4.0)
    await dismiss_dialogs(page)

    if await is_limited_maps_view(page):
        logger.warning(
            "Google Maps is showing a limited view for %s. "
            "Sign in using --profile-dir for better results.",
            hotel_name,
        )

    await click_reviews_tab(page)
    await random_delay(1.5, 3.0)

    stable_rounds = 0
    saved_count = 0

    for iteration in range(MAX_SCROLL_ITERATIONS):
        await expand_review_text(page)
        new_reviews = await extract_reviews(page, hotel_name)
        batch: list[RawReview] = []

        for review in new_reviews:
            key = (
                review.hotel_name,
                review.reviewer_name,
                review.review_date,
                review.review_text,
            )
            if key not in existing_keys:
                existing_keys.add(key)
                batch.append(review)

        if batch:
            append_reviews(batch)
            saved_count += len(batch)
            logger.info(
                "Iteration %d: saved %d new review(s) for %s",
                iteration + 1,
                len(batch),
                hotel_name,
            )

        loaded = await scroll_review_pane(page)
        if loaded <= 0:
            stable_rounds += 1
        else:
            stable_rounds = 0

        if stable_rounds >= SCROLL_STABLE_ROUNDS:
            logger.info("No new reviews loaded after %d scrolls; stopping.", iteration + 1)
            break

    return saved_count


async def run_scraper(
    headless: bool = False,
    profile_dir: str | None = None,
    google_email: str | None = None,
    google_password: str | None = None,
) -> None:
    competitors = load_competitors()
    existing_keys = load_existing_keys()
    valid_entries = [
        entry
        for entry in competitors
        if str(entry.get("hotel_name", "")).strip()
    ]

    if not valid_entries:
        logger.warning("No competitors found in %s", COMPETITORS_FILE)
        return

    async with async_playwright() as playwright:
        launch_kwargs = {
            "headless": headless,
            "args": ["--disable-blink-features=AutomationControlled"],
        }
        if profile_dir:
            context = await playwright.chromium.launch_persistent_context(
                profile_dir,
                locale="en-US",
                viewport={"width": 1400, "height": 900},
                user_agent=USER_AGENT,
                **launch_kwargs,
            )
            await apply_stealth(context)
            page = context.pages[0] if context.pages else await context.new_page()
            browser = None
        else:
            try:
                browser = await playwright.chromium.launch(channel="chrome", **launch_kwargs)
            except Exception:
                browser = await playwright.chromium.launch(**launch_kwargs)
            context = await browser.new_context(
                locale="en-US",
                viewport={"width": 1400, "height": 900},
                user_agent=USER_AGENT,
            )
            await apply_stealth(context)
            page = await context.new_page()

        await ensure_signed_in(page, google_email, google_password)

        total_saved = 0
        for entry in valid_entries:
            hotel_name = str(entry["hotel_name"]).strip()
            url = str(entry.get("google_maps_url", "")).strip()
            if not url:
                logger.warning(
                    "No google_maps_url for %s; using Maps search fallback.",
                    hotel_name,
                )
            try:
                saved = await scrape_hotel(page, hotel_name, url, existing_keys)
                total_saved += saved
            except Exception as exc:
                logger.error("Failed to scrape %s: %s", hotel_name, exc)
            await random_delay(2.0, 4.0)

        if browser is not None:
            await browser.close()
        else:
            await context.close()

    logger.info("Scraping complete. Total new reviews saved: %d", total_saved)


def main() -> None:
    parser = argparse.ArgumentParser(description="Scrape Google Maps hotel reviews.")
    parser.add_argument(
        "--headless",
        action="store_true",
        help="Run browser in headless mode (default: visible browser).",
    )
    parser.add_argument(
        "--profile-dir",
        default=None,
        help="Persistent browser profile directory (use after signing in to Google).",
    )
    parser.add_argument(
        "--google-email",
        default=None,
        help="Google account email to sign in before scraping.",
    )
    parser.add_argument(
        "--google-password",
        default=None,
        help="Google account password to sign in before scraping.",
    )
    args = parser.parse_args()
    if (args.google_email and not args.google_password) or (
        args.google_password and not args.google_email
    ):
        parser.error("Both --google-email and --google-password must be provided together.")
    start = time.time()
    asyncio.run(
        run_scraper(
            headless=args.headless,
            profile_dir=args.profile_dir,
            google_email=args.google_email,
            google_password=args.google_password,
        )
    )
    logger.info("Finished in %.1f seconds", time.time() - start)


if __name__ == "__main__":
    main()
