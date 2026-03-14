"""
IT-P4: AccessibilityAI — WCAG 2.2 Compliance Auditor Starter Skeleton
=======================================================================
Run:
    python starter.py --data_dir ./data --output_dir ./submission

Requirements:
    pip install playwright beautifulsoup4 aiohttp aiofiles
    pip install Pillow numpy scikit-learn
    playwright install chromium
"""

import argparse
import asyncio
import colorsys
import json
import logging
import math
import re
import urllib.parse
from dataclasses import dataclass, asdict, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple
from collections import defaultdict

from bs4 import BeautifulSoup

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_DATA_DIR = "./data"
DEFAULT_OUTPUT_DIR = "./submission"
TARGET_URLS_FILENAME = "target_urls.txt"
CONFIG_FILENAME = "config.json"
DEFAULT_MAX_PAGES = 100
DEFAULT_TIMEOUT_SEC = 60

# WCAG 2.2 Level AA criterion IDs (subset — add remaining to complete all 50)
WCAG_CRITERIA = [
    "1.1.1",  # Non-text Content
    "1.2.1",  # Audio-only and Video-only
    "1.2.2",  # Captions (Prerecorded)
    "1.3.1",  # Info and Relationships
    "1.3.2",  # Meaningful Sequence
    "1.3.3",  # Sensory Characteristics
    "1.3.4",  # Orientation
    "1.3.5",  # Identify Input Purpose
    "1.4.1",  # Use of Color
    "1.4.2",  # Audio Control
    "1.4.3",  # Contrast (Minimum)
    "1.4.4",  # Resize Text
    "1.4.5",  # Images of Text
    "1.4.10", # Reflow
    "1.4.11", # Non-text Contrast
    "1.4.12", # Text Spacing
    "1.4.13", # Content on Hover or Focus
    "2.1.1",  # Keyboard
    "2.1.2",  # No Keyboard Trap
    "2.1.4",  # Character Key Shortcuts
    "2.2.1",  # Timing Adjustable
    "2.2.2",  # Pause, Stop, Hide
    "2.3.1",  # Three Flashes or Below Threshold
    "2.4.1",  # Bypass Blocks
    "2.4.2",  # Page Titled
    "2.4.3",  # Focus Order
    "2.4.4",  # Link Purpose (In Context)
    "2.4.6",  # Headings and Labels
    "2.4.7",  # Focus Visible
    "2.4.11", # Focus Not Obscured (Minimum)
    "2.5.1",  # Pointer Gestures
    "2.5.2",  # Pointer Cancellation
    "2.5.3",  # Label in Name
    "2.5.4",  # Motion Actuation
    "2.5.7",  # Dragging Movements
    "2.5.8",  # Target Size (Minimum)
    "3.1.1",  # Language of Page
    "3.1.2",  # Language of Parts
    "3.2.1",  # On Focus
    "3.2.2",  # On Input
    "3.2.3",  # Consistent Navigation
    "3.2.4",  # Consistent Identification
    "3.2.6",  # Consistent Help
    "3.3.1",  # Error Identification
    "3.3.2",  # Labels or Instructions
    "3.3.3",  # Error Suggestion
    "3.3.4",  # Error Prevention (Legal, Financial, Data)
    "3.3.7",  # Redundant Entry
    "3.3.8",  # Accessible Authentication (Minimum)
    "4.1.2",  # Name, Role, Value
    "4.1.3",  # Status Messages
]

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class Violation:
    criterion: str
    element_selector: str
    severity: str          # critical | serious | moderate | minor
    description: str
    suggested_fix: str
    auto_fixed: bool = False
    page_url: str = ""

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class PageData:
    url: str
    html: str
    accessibility_tree: Dict = field(default_factory=dict)
    screenshot_bytes: bytes = field(default_factory=bytes)


# ---------------------------------------------------------------------------
# WCAG colour contrast utilities
# ---------------------------------------------------------------------------


def _parse_rgb(css_color: str) -> Optional[Tuple[int, int, int]]:
    """Parse 'rgb(r, g, b)' or '#rrggbb' into (r, g, b) tuple."""
    css_color = css_color.strip()
    m = re.match(r"rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)", css_color)
    if m:
        return int(m.group(1)), int(m.group(2)), int(m.group(3))
    m = re.match(r"#([0-9a-fA-F]{6})", css_color)
    if m:
        h = m.group(1)
        return int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return None


def _relative_luminance(r: int, g: int, b: int) -> float:
    """WCAG 2.x relative luminance formula."""
    def linearise(c: float) -> float:
        c = c / 255.0
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4
    return 0.2126 * linearise(r) + 0.7152 * linearise(g) + 0.0722 * linearise(b)


def contrast_ratio(fg: Tuple[int, int, int], bg: Tuple[int, int, int]) -> float:
    """Return WCAG contrast ratio (1:1 to 21:1)."""
    l1 = _relative_luminance(*fg)
    l2 = _relative_luminance(*bg)
    lighter = max(l1, l2)
    darker = min(l1, l2)
    return (lighter + 0.05) / (darker + 0.05)


def find_compliant_bg_color(fg: Tuple[int, int, int], bg: Tuple[int, int, int], target_ratio: float = 4.5) -> str:
    """Binary-search for the nearest background colour (lighter or darker) achieving target_ratio.

    Returns a hex colour string.
    TODO: Extend to also try darkening the background.
    """
    r, g, b = bg
    h, l, s = colorsys.rgb_to_hls(r / 255, g / 255, b / 255)

    lo, hi = l, 1.0
    for _ in range(40):
        mid = (lo + hi) / 2.0
        nr, ng, nb = [int(x * 255) for x in colorsys.hls_to_rgb(h, mid, s)]
        if contrast_ratio(fg, (nr, ng, nb)) >= target_ratio:
            hi = mid
        else:
            lo = mid

    nr, ng, nb = [int(x * 255) for x in colorsys.hls_to_rgb(h, hi, s)]
    return f"#{nr:02x}{ng:02x}{nb:02x}"


# ---------------------------------------------------------------------------
# Static HTML checks
# ---------------------------------------------------------------------------


def check_images_alt(soup: BeautifulSoup, page_url: str) -> List[Violation]:
    """WCAG 1.1.1 — images must have an alt attribute."""
    violations = []
    for img in soup.find_all("img"):
        # Skip if presentational
        if img.get("role") in ("presentation", "none"):
            continue
        if img.get("aria-hidden") == "true":
            continue
        if img.get("alt") is None:
            selector = _element_selector(img)
            violations.append(Violation(
                criterion="1.1.1",
                element_selector=selector,
                severity="critical",
                description="Image is missing an alt attribute",
                suggested_fix='Add alt="" (empty for decorative) or a descriptive alt text',
                page_url=page_url,
            ))
    return violations


def check_form_labels(soup: BeautifulSoup, page_url: str) -> List[Violation]:
    """WCAG 1.3.1 — every input must have an associated label or aria-label."""
    violations = []
    skip_types = {"hidden", "button", "submit", "reset", "image"}
    for inp in soup.find_all("input"):
        if inp.get("type", "text").lower() in skip_types:
            continue
        has_label = False
        inp_id = inp.get("id")
        if inp_id and soup.find("label", attrs={"for": inp_id}):
            has_label = True
        if inp.get("aria-label") or inp.get("aria-labelledby"):
            has_label = True
        if not has_label:
            violations.append(Violation(
                criterion="1.3.1",
                element_selector=_element_selector(inp),
                severity="serious",
                description="Form input has no associated label",
                suggested_fix="Add a <label for='id'> element or an aria-label attribute",
                page_url=page_url,
            ))
    return violations


def check_page_title(soup: BeautifulSoup, page_url: str) -> List[Violation]:
    """WCAG 2.4.2 — page must have a non-empty <title>."""
    title = soup.find("title")
    if not title or not title.get_text(strip=True):
        return [Violation(
            criterion="2.4.2",
            element_selector="head > title",
            severity="serious",
            description="Page has no descriptive <title> element",
            suggested_fix="Add <title>Descriptive Page Name</title> in the <head>",
            page_url=page_url,
        )]
    return []


def check_language_attribute(soup: BeautifulSoup, page_url: str) -> List[Violation]:
    """WCAG 3.1.1 — <html> must have a lang attribute."""
    html_tag = soup.find("html")
    if not html_tag or not html_tag.get("lang"):
        return [Violation(
            criterion="3.1.1",
            element_selector="html",
            severity="serious",
            description="<html> element is missing a lang attribute",
            suggested_fix='Add lang="en" (or appropriate language code) to the <html> tag',
            page_url=page_url,
        )]
    return []


def check_heading_hierarchy(soup: BeautifulSoup, page_url: str) -> List[Violation]:
    """WCAG 1.3.1 / 2.4.6 — headings must not skip levels."""
    violations = []
    prev_level = 0
    for tag in soup.find_all(re.compile(r"^h[1-6]$")):
        level = int(tag.name[1])
        if prev_level > 0 and level > prev_level + 1:
            violations.append(Violation(
                criterion="1.3.1",
                element_selector=_element_selector(tag),
                severity="moderate",
                description=f"Heading level skipped: h{prev_level} followed by h{level}",
                suggested_fix=f"Change to h{prev_level + 1} or restructure the heading hierarchy",
                page_url=page_url,
            ))
        prev_level = level
    return violations


def _element_selector(tag) -> str:
    """Generate a simple CSS selector for a BeautifulSoup tag."""
    parts = [tag.name]
    tag_id = tag.get("id")
    if tag_id:
        parts.append(f"#{tag_id}")
    classes = tag.get("class", [])
    if classes:
        parts.append("." + ".".join(classes[:2]))
    return "".join(parts)


def run_static_checks(html: str, page_url: str) -> List[Violation]:
    """Run all static HTML checks on a page."""
    soup = BeautifulSoup(html, "html.parser")
    violations: List[Violation] = []
    violations += check_images_alt(soup, page_url)
    violations += check_form_labels(soup, page_url)
    violations += check_page_title(soup, page_url)
    violations += check_language_attribute(soup, page_url)
    violations += check_heading_hierarchy(soup, page_url)
    # TODO: add remaining 45 WCAG criteria checks
    return violations


# ---------------------------------------------------------------------------
# Crawler
# ---------------------------------------------------------------------------


class Crawler:
    """Async web crawler using aiohttp for static pages.

    For JavaScript-rendered pages, replace aiohttp with playwright (see HINTS.md).
    """

    def __init__(self, start_url: str, max_pages: int = DEFAULT_MAX_PAGES, timeout_sec: int = DEFAULT_TIMEOUT_SEC):
        self.start_url = start_url
        self.max_pages = max_pages
        self.timeout_sec = timeout_sec
        self._visited: Set[str] = set()
        self._origin = urllib.parse.urlparse(start_url).netloc

    async def crawl(self) -> List[PageData]:
        """Crawl the site and return PageData for each discovered page.

        TODO: Replace aiohttp fetching with playwright for SPA support:
            from playwright.async_api import async_playwright
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                await page.goto(url)
                html = await page.content()
                snapshot = await page.accessibility.snapshot()
        """
        import aiohttp

        results: List[PageData] = []
        queue: asyncio.Queue = asyncio.Queue()
        await queue.put(self.start_url)

        async with aiohttp.ClientSession() as session:
            while not queue.empty() and len(results) < self.max_pages:
                url = await queue.get()
                if url in self._visited:
                    continue
                self._visited.add(url)

                try:
                    async with session.get(url, timeout=aiohttp.ClientTimeout(total=self.timeout_sec)) as resp:
                        if resp.content_type and "html" not in resp.content_type:
                            continue
                        html = await resp.text(errors="replace")
                except Exception as exc:
                    log.debug("Failed to fetch %s: %s", url, exc)
                    continue

                page_data = PageData(url=url, html=html)
                results.append(page_data)
                log.debug("Crawled: %s (%d/%d)", url, len(results), self.max_pages)

                # Enqueue same-origin links
                soup = BeautifulSoup(html, "html.parser")
                for a_tag in soup.find_all("a", href=True):
                    href = urllib.parse.urljoin(url, a_tag["href"])
                    parsed = urllib.parse.urlparse(href)
                    if parsed.netloc == self._origin and href not in self._visited:
                        await queue.put(href)

        log.info("Crawl complete: %d pages from %s", len(results), self.start_url)
        return results


# ---------------------------------------------------------------------------
# Auto-fixer
# ---------------------------------------------------------------------------


def generate_autofix_patch(violation: Violation) -> Optional[str]:
    """Generate a minimal HTML/CSS patch string for fixable violation types.

    Returns the patch as a string, or None if auto-fix is not implemented for this criterion.
    """
    if violation.criterion == "1.1.1":
        return f'<!-- Auto-fix: add alt attribute -->\n<!-- {violation.element_selector} -->\nalt=""'
    if violation.criterion == "2.4.2":
        return "<title>TODO: Add descriptive page title</title>"
    if violation.criterion == "3.1.1":
        return 'lang="en"'
    # TODO: implement contrast auto-fix for criterion 1.4.3 using find_compliant_bg_color()
    return None


# ---------------------------------------------------------------------------
# Report writer
# ---------------------------------------------------------------------------


class ReportWriter:
    def __init__(self, output_dir: Path):
        self.output_dir = output_dir

    def _url_slug(self, url: str) -> str:
        parsed = urllib.parse.urlparse(url)
        slug = (parsed.netloc + parsed.path).strip("/").replace("/", "_").replace(".", "_")
        return slug or "root"

    def write_violations(self, url: str, violations: List[Violation]) -> Path:
        slug = self._url_slug(url)
        report_dir = self.output_dir / "reports" / slug
        report_dir.mkdir(parents=True, exist_ok=True)

        # Apply auto-fixes
        patches_dir = report_dir / "autofix_patches"
        fixed_count = 0
        for v in violations:
            patch = generate_autofix_patch(v)
            if patch:
                patches_dir.mkdir(parents=True, exist_ok=True)
                patch_file = patches_dir / f"{v.criterion}_{v.element_selector[:30]}.patch"
                patch_file.write_text(patch)
                v.auto_fixed = True
                fixed_count += 1

        path = report_dir / "violations.json"
        with open(path, "w") as f:
            json.dump([v.to_dict() for v in violations], f, indent=2)
        log.info("Wrote %d violations (%d auto-fixed) to %s", len(violations), fixed_count, path)
        return path

    def write_compliance_score(self, url: str, violations: List[Violation]) -> Path:
        slug = self._url_slug(url)
        report_dir = self.output_dir / "reports" / slug
        report_dir.mkdir(parents=True, exist_ok=True)

        violated_criteria = {v.criterion for v in violations}
        per_criterion = {c: ("FAIL" if c in violated_criteria else "PASS") for c in WCAG_CRITERIA}
        pass_count = sum(1 for v in per_criterion.values() if v == "PASS")
        compliance_score = round(pass_count / len(WCAG_CRITERIA) * 100, 1)

        data = {
            "url": url,
            "compliance_score_pct": compliance_score,
            "total_criteria": len(WCAG_CRITERIA),
            "passed": pass_count,
            "failed": len(WCAG_CRITERIA) - pass_count,
            "per_criterion": per_criterion,
        }
        path = report_dir / "compliance_score.json"
        with open(path, "w") as f:
            json.dump(data, f, indent=2)
        return path


# ---------------------------------------------------------------------------
# Summary aggregator
# ---------------------------------------------------------------------------


def compute_summary(all_violations: Dict[str, List[Violation]], output_dir: Path) -> Dict:
    """Compute aggregate metrics across all audited sites.

    Note: precision/recall require ground truth comparison — see evaluate.py.
    """
    total_violations = sum(len(v) for v in all_violations.values())
    auto_fixed = sum(1 for vs in all_violations.values() for v in vs if v.auto_fixed)
    auto_fix_rate = round(auto_fixed / total_violations * 100, 1) if total_violations > 0 else 0.0

    summary = {
        "sites_audited": len(all_violations),
        "total_violations_detected": total_violations,
        "auto_fixed_count": auto_fixed,
        "auto_fix_rate_pct": auto_fix_rate,
        "precision": 0.0,    # TODO: compute against ground truth in evaluate.py
        "recall": 0.0,       # TODO: compute against ground truth in evaluate.py
        "f1": 0.0,           # TODO: compute
        "false_positive_rate_pct": 0.0,  # TODO: compute
    }
    path = output_dir / "summary.json"
    with open(path, "w") as f:
        json.dump(summary, f, indent=2)
    log.info("Summary written to %s", path)
    return summary


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------


def load_config(data_dir: Path) -> Dict:
    config_path = data_dir / CONFIG_FILENAME
    defaults = {"max_pages": DEFAULT_MAX_PAGES, "timeout_sec": DEFAULT_TIMEOUT_SEC, "headless": True, "wcag_level": "AA"}
    if not config_path.exists():
        return defaults
    with open(config_path) as f:
        return {**defaults, **json.load(f)}


def load_target_urls(data_dir: Path) -> List[str]:
    path = data_dir / TARGET_URLS_FILENAME
    if not path.exists():
        log.warning("target_urls.txt not found — using example URL")
        return ["https://example.com"]
    with open(path) as f:
        return [line.strip() for line in f if line.strip()]


async def audit_url(url: str, config: Dict, writer: ReportWriter) -> Tuple[str, List[Violation]]:
    """Crawl one URL and run all checks."""
    crawler = Crawler(url, max_pages=config["max_pages"], timeout_sec=config["timeout_sec"])
    pages = await crawler.crawl()

    all_violations: List[Violation] = []
    for page in pages:
        violations = run_static_checks(page.html, page.url)
        # TODO: run dynamic checks using playwright for contrast, focus-order, etc.
        all_violations.extend(violations)

    writer.write_violations(url, all_violations)
    writer.write_compliance_score(url, all_violations)
    return url, all_violations


async def async_main(args: argparse.Namespace) -> None:
    data_dir = Path(args.data_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    config = load_config(data_dir)
    urls = load_target_urls(data_dir)
    writer = ReportWriter(output_dir)

    log.info("Auditing %d site(s)", len(urls))
    tasks = [audit_url(url, config, writer) for url in urls]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    all_violations: Dict[str, List[Violation]] = {}
    for result in results:
        if isinstance(result, Exception):
            log.error("Audit failed: %s", result)
        else:
            url, violations = result
            all_violations[url] = violations

    summary = compute_summary(all_violations, output_dir)
    log.info("Audit complete. Total violations: %d", summary["total_violations_detected"])


def main() -> None:
    parser = argparse.ArgumentParser(description="AccessibilityAI WCAG 2.2 Auditor — IT-P4")
    parser.add_argument("--data_dir", default=DEFAULT_DATA_DIR, help="Path to input data directory")
    parser.add_argument("--output_dir", default=DEFAULT_OUTPUT_DIR, help="Path to submission output directory")
    args = parser.parse_args()
    asyncio.run(async_main(args))


if __name__ == "__main__":
    main()
