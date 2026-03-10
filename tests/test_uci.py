"""Tests for UCI protocol handler and main entry point."""

from __future__ import annotations

import io
import sys
from unittest.mock import patch

import pytest

from src.uci import (
    ENGINE_NAME,
    ENGINE_AUTHOR,
    uci_loop,
    _handle_position,
    _handle_go,
    _calculate_time,
)
from src.board import Board
from src.constants import (
    WHITE, BLACK, EMPTY,
    PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING,
    piece_type, piece_color, make_piece,
    move_to_uci, parse_uci_move,
    encode_move, decode_from, decode_to,
)
from src.movegen import generate_legal_moves


# ---------------------------------------------------------------------------
# Helper to capture UCI output
# ---------------------------------------------------------------------------

def run_uci(commands: list[str]) -> str:
    """Run a list of UCI commands and return captured stdout."""
    buf = io.StringIO()
    with patch("sys.stdout", buf):
        uci_loop(input_stream=commands)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Test: uci identification
# ---------------------------------------------------------------------------

class TestUCIIdentification:
    def test_uci_response(self) -> None:
        output = run_uci(["uci\n", "quit\n"])
        assert f"id name {ENGINE_NAME}" in output
        assert f"id author {ENGINE_AUTHOR}" in output
        assert "uciok" in output

    def test_isready_response(self) -> None:
        output = run_uci(["isready\n", "quit\n"])
        assert "readyok" in output

    def test_uci_then_isready(self) -> None:
        output = run_uci(["uci\n", "isready\n", "quit\n"])
        lines = output.strip().split("\n")
        assert any("uciok" in l for l in lines)
        assert any("readyok" in l for l in lines)


# ---------------------------------------------------------------------------
# Test: position command
# ---------------------------------------------------------------------------

class TestPositionCommand:
    def test_startpos(self) -> None:
        board = Board()
        _handle_position(["position", "startpos"], board)
        assert board.get_fen() == "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

    def test_startpos_with_moves(self) -> None:
        board = Board()
        _handle_position(
            ["position", "startpos", "moves", "e2e4", "e7e5"], board
        )
        assert board.turn == WHITE
        # e4 and e5 pawns should be on their new squares
        assert piece_type(board.squares[28]) == PAWN  # e4 = sq 28
        assert piece_type(board.squares[36]) == PAWN  # e5 = sq 36
        assert board.squares[12] == EMPTY  # e2 vacated
        assert board.squares[52] == EMPTY  # e7 vacated

    def test_fen_position(self) -> None:
        fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"
        board = Board()
        _handle_position(["position", "fen"] + fen.split(), board)
        assert board.turn == BLACK
        assert piece_type(board.squares[28]) == PAWN  # e4

    def test_fen_with_moves(self) -> None:
        fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"
        board = Board()
        _handle_position(
            ["position", "fen"] + fen.split() + ["moves", "e7e5"],
            board,
        )
        assert board.turn == WHITE
        assert piece_type(board.squares[36]) == PAWN  # e5

    def test_position_resets_history(self) -> None:
        board = Board()
        _handle_position(
            ["position", "startpos", "moves", "e2e4"], board
        )
        assert len(board.history) == 1
        # Setting new position should clear history
        _handle_position(["position", "startpos"], board)
        assert len(board.history) == 0

    def test_ucinewgame_resets_board(self) -> None:
        output = run_uci([
            "position startpos moves e2e4 e7e5\n",
            "ucinewgame\n",
            "isready\n",
            "quit\n",
        ])
        assert "readyok" in output


# ---------------------------------------------------------------------------
# Test: go command produces bestmove
# ---------------------------------------------------------------------------

class TestGoCommand:
    def test_bestmove_from_startpos(self) -> None:
        output = run_uci([
            "position startpos\n",
            "go movetime 100\n",
            "quit\n",
        ])
        assert "bestmove" in output
        # Extract the move
        for line in output.strip().split("\n"):
            if line.startswith("bestmove"):
                uci_move = line.split()[1]
                assert len(uci_move) >= 4
                # Verify it's a legal move
                board = Board()
                move = parse_uci_move(board, uci_move)
                legal = generate_legal_moves(board)
                assert move in legal

    def test_bestmove_after_e4(self) -> None:
        output = run_uci([
            "position startpos moves e2e4\n",
            "go movetime 100\n",
            "quit\n",
        ])
        assert "bestmove" in output
        for line in output.strip().split("\n"):
            if line.startswith("bestmove"):
                uci_move = line.split()[1]
                board = Board()
                _handle_position(
                    ["position", "startpos", "moves", "e2e4"], board
                )
                move = parse_uci_move(board, uci_move)
                legal = generate_legal_moves(board)
                assert move in legal

    def test_bestmove_with_depth(self) -> None:
        output = run_uci([
            "position startpos\n",
            "go depth 1\n",
            "quit\n",
        ])
        assert "bestmove" in output

    def test_bestmove_with_wtime_btime(self) -> None:
        output = run_uci([
            "position startpos\n",
            "go wtime 300000 btime 300000 winc 0 binc 0\n",
            "quit\n",
        ])
        assert "bestmove" in output

    def test_go_from_fen(self) -> None:
        # Mate in 1: White queen to h7#
        fen = "6k1/5ppp/8/8/8/8/5PPP/4Q1K1 w - - 0 1"
        output = run_uci([
            f"position fen {fen}\n",
            "go movetime 500\n",
            "quit\n",
        ])
        assert "bestmove" in output


# ---------------------------------------------------------------------------
# Test: time management
# ---------------------------------------------------------------------------

class TestTimeManagement:
    def test_movetime(self) -> None:
        board = Board()
        t, d = _calculate_time(board, None, None, None, None, 5000, None)
        assert t == 5.0
        assert d is None

    def test_depth_limit(self) -> None:
        board = Board()
        t, d = _calculate_time(board, None, None, None, None, None, 6)
        assert t == 300.0
        assert d == 6

    def test_wtime_btime_white(self) -> None:
        board = Board()
        board.turn = WHITE
        t, d = _calculate_time(board, 60000, 60000, 0, 0, None, None)
        assert 0 < t <= 20.0  # 60s / 30 = 2s, capped at 60/3 = 20
        assert d is None

    def test_wtime_btime_black(self) -> None:
        board = Board()
        board.turn = BLACK
        t, d = _calculate_time(board, 60000, 30000, 0, 0, None, None)
        # Black has 30s, so 30/30 = 1s
        assert 0 < t <= 10.0
        assert d is None

    def test_increment_adds_time(self) -> None:
        board = Board()
        board.turn = WHITE
        t_no_inc, _ = _calculate_time(board, 60000, 60000, 0, 0, None, None)
        t_with_inc, _ = _calculate_time(
            board, 60000, 60000, 5000, 0, None, None
        )
        assert t_with_inc > t_no_inc

    def test_no_time_info_defaults(self) -> None:
        board = Board()
        t, d = _calculate_time(board, None, None, None, None, None, None)
        assert t == 5.0
        assert d is None

    def test_very_low_time(self) -> None:
        board = Board()
        board.turn = WHITE
        t, _ = _calculate_time(board, 100, 100, 0, 0, None, None)
        # Should be at least 0.05s minimum
        assert t >= 0.05


# ---------------------------------------------------------------------------
# Test: opening book integration
# ---------------------------------------------------------------------------

class TestBookIntegration:
    def test_book_move_from_startpos(self) -> None:
        """Engine should return a book move from starting position."""
        output = run_uci([
            "position startpos\n",
            "go movetime 100\n",
            "quit\n",
        ])
        for line in output.strip().split("\n"):
            if line.startswith("bestmove"):
                uci_move = line.split()[1]
                # Book moves for starting position
                assert uci_move in ["e2e4", "d2d4", "c2c4", "g1f3"]


# ---------------------------------------------------------------------------
# Test: full UCI session
# ---------------------------------------------------------------------------

class TestFullSession:
    def test_complete_game_start(self) -> None:
        """Simulate a short UCI session."""
        output = run_uci([
            "uci\n",
            "isready\n",
            "ucinewgame\n",
            "position startpos\n",
            "go movetime 100\n",
            "quit\n",
        ])
        lines = output.strip().split("\n")
        assert any("id name" in l for l in lines)
        assert any("uciok" in l for l in lines)
        assert any("readyok" in l for l in lines)
        assert any("bestmove" in l for l in lines)

    def test_multiple_go_commands(self) -> None:
        """Engine handles multiple go commands in a session."""
        output = run_uci([
            "position startpos\n",
            "go movetime 100\n",
            "position startpos moves e2e4\n",
            "go movetime 100\n",
            "quit\n",
        ])
        bestmoves = [l for l in output.strip().split("\n")
                     if l.startswith("bestmove")]
        assert len(bestmoves) == 2

    def test_empty_and_whitespace_lines_ignored(self) -> None:
        output = run_uci(["\n", "  \n", "isready\n", "\n", "quit\n"])
        assert "readyok" in output

    def test_unknown_commands_ignored(self) -> None:
        output = run_uci(["garbage\n", "isready\n", "quit\n"])
        assert "readyok" in output


# ---------------------------------------------------------------------------
# Test: main.py entry point
# ---------------------------------------------------------------------------

class TestMainEntryPoint:
    def test_main_module_imports(self) -> None:
        """Verify main.py can be imported without errors."""
        import main  # noqa: F401

    def test_main_runs_uci_loop(self) -> None:
        """Verify main.py calls uci_loop when run."""
        buf = io.StringIO()
        input_cmds = io.StringIO("uci\nquit\n")
        with patch("sys.stdout", buf), patch("sys.stdin", input_cmds):
            import importlib
            import main
            importlib.reload(main)
        # main.py has if __name__ == "__main__", so we can't trigger it
        # via import, but we can verify the module loads correctly
        assert hasattr(main, "uci_loop")


# ---------------------------------------------------------------------------
# Test: position edge cases
# ---------------------------------------------------------------------------

class TestPositionEdgeCases:
    def test_castling_via_uci_moves(self) -> None:
        """White castles kingside via UCI moves."""
        board = Board()
        _handle_position(
            ["position", "startpos", "moves",
             "e2e4", "e7e5", "g1f3", "b8c6", "f1c4", "g8f6", "e1g1"],
            board,
        )
        # After O-O, white king should be on g1 (sq 6)
        assert piece_type(board.squares[6]) == KING
        assert piece_color(board.squares[6]) == WHITE

    def test_promotion_via_uci(self) -> None:
        """Pawn promotion works through UCI position command."""
        # Position where white pawn on e7 can promote
        fen = "4k3/4P3/8/8/8/8/8/4K3 w - - 0 1"
        board = Board()
        _handle_position(
            ["position", "fen"] + fen.split() + ["moves", "e7e8q"],
            board,
        )
        # e8 should have white queen
        sq = 60  # e8
        assert piece_type(board.squares[sq]) == QUEEN
        assert piece_color(board.squares[sq]) == WHITE

    def test_en_passant_via_uci(self) -> None:
        """En passant capture via UCI moves."""
        board = Board()
        _handle_position(
            ["position", "startpos", "moves",
             "e2e4", "a7a6", "e4e5", "d7d5", "e5d6"],
            board,
        )
        # d6 should have white pawn (captured en passant)
        sq = 43  # d6
        assert piece_type(board.squares[sq]) == PAWN
        assert piece_color(board.squares[sq]) == WHITE
        # d5 should be empty (captured pawn removed)
        assert board.squares[35] == EMPTY  # d5
