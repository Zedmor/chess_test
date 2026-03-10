"""Tests for the opening book module."""

from __future__ import annotations

from src.board import Board
from src.constants import (
    decode_from, decode_to, move_to_uci, parse_uci_move, encode_move,
    QUIET, DOUBLE_PAWN, CAPTURE,
)
from src.opening_book import get_book_move, OPENING_BOOK
from src.movegen import generate_legal_moves


# ---------------------------------------------------------------------------
# Basic book lookup
# ---------------------------------------------------------------------------

def test_starting_position_returns_move() -> None:
    """Book should return a move for the starting position."""
    board = Board()
    move = get_book_move(board)
    assert move is not None


def test_unknown_position_returns_none() -> None:
    """Book should return None for a position not in the book."""
    # A random mid-game position unlikely to be in the book
    board = Board("8/8/4k3/8/8/4K3/8/8 w - - 0 1")
    move = get_book_move(board)
    assert move is None


def test_starting_move_is_legal() -> None:
    """The book move for the starting position must be legal."""
    board = Board()
    move = get_book_move(board)
    assert move is not None
    legal_moves = generate_legal_moves(board)
    assert move in legal_moves


# ---------------------------------------------------------------------------
# All book entries produce legal moves
# ---------------------------------------------------------------------------

def test_all_book_moves_are_legal() -> None:
    """Every move in the book should be legal in its position."""
    for fen, uci_list in OPENING_BOOK.items():
        full_fen = fen + " 0 1"
        board = Board(full_fen)
        legal_moves = generate_legal_moves(board)
        for uci_str in uci_list:
            move = parse_uci_move(board, uci_str)
            assert move in legal_moves, (
                f"Illegal book move {uci_str} in position {fen}"
            )


# ---------------------------------------------------------------------------
# Opening coverage: e4 and d4 responses
# ---------------------------------------------------------------------------

def test_e4_response_exists() -> None:
    """After 1.e4, the book should have a Black response."""
    board = Board()
    board.make_move(parse_uci_move(board, "e2e4"))
    move = get_book_move(board)
    assert move is not None


def test_d4_response_exists() -> None:
    """After 1.d4, the book should have a Black response."""
    board = Board()
    board.make_move(parse_uci_move(board, "d2d4"))
    move = get_book_move(board)
    assert move is not None


# ---------------------------------------------------------------------------
# Specific opening theory
# ---------------------------------------------------------------------------

def test_italian_game_bc4() -> None:
    """After 1.e4 e5 2.Nf3 Nc6, Bc4 (Italian) should be a book move."""
    board = Board()
    for uci in ["e2e4", "e7e5", "g1f3", "b8c6"]:
        board.make_move(parse_uci_move(board, uci))
    move = get_book_move(board)
    assert move is not None
    uci_str = move_to_uci(move)
    assert uci_str in ("f1c4", "f1b5"), f"Expected Italian or Ruy Lopez, got {uci_str}"


def test_ruy_lopez_bb5() -> None:
    """After 1.e4 e5 2.Nf3 Nc6, Bb5 (Ruy Lopez) is a valid book move."""
    board = Board()
    for uci in ["e2e4", "e7e5", "g1f3", "b8c6"]:
        board.make_move(parse_uci_move(board, uci))
    # Both Bc4 and Bb5 are in the book
    key = board.get_position_fen()
    assert "f1b5" in OPENING_BOOK[key]


def test_sicilian_defense() -> None:
    """After 1.e4 c5 (Sicilian), the book should have a White response."""
    board = Board()
    for uci in ["e2e4", "c7c5"]:
        board.make_move(parse_uci_move(board, uci))
    move = get_book_move(board)
    assert move is not None
    uci_str = move_to_uci(move)
    assert uci_str in ("g1f3", "b1c3"), f"Expected Nf3 or Nc3, got {uci_str}"


def test_french_defense() -> None:
    """After 1.e4 e6 (French), the book should respond with d4."""
    board = Board()
    for uci in ["e2e4", "e7e6"]:
        board.make_move(parse_uci_move(board, uci))
    move = get_book_move(board)
    assert move is not None
    assert move_to_uci(move) == "d2d4"


def test_queens_gambit() -> None:
    """After 1.d4 d5, c4 (Queen's Gambit) should be a book move."""
    board = Board()
    for uci in ["d2d4", "d7d5"]:
        board.make_move(parse_uci_move(board, uci))
    move = get_book_move(board)
    assert move is not None
    uci_str = move_to_uci(move)
    assert uci_str in ("c2c4", "g1f3"), f"Expected c4 or Nf3, got {uci_str}"


def test_kings_indian_setup() -> None:
    """After 1.d4 Nf6 2.c4, g6 should be a book move for Black."""
    board = Board()
    for uci in ["d2d4", "g8f6", "c2c4"]:
        board.make_move(parse_uci_move(board, uci))
    move = get_book_move(board)
    assert move is not None
    uci_str = move_to_uci(move)
    assert uci_str in ("g7g6", "e7e6"), f"Expected g6 or e6, got {uci_str}"


# ---------------------------------------------------------------------------
# Depth of book lines
# ---------------------------------------------------------------------------

def test_ruy_lopez_line_depth() -> None:
    """Ruy Lopez line should go at least 5 half-moves deep."""
    board = Board()
    for uci in ["e2e4", "e7e5", "g1f3", "b8c6", "f1b5"]:
        board.make_move(parse_uci_move(board, uci))
    # After 3.Bb5, Black should have a book move (a6, Nf6, or Bc5)
    move = get_book_move(board)
    assert move is not None


def test_sicilian_najdorf_depth() -> None:
    """Sicilian line should go at least 4 half-moves deep."""
    board = Board()
    for uci in ["e2e4", "c7c5", "g1f3", "d7d6"]:
        board.make_move(parse_uci_move(board, uci))
    move = get_book_move(board)
    assert move is not None
    assert move_to_uci(move) == "d2d4"


def test_italian_game_depth() -> None:
    """Italian Game after Bc4 should have Black responses."""
    board = Board()
    for uci in ["e2e4", "e7e5", "g1f3", "b8c6", "f1c4"]:
        board.make_move(parse_uci_move(board, uci))
    move = get_book_move(board)
    assert move is not None
    uci_str = move_to_uci(move)
    assert uci_str in ("f8c5", "g8f6"), f"Expected Bc5 or Nf6, got {uci_str}"


# ---------------------------------------------------------------------------
# Book variety
# ---------------------------------------------------------------------------

def test_starting_position_variety() -> None:
    """Starting position should have multiple book options."""
    board = Board()
    key = board.get_position_fen()
    assert len(OPENING_BOOK[key]) >= 3, "Starting position should offer variety"


def test_book_covers_both_colors() -> None:
    """Book should have entries for both White and Black to move."""
    white_entries = 0
    black_entries = 0
    for fen in OPENING_BOOK:
        if " w " in fen:
            white_entries += 1
        elif " b " in fen:
            black_entries += 1
    assert white_entries >= 5, f"Only {white_entries} White-to-move entries"
    assert black_entries >= 5, f"Only {black_entries} Black-to-move entries"


def test_book_has_sufficient_positions() -> None:
    """Book should contain at least 20 positions."""
    assert len(OPENING_BOOK) >= 20


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------

def test_book_move_after_non_book_line() -> None:
    """After leaving book lines, get_book_move should return None."""
    board = Board()
    # Play a weird opening not in the book
    board.make_move(parse_uci_move(board, "a2a3"))
    board.make_move(parse_uci_move(board, "a7a6"))
    board.make_move(parse_uci_move(board, "b2b3"))
    move = get_book_move(board)
    assert move is None


def test_book_fen_keys_are_valid() -> None:
    """All FEN keys in the book should be parseable."""
    for fen in OPENING_BOOK:
        full_fen = fen + " 0 1"
        board = Board(full_fen)
        # Should not raise
        result_fen = board.get_position_fen()
        assert result_fen == fen, f"FEN roundtrip failed: {fen} -> {result_fen}"
