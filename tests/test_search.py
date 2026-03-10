"""Tests for search module: alpha-beta, quiescence, iterative deepening."""

from __future__ import annotations

import time

import pytest

from src.board import Board
from src.constants import (
    decode_from, decode_to, move_to_uci,
    is_capture, encode_move,
    WHITE, BLACK,
)
from src.evaluation import MATE_SCORE
from src.movegen import generate_legal_moves
from src.search import (
    search, negamax_root, negamax, quiescence,
    SearchTimeout,
)
from src.move_ordering import create_killer_table


def _ply(board: Board) -> int:
    return len(board.history)


class TestMateInOne:
    """Search must find mate-in-1 in obvious positions."""

    def test_white_back_rank_mate(self) -> None:
        # White Ra1, Kg6; Black Kg8 — Ra8# is mate
        board = Board("6k1/8/6K1/8/8/8/8/R7 w - - 0 1")
        move = search(board, 2.0)
        uci = move_to_uci(move)
        assert uci == "a1a8", f"Expected a1a8 (Ra8#), got {uci}"

    def test_white_rook_mate(self) -> None:
        # White Rh1, Kb6; Black Ka8 — Rh8# is mate
        board = Board("k7/8/1K6/8/8/8/8/7R w - - 0 1")
        move = search(board, 2.0)
        uci = move_to_uci(move)
        assert uci == "h1h8", f"Expected h1h8 (Rh8#), got {uci}"

    def test_black_mate_in_one(self) -> None:
        # Black Ra7, Ke6; White Ke8 — Ra8# is mate
        # After Ra8+: d8/f8 covered by rook, d7/e7/f7 covered by king
        board = Board("4K3/r7/4k3/8/8/8/8/8 b - - 0 1")
        move = search(board, 2.0)
        uci = move_to_uci(move)
        assert uci == "a7a8", f"Expected a7a8 (Ra8#), got {uci}"

    def test_mate_in_one_verified(self) -> None:
        # Generic mate-in-1 verification: engine's move must leave opponent
        # with no legal moves and in check
        board = Board("6k1/8/6K1/8/8/8/8/R7 w - - 0 1")
        move = search(board, 2.0)
        board.make_move(move)
        legal = generate_legal_moves(board)
        assert len(legal) == 0
        assert board.is_in_check()


class TestMateInTwo:
    """Search must find mate-in-2."""

    def test_mate_in_two_kqvk(self) -> None:
        # White Kd6, Qe1; Black Kd8
        # Multiple mates in 2 exist (e.g. Qe7+ Kc8 Qc7#)
        board = Board("3k4/8/3K4/8/8/8/8/4Q3 w - - 0 1")
        move = search(board, 3.0)
        uci = move_to_uci(move)
        # Verify forced mate in at most 2 moves
        board.make_move(move)
        black_moves = generate_legal_moves(board)
        if not black_moves:
            # Mate in 1
            assert board.is_in_check()
            return
        for black_move in black_moves:
            board.make_move(black_move)
            w_reply = search(board, 1.0)
            board.make_move(w_reply)
            legal = generate_legal_moves(board)
            is_mate = len(legal) == 0 and board.is_in_check()
            board.unmake_move()
            board.unmake_move()
            assert is_mate, (
                f"After {uci} {move_to_uci(black_move)} "
                f"{move_to_uci(w_reply)} is not mate"
            )

    def test_mate_in_two_queen_rook(self) -> None:
        # White Kg1, Qh5, Ra1; Black Kg8, f7/g7/h7 pawns
        board = Board("6k1/5ppp/8/7Q/8/8/8/R5K1 w - - 0 1")
        move = search(board, 3.0)
        uci = move_to_uci(move)
        board.make_move(move)
        black_moves = generate_legal_moves(board)
        if not black_moves:
            assert board.is_in_check()
            return
        for black_move in black_moves:
            board.make_move(black_move)
            w_reply = search(board, 1.0)
            board.make_move(w_reply)
            legal = generate_legal_moves(board)
            is_mate = len(legal) == 0 and board.is_in_check()
            board.unmake_move()
            board.unmake_move()
            assert is_mate, (
                f"After {uci} {move_to_uci(black_move)}, "
                f"{move_to_uci(w_reply)} is not mate"
            )


class TestReturnsLegalMove:
    """Search must always return a legal move when one exists."""

    def test_starting_position(self) -> None:
        board = Board()
        move = search(board, 1.0)
        legal = generate_legal_moves(board)
        assert move in legal

    def test_kiwipete(self) -> None:
        board = Board(
            "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/"
            "PPPBBPPP/R3K2R w KQkq - 0 1"
        )
        move = search(board, 1.0)
        legal = generate_legal_moves(board)
        assert move in legal

    def test_endgame_position(self) -> None:
        board = Board("8/8/4k3/8/8/4K3/4P3/8 w - - 0 1")
        move = search(board, 1.0)
        legal = generate_legal_moves(board)
        assert move in legal

    def test_black_to_move(self) -> None:
        board = Board(
            "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"
        )
        move = search(board, 1.0)
        legal = generate_legal_moves(board)
        assert move in legal


class TestDeeperSearchBetter:
    """Deeper search should find equal or better moves."""

    def test_deeper_finds_tactic(self) -> None:
        # White has a rook, black has nothing (besides king)
        # At any depth white should find a good score
        board = Board("4k3/8/8/8/8/8/8/R3K3 w - - 0 1")
        killer1 = create_killer_table()
        killer2 = create_killer_table()
        deadline = time.time() + 10.0

        score_d1, _ = negamax_root(board, 1, killer1, deadline)
        score_d3, _ = negamax_root(board, 3, killer2, deadline)

        # Both should recognize white has a big advantage
        assert score_d1 > 400
        assert score_d3 > 400


class TestTimeLimit:
    """Search must respect the time limit."""

    def test_returns_within_time(self) -> None:
        board = Board()
        time_limit = 0.5
        start = time.time()
        move = search(board, time_limit)
        elapsed = time.time() - start
        assert elapsed < time_limit * 2.0, (
            f"Search took {elapsed:.2f}s, limit was {time_limit}s"
        )
        assert move is not None

    def test_very_short_time(self) -> None:
        board = Board()
        move = search(board, 0.01)
        legal = generate_legal_moves(board)
        assert move in legal


class TestQuiescence:
    """Quiescence search handles captures correctly."""

    def test_quiet_position_returns_eval(self) -> None:
        board = Board("4k3/8/8/8/8/8/8/4K3 w - - 0 1")
        deadline = time.time() + 5.0
        score = quiescence(board, -MATE_SCORE, MATE_SCORE, deadline)
        assert abs(score) < 50

    def test_winning_capture_improves_score(self) -> None:
        # White pawn on e3 can capture black queen on d4 (PxQ)
        board = Board("4k3/8/8/8/3q4/4P3/8/4K3 w - - 0 1")
        deadline = time.time() + 5.0
        score = quiescence(board, -MATE_SCORE, MATE_SCORE, deadline)
        # After exd4, white gains ~800cp (queen - pawn values)
        assert score > 0, f"Expected positive score, got {score}"

    def test_timeout_in_quiescence(self) -> None:
        board = Board()
        with pytest.raises(SearchTimeout):
            quiescence(board, -MATE_SCORE, MATE_SCORE, time.time() - 1.0)


class TestNegamax:
    """Direct negamax tests."""

    def test_mate_score_high(self) -> None:
        # White can mate in 1 with Ra8#
        board = Board("6k1/8/6K1/8/8/8/8/R7 w - - 0 1")
        killers = create_killer_table()
        deadline = time.time() + 5.0
        score = negamax(board, 2, -MATE_SCORE - 1, MATE_SCORE + 1,
                        killers, deadline, _ply(board))
        assert score > MATE_SCORE - 100

    def test_stalemate_returns_zero(self) -> None:
        # Black to move, stalemated
        board = Board("k7/2Q5/1K6/8/8/8/8/8 b - - 0 1")
        legal = generate_legal_moves(board)
        assert len(legal) == 0
        assert not board.is_in_check()
        killers = create_killer_table()
        deadline = time.time() + 5.0
        score = negamax(board, 1, -MATE_SCORE - 1, MATE_SCORE + 1,
                        killers, deadline, _ply(board))
        assert score == 0

    def test_timeout_raises(self) -> None:
        board = Board()
        killers = create_killer_table()
        with pytest.raises(SearchTimeout):
            negamax(board, 10, -MATE_SCORE - 1, MATE_SCORE + 1,
                    killers, time.time() - 1.0, _ply(board))


class TestDrawDetection:
    """Search handles draws correctly."""

    def test_fifty_move_rule(self) -> None:
        board = Board("4k3/8/8/8/8/8/8/4K3 w - - 100 50")
        killers = create_killer_table()
        deadline = time.time() + 5.0
        score = negamax(board, 1, -MATE_SCORE - 1, MATE_SCORE + 1,
                        killers, deadline, _ply(board))
        assert score == 0

    def test_returns_move_in_drawn_position(self) -> None:
        board = Board("4k3/8/8/8/8/8/8/4K3 w - - 0 1")
        move = search(board, 1.0)
        legal = generate_legal_moves(board)
        assert move in legal


class TestMateScore:
    """Mate scores prefer shorter mates."""

    def test_prefers_shorter_mate(self) -> None:
        board = Board("6k1/8/6K1/8/8/8/8/R7 w - - 0 1")
        killers = create_killer_table()
        deadline = time.time() + 5.0
        score, move = negamax_root(board, 4, killers, deadline)
        assert score > MATE_SCORE - 10
        uci = move_to_uci(move)
        assert uci == "a1a8"


class TestSearchIntegrity:
    """Board state must be unchanged after search."""

    def test_board_unchanged_after_search(self) -> None:
        board = Board()
        fen_before = board.get_fen()
        search(board, 1.0)
        fen_after = board.get_fen()
        assert fen_before == fen_after

    def test_board_unchanged_kiwipete(self) -> None:
        fen = (
            "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/"
            "PPPBBPPP/R3K2R w KQkq - 0 1"
        )
        board = Board(fen)
        fen_before = board.get_fen()
        search(board, 1.0)
        fen_after = board.get_fen()
        assert fen_before == fen_after

    def test_history_unchanged(self) -> None:
        board = Board()
        hist_len = len(board.history)
        search(board, 0.5)
        assert len(board.history) == hist_len


class TestCaptureAvoidance:
    """Quiescence should prevent horizon effect on obvious captures."""

    def test_does_not_walk_into_capture(self) -> None:
        # White Qd4, Ke1; Black Ke8, Rd8 (defends d-file)
        # Queen should not go to d8 where rook captures it
        board = Board("3rk3/8/8/8/3Q4/8/8/4K3 w - - 0 1")
        move = search(board, 2.0)
        uci = move_to_uci(move)
        assert uci != "d4d8", "Engine blundered queen to d8 where rook takes"

    def test_captures_free_piece(self) -> None:
        # White Rd1, Ke1; Black Ke8, Nd5 (undefended)
        # Rook should capture knight: Rxd5
        board = Board("4k3/8/8/3n4/8/8/8/3RK3 w - - 0 1")
        move = search(board, 2.0)
        uci = move_to_uci(move)
        # d5 = sq 35, d1 = sq 3
        assert decode_to(move) == 35, (
            f"Expected capture on d5 (sq 35), got {uci}"
        )
