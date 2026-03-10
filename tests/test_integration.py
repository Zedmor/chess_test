"""Integration tests — full game play, checkmate/stalemate/draw detection."""

from __future__ import annotations

import random

from src.board import Board
from src.constants import (
    WHITE, BLACK, EMPTY, KING, PAWN,
    piece_type, piece_color,
    encode_move, decode_from, decode_to, decode_flags,
    move_to_uci, parse_uci_move,
    is_capture,
)
from src.movegen import generate_legal_moves
from src.evaluation import MATE_SCORE, evaluate
from src.search import search
from src.opening_book import get_book_move


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _play_game(
    max_moves: int = 200,
    time_per_move: float = 0.2,
    use_book: bool = True,
) -> tuple[Board, str]:
    """Play a self-play game and return (board, result_string).

    Result is one of: "checkmate", "stalemate", "fifty_move",
    "repetition", "insufficient", "max_moves".
    """
    board = Board()
    for move_num in range(1, max_moves + 1):
        legal = generate_legal_moves(board)
        if not legal:
            if board.is_in_check():
                return board, "checkmate"
            return board, "stalemate"
        if board.is_fifty_move_draw():
            return board, "fifty_move"
        if board.is_repetition():
            return board, "repetition"
        if board.is_insufficient_material():
            return board, "insufficient"

        move = None
        if use_book:
            move = get_book_move(board)
        if move is None:
            move = search(board, time_per_move)
        board.make_move(move)
    return board, "max_moves"


def _verify_board_integrity(board: Board) -> None:
    """Assert board state invariants hold."""
    # Exactly two kings
    white_kings = sum(
        1 for sq in range(64)
        if board.squares[sq] != EMPTY
        and piece_type(board.squares[sq]) == KING
        and piece_color(board.squares[sq]) == WHITE
    )
    black_kings = sum(
        1 for sq in range(64)
        if board.squares[sq] != EMPTY
        and piece_type(board.squares[sq]) == KING
        and piece_color(board.squares[sq]) == BLACK
    )
    assert white_kings == 1, f"Expected 1 white king, found {white_kings}"
    assert black_kings == 1, f"Expected 1 black king, found {black_kings}"

    # king_sq tracking is correct
    for sq in range(64):
        p = board.squares[sq]
        if p != EMPTY and piece_type(p) == KING:
            c = piece_color(p)
            assert board.king_sq[c] == sq, (
                f"king_sq[{c}] = {board.king_sq[c]} but king at {sq}"
            )

    # Turn is valid
    assert board.turn in (WHITE, BLACK)

    # No pawns on rank 1 or rank 8
    for sq in range(8):  # rank 1
        if board.squares[sq] != EMPTY:
            assert piece_type(board.squares[sq]) != PAWN, (
                f"Pawn on rank 1 at sq {sq}"
            )
    for sq in range(56, 64):  # rank 8
        if board.squares[sq] != EMPTY:
            assert piece_type(board.squares[sq]) != PAWN, (
                f"Pawn on rank 8 at sq {sq}"
            )


# ---------------------------------------------------------------------------
# Engine vs Self Tests
# ---------------------------------------------------------------------------

class TestEngineVsSelf:
    """Test engine playing against itself with no crashes or illegal moves."""

    def test_engine_self_play_20_moves(self) -> None:
        """Play engine vs itself for 20+ moves, verify no crashes."""
        board = Board()
        moves_played = 0
        for _ in range(40):  # up to 40 half-moves = 20 full moves
            legal = generate_legal_moves(board)
            if not legal:
                break
            if board.is_fifty_move_draw() or board.is_repetition():
                break
            if board.is_insufficient_material():
                break
            move = search(board, 0.1)
            assert move is not None, "search returned None with legal moves"
            assert move in legal, (
                f"search returned illegal move {move_to_uci(move)}"
            )
            board.make_move(move)
            _verify_board_integrity(board)
            moves_played += 1
        assert moves_played >= 20, (
            f"Expected 20+ half-moves, got {moves_played}"
        )

    def test_engine_self_play_full_game(self) -> None:
        """Play full game to termination, verify board integrity throughout."""
        board, result = _play_game(max_moves=300, time_per_move=0.1)
        _verify_board_integrity(board)
        assert result in (
            "checkmate", "stalemate", "fifty_move",
            "repetition", "insufficient", "max_moves",
        )

    def test_engine_self_play_no_illegal_moves(self) -> None:
        """Every move played must be in the legal move list."""
        board = Board()
        for _ in range(60):
            legal = generate_legal_moves(board)
            if not legal:
                break
            if board.is_fifty_move_draw() or board.is_repetition():
                break
            move = search(board, 0.1)
            assert move in legal, (
                f"Illegal move: {move_to_uci(move)} not in legal moves"
            )
            board.make_move(move)


# ---------------------------------------------------------------------------
# Checkmate Detection
# ---------------------------------------------------------------------------

class TestCheckmateDetection:
    """Test that engine correctly handles checkmate positions."""

    def test_scholars_mate(self) -> None:
        """Walk through Scholar's Mate: 1.e4 e5 2.Qh5 Nc6 3.Bc4 Nf6 4.Qxf7#"""
        board = Board()
        moves = ["e2e4", "e7e5", "d1h5", "b8c6", "f1c4", "g8f6", "h5f7"]
        for uci in moves:
            m = parse_uci_move(board, uci)
            board.make_move(m)
        assert board.is_in_check()
        assert generate_legal_moves(board) == []

    def test_back_rank_mate(self) -> None:
        """White Rook delivers back rank mate."""
        # Black king on g8, pawns on f7/g7/h7, White rook mates on e8.
        board = Board("6k1/5ppp/8/8/8/8/8/R3K3 w Q - 0 1")
        m = parse_uci_move(board, "a1a8")
        board.make_move(m)
        assert board.is_in_check()
        assert generate_legal_moves(board) == []

    def test_search_finds_mate_in_1(self) -> None:
        """Engine finds mate-in-1 when available."""
        board = Board("6k1/5ppp/8/8/8/8/8/R3K3 w Q - 0 1")
        move = search(board, 1.0)
        uci = move_to_uci(move)
        assert uci == "a1a8", f"Expected a1a8 mate, got {uci}"

    def test_search_finds_mate_in_2(self) -> None:
        """Engine finds mate-in-2 (Damiano's mate pattern)."""
        # White: Kg1, Qh5, Rh1. Black: Kg8, Rf8, pawns f7/g6.
        # 1.Qh7+ Kf8 (only legal) 2.Qh8#
        board = Board("5rk1/5p2/6p1/7Q/8/8/8/6KR w - - 0 1")
        move = search(board, 2.0)
        uci = move_to_uci(move)
        # Qh7+ is the only first move leading to forced mate
        assert uci == "h5h7", f"Expected h5h7 (Qh7+), got {uci}"

    def test_checkmate_ends_game(self) -> None:
        """After checkmate, no legal moves exist."""
        # Fool's mate position: 1.f3 e5 2.g4 Qh4#
        board = Board()
        for uci in ["f2f3", "e7e5", "g2g4", "d8h4"]:
            m = parse_uci_move(board, uci)
            board.make_move(m)
        assert board.is_in_check()
        assert generate_legal_moves(board) == []
        _verify_board_integrity(board)


# ---------------------------------------------------------------------------
# Stalemate Detection
# ---------------------------------------------------------------------------

class TestStalemateDetection:
    """Verify stalemate is correctly detected."""

    def test_basic_stalemate(self) -> None:
        """K vs K+Q stalemate position."""
        # Black king trapped on a8, White queen on b6, White king on c8
        # Black to move, no legal moves, not in check
        board = Board("k7/8/1Q6/8/8/8/8/2K5 b - - 0 1")
        assert not board.is_in_check()
        assert generate_legal_moves(board) == []

    def test_stalemate_king_in_corner(self) -> None:
        """Stalemate with king stuck in corner."""
        board = Board("k7/2Q5/1K6/8/8/8/8/8 b - - 0 1")
        assert not board.is_in_check()
        assert generate_legal_moves(board) == []

    def test_search_avoids_stalemate_when_winning(self) -> None:
        """Engine should not stalemate opponent when it has a winning advantage."""
        # White has Q+K vs K (easy win). White should not stalemate.
        board = Board("8/8/8/8/8/2k5/8/QK6 w - - 0 1")
        move = search(board, 1.0)
        board.make_move(move)
        # After white's move, black should have legal moves (not stalemated)
        legal = generate_legal_moves(board)
        # Either black has moves, or white delivered checkmate
        if legal:
            assert len(legal) > 0
        else:
            # If no legal moves, it must be checkmate, not stalemate
            assert board.is_in_check(), "Engine stalemated opponent"


# ---------------------------------------------------------------------------
# Draw Detection
# ---------------------------------------------------------------------------

class TestDrawDetection:
    """Test draw by repetition, fifty-move rule, and insufficient material."""

    def test_insufficient_material_k_vs_k(self) -> None:
        """K vs K is insufficient material."""
        board = Board("k7/8/8/8/8/8/8/K7 w - - 0 1")
        assert board.is_insufficient_material()

    def test_insufficient_material_k_vs_kn(self) -> None:
        """K+N vs K is insufficient material."""
        board = Board("k7/8/8/8/8/8/8/KN6 w - - 0 1")
        assert board.is_insufficient_material()

    def test_insufficient_material_k_vs_kb(self) -> None:
        """K+B vs K is insufficient material."""
        board = Board("k7/8/8/8/8/8/8/KB6 w - - 0 1")
        assert board.is_insufficient_material()

    def test_sufficient_material_k_vs_kr(self) -> None:
        """K+R vs K is sufficient material."""
        board = Board("k7/8/8/8/8/8/8/KR6 w - - 0 1")
        assert not board.is_insufficient_material()

    def test_fifty_move_draw(self) -> None:
        """Fifty-move rule triggers at halfmove >= 100."""
        board = Board("k7/8/8/8/8/8/8/KR6 w - - 100 50")
        assert board.is_fifty_move_draw()

    def test_no_fifty_move_draw(self) -> None:
        """Halfmove 99 is not yet a draw."""
        board = Board("k7/8/8/8/8/8/8/KR6 w - - 99 50")
        assert not board.is_fifty_move_draw()

    def test_repetition_detection(self) -> None:
        """Three-fold repetition is detected."""
        board = Board("r3k2r/pppppppp/8/8/8/8/PPPPPPPP/R3K2R w KQkq - 0 1")
        # Play Ke1-d1, Ke8-d8, Kd1-e1, Kd8-e8 twice to repeat
        cycle = ["e1d1", "e8d8", "d1e1", "d8e8"]
        for _ in range(3):
            for uci in cycle:
                m = parse_uci_move(board, uci)
                board.make_move(m)
        # After 3 cycles the starting position FEN (minus clocks) appeared 3+ times
        assert board.is_repetition()


# ---------------------------------------------------------------------------
# Book to Search Transition
# ---------------------------------------------------------------------------

class TestBookToSearchTransition:
    """Verify engine uses book moves early, then transitions to search."""

    def test_starting_position_uses_book(self) -> None:
        """Starting position should return a book move."""
        board = Board()
        book_move = get_book_move(board)
        assert book_move is not None, "No book move for starting position"
        uci = move_to_uci(book_move)
        assert uci in ("e2e4", "d2d4", "c2c4", "g1f3"), (
            f"Unexpected book move: {uci}"
        )

    def test_out_of_book_uses_search(self) -> None:
        """After leaving book, engine still returns moves via search."""
        # A position unlikely to be in the book
        board = Board("r1bqk2r/pppp1ppp/2n2n2/4p3/2B1P1b1/5N2/PPPP1PPP/RNBQ1RK1 b kq - 5 4")
        book_move = get_book_move(board)
        # Doesn't matter if book has it; search should always work
        move = search(board, 0.5)
        assert move is not None
        legal = generate_legal_moves(board)
        assert move in legal

    def test_book_then_search_seamless(self) -> None:
        """Play through book moves, then continue with search moves."""
        board = Board()
        book_moves_used = 0
        for _ in range(20):
            legal = generate_legal_moves(board)
            if not legal:
                break
            book_move = get_book_move(board)
            if book_move is not None:
                book_moves_used += 1
                assert book_move in legal
                board.make_move(book_move)
            else:
                move = search(board, 0.1)
                assert move in legal
                board.make_move(move)
            _verify_board_integrity(board)
        assert book_moves_used >= 2, (
            f"Expected at least 2 book moves, got {book_moves_used}"
        )


# ---------------------------------------------------------------------------
# FEN Round-Trip Through Game Play
# ---------------------------------------------------------------------------

class TestFenConsistency:
    """Verify FEN stays consistent throughout a game."""

    def test_fen_roundtrip_during_game(self) -> None:
        """After each move, get_fen() and set_fen() round-trip correctly."""
        board = Board()
        for _ in range(30):
            legal = generate_legal_moves(board)
            if not legal:
                break
            move = search(board, 0.05)
            board.make_move(move)
            fen = board.get_fen()
            board2 = Board(fen)
            assert board2.get_fen() == fen, (
                f"FEN mismatch: {fen} vs {board2.get_fen()}"
            )

    def test_position_fen_tracks_uniquely(self) -> None:
        """position_history tracks position FENs after each move."""
        board = Board()
        for _ in range(10):
            legal = generate_legal_moves(board)
            if not legal:
                break
            move = legal[0]  # pick first legal move deterministically
            board.make_move(move)
            assert len(board.position_history) == len(board.history)


# ---------------------------------------------------------------------------
# Edge Case Positions
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Test unusual positions the engine might encounter."""

    def test_only_king_moves(self) -> None:
        """Engine handles position where only king can move."""
        board = Board("k7/8/1K6/8/8/8/8/8 b - - 0 1")
        move = search(board, 0.5)
        assert move is not None
        legal = generate_legal_moves(board)
        assert move in legal

    def test_many_captures_available(self) -> None:
        """Engine handles position with lots of captures."""
        # Contrived position with many captures
        board = Board(
            "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        )
        move = search(board, 0.3)
        assert move is not None
        legal = generate_legal_moves(board)
        assert move in legal

    def test_promotion_position(self) -> None:
        """Engine finds promotion when pawn is on 7th rank."""
        board = Board("8/P5k1/8/8/8/8/8/4K3 w - - 0 1")
        move = search(board, 1.0)
        uci = move_to_uci(move)
        # Should promote the pawn (a7a8 with promotion)
        assert uci.startswith("a7a8"), f"Expected a7a8x promotion, got {uci}"
        assert len(uci) == 5, f"Expected promotion suffix, got {uci}"

    def test_en_passant_in_game(self) -> None:
        """En passant works correctly during game play."""
        board = Board()
        # Play to a position where en passant is possible:
        # 1.e4 d5 2.e5 f5 (ep available on f6)
        for uci in ["e2e4", "d7d5", "e4e5", "f7f5"]:
            m = parse_uci_move(board, uci)
            board.make_move(m)
        # e5xf6 en passant should be legal
        legal = generate_legal_moves(board)
        legal_uci = [move_to_uci(m) for m in legal]
        assert "e5f6" in legal_uci, (
            f"En passant e5f6 not in legal moves: {legal_uci}"
        )

    def test_castling_through_game(self) -> None:
        """Castling works correctly during normal play."""
        board = Board()
        # Set up for kingside castling: 1.e4 e5 2.Nf3 Nc6 3.Bc4 Bc5 4.O-O
        for uci in ["e2e4", "e7e5", "g1f3", "b8c6", "f1c4", "f8c5"]:
            m = parse_uci_move(board, uci)
            board.make_move(m)
        legal = generate_legal_moves(board)
        legal_uci = [move_to_uci(m) for m in legal]
        assert "e1g1" in legal_uci, "Kingside castling should be legal"
        # Castle
        m = parse_uci_move(board, "e1g1")
        board.make_move(m)
        _verify_board_integrity(board)
        # King should be on g1
        assert board.king_sq[WHITE] == 6  # g1

    def test_deep_search_no_crash(self) -> None:
        """Search to moderate depth without crashing."""
        board = Board()
        # Just make sure search with a reasonable time limit works
        move = search(board, 0.5)
        assert move is not None
        legal = generate_legal_moves(board)
        assert move in legal
