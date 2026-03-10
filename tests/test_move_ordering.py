"""Tests for move ordering: MVV-LVA and killer moves."""

from src.constants import (
    EMPTY, PAWN, KNIGHT, QUEEN,
    WHITE_PAWN, WHITE_KNIGHT, WHITE_QUEEN,
    BLACK_PAWN, BLACK_QUEEN,
    CAPTURE, QUIET, EP_CAPTURE,
    encode_move,
)
from src.board import Board
from src.move_ordering import (
    MVV_LVA_SCORES,
    create_killer_table,
    update_killers,
    order_moves,
    order_captures,
)


# Square indices: a1=0, b1=1, ..., h1=7, a2=8, ..., h8=63
E2 = 12
E3 = 20
E4 = 28
D5 = 35
E5 = 36
D4 = 27
C3 = 18
A2 = 8
A3 = 16
D6 = 43


# ------------------------------------------------------------------ MVV-LVA
class TestMvvLva:
    def test_pxq_ranked_before_qxp(self) -> None:
        """PxQ has higher MVV-LVA score than QxP."""
        # PxQ = 900*10 - 100 = 8900
        # QxP = 100*10 - 900 = 100
        assert MVV_LVA_SCORES[(QUEEN, PAWN)] > MVV_LVA_SCORES[(PAWN, QUEEN)]
        assert MVV_LVA_SCORES[(QUEEN, PAWN)] == 8900
        assert MVV_LVA_SCORES[(PAWN, QUEEN)] == 100

    def test_capture_ordering_by_victim_value(self) -> None:
        """Captures sorted: PxQ before NxP in order_moves."""
        board = Board("4k3/8/8/3qp3/3PN3/8/8/4K3 w - - 0 1")
        # White pawn d4=27 captures black queen d5=35
        pxq = encode_move(D4, D5, CAPTURE)
        # White knight e4=28 captures black pawn e5=36
        nxp = encode_move(E4, E5, CAPTURE)

        moves = [nxp, pxq]
        killers = create_killer_table()
        order_moves(moves, board, killers, 0)

        assert moves[0] == pxq
        assert moves[1] == nxp

    def test_mvv_lva_precomputed_scores(self) -> None:
        """Key MVV-LVA scores are correctly pre-computed."""
        assert MVV_LVA_SCORES[(QUEEN, PAWN)] == 8900   # PxQ
        assert MVV_LVA_SCORES[(PAWN, KNIGHT)] == 680    # NxP
        assert MVV_LVA_SCORES[(QUEEN, QUEEN)] == 8100   # QxQ


# ------------------------------------------------------ Captures before quiet
class TestCapturesBeforeQuiet:
    def test_captures_sorted_before_quiet_moves(self) -> None:
        """After ordering, captures come before non-captures."""
        board = Board("4k3/8/8/3p4/4P3/8/P7/4K3 w - - 0 1")
        # White pawn e4=28 captures black pawn d5=35
        capture = encode_move(E4, D5, CAPTURE)
        # White pawn a2=8 pushes to a3=16
        quiet = encode_move(A2, A3, QUIET)

        moves = [quiet, capture]
        killers = create_killer_table()
        order_moves(moves, board, killers, 0)

        assert moves[0] == capture
        assert moves[1] == quiet


# ------------------------------------------------- Killers before other quiet
class TestKillerMoves:
    def test_killer_before_other_quiet(self) -> None:
        """Killer moves are ordered between captures and quiet moves."""
        board = Board("4k3/8/8/3p4/4P3/8/P3P3/4K3 w - - 0 1")
        capture = encode_move(E4, D5, CAPTURE)
        killer = encode_move(E2, E3, QUIET)
        quiet = encode_move(A2, A3, QUIET)

        killers = create_killer_table()
        killers[0][0] = killer

        moves = [quiet, killer, capture]
        order_moves(moves, board, killers, 0)

        assert moves[0] == capture
        assert moves[1] == killer
        assert moves[2] == quiet

    def test_first_killer_before_second(self) -> None:
        """First killer slot has higher priority than second."""
        board = Board("4k3/8/8/8/8/8/P3P3/4K3 w - - 0 1")
        killer1 = encode_move(A2, A3, QUIET)
        killer2 = encode_move(E2, E3, QUIET)
        quiet = encode_move(E2, E4, QUIET)  # just another quiet move

        killers = create_killer_table()
        killers[0][0] = killer1
        killers[0][1] = killer2

        moves = [quiet, killer2, killer1]
        order_moves(moves, board, killers, 0)

        assert moves[0] == killer1
        assert moves[1] == killer2
        assert moves[2] == quiet


# ------------------------------------------------ order_moves modifies in-place
class TestInPlaceSort:
    def test_order_moves_in_place(self) -> None:
        """order_moves modifies the list in-place and returns None."""
        board = Board("4k3/8/8/3p4/4P3/8/P7/4K3 w - - 0 1")
        capture = encode_move(E4, D5, CAPTURE)
        quiet = encode_move(A2, A3, QUIET)

        moves = [quiet, capture]
        result = order_moves(moves, board, create_killer_table(), 0)

        assert result is None
        assert moves[0] == capture

    def test_order_captures_in_place(self) -> None:
        """order_captures modifies the list in-place and returns None."""
        board = Board("4k3/8/8/3qp3/3PN3/8/8/4K3 w - - 0 1")
        pxq = encode_move(D4, D5, CAPTURE)
        nxp = encode_move(E4, E5, CAPTURE)

        moves = [nxp, pxq]
        result = order_captures(moves, board)

        assert result is None
        assert moves[0] == pxq
        assert moves[1] == nxp


# ------------------------------------------------ update_killers
class TestUpdateKillers:
    def test_insert_killer(self) -> None:
        """First killer goes to slot [0]."""
        killers = create_killer_table()
        move_a = encode_move(E2, E4, QUIET)

        update_killers(killers, move_a, 0)

        assert killers[0][0] == move_a
        assert killers[0][1] is None

    def test_shift_on_new_killer(self) -> None:
        """New killer shifts old [0] to [1]."""
        killers = create_killer_table()
        move_a = encode_move(E2, E4, QUIET)
        move_b = encode_move(A2, A3, QUIET)

        update_killers(killers, move_a, 0)
        update_killers(killers, move_b, 0)

        assert killers[0][0] == move_b
        assert killers[0][1] == move_a

    def test_same_killer_not_duplicated(self) -> None:
        """Inserting the same move again does not shift."""
        killers = create_killer_table()
        move_a = encode_move(E2, E4, QUIET)
        move_b = encode_move(A2, A3, QUIET)

        update_killers(killers, move_a, 0)
        update_killers(killers, move_b, 0)
        update_killers(killers, move_b, 0)  # duplicate

        assert killers[0][0] == move_b
        assert killers[0][1] == move_a

    def test_killers_independent_per_depth(self) -> None:
        """Killers at different depths don't interfere."""
        killers = create_killer_table()
        move_a = encode_move(E2, E4, QUIET)
        move_b = encode_move(A2, A3, QUIET)

        update_killers(killers, move_a, 0)
        update_killers(killers, move_b, 3)

        assert killers[0][0] == move_a
        assert killers[3][0] == move_b
        assert killers[1][0] is None


# ------------------------------------------------ order_captures standalone
class TestOrderCaptures:
    def test_captures_sorted_by_mvv_lva(self) -> None:
        """order_captures sorts by MVV-LVA, higher victim first."""
        board = Board("4k3/8/8/3qp3/3PN3/8/8/4K3 w - - 0 1")
        pxq = encode_move(D4, D5, CAPTURE)
        nxp = encode_move(E4, E5, CAPTURE)

        moves = [nxp, pxq]
        order_captures(moves, board)

        assert moves[0] == pxq
        assert moves[1] == nxp


# ------------------------------------------------ en passant
class TestEnPassant:
    def test_ep_capture_treated_as_capture(self) -> None:
        """En passant is ordered as a capture (before quiet moves)."""
        board = Board("4k3/8/8/4Pp2/8/8/P7/4K3 w - f6 0 1")
        # White pawn e5=36, en passant target f6=45
        ep = encode_move(E5, 45, EP_CAPTURE)
        quiet = encode_move(A2, A3, QUIET)

        moves = [quiet, ep]
        killers = create_killer_table()
        order_moves(moves, board, killers, 0)

        assert moves[0] == ep
        assert moves[1] == quiet
