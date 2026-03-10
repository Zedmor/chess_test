"""Tests for move ordering: MVV-LVA and killer moves."""

import pytest

from src.board import (
    EMPTY, W_PAWN, W_KNIGHT, W_ROOK, W_QUEEN,
    B_PAWN, B_KNIGHT, B_QUEEN, WHITE, Board,
)
from src.move_ordering import (
    MVV_LVA_SCORES,
    create_killer_table,
    update_killers,
    order_moves,
    order_captures,
    _is_capture,
)


def _make_board() -> Board:
    """Return an empty board with white to move."""
    return Board()


class TestCapturesBeforeNonCaptures:
    def test_captures_before_non_captures(self) -> None:
        """After ordering, all captures come before non-captures."""
        board = _make_board()
        # White pawn on e4 (sq 28), black pawn on d5 (sq 35)
        # White pawn on e2 (sq 12) for a quiet push
        board.squares[28] = W_PAWN
        board.squares[35] = B_PAWN
        board.squares[12] = W_PAWN

        capture = (28, 35, 0)   # pawn takes pawn
        quiet = (12, 20, 0)     # pawn push e2-e3
        moves = [quiet, capture]

        killers = create_killer_table()
        ordered = order_moves(moves, board, killers, 0)

        assert ordered[0] == capture
        assert ordered[1] == quiet


class TestMvvLvaQueenCaptureFirst:
    def test_mvv_lva_queen_capture_first(self) -> None:
        """Capturing a queen is ranked higher than capturing a pawn."""
        board = _make_board()
        # White pawn on d4 (sq 27), black queen on e5 (sq 36)
        # White knight on c3 (sq 18), black pawn on d5 (sq 35)
        board.squares[27] = W_PAWN
        board.squares[36] = B_QUEEN
        board.squares[18] = W_KNIGHT
        board.squares[35] = B_PAWN

        pawn_takes_queen = (27, 36, 0)   # PxQ: 900*10 - 100 = 8900
        knight_takes_pawn = (18, 35, 0)   # NxP: 100*10 - 320 = 680

        killers = create_killer_table()
        ordered = order_moves(
            [knight_takes_pawn, pawn_takes_queen], board, killers, 0
        )

        assert ordered[0] == pawn_takes_queen
        assert ordered[1] == knight_takes_pawn

    def test_mvv_lva_scores_precomputed(self) -> None:
        """MVV-LVA table has correct scores for key pairs."""
        # PxQ = 900*10 - 100 = 8900
        assert MVV_LVA_SCORES[(5, 1)] == 8900
        # NxP = 100*10 - 320 = 680
        assert MVV_LVA_SCORES[(1, 2)] == 680
        # QxQ = 900*10 - 900 = 8100
        assert MVV_LVA_SCORES[(5, 5)] == 8100


class TestKillerMovesAfterCaptures:
    def test_killer_moves_after_captures(self) -> None:
        """Killer moves sorted between captures and quiet moves."""
        board = _make_board()
        board.squares[28] = W_PAWN
        board.squares[35] = B_PAWN
        board.squares[12] = W_PAWN
        board.squares[8] = W_PAWN

        capture = (28, 35, 0)
        killer_move = (12, 20, 0)
        quiet = (8, 16, 0)

        killers = create_killer_table()
        killers[0][0] = killer_move

        ordered = order_moves([quiet, killer_move, capture], board, killers, 0)

        assert ordered[0] == capture
        assert ordered[1] == killer_move
        assert ordered[2] == quiet

    def test_second_killer_after_first(self) -> None:
        """Second killer slot has lower priority than first."""
        board = _make_board()
        board.squares[8] = W_PAWN
        board.squares[12] = W_PAWN
        board.squares[16] = W_PAWN

        killer1 = (8, 16, 0)
        killer2 = (12, 20, 0)
        quiet = (16, 24, 0)

        # Manually set both pieces on destination to EMPTY (non-captures)
        killers = create_killer_table()
        killers[0][0] = killer1
        killers[0][1] = killer2

        ordered = order_moves([quiet, killer2, killer1], board, killers, 0)

        assert ordered[0] == killer1
        assert ordered[1] == killer2
        assert ordered[2] == quiet


class TestUpdateKillers:
    def test_update_killers(self) -> None:
        """Inserting a killer shifts the old one to slot [1]."""
        killers = create_killer_table()
        move_a = (12, 28, 0)
        move_b = (8, 16, 0)

        update_killers(killers, move_a, 0)
        assert killers[0][0] == move_a
        assert killers[0][1] is None

        update_killers(killers, move_b, 0)
        assert killers[0][0] == move_b
        assert killers[0][1] == move_a

    def test_same_killer_not_duplicated(self) -> None:
        """Inserting the same move again does not shift."""
        killers = create_killer_table()
        move_a = (12, 28, 0)
        move_b = (8, 16, 0)

        update_killers(killers, move_a, 0)
        update_killers(killers, move_b, 0)
        update_killers(killers, move_b, 0)  # duplicate

        assert killers[0][0] == move_b
        assert killers[0][1] == move_a

    def test_killers_independent_per_depth(self) -> None:
        """Killer moves at different depths are independent."""
        killers = create_killer_table()
        move_a = (12, 28, 0)
        move_b = (8, 16, 0)

        update_killers(killers, move_a, 0)
        update_killers(killers, move_b, 3)

        assert killers[0][0] == move_a
        assert killers[3][0] == move_b
        assert killers[1][0] is None


class TestOrderCapturesOnly:
    def test_order_captures_only(self) -> None:
        """order_captures returns only captures, sorted by MVV-LVA."""
        board = _make_board()
        board.squares[27] = W_PAWN
        board.squares[36] = B_QUEEN
        board.squares[18] = W_KNIGHT
        board.squares[35] = B_PAWN
        board.squares[12] = W_PAWN

        pawn_takes_queen = (27, 36, 0)
        knight_takes_pawn = (18, 35, 0)
        quiet = (12, 20, 0)

        result = order_captures(
            [quiet, knight_takes_pawn, pawn_takes_queen], board
        )

        assert len(result) == 2
        assert result[0] == pawn_takes_queen
        assert result[1] == knight_takes_pawn

    def test_no_captures_returns_empty(self) -> None:
        """order_captures with no captures returns empty list."""
        board = _make_board()
        board.squares[12] = W_PAWN
        result = order_captures([(12, 20, 0)], board)
        assert result == []


class TestEnPassantCapture:
    def test_en_passant_capture(self) -> None:
        """En passant is counted as a capture with pawn victim."""
        board = _make_board()
        # White pawn on e5 (sq 36), black pawn just double-pushed to d5 (sq 35)
        # ep_square = d6 (sq 43)
        board.squares[36] = W_PAWN
        board.squares[35] = B_PAWN
        board.ep_square = 43

        ep_move = (36, 43, 0)  # pawn captures en passant
        assert _is_capture(ep_move, board) is True

    def test_en_passant_in_ordering(self) -> None:
        """En passant capture is ordered before quiet moves."""
        board = _make_board()
        board.squares[36] = W_PAWN
        board.squares[35] = B_PAWN
        board.squares[12] = W_PAWN
        board.ep_square = 43

        ep_move = (36, 43, 0)
        quiet = (12, 20, 0)

        killers = create_killer_table()
        ordered = order_moves([quiet, ep_move], board, killers, 0)

        assert ordered[0] == ep_move
        assert ordered[1] == quiet

    def test_en_passant_in_order_captures(self) -> None:
        """En passant appears in order_captures results."""
        board = _make_board()
        board.squares[36] = W_PAWN
        board.squares[35] = B_PAWN
        board.ep_square = 43

        ep_move = (36, 43, 0)
        quiet = (12, 20, 0)
        board.squares[12] = W_PAWN

        result = order_captures([quiet, ep_move], board)

        assert len(result) == 1
        assert result[0] == ep_move
