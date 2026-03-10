"""Material + piece-square table evaluation."""

from __future__ import annotations

from src.constants import (
    EMPTY,
    PAWN,
    KNIGHT,
    BISHOP,
    ROOK,
    QUEEN,
    KING,
    WHITE,
)

MATE_SCORE: int = 100000

PIECE_VALUES: dict[int, int] = {
    PAWN: 100,
    KNIGHT: 320,
    BISHOP: 330,
    ROOK: 500,
    QUEEN: 900,
    KING: 20000,
}

# Piece-square tables from white's perspective (a1=index 0).
# Values from Tomasz Michniewski's Simplified Evaluation Function.
PST: dict[int, tuple[int, ...]] = {
    PAWN: (
          0,   0,   0,   0,   0,   0,   0,   0,  # rank 1
          5,  10,  10, -20, -20,  10,  10,   5,  # rank 2
          5,  -5, -10,   0,   0, -10,  -5,   5,  # rank 3
          0,   0,   0,  20,  20,   0,   0,   0,  # rank 4
          5,   5,  10,  25,  25,  10,   5,   5,  # rank 5
         10,  10,  20,  30,  30,  20,  10,  10,  # rank 6
         50,  50,  50,  50,  50,  50,  50,  50,  # rank 7
          0,   0,   0,   0,   0,   0,   0,   0,  # rank 8
    ),
    KNIGHT: (
        -50, -40, -30, -30, -30, -30, -40, -50,
        -40, -20,   0,   5,   5,   0, -20, -40,
        -30,   5,  10,  15,  15,  10,   5, -30,
        -30,   0,  15,  20,  20,  15,   0, -30,
        -30,   5,  15,  20,  20,  15,   5, -30,
        -30,   0,  10,  15,  15,  10,   0, -30,
        -40, -20,   0,   0,   0,   0, -20, -40,
        -50, -40, -30, -30, -30, -30, -40, -50,
    ),
    BISHOP: (
        -20, -10, -10, -10, -10, -10, -10, -20,
        -10,   5,   0,   0,   0,   0,   5, -10,
        -10,  10,  10,  10,  10,  10,  10, -10,
        -10,   0,  10,  10,  10,  10,   0, -10,
        -10,   5,   5,  10,  10,   5,   5, -10,
        -10,   0,   5,  10,  10,   5,   0, -10,
        -10,   0,   0,   0,   0,   0,   0, -10,
        -20, -10, -10, -10, -10, -10, -10, -20,
    ),
    ROOK: (
          0,   0,   0,   5,   5,   0,   0,   0,
         -5,   0,   0,   0,   0,   0,   0,  -5,
         -5,   0,   0,   0,   0,   0,   0,  -5,
         -5,   0,   0,   0,   0,   0,   0,  -5,
         -5,   0,   0,   0,   0,   0,   0,  -5,
         -5,   0,   0,   0,   0,   0,   0,  -5,
          5,  10,  10,  10,  10,  10,  10,   5,
          0,   0,   0,   0,   0,   0,   0,   0,
    ),
    QUEEN: (
        -20, -10, -10,  -5,  -5, -10, -10, -20,
        -10,   0,   5,   0,   0,   0,   0, -10,
        -10,   5,   5,   5,   5,   5,   0, -10,
          0,   0,   5,   5,   5,   5,   0,  -5,
         -5,   0,   5,   5,   5,   5,   0,  -5,
        -10,   0,   5,   5,   5,   5,   0, -10,
        -10,   0,   0,   0,   0,   0,   0, -10,
        -20, -10, -10,  -5,  -5, -10, -10, -20,
    ),
    KING: (
         20,  30,  10,   0,   0,  10,  30,  20,
         20,  20,   0,   0,   0,   0,  20,  20,
        -10, -20, -20, -20, -20, -20, -20, -10,
        -20, -30, -30, -40, -40, -30, -30, -20,
        -30, -40, -40, -50, -50, -40, -40, -30,
        -30, -40, -40, -50, -50, -40, -40, -30,
        -30, -40, -40, -50, -50, -40, -40, -30,
        -30, -40, -40, -50, -50, -40, -40, -30,
    ),
}


def evaluate(board: object) -> int:
    """Return eval in centipawns from side-to-move perspective.

    Iterates over all 64 squares.  For each piece found, adds
    PIECE_VALUES[type] + PST[type][sq] for white pieces and subtracts
    the same (using mirrored sq) for black pieces.  Returns from
    side-to-move perspective.
    """
    squares: list[int] = board.squares  # type: ignore[attr-defined]
    turn: int = board.turn  # type: ignore[attr-defined]
    score = 0
    for sq in range(64):
        piece = squares[sq]
        if piece == EMPTY:
            continue
        pt = piece & 7
        color = piece >> 3
        val = PIECE_VALUES[pt] + PST[pt][sq if color == WHITE else sq ^ 56]
        if color == WHITE:
            score += val
        else:
            score -= val
    return score if turn == WHITE else -score
