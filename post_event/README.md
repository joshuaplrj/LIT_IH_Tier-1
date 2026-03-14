# Post-Event Learning Package

This folder contains materials released after the Grand Engineering Problem Statement Challenge concludes and judging is complete. Its purpose is to help all participants learn from the event — regardless of how they scored.

---

## What Is in This Folder

| Item | Description |
|------|-------------|
| `README.md` (this file) | Guide to the post-event materials |
| `solution_writeup_template.md` | Template for teams to document their approach |
| `solutions/<DISCIPLINE>/P<N>/` | Reference solutions, added after judging is finalized |
| `writeups/` | Community write-ups submitted by participating teams |

---

## Reference Solutions

Reference solutions will be added to `solutions/<DISCIPLINE>/P<N>/` once judging is complete and scores are locked.

Each reference solution folder will contain:
- `solution.py` or equivalent — a clean, commented implementation
- `EXPLANATION.md` — a walkthrough of the approach, key decisions, and common pitfalls
- Performance notes (time complexity, edge cases, scoring breakdown)

**They are not available during the event.** After the event, pull the latest `main` branch to access them:

```bash
git checkout main
git pull origin main
```

---

## Submit Your Own Write-Up

We invite all teams to share what they built, what they tried, and what they learned — even if your score was not what you hoped for.

To submit a write-up:

1. Copy `solution_writeup_template.md` to a new file:
   ```
   post_event/writeups/<your-team-name>-<DISCIPLINE>-P<N>.md
   ```
   Example: `post_event/writeups/team-alpha-CSE-P1.md`

2. Fill in all sections of the template honestly — partial solutions and failed attempts are just as valuable as perfect scores.

3. Open a Pull Request with your file. Title the PR:
   ```
   writeup: <team-name> — <DISCIPLINE> P<N>
   ```

Write-ups are reviewed only for format; there is no judgment on approach quality. All valid submissions will be merged.

---

## Why Write-Ups Matter

- Forces you to articulate your reasoning, which deepens understanding
- Helps future participants learn from real attempts, not just reference solutions
- Builds a searchable archive of approaches for each problem type
- The write-up process often reveals what you actually understood versus what you thought you understood

---

## Template Structure

`solution_writeup_template.md` has the following sections:

1. **Team Name and Members** — who worked on this
2. **Problem Attempted** — discipline and problem number
3. **Approach Summary** — 3-5 sentence description of your method
4. **Key Algorithms and Techniques** — specific tools, algorithms, or frameworks used
5. **What Worked** — what contributed positively to your score
6. **What Didn't Work** — approaches tried and abandoned, and why
7. **Score Achieved** — your final score for this problem
8. **Code Repository Link** — optional, if you want to share your source
9. **Lessons Learned** — key takeaways for the next time you face a similar problem
