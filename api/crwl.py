"""Crawl a site section and count HTML files whose names start with O-Z."""
import re
import subprocess
from collections import deque
from html.parser import HTMLParser
from urllib.parse import urljoin, urldefrag, urlparse

START = "https://sanand0.github.io/tdsdata/crawl_html/"


class LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            href = dict(attrs).get("href")
            if href:
                self.links.append(href)


def fetch(url):
    # curl, because Python's resolver fails on this machine for some hosts
    return subprocess.run(["curl", "-sL", url], capture_output=True, text=True, encoding="utf-8").stdout


def crawl(start):
    seen, queue = {start}, deque([start])
    while queue:
        url = queue.popleft()
        parser = LinkParser()
        parser.feed(fetch(url))
        for href in parser.links:
            link = urldefrag(urljoin(url, href)).url
            if link.startswith(start) and link not in seen:
                seen.add(link)
                queue.append(link)
    return seen


def main():
    pages = crawl(START)
    html_files = sorted(p for p in pages if p.endswith(".html"))
    names = [urlparse(p).path.rsplit("/", 1)[-1] for p in html_files]
    o_to_z = [n for n in names if re.match(r"[o-z]", n, re.I)]
    print(f"Pages crawled: {len(pages)} | HTML files: {len(html_files)}")
    print(f"HTML files starting with O-Z: {len(o_to_z)}")


if __name__ == "__main__":
    main()
