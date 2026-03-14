# IT-P4: AccessibilityAI — Test Websites Dataset

## Overview
Five test websites with deliberately embedded WCAG 2.2 violations for evaluating
automated accessibility analysis tools and AI-powered auditing systems.

## Directory Structure
```
IT-P4/
├── test_websites/
│   ├── site_1/          # E-commerce product page
│   │   ├── index.html
│   │   └── style.css
│   ├── site_2/          # News article page
│   │   ├── index.html
│   │   └── style.css
│   ├── site_3/          # Government form page
│   │   ├── index.html
│   │   └── style.css
│   ├── site_4/          # Healthcare portal
│   │   ├── index.html
│   │   └── style.css
│   └── site_5/          # Education platform
│       ├── index.html
│       └── style.css
├── ground_truth.json    # Known violations per site
└── README.md
```

## Sites Summary

| Site | Type | WCAG Violations | Key Issues |
|------|------|-----------------|------------|
| site_1 | E-commerce product page | 5 | Missing alt text, low contrast (#999 on white), unlabeled input, non-descriptive link text, autoplay video |
| site_2 | News article | 4 | Heading hierarchy skips h2/h3, missing html lang, color-only error indicators, keyboard trap in modal |
| site_3 | Government form | 6 | Table uses td instead of th headers, unmarked required fields, color-only error feedback, ARIA-less custom checkbox, no keyboard support on custom control, PDF link lacks type indication |
| site_4 | Healthcare portal | 3 | Session timeout with no accessible warning, canvas chart with no text alternative, action buttons 18x18px (below 24x24 minimum) |
| site_5 | Education platform | 5 | CSS flash animation at 5 Hz (>3 Hz limit), audio without transcript, image-of-text heading with empty alt, global outline:none removes all focus indicators, auto-carousel with no pause control |

## WCAG Criteria Tested

| Criterion | Description | Sites |
|-----------|-------------|-------|
| 1.1.1 | Non-text Content | 1, 3, 4 |
| 1.2.1 | Audio-only Content | 5 |
| 1.3.1 | Info and Relationships | 1, 2, 3 |
| 1.4.1 | Use of Color | 2, 3 |
| 1.4.2 | Audio Control | 1 |
| 1.4.3 | Contrast (Minimum) | 1 |
| 1.4.5 | Images of Text | 5 |
| 2.1.1 | Keyboard | 3 |
| 2.1.2 | No Keyboard Trap | 2 |
| 2.2.1 | Timing Adjustable | 4 |
| 2.2.2 | Pause, Stop, Hide | 5 |
| 2.3.1 | Three Flashes | 5 |
| 2.4.4 | Link Purpose | 1 |
| 2.4.7 | Focus Visible | 5 |
| 2.5.8 | Target Size (Minimum) | 4 |
| 3.1.1 | Language of Page | 2 |
| 3.3.1 | Error Identification | 3 |
| 3.3.2 | Labels or Instructions | 3 |
| 4.1.2 | Name, Role, Value | 3 |

## Ground Truth Format

`ground_truth.json` contains per-site violation details:

```json
{
  "site_N": {
    "total_violations": 5,
    "violations": [
      {
        "wcag_criterion": "1.1.1",
        "element_selector": "img.product-img",
        "severity": "critical",
        "description": "Image missing alt text"
      }
    ]
  }
}
```

## Severity Levels

- **critical** — Completely blocks access for affected users
- **serious** — Significantly impairs access
- **moderate** — Creates barriers but workarounds exist
- **minor** — Best-practice issue with minimal impact

## Violation Counts by Severity

| Severity | Count | Sites |
|----------|-------|-------|
| critical | 7 | 1 (×2), 2, 3 (×2), 4, 5 |
| serious | 8 | 1 (×2), 2 (×2), 3 (×2), 4, 5 |
| moderate | 8 | 1 (×2), 2, 3 (×2), 4, 5 (×2) |

## Usage Notes for Participants

1. Open each `index.html` in a browser to view the page
2. Use automated tools (axe-core, WAVE, Lighthouse) to scan for violations
3. Compare tool output against `ground_truth.json` to evaluate recall/precision
4. Some violations (keyboard trap, session timeout, carousel auto-advance) require
   interactive testing and may not be detectable by static analysis tools alone
5. The flashing animation in site_5 is intentionally seizure-triggering per WCAG 2.3.1
   test purposes — do not view site_5 if you are photosensitive
