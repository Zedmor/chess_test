"""Tests for move generation and perft validation."""

from __future__ import annotations

import pytest
from src.board import Board
from src.constants import (
    EMPTY, PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING,
    WHITE, BLACK,
    piece_type, piece_color, make_piece,
    QUIET, DOUBLE_PAWN, CASTLE_KING, CASTLE_QUEEN, CAPTURE, EP_CAPTURE,
    PROMO_KNIGHT, PROMO_BISHOP, PROMO_ROOK, PROMO_QUEEN,
    PROMO_KNIGHT_CAP,
    encode_move, decode_from, decode_to, decode_flags,
    is_capture, is_promotion, move_to_uci,
)
from src.movegen import (
    generate_legal_moves,
    generate_legal_captures,
    perft,
)


def _move_set(board: Board) -> set[str]:
    """Return set of UCI strings for all legal moves."""
    return {move_to_uci(m) for m in generate_legal_moves(board)}


# -----------------------------------------------------------------------
# Perft: starting position
# -----------------------------------------------------------------------

class TestPerftStartpos:
    """Perft tests from the standard starting position."""

    def test_perft_depth_1(self) -> None:
        board = Board()
        assert perft(board, 1) == 20

    def test_perft_depth_2(self) -> None:
        board = Board()
        assert perft(board, 2) == 400

    def test_perft_depth_3(self) -> None:
        board = Board()
        assert perft(board, 3) == 8902

    def test_perft_depth_4(self) -> None:
        board = Board()
        assert perft(board, 4) == 197281


# -----------------------------------------------------------------------
# Perft: Kiwipete
# -----------------------------------------------------------------------

KIWIPETE = 'r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq -'


class TestPerftKiwipete:
    """Perft tests for the Kiwipete position."""

    def test_perft_depth_1(self) -> None:
        board = Board(f'{KIWIPETE} 0 1')
        assert perft(board, 1) == 48

    def test_perft_depth_2(self) -> None:
        board = Board(f'{KIWIPETE} 0 1')
        assert perft(board, 2) == 2039

    def test_perft_depth_3(self) -> None:
        board = Board(f'{KIWIPETE} 0 1')
        assert perft(board, 3) == 97862


# -----------------------------------------------------------------------
# En passant
# -----------------------------------------------------------------------

class TestEnPassant:
    """Test en passant move generation."""

    def test_white_en_passant(self) -> None:
        # White pawn on e5, black just played d7d5 -> ep square d6
        board = Board('rnbqkbnr/ppp1pppp/8/3pP3/8/8/PPPP1PPP/RNBQKBNR w KQkq d6 0 3')
        moves = _move_set(board)
        assert 'e5d6' in moves

    def test_black_en_passant(self) -> None:
        # Black pawn on d4, white just played c2c4 -> ep square c3
        board = Board('rnbqkbnr/ppp1pppp/8/8/2Pp4/8/PP1PPPPP/RNBQKBNR b KQkq c3 0 3')
        moves = _move_set(board)
        assert 'd4c3' in moves

    def test_no_en_passant_when_pinned(self) -> None:
        # En passant would expose king to a check along the rank
        # White king on a5, black rook on h5, white pawn on d5, black pawn on e5, ep=e6
        board = Board('8/8/8/KPp4r/8/8/8/4k3 w - c6 0 1')
        moves = _move_set(board)
        # b5c6 would expose king on a5 to rook on h5
        assert 'b5c6' not in moves


# -----------------------------------------------------------------------
# Castling
# -----------------------------------------------------------------------

class TestCastling:
    """Test castling move generation and restrictions."""

    def test_white_kingside_castle(self) -> None:
        board = Board('r3k2r/pppppppp/8/8/8/8/PPPPPPPP/R3K2R w KQkq - 0 1')
        moves = _move_set(board)
        assert 'e1g1' in moves

    def test_white_queenside_castle(self) -> None:
        board = Board('r3k2r/pppppppp/8/8/8/8/PPPPPPPP/R3K2R w KQkq - 0 1')
        moves = _move_set(board)
        assert 'e1c1' in moves

    def test_black_kingside_castle(self) -> None:
        board = Board('r3k2r/pppppppp/8/8/8/8/PPPPPPPP/R3K2R b KQkq - 0 1')
        moves = _move_set(board)
        assert 'e8g8' in moves

    def test_black_queenside_castle(self) -> None:
        board = Board('r3k2r/pppppppp/8/8/8/8/PPPPPPPP/R3K2R b KQkq - 0 1')
        moves = _move_set(board)
        assert 'e8c8' in moves

    def test_no_castle_through_check(self) -> None:
        # Bishop on c4 attacks f1 — blocks white kingside castle
        board = Board('r3k2r/8/8/8/2b5/8/8/R3K2R w KQkq - 0 1')
        moves = _move_set(board)
        assert 'e1g1' not in moves

    def test_no_castle_in_check(self) -> None:
        # Black rook gives check on e1 file — white king is in check
        board = Board('4k3/8/8/8/8/8/8/R3K2r w Kq - 0 1')
        moves = _move_set(board)
        assert 'e1g1' not in moves

    def test_no_castle_without_rights(self) -> None:
        board = Board('r3k2r/pppppppp/8/8/8/8/PPPPPPPP/R3K2R w - - 0 1')
        moves = _move_set(board)
        assert 'e1g1' not in moves
        assert 'e1c1' not in moves

    def test_no_castle_pieces_in_way(self) -> None:
        board = Board('r3k2r/pppppppp/8/8/8/8/PPPPPPPP/RN2K1NR w KQkq - 0 1')
        moves = _move_set(board)
        assert 'e1g1' not in moves  # knight on g1
        assert 'e1c1' not in moves  # knight on b1


# -----------------------------------------------------------------------
# Promotions
# -----------------------------------------------------------------------

class TestPromotion:
    """Test pawn promotion generates all 4 piece types."""

    def test_white_promotion_4_types(self) -> None:
        board = Board('8/4P3/8/8/8/8/8/4K2k w - - 0 1')
        moves = _move_set(board)
        assert 'e7e8q' in moves
        assert 'e7e8r' in moves
        assert 'e7e8b' in moves
        assert 'e7e8n' in moves

    def test_black_promotion_4_types(self) -> None:
        board = Board('4K2k/8/8/8/8/8/4p3/8 b - - 0 1')
        moves = _move_set(board)
        assert 'e2e1q' in moves
        assert 'e2e1r' in moves
        assert 'e2e1b' in moves
        assert 'e2e1n' in moves

    def test_capture_promotion(self) -> None:
        board = Board('3r4/4P3/8/8/8/8/8/4K2k w - - 0 1')
        moves = _move_set(board)
        # Should generate capture promotions
        assert 'e7d8q' in moves
        assert 'e7d8r' in moves
        assert 'e7d8b' in moves
        assert 'e7d8n' in moves


# -----------------------------------------------------------------------
# Pins
# -----------------------------------------------------------------------

class TestPins:
    """Test that pinned pieces can only move along the pin ray."""

    def test_pinned_piece_cannot_move_off_ray(self) -> None:
        # White knight pinned by black rook on e-file
        board = Board('4k3/4r3/8/8/4N3/8/8/4K3 w - - 0 1')
        moves = _move_set(board)
        # Knight can't move at all (any move exposes king)
        knight_moves = [m for m in moves if m.startswith('e4')]
        assert len(knight_moves) == 0

    def test_pinned_bishop_on_diagonal(self) -> None:
        # White bishop on d2, pinned by black bishop on a5 (diagonal a5-e1)
        # Bishop can slide along the pin diagonal
        board = Board('4k3/8/8/b7/8/8/3B4/4K3 w - - 0 1')
        moves = _move_set(board)
        bishop_moves = {m for m in moves if m.startswith('d2')}
        # Bishop can move to c3 (block), and no other bishop moves
        assert 'd2c3' in bishop_moves
        # d2e3 would leave king exposed to a5
        assert 'd2e3' not in bishop_moves

    def test_pinned_rook_on_file(self) -> None:
        # White rook on e4, pinned along e-file by black rook on e8
        board = Board('4r3/8/8/8/4R3/8/8/4K2k w - - 0 1')
        moves = _move_set(board)
        rook_moves = {m for m in moves if m.startswith('e4')}
        # Can move up/down e-file but not off it
        assert 'e4e5' in rook_moves
        assert 'e4e6' in rook_moves
        assert 'e4e7' in rook_moves
        assert 'e4e8' in rook_moves  # capture rook
        assert 'e4e3' in rook_moves
        assert 'e4e2' in rook_moves
        # Cannot move off the file
        assert 'e4d4' not in rook_moves
        assert 'e4f4' not in rook_moves


# -----------------------------------------------------------------------
# Check evasion
# -----------------------------------------------------------------------

class TestCheckEvasion:
    """Test that only moves resolving check are legal."""

    def test_only_check_evasions(self) -> None:
        # White king in check from black rook on e8
        board = Board('4r3/8/8/8/8/8/8/4K3 w - - 0 1')
        moves = _move_set(board)
        # King must move; e1 is attacked on e-file
        for m in moves:
            assert m.startswith('e1')
        # Verify king can't stay on e-file (e1e2 still in check)
        assert 'e1e2' not in moves

    def test_block_check(self) -> None:
        # White king on e1, black rook on e8, white rook on a5
        # White can block with rook to e5
        board = Board('4r3/8/8/R7/8/8/8/4K3 w - - 0 1')
        moves = _move_set(board)
        assert 'a5e5' in moves  # block the check

    def test_double_check_only_king_moves(self) -> None:
        # Double check: only king can move
        board = Board('4k3/8/8/8/8/5n2/4r3/3K4 w - - 0 1')
        moves = _move_set(board)
        # All moves must be king moves
        for m in moves:
            assert m.startswith('d1')


# -----------------------------------------------------------------------
# Legal captures only
# -----------------------------------------------------------------------

class TestLegalCaptures:
    """Test generate_legal_captures returns only captures."""

    def test_captures_only(self) -> None:
        board = Board()
        captures = generate_legal_captures(board)
        # Starting position has no legal captures
        assert len(captures) == 0

    def test_captures_in_position(self) -> None:
        # Position where white can capture
        board = Board('4k3/8/8/8/3p4/4P3/8/4K3 w - - 0 1')
        captures = generate_legal_captures(board)
        uci_caps = {move_to_uci(m) for m in captures}
        assert 'e3d4' in uci_caps
        # Quiet moves like e3e4 should NOT be here
        assert 'e3e4' not in uci_caps

    def test_ep_is_capture(self) -> None:
        board = Board('4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1')
        captures = generate_legal_captures(board)
        uci_caps = {move_to_uci(m) for m in captures}
        assert 'e5d6' in uci_caps


# -----------------------------------------------------------------------
# Perft: additional positions for robustness
# -----------------------------------------------------------------------

class TestPerftAdditional:
    """Additional perft positions for edge case validation."""

    def test_perft_position_3(self) -> None:
        # Position 3 from the Chess Programming Wiki
        board = Board('8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1')
        assert perft(board, 1) == 14
        assert perft(board, 2) == 191
        assert perft(board, 3) == 2812

    def test_perft_position_4(self) -> None:
        # Position 4
        fen = 'r3k2r/Pppp1ppp/1b3nbN/nP6/BBP1P3/q4N2/Pp1P2PP/R2Q1RK1 w kq - 0 1'
        board = Board(fen)
        assert perft(board, 1) == 6
        assert perft(board, 2) == 264

    def test_perft_position_5(self) -> None:
        # Position 5
        fen = 'rnbq1k1r/pp1Pbppp/2p5/8/2B5/8/PPP1NnPP/RNBQK2R w KQ - 1 8'
        board = Board(fen)
        assert perft(board, 1) == 44
        assert perft(board, 2) == 1486

    def test_perft_position_6(self) -> None:
        # Position 6
        fen = 'r4rk1/1pp1qppp/p1np1n2/2b1p1B1/2B1P1b1/P1NP1N2/1PP1QPPP/R4RK1 w - - 0 10'
        board = Board(fen)
        assert perft(board, 1) == 46
        assert perft(board, 2) == 2079


# -----------------------------------------------------------------------
# Board state preserved after generate
# -----------------------------------------------------------------------

class TestBoardIntegrity:
    """Ensure board state is unchanged after move generation."""

    def test_board_unchanged_after_legal_gen(self) -> None:
        board = Board()
        fen_before = board.get_fen()
        generate_legal_moves(board)
        assert board.get_fen() == fen_before

    def test_board_unchanged_after_perft(self) -> None:
        board = Board()
        fen_before = board.get_fen()
        perft(board, 3)
        assert board.get_fen() == fen_before

    def test_board_unchanged_kiwipete(self) -> None:
        board = Board(f'{KIWIPETE} 0 1')
        fen_before = board.get_fen()
        perft(board, 2)
        assert board.get_fen() == fen_before


# -----------------------------------------------------------------------
# Specific move counts
# -----------------------------------------------------------------------

class TestMoveCounts:
    """Test specific move counts in well-known positions."""

    def test_starting_position_20_moves(self) -> None:
        board = Board()
        moves = generate_legal_moves(board)
        assert len(moves) == 20

    def test_kiwipete_48_moves(self) -> None:
        board = Board(f'{KIWIPETE} 0 1')
        moves = generate_legal_moves(board)
        assert len(moves) == 48

    def test_stalemate_zero_moves(self) -> None:
        # Black king stalemated
        board = Board('k7/2Q5/1K6/8/8/8/8/8 b - - 0 1')
        moves = generate_legal_moves(board)
        assert len(moves) == 0

    def test_checkmate_zero_moves(self) -> None:
        # Black king checkmated (back rank)
        board = Board('6k1/5ppp/8/8/8/8/8/R3K3 b - - 0 1')
        # Check if this is actually checkmate
        moves = generate_legal_moves(board)
        # King can potentially move; let's use a proper checkmate
        board2 = Board('r1bqkb1r/pppp1ppp/2n2n2/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 4 4')
        # This is a scholars mate setup, let's use a known checkmate
        board3 = Board('rnb1kbnr/pppp1ppp/8/4p3/6Pq/5P2/PPPPP2P/RNBQKBNR w KQkq - 1 3')
        moves3 = generate_legal_moves(board3)
        assert len(moves3) == 0
        assert board3.is_in_check()
