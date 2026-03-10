"""Move ordering for search efficiency: MVV-LVA and killer moves."""

from __future__ import annotations

from src.constants import (
    EMPTY, PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING,
    piece_type,
    decode_from, decode_to, is_capture, is_promotion,
)
from src.board import Board

# Material values (centipawns) for MVV-LVA scoring
PIECE_VALUES: dict[int, int] = {
    PAWN: 100,
    KNIGHT: 320,
    BISHOP: 330,
    ROOK: 500,
    QUEEN: 900,
    KING: 20000,
}

# Pre-compute MVV-LVA scores for all (victim_type, attacker_type) pairs
# Score = PIECE_VALUES[victim] * 10 - PIECE_VALUES[attacker]
MVV_LVA_SCORES: dict[tuple[int, int], int] = {}
for _vt in range(1, 7):
    for _at in range(1, 7):
        MVV_LVA_SCORES[(_vt, _at)] = PIECE_VALUES[_vt] * 10 - PIECE_VALUES[_at]

MAX_KILLER_DEPTH: int = 64


def create_killer_table() -> list[list[int | None]]:
    """Return killer_moves[depth] = [None, None] for each depth."""
    return [[None, None] for _ in range(MAX_KILLER_DEPTH)]


def update_killers(
    killer_moves: list[list[int | None]], move: int, depth: int
) -> None:
    """Insert move at [depth][0], shift old [0] to [1]."""
    if killer_moves[depth][0] != move:
        killer_moves[depth][1] = killer_moves[depth][0]
        killer_moves[depth][0] = move


def _mvv_lva_score(move: int, board: Board) -> int:
    """Return MVV-LVA score for a capture move."""
    from_sq = decode_from(move)
    to_sq = decode_to(move)
    captured = board.squares[to_sq]
    attacker = board.squares[from_sq]
    if captured == EMPTY:
        # En passant — victim is a pawn
        victim_t = PAWN
    else:
        victim_t = piece_type(captured)
    attacker_t = piece_type(attacker)
    return MVV_LVA_SCORES.get((victim_t, attacker_t), 0)


def _move_score(
    move: int, board: Board, killer_moves: list, depth: int
) -> int:
    """Assign a sort score to a move for ordering."""
    if is_capture(move):
        return 10000 + _mvv_lva_score(move, board)
    if move == killer_moves[depth][0]:
        return 9000
    if move == killer_moves[depth][1]:
        return 8000
    return 0


def order_moves(
    moves: list[int],
    board: Board,
    killer_moves: list,
    depth: int,
) -> None:
    """Sort moves in-place: captures by MVV-LVA, then killers, then quiet."""
    moves.sort(
        key=lambda m: _move_score(m, board, killer_moves, depth),
        reverse=True,
    )


def order_captures(moves: list[int], board: Board) -> None:
    """Sort capture moves in-place by MVV-LVA score."""
    moves.sort(key=lambda m: _mvv_lva_score(m, board), reverse=True)
