"""Tests for evaluation module."""

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
    BLACK,
    WHITE_PAWN,
    WHITE_KNIGHT,
    WHITE_BISHOP,
    WHITE_ROOK,
    WHITE_QUEEN,
    WHITE_KING,
    BLACK_PAWN,
    BLACK_KNIGHT,
    BLACK_BISHOP,
    BLACK_ROOK,
    BLACK_QUEEN,
    BLACK_KING,
    FEN_TO_PIECE,
)
from src.evaluation import MATE_SCORE, PIECE_VALUES, PST, evaluate


# ---------------------------------------------------------------------------
# Lightweight Board stub (mirrors the real Board interface)
# ---------------------------------------------------------------------------
class _BoardStub:
    """Minimal board for evaluation tests — no make/unmake needed."""

    __slots__ = ("squares", "turn")

    def __init__(self, fen: str | None = None) -> None:
        self.squares: list[int] = [EMPTY] * 64
        self.turn: int = WHITE
        if fen is None:
            fen = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        self._set_fen(fen)

    def _set_fen(self, fen: str) -> None:
        parts = fen.split()
        ranks = parts[0].split("/")
        self.squares = [EMPTY] * 64
        for rank_idx, rank_str in enumerate(ranks):
            sq = (7 - rank_idx) * 8
            for ch in rank_str:
                if ch.isdigit():
                    sq += int(ch)
                else:
                    self.squares[sq] = FEN_TO_PIECE[ch]
                    sq += 1
        self.turn = WHITE if parts[1] == "w" else BLACK


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_starting_position_eval() -> None:
    """Starting position should evaluate to exactly 0 (symmetric)."""
    board = _BoardStub()
    score = evaluate(board)
    assert score == 0


def test_white_material_advantage() -> None:
    """Remove a black knight — white should have positive eval."""
    # Remove knight from b8 (square 57)
    board = _BoardStub()
    board.squares[57] = EMPTY  # b8 black knight removed
    score = evaluate(board)
    assert score > 0


def test_black_material_advantage() -> None:
    """Remove a white knight — eval should be negative for white to move."""
    # Remove knight from b1 (square 1)
    board = _BoardStub()
    board.squares[1] = EMPTY  # b1 white knight removed
    score = evaluate(board)
    assert score < 0


def test_pst_knight_center_vs_corner() -> None:
    """Knight on e4 should score higher PST than knight on a1."""
    # e4 = rank 3, file 4 → sq 28
    # a1 = sq 0
    pst_e4 = PST[KNIGHT][28]
    pst_a1 = PST[KNIGHT][0]
    assert pst_e4 > pst_a1


def test_piece_values_correct() -> None:
    """Verify PIECE_VALUES has the correct values."""
    assert PIECE_VALUES[PAWN] == 100
    assert PIECE_VALUES[KNIGHT] == 320
    assert PIECE_VALUES[BISHOP] == 330
    assert PIECE_VALUES[ROOK] == 500
    assert PIECE_VALUES[QUEEN] == 900
    assert PIECE_VALUES[KING] == 20000


def test_mate_score_accessible() -> None:
    """MATE_SCORE constant should be 100000."""
    assert MATE_SCORE == 100000


def test_side_to_move_perspective() -> None:
    """Same board, flip turn — sign changes."""
    board = _BoardStub()
    board.squares[57] = EMPTY  # remove black knight for asymmetry

    score_white = evaluate(board)
    board.turn = BLACK
    score_black = evaluate(board)

    assert score_white == -score_black


def test_extra_queen_dominant() -> None:
    """Adding an extra white queen should produce a large positive score."""
    board = _BoardStub()
    # Place an extra white queen on d4 (sq 27) — normally empty
    board.squares[27] = WHITE_QUEEN
    score = evaluate(board)
    assert score > 900  # at least the queen's material value


def test_empty_board_zero() -> None:
    """A completely empty board evaluates to 0."""
    board = _BoardStub()
    board.squares = [EMPTY] * 64
    score = evaluate(board)
    assert score == 0


def test_lone_pieces_material_diff() -> None:
    """White king + pawn vs black king — positive for white."""
    board = _BoardStub()
    board.squares = [EMPTY] * 64
    board.squares[4] = WHITE_KING    # e1
    board.squares[12] = WHITE_PAWN   # e2
    board.squares[60] = BLACK_KING   # e8
    score = evaluate(board)
    # White has material advantage (pawn + PST difference)
    assert score > 0


def test_symmetric_pst() -> None:
    """PST for pawn at e4 (white) equals PST for pawn at e5 (black mirrored)."""
    # White pawn on e4: sq=28, PST[PAWN][28]
    # Black pawn on e5: sq=36, mirrored = 36^56 = 28 → PST[PAWN][28]
    # So they should get the same PST bonus
    assert PST[PAWN][28] == PST[PAWN][36 ^ 56]


def test_pst_tables_have_64_entries() -> None:
    """Each PST table must have exactly 64 entries."""
    for pt in (PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING):
        assert len(PST[pt]) == 64, f"PST[{pt}] has {len(PST[pt])} entries"


def test_black_to_move_extra_black_piece() -> None:
    """Extra black piece with black to move should give positive eval."""
    board = _BoardStub()
    board.squares[1] = EMPTY  # remove white knight b1
    board.turn = BLACK
    score = evaluate(board)
    # Black has more material, and it's black to move → positive
    assert score > 0
