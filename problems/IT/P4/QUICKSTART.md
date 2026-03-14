# AccessibilityAI — Quick Start

## Objective
Build an AI-powered auditing tool that crawls a website, checks every page against all 50 WCAG 2.2 Level AA success criteria, and generates a structured violations report with location, severity, and suggested fixes — keeping false positives below 10%.

## Inputs
- `data/target_urls.txt` — One URL per line; each URL is the entry point of a test website to crawl
- `data/ground_truth/` — One JSON file per target URL (filename = URL slug): ground truth WCAG violations used by the evaluator
  - Schema: `[{"url": "...", "criterion": "1.1.1", "element_selector": "...", "severity": "critical|serious|moderate|minor"}]`
- `data/config.json` — Audit config: `{max_pages, timeout_sec, headless, wcag_level}`

## Expected Output
Submission directory `submission/` containing:
- `submission/reports/<url_slug>/violations.json` — Detected violations for each audited URL
- `submission/reports/<url_slug>/compliance_score.json` — Overall score and per-criterion pass/fail
- `submission/reports/<url_slug>/autofix_patches/` — HTML/CSS patch files for auto-fixable issues
- `submission/summary.json` — Aggregated precision, recall, F1, false positive rate across all sites

`violations.json` schema per item:
```json
{
  "criterion": "1.4.3",
  "element_selector": "button.cta",
  "severity": "serious",
  "description": "Insufficient colour contrast ratio (2.1:1, required 4.5:1)",
  "suggested_fix": "Change background from #999 to #767676",
  "auto_fixed": false
}
```

## Recommended First Steps
1. Implement a breadth-first crawler using `aiohttp` + `BeautifulSoup`; respect `robots.txt`, cap at `max_pages`, and extract `<a href>` links staying within the same domain.
2. Implement the two highest-coverage checks first: missing `alt` attributes on `<img>` (criterion 1.1.1) and insufficient colour contrast (criterion 1.4.3) — together these catch ~40% of real-world violations.
3. Load `data/ground_truth/` and compute precision/recall against your output to calibrate your detector before adding more criteria.

## Scoring Breakdown
| Metric                    | Weight |
|---------------------------|--------|
| Detection precision/recall| 50%    |
| Report quality            | 25%    |
| False positive rate       | 25%    |

## Common Pitfalls
- Checking only static HTML: JavaScript-rendered SPAs require a headless browser (Playwright/Puppeteer) to build the full DOM before analysis — missing this means missing the majority of violations on modern sites.
- Flagging every element that technically fails a criterion as "critical": calibrate severity using WCAG's own severity taxonomy (critical/serious/moderate/minor) or your false positive rate will balloon.
- Forgetting ARIA overrides: `role="presentation"` on an `<img>` makes criterion 1.1.1 not applicable — blindly flagging it inflates your false positive count.
