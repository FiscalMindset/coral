#!/usr/bin/env python3
"""Scrape web pages and write structured JSONL for the Coral web_scraper source.

Zero external dependencies — uses only Python stdlib.

Usage:
    python3 scrape.py https://example.com https://example.com/about
    python3 scrape.py --file urls.txt
    python3 scrape.py --file urls.txt --output ~/.coral/web_scraper

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
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

DEFAULT_OUTPUT = os.path.expanduser("~/.coral/web_scraper")
USER_AGENT = (
    "Mozilla/5.0 (compatible; CoralWebScraper/1.0; "
    "+https://github.com/withcoral/coral)"
)


class PageParser(HTMLParser):
    def __init__(self, base_url):
        super().__init__()
        self.base_url = base_url
        self.title = None
        self.description = None
        self.language = None
        self.links = []
        self.text_parts = []
        self._in_title = False
        self._skip_tags = {"script", "style", "noscript"}
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)

        if tag == "html" and "lang" in attrs_dict:
            self.language = attrs_dict["lang"]

        if tag == "title":
            self._in_title = True

        if tag in self._skip_tags:
            self._skip_depth += 1

        if tag == "meta":
            name = attrs_dict.get("name", "").lower()
            content = attrs_dict.get("content", "")
            if name == "description" and content:
                self.description = content.strip()

        if tag == "a" and "href" in attrs_dict:
            href = attrs_dict["href"].strip()
            if href and not href.startswith(("#", "javascript:", "mailto:", "tel:")):
                self.links.append({"href": href, "text_parts": []})

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        if tag in self._skip_tags and self._skip_depth > 0:
            self._skip_depth -= 1
        if tag == "a" and self.links and "text_parts" in self.links[-1]:
            link = self.links[-1]
            link["text"] = " ".join(link.pop("text_parts")).strip() or None

    def handle_data(self, data):
        if self._in_title:
            self.title = (self.title or "") + data

        if self._skip_depth == 0:
            stripped = data.strip()
            if stripped:
                self.text_parts.append(stripped)

        if self.links and "text_parts" in self.links[-1]:
            self.links[-1]["text_parts"].append(data.strip())

    def get_text(self):
        return "\n".join(self.text_parts)

    def get_title(self):
        return self.title.strip() if self.title else None

    def get_links(self):
        parsed_base = urlparse(self.base_url)
        result = []
        for link in self.links:
            absolute = urljoin(self.base_url, link["href"])
            parsed = urlparse(absolute)
            is_external = parsed.netloc != parsed_base.netloc
            result.append({
                "source_url": self.base_url,
                "href": absolute,
                "text": link.get("text"),
                "is_external": is_external,
            })
        return result


def scrape_url(url, timeout=30):
    req = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        resp = urlopen(req, timeout=timeout)
        final_url = resp.url
        status_code = resp.status
        content_type = resp.headers.get("Content-Type", "")
        html = resp.read().decode("utf-8", errors="replace")
        return {
            "final_url": final_url,
            "status_code": status_code,
            "content_type": content_type,
            "html": html,
        }
    except HTTPError as exc:
        return {
            "final_url": url,
            "status_code": exc.code,
            "content_type": exc.headers.get("Content-Type", ""),
            "html": "",
        }
    except URLError as exc:
        print(f"  ✗ {url}: {exc.reason}", file=sys.stderr)
        return None
    except Exception as exc:
        print(f"  ✗ {url}: {exc}", file=sys.stderr)
        return None


def main():
    parser = argparse.ArgumentParser(description="Scrape URLs to JSONL for Coral")
    parser.add_argument("urls", nargs="*", help="URLs to scrape")
    parser.add_argument("--file", "-f", help="File with one URL per line")
    parser.add_argument(
        "--output", "-o", default=DEFAULT_OUTPUT,
        help=f"Output directory (default: {DEFAULT_OUTPUT})",
    )
    parser.add_argument("--timeout", "-t", type=int, default=30, help="Request timeout")
    args = parser.parse_args()

    urls = list(args.urls)
    if args.file:
        with open(args.file) as fh:
            urls.extend(line.strip() for line in fh if line.strip() and not line.startswith("#"))

    if not urls:
        parser.error("No URLs provided. Pass URLs as arguments or use --file.")

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)
    pages_path = output_dir / "pages.jsonl"
    links_path = output_dir / "links.jsonl"

    pages_count = 0
    links_count = 0

    with open(pages_path, "w") as pages_fh, open(links_path, "w") as links_fh:
        for url in urls:
            if not url.startswith(("http://", "https://")):
                url = "https://" + url

            print(f"  → {url}")
            result = scrape_url(url, timeout=args.timeout)
            if result is None:
                continue

            page_parser = PageParser(url)
            try:
                page_parser.feed(result["html"])
            except Exception:
                pass

            page = {
                "url": url,
                "final_url": result["final_url"],
                "title": page_parser.get_title(),
                "description": page_parser.description,
                "text": page_parser.get_text(),
                "status_code": result["status_code"],
                "content_type": result["content_type"],
                "language": page_parser.language,
                "scraped_at": datetime.now(timezone.utc).isoformat(),
            }
            pages_fh.write(json.dumps(page) + "\n")
            pages_count += 1

            for link in page_parser.get_links():
                links_fh.write(json.dumps(link) + "\n")
                links_count += 1

    print(f"\n  ✓ {pages_count} pages → {pages_path}")
    print(f"  ✓ {links_count} links → {links_path}")


if __name__ == "__main__":
    main()
