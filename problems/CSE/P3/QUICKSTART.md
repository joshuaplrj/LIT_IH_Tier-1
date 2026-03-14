# Infinite Chess Grandmaster — Quick Start

## Objective
Build an AI agent that plays Generalized Chess on an N×N board (N = 8, 10, 12, 16) with three non-standard mechanics: bomb squares (landing on one destroys the piece), teleporter pairs (stepping on one teleports to the other), and time dilation (every 10 moves, the active player gets 2 consecutive moves). The agent must beat a depth-3 minimax baseline in at least 80% of 8×8 games.

## Inputs
- No static data files. The game engine calls your agent's `get_move(board_state)` function.
- `board_state` dictionary contains:
  - `board`: N×N array of piece codes (e.g., `"wK"`, `"bQ"`, `"--"` for empty)
  - `turn`: `"white"` or `"black"`
  - `n`: board size (8, 10, 12, or 16)
  - `bombs`: list of `[row, col]` squares with active bombs
  - `teleporters`: list of two pairs `[[r1,c1],[r2,c2]]`
  - `move_number`: integer (1-indexed), used to detect time-dilation rounds

## Expected Output
- Your agent must expose a callable: `get_move(board_state: dict) -> str`
- Move format: UCI-like string `"e2e4"` (source square → destination square, column-letter + row-number).
- For time-dilation rounds (move_number divisible by 10), return two moves separated by a space: `"e2e4 d2d4"`.
- Must respond within **5 seconds** per turn.

## Recommended First Steps
1. Implement a legal move generator that respects standard chess rules plus the three custom mechanics (mark bomb squares as valid but destructive destinations; re-route teleporter arrivals; generate two-move sequences on time-dilation turns).
2. Write a position evaluation function: material count, mobility, king safety, and a penalty for pieces adjacent to bomb squares.
3. Wrap the search in iterative deepening alpha-beta with a 4-second hard cutoff, returning the best move found so far when time expires.

## Scoring Breakdown
| Metric | Weight |
|---|---|
| Win rate vs. depth-3 baseline on 8×8 (must reach ≥80% to score) | Primary pass/fail |
| Performance on N=10, 12, 16 boards (win rate, move quality) | Tested / documented |
| Source code clarity and architecture document | Qualitative |
| Tournament results on ≥50 games per board size | Required deliverable |

## Common Pitfalls
- Treating bomb squares as permanently blocked; a piece can land on a bomb (destroying both piece and bomb) — this can be strategically desirable. Your move generator must allow it.
- Ignoring teleporter arrivals in the search tree: a piece that teleports may land on an occupied square (capture) or on a bomb (double elimination).
- Forgetting that time-dilation doubles only the current player's move, not both players; generating standard alternating-move trees for dilation rounds is incorrect.
- Using standard piece-square tables designed for 8×8; they are invalid for N=10+ boards. Scale or relearn them.
- Not implementing transposition tables: without them, the search is too slow for N=12 and N=16 boards.
