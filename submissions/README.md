# Submission Guide

This document explains how to submit your solutions for the Grand Engineering Problem Statement Challenge.

---

## Folder Structure

Place your submission files under:

```
submissions/<your-team-name>/<DISCIPLINE>/P<N>/
```

**Example:**

```
submissions/team-alpha/CSE/P1/
submissions/team-alpha/CSE/P2/
submissions/team-alpha/MECH/P3/
```

### Rules for team names
- Lowercase letters only
- Hyphens (`-`) as separators — no spaces, no underscores, no special characters
- Examples of valid names: `team-alpha`, `ctrl-alt-defeat`, `byte-brigade`
- Examples of invalid names: `Team Alpha`, `team_alpha`, `TeamAlpha`

### Valid discipline codes
`CSE` | `CYBER` | `IT` | `EEE` | `ECE` | `MECH` | `AIDS` | `MBA`

### Valid problem numbers
`P1` through `P5` for each discipline.

---

## What to Put in Each Folder

Each problem's `evaluate.py` defines exactly which output files it expects. Check the problem folder for details:

```
problems/<DISCIPLINE>/P<N>/evaluate.py
```

**General rule:** submit only the final output/artifact files required by the evaluator.

- Do **not** commit your source code, notebooks, or scratch files here.
- Do **not** commit large binary files or datasets.
- Only the files that `evaluate.py` reads when scoring your submission belong here.

**Example** — if `CSE/P1/evaluate.py` expects a file called `predictions.csv`, your folder should look like:

```
submissions/team-alpha/CSE/P1/
└── predictions.csv
```

---

## How to Submit

1. **Fork or clone** this repository.
2. **Create a branch** named after your team:
   ```bash
   git checkout -b team-alpha
   ```
3. **Place your output files** in the correct path under `submissions/`.
4. **Commit and push** your branch:
   ```bash
   git add submissions/team-alpha/
   git commit -m "team-alpha: submit CSE/P1"
   git push origin team-alpha
   ```
5. **Open a Pull Request** from your branch into `main`.
6. **GitHub Actions will automatically:**
   - Detect which submission folders changed
   - Run the corresponding `evaluate.py` for each changed folder
   - Parse the score and update the leaderboard
   - Post the score as a comment on your PR

You do not need to merge the PR for scoring to occur — the workflow runs on the PR event itself.

---

## Tips

- You can submit to multiple problems in a single PR by adding files to multiple folders.
- Re-pushing to the same branch will trigger re-evaluation only for the folders that changed.
- Check the **Actions** tab for evaluation logs if your score looks unexpected.
- The leaderboard at `leaderboard/index.html` auto-refreshes every 30 seconds.

---

## Quick Reference

| Item | Value |
|------|-------|
| Max score per problem | 100 points |
| Problems per discipline | 5 |
| Total disciplines | 8 |
| Max possible score (per team) | 4,000 points |
