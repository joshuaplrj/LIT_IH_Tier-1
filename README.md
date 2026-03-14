# Grand Engineering Problem Statement Challenge

A 3-hour competitive engineering hackathon across 8 disciplines, 5 problems each — 40 problems total. Teams work in parallel, submit output artifacts via Git, and receive automated scores updated live on the leaderboard.

---

## Quick Links

| Resource | Path |
|----------|------|
| Problems Index | `problems/` |
| Live Leaderboard | `leaderboard/index.html` (GitHub Pages) |
| Submission Guide | `submissions/README.md` |
| Post-Event Materials | `post_event/README.md` |

---

## Event Format

| Attribute | Value |
|-----------|-------|
| Duration | 3 hours |
| Disciplines | 8 |
| Problems per discipline | 5 |
| Total problems | 40 |
| Max score per problem | 100 points |
| Max score per team | 4,000 points |
| Scoring | Automated via GitHub Actions on every submission |

Teams may attempt any combination of problems from any discipline. There is no requirement to stay within a single discipline.

---

## How to Get Started

1. **Clone the repository:**
   ```bash
   git clone <repo-url>
   cd <repo-name>
   ```

2. **Create your team branch** (lowercase, hyphens only):
   ```bash
   git checkout -b team-your-name
   ```

3. **Pick a problem** — browse the `problems/` directory:
   ```
   problems/
   ├── CSE/P1/
   ├── CSE/P2/
   ...
   └── MBA/P5/
   ```

4. **Read the problem quickstart:**
   ```bash
   cat problems/<DISCIPLINE>/P<N>/QUICKSTART.md
   ```

5. **Use the starter script** as your baseline:
   ```bash
   python problems/<DISCIPLINE>/P<N>/starter.py
   ```

6. **Place your output file(s)** in the correct submission folder:
   ```
   submissions/<your-team-name>/<DISCIPLINE>/P<N>/
   ```

7. **Submit:**
   ```bash
   git add submissions/<your-team-name>/
   git commit -m "submit <DISCIPLINE>/P<N>"
   git push origin team-your-name
   # Then open a Pull Request on GitHub
   ```

GitHub Actions will automatically run `evaluate.py` against your submission and update the leaderboard.

---

## Disciplines Overview

| Code | Full Name | Focus Area |
|------|-----------|------------|
| CSE | Computer Science and Engineering | Algorithms, data processing, ML/AI tasks |
| CYBER | Cybersecurity | Threat analysis, cryptography, log forensics |
| IT | Information Technology | Systems, networking, data pipelines |
| EEE | Electrical and Electronics Engineering | Signal processing, circuit analysis, power systems |
| ECE | Electronics and Communication Engineering | Communications, embedded systems, DSP |
| MECH | Mechanical Engineering | Simulation, optimization, thermodynamics |
| AIDS | Artificial Intelligence and Data Science | Predictive modeling, data analysis, visualization |
| MBA | Management and Business Analytics | Decision analysis, operations research, forecasting |

---

## Scoring

- Each problem is scored **0 to 100** by its `evaluate.py` script.
- The evaluator outputs a JSON object with a `"total"` key, e.g.:
  ```json
  {"total": 87, "breakdown": {"accuracy": 72, "efficiency": 15}}
  ```
- Scores are parsed automatically by the GitHub Actions workflow.
- The leaderboard (`leaderboard/index.html`) updates within minutes of a submission and auto-refreshes every 30 seconds.
- Re-submitting to the same problem overwrites the previous score.

---

## Hint System

Each problem provides a tiered hint system in `HINTS.md`:

| Tier | Content | Score Penalty |
|------|---------|---------------|
| Hint 1 | High-level conceptual nudge | -5 points |
| Hint 2 | Algorithmic direction | -10 points |
| Hint 3 | Near-complete approach | -20 points |

Hints are opt-in. Read `problems/<DISCIPLINE>/P<N>/HINTS.md` and apply the corresponding penalty to your score manually. The honor system applies — evaluators do not enforce hint usage, but post-event analysis may highlight unusually fast high scores.

---

## Important Constraints

- **CSE-P1:** No external pre-trained models permitted. Your solution must be trained from scratch on the provided dataset only.
- **All problems:** Solutions must run in an offline environment. No external API calls, no internet access during evaluation.
- **Submissions:** Only output/artifact files belong in `submissions/`. Do not commit source code, datasets, or dependencies to the submissions folder.
- **Team names:** Lowercase letters and hyphens only. No spaces, no underscores, no special characters.

---

## Repository Structure

```
.
├── problems/
│   └── <DISCIPLINE>/
│       └── P<N>/
│           ├── QUICKSTART.md      # Problem statement and I/O spec
│           ├── HINTS.md           # Tiered hints with score penalties
│           ├── starter.py         # Baseline starter script
│           └── evaluate.py        # Automated scorer
│
├── submissions/
│   └── <team-name>/
│       └── <DISCIPLINE>/
│           └── P<N>/              # Your output files go here
│
├── leaderboard/
│   ├── index.html                 # GitHub Pages live leaderboard
│   └── leaderboard.json           # Score data (auto-updated)
│
├── .github/
│   └── workflows/
│       ├── evaluate.yml           # CI/CD pipeline
│       └── update_leaderboard.py  # Score merge helper
│
└── post_event/
    ├── README.md                  # Post-hackathon guide
    ├── solution_writeup_template.md
    ├── solutions/                 # Reference solutions (post-event)
    └── writeups/                  # Community write-ups
```

---

## After the Event

Reference solutions and a learning package will be published in `post_event/solutions/` after judging is complete. Teams are encouraged to submit write-ups of their approach using `post_event/solution_writeup_template.md`.

See `post_event/README.md` for full details.
