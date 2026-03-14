# Infinite Chess Grandmaster — Hints

> Each tier costs score points. Only request when genuinely stuck.

## Tier 1 — Conceptual Direction (-5% score penalty)

The key challenge is not implementing chess — it is handling the three rule modifications inside a minimax search tree. Think about how each mechanic changes the game tree:

- **Bombs** change material balance unpredictably: a "free capture" on a bomb square is actually a mutual annihilation. Your evaluation function must treat adjacent-to-bomb positions as risky and factor in the probability that an opponent will force your piece onto a bomb.
- **Teleporters** create non-local interactions: a piece on one side of the board can instantly appear anywhere via a teleporter. Your move generator must treat teleporter entry squares as having an extra successor (the paired exit square). Two-step teleporter paths (enter → exit → move again) are valid but count as one "move".
- **Time dilation** at every 10th move creates asymmetric trees where one player gets two plies. Your search must detect this and expand two-ply branches for the dilated player (generating all pairs of legal moves) rather than a single ply.

The right framework is still alpha-beta search — the mechanics change what the tree looks like, not the algorithm that searches it.

## Tier 2 — Technique Guidance (-10% score penalty)

**Move generator additions:**
- Standard moves: generate all legal destination squares for each piece type.
- Bomb interaction: if `dest in bombs`, the move is legal; mark it as a "bomb capture" — the moving piece is removed along with the bomb.
- Teleporter interaction: if `dest == teleporter[0]`, the piece arrives at `teleporter[1]` (and vice versa). Check the arrival square for occupancy (capture opponent, or blocked by own piece).
- Time dilation: when `move_number % 10 == 0`, generate two-move sequences (all first moves × all second moves after the first move is applied). Prune clearly losing first moves before expanding second moves to contain the branching factor.

**Search algorithm:**
- **Iterative deepening alpha-beta (IDDFS-AB)**: search to depth 1, 2, 3, … until the time limit (4.5 seconds). Always return the best move found at the last completed depth.
- **Transposition table**: use a Zobrist hash of the board state (piece positions + bomb positions + teleporter state) as a key. Store `(depth, score, flag, best_move)` tuples. This is critical for N=12 and N=16.
- **Move ordering**: score captures first (MVV-LVA: Most Valuable Victim – Least Valuable Attacker), then checks, then quiet moves. Good move ordering reduces effective branching factor dramatically.

**Evaluation function features:**
- Material: standard piece values scaled by N (on large boards, mobility matters more than material).
- Mobility: number of legal moves for each side.
- King safety: penalise open files near the king; add a penalty for king proximity to bomb squares.
- Bomb pressure: bonus for forcing the opponent to move pieces near bombs.

## Tier 3 — Implementation Guidance (-15% score penalty)

**Concrete implementation steps:**

1. **Board representation**: use a 2D list (N×N) of strings. Maintain auxiliary sets: `bombs: set of (r,c)`, `teleporters: list of [(r1,c1),(r2,c2)]`. Use a Zobrist hash table for transposition.

2. **Zobrist hashing**:
   ```python
   import random
   ZOBRIST = {}
   for r in range(MAX_N):
       for c in range(MAX_N):
           for piece in ALL_PIECES:
               ZOBRIST[(r, c, piece)] = random.getrandbits(64)
   ZOBRIST_BOMB = {(r,c): random.getrandbits(64) for r in range(MAX_N) for c in range(MAX_N)}
   ```
   XOR the hash when a piece moves or a bomb is removed.

3. **Alpha-beta with TT**:
   ```python
   def alphabeta(board, depth, alpha, beta, maximizing, tt, move_number):
       key = board.zobrist_hash()
       if key in tt and tt[key]['depth'] >= depth:
           return tt[key]['score']
       if depth == 0 or board.is_terminal():
           return evaluate(board)
       moves = board.generate_moves()
       order_moves(moves, board)    # MVV-LVA ordering
       best = -INF if maximizing else +INF
       for move in moves:
           board.apply(move)
           score = alphabeta(board, depth-1, alpha, beta, not maximizing, tt, move_number+1)
           board.undo(move)
           if maximizing: best = max(best, score); alpha = max(alpha, best)
           else:          best = min(best, score); beta  = min(beta,  best)
           if alpha >= beta: break    # prune
       tt[key] = {'depth': depth, 'score': best}
       return best
   ```

4. **Time-dilation branch**: when `move_number % 10 == 0`, in `generate_moves()` return tuples `(move1, move2)`. In `alphabeta()`, detect these tuples and apply both moves before recursing, keeping the same `maximizing` side for the inner pair.

5. **Tournament harness**: write a `play_game(white_agent, black_agent, n, config)` function that alternates calling agents, applies moves, checks for mate/draw, and records results. Run 50+ games per board size with randomised bomb/teleporter placements.

6. **Evaluation tuning**: start with standard material weights (P=1, N=3, B=3, R=5, Q=9) and add mobility weight = 0.1. Then use self-play to tune bomb-avoidance penalty (try 0.5–2.0 per adjacent bomb) and teleporter proximity bonus.
