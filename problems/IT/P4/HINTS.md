# AccessibilityAI — Hints

> Each tier costs score points. Only request when genuinely stuck.

## Tier 1 — Conceptual Direction (-5% score penalty)
WCAG 2.2 has four principles (POUR): **Perceivable, Operable, Understandable, Robust**. Split your tool into four matching analysis engines — do not try to build one monolithic checker. Within each engine, separate **static checks** (parsing raw HTML/CSS) from **dynamic checks** (inspecting the rendered accessibility tree). Static checks are fast and high-precision; dynamic checks catch failures invisible in the source. The quality of your **per-element CSS colour resolution** will determine your precision on the largest category of real-world failures (contrast violations).

## Tier 2 — Technique Guidance (-10% score penalty)
- **Crawler**: Use `playwright-python` (async API) instead of raw `aiohttp` for dynamic pages. `page.goto(url)` + `page.content()` gives you the fully rendered HTML; `page.accessibility.snapshot()` gives the accessibility tree as a Python dict — both are essential.
- **Contrast checking (1.4.3)**: Compute the WCAG relative luminance formula for foreground and background RGB; ratio = (L1 + 0.05) / (L2 + 0.05). Ratio < 4.5:1 for normal text, < 3:1 for large text. Use `playwright` to call `window.getComputedStyle(element)` to resolve the effective colour, then parse the `rgb(...)` string.
- **Alt text (1.1.1)**: In BeautifulSoup, `soup.find_all("img", alt=False)` finds images with no alt attribute. Cross-check against `role="presentation"` and `aria-hidden="true"` to avoid false positives.
- **Form labels (1.3.1)**: For every `<input>` not of type `hidden` or `button`, check for: an associated `<label for="id">`, an `aria-label` attribute, or an `aria-labelledby` pointing to a non-empty element.
- **Focus order (2.4.3)**: Use Playwright `page.keyboard.press("Tab")` repeatedly and record `page.evaluate("document.activeElement.tagName")` sequence; check that it matches the visual top-to-bottom, left-to-right DOM order.
- **Auto-fix patches**: For each fixable violation, generate a minimal CSS/HTML patch as a string. Contrast fixes: compute the closest compliant colour using binary search on lightness in HSL space. Missing alt text: generate a patch that adds `alt=""` (empty string for decorative images, or a placeholder text warning).
- **Report aggregation**: After scanning all pages, group violations by `criterion`, compute `precision = TP / (TP + FP)` and `recall = TP / (TP + FN)` against ground truth, write to `summary.json`.

## Tier 3 — Implementation Guidance (-15% score penalty)
1. **Crawler** (`crawler.py`): `class Crawler`: `async def crawl(start_url, max_pages) -> List[PageData]`. Use `playwright.async_api` — `async with async_playwright() as p` → `browser = await p.chromium.launch(headless=True)`. For each page, store `{url, html, accessibility_tree, screenshot_bytes}`. Breadth-first queue with a `visited: set[str]` guard and same-origin link filter.
2. **Static checkers** (`checks/static.py`): functions `check_images_alt(soup) -> List[Violation]`, `check_form_labels(soup) -> List[Violation]`, `check_heading_hierarchy(soup) -> List[Violation]`, `check_language_attribute(soup) -> List[Violation]`. Each returns a list of `Violation` dataclasses.
3. **Dynamic checkers** (`checks/dynamic.py`): `async def check_contrast(page) -> List[Violation]`: inject JS to iterate all text nodes, call `getComputedStyle`, compute luminance ratio, flag failures. `async def check_focus_order(page) -> List[Violation]`: simulate Tab key presses, record element sequence.
4. **Visual checker** (`checks/visual.py`): load screenshot into a PIL image; use a pre-trained CLIP or ResNet model to detect text-in-image regions (criterion 1.4.5); flag any text-like region with confidence > 0.7.
5. **Report writer** (`reporter.py`): `class ReportWriter`: `write_violations(url_slug, violations) -> Path` writes `submission/reports/{url_slug}/violations.json`. `write_compliance_score(url_slug, violations) -> Path` writes per-criterion pass/fail JSON.
6. **Auto-fixer** (`autofixer.py`): `def generate_contrast_patch(element_selector, current_bg_hex) -> str` — binary-search HSL lightness until ratio >= 4.5:1; return CSS patch string. `def generate_alt_patch(element_selector) -> str` — return HTML attribute addition.
7. **Main pipeline** (`main.py` / `starter.py`): iterate `target_urls.txt`, crawl each site, run all checkers, write reports, compute `summary.json` with aggregate precision/recall/FPR.
