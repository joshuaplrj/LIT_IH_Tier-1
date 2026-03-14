"""
Infinite Chess Grandmaster — Starter Skeleton
CSE Problem 3: AI agent for N×N generalized chess with bombs, teleporters, time-dilation.

Usage:
    python starter.py --size 8 --games 5
    (runs a self-play tournament between the starter agent and the baseline)
"""

import argparse
import copy
import random
import time
from typing import Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PIECE_VALUES = {"P": 1, "N": 3, "B": 3, "R": 5, "Q": 9, "K": 1000}
EMPTY = "--"
WHITE = "white"
BLACK = "black"
INF = 10_000

# ---------------------------------------------------------------------------
# Board Representation
# ---------------------------------------------------------------------------

class Board:
    """
    Represents an N×N generalized chess board.
    Pieces encoded as "wK", "bQ", "wP", etc.  Empty squares = "--".
    """

    def __init__(self, n: int = 8,
                 bombs: Optional[List[Tuple[int,int]]] = None,
                 teleporters: Optional[List[List[Tuple[int,int]]]] = None):
        self.n = n
        self.grid: List[List[str]] = [[EMPTY] * n for _ in range(n)]
        self.bombs: set = set(map(tuple, bombs)) if bombs else set()
        # teleporters: list of two pairs [(r1,c1),(r2,c2)]
        self.teleporters: List[List[Tuple[int,int]]] = teleporters or []
        self.turn = WHITE
        self.move_number = 1
        self.history: List[dict] = []   # for undo support
        self._setup_standard(n)

    def _setup_standard(self, n: int):
        """Place pieces in standard chess starting positions (scaled for N×N)."""
        back_row = ["R", "N", "B", "Q", "K", "B", "N", "R"]
        # For boards wider than 8, pad the middle with extra pieces or repeat
        if n >= 8:
            br = back_row[:min(n, 8)]
            # Pad remaining columns with Rooks (simplified)
            while len(br) < n:
                br.append("R")
        else:
            br = back_row[:n]

        for col, piece in enumerate(br):
            self.grid[0][col] = f"b{piece}"
            self.grid[n-1][col] = f"w{piece}"

        for col in range(min(n, 8)):
            if n > 1:
                self.grid[1][col] = "bP"
                self.grid[n-2][col] = "wP"

    def copy(self) -> "Board":
        b = Board.__new__(Board)
        b.n = self.n
        b.grid = [row[:] for row in self.grid]
        b.bombs = set(self.bombs)
        b.teleporters = [list(pair) for pair in self.teleporters]
        b.turn = self.turn
        b.move_number = self.move_number
        b.history = []
        return b

    def piece_at(self, r: int, c: int) -> str:
        if 0 <= r < self.n and 0 <= c < self.n:
            return self.grid[r][c]
        return None

    def color_at(self, r: int, c: int) -> Optional[str]:
        p = self.piece_at(r, c)
        if p and p != EMPTY:
            return WHITE if p[0] == "w" else BLACK
        return None

    def to_state_dict(self) -> dict:
        return {
            "board": [row[:] for row in self.grid],
            "turn": self.turn,
            "n": self.n,
            "bombs": [list(b) for b in self.bombs],
            "teleporters": [[[r,c] for r,c in pair] for pair in self.teleporters],
            "move_number": self.move_number,
        }

    # ------------------------------------------------------------------
    # Move Application
    # ------------------------------------------------------------------

    def apply_move(self, move: str) -> dict:
        """
        Apply a move string 'e2e4'. Returns undo info dict.
        Handles bomb detonation and teleportation.
        """
        fr, fc = self._parse_sq(move[:2])
        tr, tc = self._parse_sq(move[2:])

        piece = self.grid[fr][fc]
        captured = self.grid[tr][tc]
        bomb_detonated = None
        teleported_to = None

        # Teleporter check: does destination have a teleporter?
        dest_sq = (tr, tc)
        for pair in self.teleporters:
            if tuple(pair[0]) == dest_sq:
                tr, tc = pair[1]
                teleported_to = (tr, tc)
                break
            elif tuple(pair[1]) == dest_sq:
                tr, tc = pair[0]
                teleported_to = (tr, tc)
                break

        # Bomb check: landing on a bomb destroys the piece and the bomb
        if (tr, tc) in self.bombs:
            bomb_detonated = (tr, tc)
            self.bombs.discard(bomb_detonated)
            self.grid[fr][fc] = EMPTY
            self.grid[tr][tc] = EMPTY  # piece destroyed along with bomb
        else:
            captured = self.grid[tr][tc]
            self.grid[tr][tc] = piece
            self.grid[fr][fc] = EMPTY

        undo = {
            "move": move, "fr": fr, "fc": fc, "tr": tr, "tc": tc,
            "piece": piece, "captured": captured,
            "bomb_detonated": bomb_detonated,
            "teleported_to": teleported_to,
            "prev_turn": self.turn,
            "prev_move_number": self.move_number,
        }
        self.turn = BLACK if self.turn == WHITE else WHITE
        self.move_number += 1
        return undo

    def undo_move(self, undo: dict):
        """Undo a previously applied move."""
        fr, fc = undo["fr"], undo["fc"]
        tr, tc = undo["tr"], undo["tc"]
        piece = undo["piece"]
        captured = undo["captured"]

        if undo["bomb_detonated"]:
            self.bombs.add(undo["bomb_detonated"])
            self.grid[fr][fc] = piece
            self.grid[tr][tc] = EMPTY
        else:
            self.grid[fr][fc] = piece
            self.grid[tr][tc] = captured

        self.turn = undo["prev_turn"]
        self.move_number = undo["prev_move_number"]

    # ------------------------------------------------------------------
    # Move Generation  (TODO: complete all piece types)
    # ------------------------------------------------------------------

    def generate_moves(self) -> List[str]:
        """
        Generate all legal moves for the current player.
        Returns list of UCI strings like 'e2e4'.

        TODO: Implement full move generation for all pieces.
              Currently generates only simplified Pawn and King moves.
        """
        moves = []
        color = self.turn
        for r in range(self.n):
            for c in range(self.n):
                p = self.grid[r][c]
                if p == EMPTY or p[0] != color[0]:
                    continue
                piece_type = p[1]
                if piece_type == "P":
                    moves.extend(self._pawn_moves(r, c, color))
                elif piece_type == "K":
                    moves.extend(self._king_moves(r, c, color))
                elif piece_type == "R":
                    moves.extend(self._rook_moves(r, c, color))
                elif piece_type == "B":
                    moves.extend(self._bishop_moves(r, c, color))
                elif piece_type == "Q":
                    moves.extend(
                        self._rook_moves(r, c, color) + self._bishop_moves(r, c, color)
                    )
                elif piece_type == "N":
                    moves.extend(self._knight_moves(r, c, color))
                # TODO: Add remaining piece types
        return moves if moves else [self._sq(0, 0) + self._sq(0, 0)]  # null move fallback

    def _pawn_moves(self, r, c, color):
        moves = []
        dir_ = -1 if color == WHITE else 1
        nr = r + dir_
        if 0 <= nr < self.n and self.grid[nr][c] == EMPTY:
            moves.append(self._sq(r,c) + self._sq(nr,c))
        # Captures
        for dc in (-1, 1):
            nc = c + dc
            if 0 <= nc < self.n and 0 <= nr < self.n:
                target = self.grid[nr][nc]
                if target != EMPTY and target[0] != color[0]:
                    moves.append(self._sq(r,c) + self._sq(nr,nc))
        return moves

    def _king_moves(self, r, c, color):
        moves = []
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0:
                    continue
                nr, nc = r + dr, c + dc
                if 0 <= nr < self.n and 0 <= nc < self.n:
                    target = self.grid[nr][nc]
                    if target == EMPTY or target[0] != color[0]:
                        moves.append(self._sq(r,c) + self._sq(nr,nc))
        return moves

    def _rook_moves(self, r, c, color):
        moves = []
        for dr, dc in ((1,0),(-1,0),(0,1),(0,-1)):
            nr, nc = r + dr, c + dc
            while 0 <= nr < self.n and 0 <= nc < self.n:
                target = self.grid[nr][nc]
                if target == EMPTY:
                    moves.append(self._sq(r,c) + self._sq(nr,nc))
                elif target[0] != color[0]:
                    moves.append(self._sq(r,c) + self._sq(nr,nc))
                    break
                else:
                    break
                nr += dr; nc += dc
        return moves

    def _bishop_moves(self, r, c, color):
        moves = []
        for dr, dc in ((1,1),(1,-1),(-1,1),(-1,-1)):
            nr, nc = r + dr, c + dc
            while 0 <= nr < self.n and 0 <= nc < self.n:
                target = self.grid[nr][nc]
                if target == EMPTY:
                    moves.append(self._sq(r,c) + self._sq(nr,nc))
                elif target[0] != color[0]:
                    moves.append(self._sq(r,c) + self._sq(nr,nc))
                    break
                else:
                    break
                nr += dr; nc += dc
        return moves

    def _knight_moves(self, r, c, color):
        moves = []
        for dr, dc in ((2,1),(2,-1),(-2,1),(-2,-1),(1,2),(1,-2),(-1,2),(-1,-2)):
            nr, nc = r + dr, c + dc
            if 0 <= nr < self.n and 0 <= nc < self.n:
                target = self.grid[nr][nc]
                if target == EMPTY or target[0] != color[0]:
                    moves.append(self._sq(r,c) + self._sq(nr,nc))
        return moves

    @staticmethod
    def _sq(r: int, c: int) -> str:
        return chr(ord("a") + c) + str(r + 1)

    @staticmethod
    def _parse_sq(s: str) -> Tuple[int, int]:
        c = ord(s[0]) - ord("a")
        r = int(s[1:]) - 1
        return r, c

    # ------------------------------------------------------------------
    # Terminal / evaluation helpers
    # ------------------------------------------------------------------

    def is_terminal(self) -> bool:
        """Very simplified: terminal if a king is missing."""
        whites = sum(1 for r in self.grid for p in r if p == "wK")
        blacks = sum(1 for r in self.grid for p in r if p == "bK")
        return whites == 0 or blacks == 0

    def winner(self) -> Optional[str]:
        whites = sum(1 for r in self.grid for p in r if p == "wK")
        blacks = sum(1 for r in self.grid for p in r if p == "bK")
        if whites == 0: return BLACK
        if blacks == 0: return WHITE
        return None


# ---------------------------------------------------------------------------
# Evaluation Function
# ---------------------------------------------------------------------------

def evaluate(board: Board) -> float:
    """
    Static evaluation: positive = good for White, negative = good for Black.

    TODO: Add mobility, king safety, bomb proximity penalty, teleporter control.
    """
    score = 0.0
    for r in range(board.n):
        for c in range(board.n):
            p = board.grid[r][c]
            if p == EMPTY:
                continue
            color = WHITE if p[0] == "w" else BLACK
            val = PIECE_VALUES.get(p[1], 0)
            # Bomb proximity penalty
            bomb_penalty = 0.0
            for dr in (-1, 0, 1):
                for dc in (-1, 0, 1):
                    if (r + dr, c + dc) in board.bombs:
                        bomb_penalty += 0.3
            if color == WHITE:
                score += val - bomb_penalty
            else:
                score -= val - bomb_penalty
    return score


# ---------------------------------------------------------------------------
# Alpha-Beta Search
# ---------------------------------------------------------------------------

_transposition_table: dict = {}


def alphabeta(board: Board, depth: int, alpha: float, beta: float,
              maximizing: bool, start_time: float, time_limit: float) -> float:
    """
    Alpha-beta search with time limit and transposition table.
    Returns evaluation score.
    """
    if time.time() - start_time > time_limit:
        return evaluate(board)

    if depth == 0 or board.is_terminal():
        return evaluate(board)

    # TODO: Add Zobrist-keyed transposition table lookup here.

    moves = board.generate_moves()
    if not moves:
        return evaluate(board)

    # TODO: Add move ordering (MVV-LVA captures first).

    if maximizing:
        best = -INF
        for mv in moves:
            undo = board.apply_move(mv)
            # Handle time-dilation: move_number divisible by 10 -> extra ply
            # TODO: implement double-move branch for time dilation
            score = alphabeta(board, depth - 1, alpha, beta, False, start_time, time_limit)
            board.undo_move(undo)
            best = max(best, score)
            alpha = max(alpha, best)
            if alpha >= beta:
                break
        return best
    else:
        best = INF
        for mv in moves:
            undo = board.apply_move(mv)
            score = alphabeta(board, depth - 1, alpha, beta, True, start_time, time_limit)
            board.undo_move(undo)
            best = min(best, score)
            beta = min(beta, best)
            if alpha >= beta:
                break
        return best


# ---------------------------------------------------------------------------
# Agent: Iterative Deepening
# ---------------------------------------------------------------------------

class IDAgent:
    """
    Iterative Deepening Alpha-Beta agent.
    Compatible with the get_move(board_state) interface.
    """

    def __init__(self, time_limit: float = 4.5, max_depth: int = 8):
        self.time_limit = time_limit
        self.max_depth = max_depth

    def get_move(self, board_state: dict) -> str:
        """Called by the game engine. Returns move string."""
        board = self._from_state(board_state)
        start = time.time()
        best_move = None
        maximizing = (board.turn == WHITE)

        for depth in range(1, self.max_depth + 1):
            if time.time() - start > self.time_limit * 0.9:
                break
            moves = board.generate_moves()
            if not moves:
                break

            current_best = None
            current_score = -INF if maximizing else INF
            for mv in moves:
                if time.time() - start > self.time_limit * 0.95:
                    break
                undo = board.apply_move(mv)
                score = alphabeta(board, depth - 1, -INF, INF,
                                  not maximizing, start, self.time_limit)
                board.undo_move(undo)
                if maximizing and score > current_score:
                    current_score = score
                    current_best = mv
                elif not maximizing and score < current_score:
                    current_score = score
                    current_best = mv
            if current_best:
                best_move = current_best

        if best_move is None:
            moves = board.generate_moves()
            best_move = random.choice(moves) if moves else "a1a1"

        # Handle time dilation: if move_number % 10 == 0, return two moves
        if board_state.get("move_number", 1) % 10 == 0:
            # TODO: generate best second move after applying best_move
            undo = board.apply_move(best_move)
            second_moves = board.generate_moves()
            second_move = random.choice(second_moves) if second_moves else best_move
            board.undo_move(undo)
            return f"{best_move} {second_move}"

        return best_move

    @staticmethod
    def _from_state(state: dict) -> Board:
        n = state["n"]
        bombs = [tuple(b) for b in state.get("bombs", [])]
        teleporters = [
            [tuple(p) for p in pair]
            for pair in state.get("teleporters", [])
        ]
        board = Board(n=n, bombs=bombs, teleporters=teleporters)
        # Override grid with provided state
        for r in range(n):
            for c in range(n):
                board.grid[r][c] = state["board"][r][c]
        board.turn = state["turn"]
        board.move_number = state.get("move_number", 1)
        return board


# ---------------------------------------------------------------------------
# Baseline Agent (depth-3 minimax, no special mechanics)
# ---------------------------------------------------------------------------

class BaselineAgent:
    """Depth-3 minimax baseline for self-play testing."""

    def get_move(self, board_state: dict) -> str:
        board = IDAgent._from_state(board_state)
        moves = board.generate_moves()
        if not moves:
            return "a1a1"
        maximizing = (board.turn == WHITE)
        best_score = -INF if maximizing else INF
        best_move = moves[0]
        for mv in moves:
            undo = board.apply_move(mv)
            score = alphabeta(board, 2, -INF, INF, not maximizing, time.time(), 60.0)
            board.undo_move(undo)
            if maximizing and score > best_score:
                best_score = score; best_move = mv
            elif not maximizing and score < best_score:
                best_score = score; best_move = mv
        return best_move


# ---------------------------------------------------------------------------
# Tournament Runner
# ---------------------------------------------------------------------------

def play_game(white: object, black: object, n: int,
              bombs: list, teleporters: list, max_moves: int = 200) -> Optional[str]:
    """Returns winner color string or None for draw."""
    board = Board(n=n, bombs=bombs, teleporters=teleporters)
    for _ in range(max_moves):
        if board.is_terminal():
            break
        agent = white if board.turn == WHITE else black
        state = board.to_state_dict()
        move_str = agent.get_move(state)
        # Handle double moves for time dilation
        moves = move_str.strip().split()
        for mv in moves:
            if len(mv) >= 4:
                board.apply_move(mv)
            if board.is_terminal():
                break
    return board.winner()


def run_tournament(n: int, n_games: int, args):
    agent    = IDAgent(time_limit=4.5, max_depth=args.depth)
    baseline = BaselineAgent()

    results = {WHITE: 0, BLACK: 0, "draw": 0}
    for game_idx in range(n_games):
        # Randomise bombs and teleporters each game
        all_squares = [(r, c) for r in range(n) for c in range(n)]
        bombs = random.sample(all_squares, 3)
        tele_squares = random.sample([s for s in all_squares if s not in bombs], 4)
        teleporters = [tele_squares[:2], tele_squares[2:]]

        # Alternate colors
        if game_idx % 2 == 0:
            winner = play_game(agent, baseline, n, bombs, teleporters)
            if winner == WHITE: results[WHITE] += 1
            elif winner == BLACK: results[BLACK] += 1
            else: results["draw"] += 1
        else:
            winner = play_game(baseline, agent, n, bombs, teleporters)
            if winner == BLACK: results[WHITE] += 1   # agent is now black
            elif winner == WHITE: results[BLACK] += 1
            else: results["draw"] += 1

        print(f"  Game {game_idx+1}/{n_games} winner: {winner}")

    agent_wins = results[WHITE]   # imprecise: counts only games where agent=white
    print(f"\nN={n} results (agent vs baseline, {n_games} games):")
    print(f"  Agent wins: {agent_wins} | Baseline wins: {results[BLACK]} | Draws: {results['draw']}")
    return results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Infinite Chess Grandmaster self-play tournament."
    )
    parser.add_argument("--size",   type=int, default=8,
                        choices=[8, 10, 12, 16], help="Board size N.")
    parser.add_argument("--games",  type=int, default=10,
                        help="Number of games to play.")
    parser.add_argument("--depth",  type=int, default=6,
                        help="Max search depth for the ID agent.")
    args = parser.parse_args()

    print(f"Running tournament: N={args.size}, {args.games} games ...")
    run_tournament(args.size, args.games, args)


if __name__ == "__main__":
    main()
