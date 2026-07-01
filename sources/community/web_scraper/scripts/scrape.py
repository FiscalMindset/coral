#!/usr/bin/env python3
"""Scrape web pages and write structured JSONL for the Coral web_scraper source.

Uses requests + BeautifulSoup + lxml for robust scraping.
Optional: --js flag uses Playwright for JavaScript-rendered pages.

Usage:
    python3 scrape.py https://example.com https://example.com/about
    python3 scrape.py --file urls.txt
    python3 scrape.py --js https://spa-site.com        # JS rendering
    python3 scrape.py --file urls.txt --output ~/.coral/web_scraper

Dependencies:
    pip install requests beautifulsoup4 lxml             # required
    pip install playwright && playwright install chromium # optional, for --js

Output:
    pages.jsonl  — one row per URL with title, text, metadata
    links.jsonl  — one row per discovered link on each page
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse

try:
    import requests
except ImportError:
    sys.exit("Missing dependency: pip install requests")

try:
    from bs4 import BeautifulSoup
except ImportError:
    sys.exit("Missing dependency: pip install beautifulsoup4")

try:
    import lxml  # noqa: F401
    BS_PARSER = "lxml"
except ImportError:
    BS_PARSER = "html.parser"
    print(
        "Warning: lxml not installed, falling back to html.parser. "
        "Install for better parsing: pip install lxml",
        file=sys.stderr,
    )

DEFAULT_OUTPUT = os.path.expanduser("~/.coral/web_scraper")
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def fetch_with_requests(url, timeout=30):
    headers = {"User-Agent": USER_AGENT}
    try:
        resp = requests.get(url, headers=headers, timeout=timeout, allow_redirects=True)
        return {
            "final_url": resp.url,
            "status_code": resp.status_code,
            "content_type": resp.headers.get("Content-Type", ""),
            "html": resp.text,
        }
    except requests.RequestException as exc:
        print(f"  ✗ {url}: {exc}", file=sys.stderr)
        return None


def create_playwright_fetcher(timeout=30):
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        sys.exit(
            "Missing dependency for --js mode:\n"
            "  pip install playwright && playwright install chromium"
        )

    ctx = sync_playwright().start()
    browser = ctx.chromium.launch(headless=True)

    def fetch(url, timeout=timeout):
        page = browser.new_page(user_agent=USER_AGENT)
        try:
            resp = page.goto(url, timeout=timeout * 1000, wait_until="load")
            status_code = resp.status if resp else 0
            content_type = resp.headers.get("content-type", "") if resp else ""
            html = page.content()
            final_url = page.url
            return {
                "final_url": final_url,
                "status_code": status_code,
                "content_type": content_type,
                "html": html,
            }
        except Exception as exc:
            print(f"  ✗ {url}: {exc}", file=sys.stderr)
            return None
        finally:
            page.close()

    def cleanup():
        browser.close()
        ctx.stop()

    return fetch, cleanup


def extract_page(url, result):
    soup = BeautifulSoup(result["html"], BS_PARSER)

    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else None

    meta_desc = soup.find("meta", attrs={"name": re.compile(r"^description$", re.I)})
    description = (
        meta_desc["content"].strip()
        if meta_desc and meta_desc.get("content")
        else None
    )

    html_tag = soup.find("html")
    language = html_tag.get("lang") if html_tag else None

    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    text = soup.get_text(separator="\n", strip=True)

    return {
        "url": url,
        "final_url": result["final_url"],
        "title": title,
        "description": description,
        "text": text,
        "status_code": result["status_code"],
        "content_type": result["content_type"],
        "language": language,
        "scraped_at": datetime.now(timezone.utc).isoformat(),
    }


def extract_links(base_url, result):
    soup = BeautifulSoup(result["html"], BS_PARSER)
    final_url = result["final_url"]
    parsed_base = urlparse(final_url)
    links = []

    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"].strip()
        if not href or href.startswith(("#", "javascript:", "mailto:", "tel:")):
            continue

        absolute = urljoin(final_url, href)
        parsed = urlparse(absolute)
        is_external = parsed.netloc != parsed_base.netloc
        link_text = a_tag.get_text(" ", strip=True) or None

        links.append({
            "source_url": base_url,
            "href": absolute,
            "text": link_text,
            "is_external": is_external,
        })

    return links


def main():
    parser = argparse.ArgumentParser(
        description="Scrape URLs to JSONL for Coral web_scraper source"
    )
    parser.add_argument("urls", nargs="*", help="URLs to scrape")
    parser.add_argument("--file", "-f", help="File with one URL per line")
    parser.add_argument(
        "--output", "-o", default=DEFAULT_OUTPUT,
        help=f"Output directory (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument(
        "--js", action="store_true",
        help="Use Playwright for JS-rendered pages (requires: pip install playwright)",
    )
    parser.add_argument(
        "--timeout", "-t", type=int, default=30, help="Request timeout in seconds"
    )
    args = parser.parse_args()

    urls = list(args.urls)
    if args.file:
        with open(args.file) as fh:
            urls.extend(
                line.strip() for line in fh
                if line.strip() and not line.startswith("#")
            )

    if not urls:
        parser.error("No URLs provided. Pass URLs as arguments or use --file.")

    pw_cleanup = None
    if args.js:
        fetch, pw_cleanup = create_playwright_fetcher(timeout=args.timeout)
    else:
        fetch = fetch_with_requests

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    pages_path = output_dir / "pages.jsonl"
    links_path = output_dir / "links.jsonl"

    pages_count = 0
    links_count = 0

    try:
        with open(pages_path, "w") as pages_fh, open(links_path, "w") as links_fh:
            for url in urls:
                if not url.startswith(("http://", "https://")):
                    url = "https://" + url

                mode = "JS" if args.js else "HTTP"
                print(f"  → [{mode}] {url}")
                result = fetch(url, timeout=args.timeout)
                if result is None:
                    continue

                page = extract_page(url, result)
                pages_fh.write(json.dumps(page) + "\n")
                pages_count += 1

                page_links = extract_links(url, result)
                for link in page_links:
                    links_fh.write(json.dumps(link) + "\n")
                    links_count += 1
    finally:
        if pw_cleanup:
            pw_cleanup()

    print(f"\n  ✓ {pages_count} pages → {pages_path}")
    print(f"  ✓ {links_count} links → {links_path}")


if __name__ == "__main__":
    main()
