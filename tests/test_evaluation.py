"""Tests for evaluation module."""

import chess

from src.evaluation import MATE_SCORE, PIECE_VALUES, PST, evaluate


def test_starting_position_eval() -> None:
    """Starting position should evaluate to approximately 0."""
    board = chess.Board()
    score = evaluate(board)
    assert score == 0


def test_white_material_advantage() -> None:
    """Remove a black knight — white should have positive eval."""
    board = chess.Board()
    board.remove_piece_at(chess.B8)  # remove black knight
    score = evaluate(board)
    # From white's perspective (white to move), should be positive
    assert score > 0


def test_black_material_advantage() -> None:
    """Remove a white knight — eval should be negative for white to move."""
    board = chess.Board()
    board.remove_piece_at(chess.B1)  # remove white knight
    score = evaluate(board)
    # From white's perspective (white to move), should be negative
    assert score < 0


def test_pst_center_pawn() -> None:
    """White pawn on e4 should have higher PST than on a2."""
    pst_e4 = PST[chess.PAWN][chess.E4]  # e4 = center
    pst_a2 = PST[chess.PAWN][chess.A2]  # a2 = edge rank 2
    assert pst_e4 > pst_a2


def test_piece_values_correct() -> None:
    """Verify PIECE_VALUES has the correct values."""
    assert PIECE_VALUES[chess.PAWN] == 100
    assert PIECE_VALUES[chess.KNIGHT] == 320
    assert PIECE_VALUES[chess.BISHOP] == 330
    assert PIECE_VALUES[chess.ROOK] == 500
    assert PIECE_VALUES[chess.QUEEN] == 900
    assert PIECE_VALUES[chess.KING] == 20000


def test_checkmate_eval() -> None:
    """Checkmate position returns -MATE_SCORE for side to move."""
    # Scholar's mate: 1.e4 e5 2.Qh5 Nc6 3.Bc4 Nf6 4.Qxf7#
    board = chess.Board()
    for move in ["e2e4", "e7e5", "d1h5", "b8c6", "f1c4", "g8f6", "h5f7"]:
        board.push_uci(move)
    assert board.is_checkmate()
    score = evaluate(board)
    assert score == -MATE_SCORE


def test_stalemate_eval() -> None:
    """Stalemate position returns 0."""
    # Known stalemate position: black king on a8, white queen on b6, white king on a6
    board = chess.Board(fen="k7/8/KQ6/8/8/8/8/8 b - - 0 1")
    assert board.is_stalemate()
    score = evaluate(board)
    assert score == 0


def test_side_to_move_perspective() -> None:
    """Same board, flip turn — sign changes."""
    board = chess.Board()
    board.remove_piece_at(chess.B8)  # remove black knight for asymmetry

    score_white = evaluate(board)
    board.turn = chess.BLACK
    score_black = evaluate(board)

    assert score_white == -score_black
