"""Tests for src/board.py — Board class with FEN, make/unmake, attack detection."""

from src.constants import (
    EMPTY, PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING,
    WHITE, BLACK,
    WHITE_PAWN, WHITE_KNIGHT, WHITE_BISHOP, WHITE_ROOK, WHITE_QUEEN, WHITE_KING,
    BLACK_PAWN, BLACK_KNIGHT, BLACK_BISHOP, BLACK_ROOK, BLACK_QUEEN, BLACK_KING,
    CASTLE_WK, CASTLE_WQ, CASTLE_BK, CASTLE_BQ,
    QUIET, DOUBLE_PAWN, CASTLE_KING, CASTLE_QUEEN, CAPTURE, EP_CAPTURE,
    PROMO_QUEEN, PROMO_KNIGHT, PROMO_QUEEN_CAP,
    encode_move, decode_from, decode_to,
    make_piece, piece_type,
)
from src.board import Board


# -----------------------------------------------------------------------
# 1. Default FEN
# -----------------------------------------------------------------------

def test_default_fen() -> None:
    """Board() loads starting position and get_fen() returns standard FEN."""
    board = Board()
    expected = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
    assert board.get_fen() == expected


def test_default_position_pieces() -> None:
    """Starting position has correct pieces on correct squares."""
    board = Board()
    # White back rank: a1=R, b1=N, c1=B, d1=Q, e1=K, f1=B, g1=N, h1=R
    assert board.squares[0] == WHITE_ROOK
    assert board.squares[1] == WHITE_KNIGHT
    assert board.squares[2] == WHITE_BISHOP
    assert board.squares[3] == WHITE_QUEEN
    assert board.squares[4] == WHITE_KING
    assert board.squares[5] == WHITE_BISHOP
    assert board.squares[6] == WHITE_KNIGHT
    assert board.squares[7] == WHITE_ROOK
    # White pawns on rank 2 (squares 8-15)
    for sq in range(8, 16):
        assert board.squares[sq] == WHITE_PAWN
    # Empty squares in the middle
    for sq in range(16, 48):
        assert board.squares[sq] == EMPTY
    # Black pawns on rank 7 (squares 48-55)
    for sq in range(48, 56):
        assert board.squares[sq] == BLACK_PAWN
    # Black back rank
    assert board.squares[56] == BLACK_ROOK
    assert board.squares[60] == BLACK_KING
    assert board.squares[63] == BLACK_ROOK


# -----------------------------------------------------------------------
# 2. Custom FEN roundtrip
# -----------------------------------------------------------------------

def test_custom_fen_roundtrip_kiwipete() -> None:
    """Kiwipete position roundtrips through set_fen/get_fen."""
    fen = "r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq - 0 1"
    board = Board(fen)
    assert board.get_fen() == fen


def test_custom_fen_roundtrip_ep() -> None:
    """FEN with en passant square roundtrips correctly."""
    fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"
    board = Board(fen)
    assert board.get_fen() == fen
    assert board.ep_square == 20  # e3


def test_custom_fen_roundtrip_partial_castling() -> None:
    """FEN with partial castling rights roundtrips correctly."""
    fen = "r3k2r/pppppppp/8/8/8/8/PPPPPPPP/R3K2R w Kq - 0 1"
    board = Board(fen)
    assert board.get_fen() == fen
    assert board.castling == (CASTLE_WK | CASTLE_BQ)


def test_custom_fen_roundtrip_no_castling() -> None:
    """FEN with no castling rights."""
    fen = "4k3/8/8/8/8/8/8/4K3 w - - 0 1"
    board = Board(fen)
    assert board.get_fen() == fen
    assert board.castling == 0


def test_custom_fen_roundtrip_black_to_move() -> None:
    """FEN with black to move."""
    fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"
    board = Board(fen)
    assert board.turn == BLACK


# -----------------------------------------------------------------------
# 3. Make/unmake reversibility
# -----------------------------------------------------------------------

def test_make_unmake_quiet_pawn_push() -> None:
    """Quiet pawn push: make then unmake restores FEN."""
    board = Board()
    original_fen = board.get_fen()
    move = encode_move(12, 20, QUIET)  # e2-e3
    board.make_move(move)
    assert board.get_fen() != original_fen
    board.unmake_move()
    assert board.get_fen() == original_fen


def test_make_unmake_double_pawn_push() -> None:
    """Double pawn push: make then unmake restores FEN."""
    board = Board()
    original_fen = board.get_fen()
    move = encode_move(12, 28, DOUBLE_PAWN)  # e2-e4
    board.make_move(move)
    board.unmake_move()
    assert board.get_fen() == original_fen


def test_make_unmake_capture() -> None:
    """Capture: make then unmake restores state."""
    # Set up a position where white pawn can capture black pawn
    fen = "rnbqkbnr/ppp1pppp/8/3p4/4P3/8/PPPP1PPP/RNBQKBNR w KQkq d6 0 2"
    board = Board(fen)
    original_fen = board.get_fen()
    move = encode_move(28, 35, CAPTURE)  # e4xd5
    board.make_move(move)
    assert board.squares[35] == WHITE_PAWN
    assert board.squares[28] == EMPTY
    board.unmake_move()
    assert board.get_fen() == original_fen


def test_make_unmake_castling_kingside() -> None:
    """Kingside castling: make then unmake restores state."""
    fen = "r3k2r/pppppppp/8/8/8/8/PPPPPPPP/R3K2R w KQkq - 0 1"
    board = Board(fen)
    original_fen = board.get_fen()
    move = encode_move(4, 6, CASTLE_KING)  # e1-g1
    board.make_move(move)
    assert board.squares[6] == WHITE_KING
    assert board.squares[5] == WHITE_ROOK
    assert board.squares[4] == EMPTY
    assert board.squares[7] == EMPTY
    board.unmake_move()
    assert board.get_fen() == original_fen


def test_make_unmake_castling_queenside() -> None:
    """Queenside castling: make then unmake restores state."""
    fen = "r3k2r/pppppppp/8/8/8/8/PPPPPPPP/R3K2R w KQkq - 0 1"
    board = Board(fen)
    original_fen = board.get_fen()
    move = encode_move(4, 2, CASTLE_QUEEN)  # e1-c1
    board.make_move(move)
    assert board.squares[2] == WHITE_KING
    assert board.squares[3] == WHITE_ROOK
    assert board.squares[4] == EMPTY
    assert board.squares[0] == EMPTY
    board.unmake_move()
    assert board.get_fen() == original_fen


def test_make_unmake_en_passant() -> None:
    """En passant capture: make then unmake restores state."""
    # White pawn on e5, black pawn just moved d7-d5
    fen = "rnbqkbnr/ppp1pppp/8/3pP3/8/8/PPPP1PPP/RNBQKBNR w KQkq d6 0 3"
    board = Board(fen)
    original_fen = board.get_fen()
    move = encode_move(36, 43, EP_CAPTURE)  # e5xd6 (ep)
    board.make_move(move)
    # White pawn now on d6, captured pawn removed from d5
    assert board.squares[43] == WHITE_PAWN
    assert board.squares[36] == EMPTY
    assert board.squares[35] == EMPTY  # d5 captured pawn removed
    board.unmake_move()
    assert board.get_fen() == original_fen


def test_make_unmake_promotion() -> None:
    """Promotion: make then unmake restores state."""
    fen = "4k3/P7/8/8/8/8/8/4K3 w - - 0 1"
    board = Board(fen)
    original_fen = board.get_fen()
    move = encode_move(48, 56, PROMO_QUEEN)  # a7-a8=Q
    board.make_move(move)
    assert board.squares[56] == WHITE_QUEEN
    assert board.squares[48] == EMPTY
    board.unmake_move()
    assert board.get_fen() == original_fen


def test_make_unmake_promotion_capture() -> None:
    """Promotion with capture: make then unmake restores state."""
    fen = "1n2k3/P7/8/8/8/8/8/4K3 w - - 0 1"
    board = Board(fen)
    original_fen = board.get_fen()
    move = encode_move(48, 57, PROMO_QUEEN_CAP)  # a7xb8=Q
    board.make_move(move)
    assert board.squares[57] == WHITE_QUEEN
    assert board.squares[48] == EMPTY
    board.unmake_move()
    assert board.get_fen() == original_fen


# -----------------------------------------------------------------------
# 4. Pawn double push sets ep_square
# -----------------------------------------------------------------------

def test_pawn_double_push_sets_ep() -> None:
    """After e2e4, ep_square is e3 (square 20)."""
    board = Board()
    move = encode_move(12, 28, DOUBLE_PAWN)  # e2-e4
    board.make_move(move)
    assert board.ep_square == 20  # e3


def test_pawn_double_push_black_sets_ep() -> None:
    """After d7d5 by black, ep_square is d6 (square 43)."""
    # White moves first, then black does d7-d5
    fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq - 0 1"
    board = Board(fen)
    move = encode_move(51, 35, DOUBLE_PAWN)  # d7-d5
    board.make_move(move)
    assert board.ep_square == 43  # d6


def test_ep_square_cleared_after_non_double_push() -> None:
    """ep_square is -1 after a non-double-pawn move."""
    fen = "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3 0 1"
    board = Board(fen)
    assert board.ep_square == 20  # e3
    # Black plays Nf6 (quiet move)
    move = encode_move(62, 45, QUIET)  # g8-f6
    board.make_move(move)
    assert board.ep_square == -1


# -----------------------------------------------------------------------
# 5. Castling rights update
# -----------------------------------------------------------------------

def test_castling_rights_king_move_clears_both() -> None:
    """Moving the king clears both castling rights for that side."""
    fen = "r3k2r/pppppppp/8/8/8/8/PPPPPPPP/R3K2R w KQkq - 0 1"
    board = Board(fen)
    move = encode_move(4, 5, QUIET)  # Ke1-f1
    board.make_move(move)
    # White should lose both KQ castling
    assert not (board.castling & CASTLE_WK)
    assert not (board.castling & CASTLE_WQ)
    # Black should still have castling
    assert board.castling & CASTLE_BK
    assert board.castling & CASTLE_BQ


def test_castling_rights_rook_move_clears_one_side() -> None:
    """Moving a rook clears castling for that side only."""
    fen = "r3k2r/pppppppp/8/8/8/8/PPPPPPPP/R3K2R w KQkq - 0 1"
    board = Board(fen)
    move = encode_move(7, 6, QUIET)  # Rh1-g1
    board.make_move(move)
    # White kingside gone, queenside remains
    assert not (board.castling & CASTLE_WK)
    assert board.castling & CASTLE_WQ


def test_castling_rights_rook_captured() -> None:
    """Capturing a rook on its original square clears its castling right."""
    # White queen captures black rook on h8
    fen = "r3k2r/pppppppp/8/7Q/8/8/PPPPPPPP/R3K2R w KQkq - 0 1"
    board = Board(fen)
    move = encode_move(39, 63, CAPTURE)  # Qh5xh8
    board.make_move(move)
    assert not (board.castling & CASTLE_BK)
    assert board.castling & CASTLE_BQ


# -----------------------------------------------------------------------
# 6. Castling move execution
# -----------------------------------------------------------------------

def test_castling_kingside_white() -> None:
    """White kingside castle: king e1->g1, rook h1->f1."""
    fen = "r3k2r/pppppppp/8/8/8/8/PPPPPPPP/R3K2R w KQkq - 0 1"
    board = Board(fen)
    move = encode_move(4, 6, CASTLE_KING)
    board.make_move(move)
    assert board.squares[6] == WHITE_KING
    assert board.squares[5] == WHITE_ROOK
    assert board.squares[4] == EMPTY
    assert board.squares[7] == EMPTY


def test_castling_queenside_white() -> None:
    """White queenside castle: king e1->c1, rook a1->d1."""
    fen = "r3k2r/pppppppp/8/8/8/8/PPPPPPPP/R3K2R w KQkq - 0 1"
    board = Board(fen)
    move = encode_move(4, 2, CASTLE_QUEEN)
    board.make_move(move)
    assert board.squares[2] == WHITE_KING
    assert board.squares[3] == WHITE_ROOK
    assert board.squares[4] == EMPTY
    assert board.squares[0] == EMPTY


def test_castling_kingside_black() -> None:
    """Black kingside castle: king e8->g8, rook h8->f8."""
    fen = "r3k2r/pppppppp/8/8/8/8/PPPPPPPP/R3K2R b KQkq - 0 1"
    board = Board(fen)
    move = encode_move(60, 62, CASTLE_KING)
    board.make_move(move)
    assert board.squares[62] == BLACK_KING
    assert board.squares[61] == BLACK_ROOK
    assert board.squares[60] == EMPTY
    assert board.squares[63] == EMPTY


def test_castling_queenside_black() -> None:
    """Black queenside castle: king e8->c8, rook a8->d8."""
    fen = "r3k2r/pppppppp/8/8/8/8/PPPPPPPP/R3K2R b KQkq - 0 1"
    board = Board(fen)
    move = encode_move(60, 58, CASTLE_QUEEN)
    board.make_move(move)
    assert board.squares[58] == BLACK_KING
    assert board.squares[59] == BLACK_ROOK
    assert board.squares[60] == EMPTY
    assert board.squares[56] == EMPTY


# -----------------------------------------------------------------------
# 7. En passant capture
# -----------------------------------------------------------------------

def test_en_passant_removes_captured_pawn_white() -> None:
    """White EP capture removes the black pawn from the correct square."""
    fen = "rnbqkbnr/ppp1pppp/8/3pP3/8/8/PPPP1PPP/RNBQKBNR w KQkq d6 0 3"
    board = Board(fen)
    move = encode_move(36, 43, EP_CAPTURE)  # e5xd6
    board.make_move(move)
    assert board.squares[43] == WHITE_PAWN  # white pawn on d6
    assert board.squares[35] == EMPTY       # d5 black pawn gone
    assert board.squares[36] == EMPTY       # e5 vacated


def test_en_passant_removes_captured_pawn_black() -> None:
    """Black EP capture removes the white pawn from the correct square."""
    fen = "rnbqkbnr/pppp1ppp/8/8/3Pp3/8/PPP1PPPP/RNBQKBNR b KQkq d3 0 3"
    board = Board(fen)
    move = encode_move(28, 19, EP_CAPTURE)  # e4xd3
    board.make_move(move)
    assert board.squares[19] == BLACK_PAWN  # black pawn on d3
    assert board.squares[27] == EMPTY       # d4 white pawn gone
    assert board.squares[28] == EMPTY       # e4 vacated


# -----------------------------------------------------------------------
# 8. Promotion
# -----------------------------------------------------------------------

def test_promotion_queen() -> None:
    """Pawn promotes to queen on reaching 8th rank."""
    fen = "4k3/P7/8/8/8/8/8/4K3 w - - 0 1"
    board = Board(fen)
    move = encode_move(48, 56, PROMO_QUEEN)
    board.make_move(move)
    assert board.squares[56] == WHITE_QUEEN
    assert board.squares[48] == EMPTY


def test_promotion_knight() -> None:
    """Pawn promotes to knight (underpromotion)."""
    fen = "4k3/P7/8/8/8/8/8/4K3 w - - 0 1"
    board = Board(fen)
    move = encode_move(48, 56, PROMO_KNIGHT)
    board.make_move(move)
    assert board.squares[56] == WHITE_KNIGHT


def test_promotion_black() -> None:
    """Black pawn promotes on 1st rank."""
    fen = "4k3/8/8/8/8/8/p7/4K3 b - - 0 1"
    board = Board(fen)
    move = encode_move(8, 0, PROMO_QUEEN)
    board.make_move(move)
    assert board.squares[0] == BLACK_QUEEN
    assert board.squares[8] == EMPTY


# -----------------------------------------------------------------------
# 9. Knight attack detection
# -----------------------------------------------------------------------

def test_is_attacked_by_knight() -> None:
    """Knight on e4 attacks correct squares."""
    fen = "4k3/8/8/8/4N3/8/8/4K3 w - - 0 1"
    board = Board(fen)
    # Knight on e4 (sq 28, rank 3, file 4). It attacks:
    # d2(11), f2(13), c3(18), g3(22), c5(34), g5(38), d6(43), f6(45)
    attacked = {11, 13, 18, 22, 34, 38, 43, 45}
    for sq in attacked:
        assert board.is_attacked(sq, WHITE), f"sq {sq} should be attacked"


def test_is_attacked_by_knight_edge() -> None:
    """Knight on a1 only attacks b3 and c2."""
    fen = "4k3/8/8/8/8/8/8/N3K3 w - - 0 1"
    board = Board(fen)
    # Knight on a1 (sq 0). Attacks: b3(17), c2(10)
    assert board.is_attacked(17, WHITE)
    assert board.is_attacked(10, WHITE)
    # Should not wrap around
    assert not board.is_attacked(63, WHITE)


# -----------------------------------------------------------------------
# 10. Sliding piece attack detection
# -----------------------------------------------------------------------

def test_is_attacked_by_bishop() -> None:
    """Bishop attacks along diagonals, blocked by pieces."""
    fen = "4k3/8/8/8/3B4/8/8/4K3 w - - 0 1"
    board = Board(fen)
    # Bishop on d4 (sq 27). Attacks diagonals.
    assert board.is_attacked(36, WHITE)  # e5
    assert board.is_attacked(45, WHITE)  # f6
    assert board.is_attacked(18, WHITE)  # c3
    assert board.is_attacked(20, WHITE)  # e3


def test_is_attacked_by_bishop_blocked() -> None:
    """Bishop attack blocked by own piece."""
    fen = "4k3/8/8/4R3/3B4/8/8/4K3 w - - 0 1"
    board = Board(fen)
    # Bishop on d4 (sq 27), white rook on e5 (sq 36) blocks NE ray
    # g7 (sq 54) is beyond the blocker and should not be attacked by bishop
    assert not board.is_attacked(54, WHITE)  # g7 blocked by rook on e5


def test_is_attacked_by_rook() -> None:
    """Rook attacks along files and ranks."""
    fen = "4k3/8/8/8/3R4/8/8/4K3 w - - 0 1"
    board = Board(fen)
    # Rook on d4 (sq 27). Attacks along rank 4 and file d.
    assert board.is_attacked(24, WHITE)  # a4
    assert board.is_attacked(31, WHITE)  # h4
    assert board.is_attacked(3, WHITE)   # d1
    assert board.is_attacked(59, WHITE)  # d8


def test_is_attacked_by_rook_blocked() -> None:
    """Rook attack blocked by a piece on the ray."""
    fen = "4k3/8/8/3P4/3R4/8/8/4K3 w - - 0 1"
    board = Board(fen)
    # Rook on d4 (sq 27), white pawn on d5 (sq 35) blocks north
    assert not board.is_attacked(43, WHITE)  # d6 blocked
    # Horizontal still works
    assert board.is_attacked(24, WHITE)  # a4


def test_is_attacked_by_queen() -> None:
    """Queen attacks both diagonals and files/ranks."""
    fen = "4k3/8/8/8/3Q4/8/8/4K3 w - - 0 1"
    board = Board(fen)
    # Queen on d4 (sq 27) — diagonal
    assert board.is_attacked(36, WHITE)  # e5
    assert board.is_attacked(18, WHITE)  # c3
    # Queen on d4 — straight
    assert board.is_attacked(24, WHITE)  # a4
    assert board.is_attacked(3, WHITE)   # d1


# -----------------------------------------------------------------------
# 11. is_in_check
# -----------------------------------------------------------------------

def test_is_in_check_true() -> None:
    """King is in check from a rook."""
    fen = "4k3/8/8/8/8/8/8/r3K3 w - - 0 1"
    board = Board(fen)
    assert board.is_in_check()


def test_is_in_check_false() -> None:
    """King is not in check in starting position."""
    board = Board()
    assert not board.is_in_check()


def test_is_in_check_knight() -> None:
    """King in check from a knight."""
    fen = "4k3/8/8/8/8/3n4/8/4K3 w - - 0 1"
    board = Board(fen)
    # Black knight on d3 (sq 19) attacks e1 (sq 4)
    assert board.is_in_check()


def test_is_in_check_pawn() -> None:
    """King in check from a pawn."""
    fen = "4k3/8/8/8/8/8/3p4/4K3 w - - 0 1"
    board = Board(fen)
    # Black pawn on d2 (sq 11) attacks e1 (sq 4)
    assert board.is_in_check()


# -----------------------------------------------------------------------
# 12. king_sq tracking
# -----------------------------------------------------------------------

def test_king_sq_initial() -> None:
    """king_sq correctly set for starting position."""
    board = Board()
    assert board.king_sq[WHITE] == 4   # e1
    assert board.king_sq[BLACK] == 60  # e8


def test_king_sq_after_move() -> None:
    """king_sq updated when king moves."""
    fen = "4k3/8/8/8/8/8/8/4K3 w - - 0 1"
    board = Board(fen)
    move = encode_move(4, 5, QUIET)  # Ke1-f1
    board.make_move(move)
    assert board.king_sq[WHITE] == 5


def test_king_sq_after_castling() -> None:
    """king_sq updated after castling."""
    fen = "r3k2r/pppppppp/8/8/8/8/PPPPPPPP/R3K2R w KQkq - 0 1"
    board = Board(fen)
    move = encode_move(4, 6, CASTLE_KING)
    board.make_move(move)
    assert board.king_sq[WHITE] == 6  # g1


def test_king_sq_restored_after_unmake() -> None:
    """king_sq restored after unmake_move."""
    fen = "4k3/8/8/8/8/8/8/4K3 w - - 0 1"
    board = Board(fen)
    move = encode_move(4, 5, QUIET)
    board.make_move(move)
    board.unmake_move()
    assert board.king_sq[WHITE] == 4


# -----------------------------------------------------------------------
# 13. Halfmove clock
# -----------------------------------------------------------------------

def test_halfmove_resets_on_pawn_move() -> None:
    """Halfmove clock resets to 0 on pawn move."""
    fen = "4k3/8/8/8/8/8/4P3/4K3 w - - 5 1"
    board = Board(fen)
    assert board.halfmove == 5
    move = encode_move(12, 20, QUIET)  # e2-e3
    board.make_move(move)
    assert board.halfmove == 0


def test_halfmove_resets_on_capture() -> None:
    """Halfmove clock resets on capture."""
    fen = "4k3/8/8/8/3p4/4N3/8/4K3 w - - 7 1"
    board = Board(fen)
    move = encode_move(20, 27, CAPTURE)  # Ne3xd4
    board.make_move(move)
    assert board.halfmove == 0


def test_halfmove_increments_on_quiet() -> None:
    """Halfmove clock increments on non-pawn non-capture move."""
    fen = "4k3/8/8/8/8/4N3/8/4K3 w - - 3 1"
    board = Board(fen)
    move = encode_move(20, 37, QUIET)  # Ne3-f5
    board.make_move(move)
    assert board.halfmove == 4


# -----------------------------------------------------------------------
# 14. Position history
# -----------------------------------------------------------------------

def test_position_history_grows_on_make() -> None:
    """position_history grows by 1 on each make_move."""
    board = Board()
    assert len(board.position_history) == 0
    move = encode_move(12, 28, DOUBLE_PAWN)  # e2-e4
    board.make_move(move)
    assert len(board.position_history) == 1


def test_position_history_shrinks_on_unmake() -> None:
    """position_history shrinks on unmake_move."""
    board = Board()
    move = encode_move(12, 28, DOUBLE_PAWN)
    board.make_move(move)
    assert len(board.position_history) == 1
    board.unmake_move()
    assert len(board.position_history) == 0


def test_position_history_content() -> None:
    """position_history stores the position FEN without move counters."""
    board = Board()
    move = encode_move(12, 28, DOUBLE_PAWN)  # e2-e4
    board.make_move(move)
    expected = board.get_position_fen()
    assert board.position_history[-1] == expected


# -----------------------------------------------------------------------
# Additional: get_position_fen
# -----------------------------------------------------------------------

def test_get_position_fen_strips_counters() -> None:
    """get_position_fen returns FEN without halfmove and fullmove."""
    board = Board()
    pos_fen = board.get_position_fen()
    assert pos_fen == "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq -"


# -----------------------------------------------------------------------
# Additional: game state queries
# -----------------------------------------------------------------------

def test_is_insufficient_material_kk() -> None:
    """K vs K is insufficient material."""
    fen = "4k3/8/8/8/8/8/8/4K3 w - - 0 1"
    board = Board(fen)
    assert board.is_insufficient_material()


def test_is_insufficient_material_kn_vs_k() -> None:
    """K+N vs K is insufficient material."""
    fen = "4k3/8/8/8/8/4N3/8/4K3 w - - 0 1"
    board = Board(fen)
    assert board.is_insufficient_material()


def test_is_insufficient_material_kb_vs_k() -> None:
    """K+B vs K is insufficient material."""
    fen = "4k3/8/8/8/8/4B3/8/4K3 w - - 0 1"
    board = Board(fen)
    assert board.is_insufficient_material()


def test_is_not_insufficient_material() -> None:
    """Starting position is NOT insufficient material."""
    board = Board()
    assert not board.is_insufficient_material()


def test_is_fifty_move_draw() -> None:
    """Halfmove >= 100 triggers fifty-move draw."""
    fen = "4k3/8/8/8/8/8/8/4K3 w - - 100 50"
    board = Board(fen)
    assert board.is_fifty_move_draw()


def test_is_not_fifty_move_draw() -> None:
    """Halfmove < 100 does not trigger fifty-move draw."""
    fen = "4k3/8/8/8/8/8/8/4K3 w - - 99 50"
    board = Board(fen)
    assert not board.is_fifty_move_draw()


def test_is_repetition() -> None:
    """Position appearing 3 times triggers repetition."""
    board = Board()
    # Make and unmake knight moves to create repetition
    # Nf3, Nf6, Ng1, Ng8 repeated -> same position appears multiple times
    w_out = encode_move(6, 21, QUIET)   # Ng1-f3
    b_out = encode_move(62, 45, QUIET)  # Ng8-f6
    w_back = encode_move(21, 6, QUIET)  # Nf3-g1
    b_back = encode_move(45, 62, QUIET) # Nf6-g8

    # First time doesn't count since position_history is empty at start
    board.make_move(w_out)
    board.make_move(b_out)
    board.make_move(w_back)
    board.make_move(b_back)
    # Now the starting position appears once more in position_history
    board.make_move(w_out)
    board.make_move(b_out)
    board.make_move(w_back)
    board.make_move(b_back)
    # Now it should appear at least twice with starting position FEN
    # Actually let's check: after b_back the board is back to start
    # position_history entries: [after w_out, after b_out, after w_back, after b_back,
    #                           after w_out2, after b_out2, after w_back2, after b_back2]
    # b_back positions (indices 3 and 7) have same FEN, but need 3 for repetition
    board.make_move(w_out)
    board.make_move(b_out)
    board.make_move(w_back)
    board.make_move(b_back)
    # Now position_history has the starting position FEN 3 times
    assert board.is_repetition()


def test_is_not_repetition() -> None:
    """No repetition after just one occurrence."""
    board = Board()
    move = encode_move(12, 28, DOUBLE_PAWN)
    board.make_move(move)
    assert not board.is_repetition()


# -----------------------------------------------------------------------
# Additional: Board.copy
# -----------------------------------------------------------------------

def test_copy_independence() -> None:
    """Copied board is independent of original."""
    board = Board()
    copy = board.copy()
    move = encode_move(12, 28, DOUBLE_PAWN)
    board.make_move(move)
    # Original changed, copy should not
    assert copy.get_fen() != board.get_fen()
    assert copy.get_fen() == "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"


# -----------------------------------------------------------------------
# Additional: Fullmove counter
# -----------------------------------------------------------------------

def test_fullmove_increments_after_black() -> None:
    """Fullmove counter increments after black's move."""
    board = Board()
    assert board.fullmove == 1
    # White move
    board.make_move(encode_move(12, 28, DOUBLE_PAWN))
    assert board.fullmove == 1
    # Black move
    board.make_move(encode_move(52, 36, DOUBLE_PAWN))
    assert board.fullmove == 2


def test_turn_alternates() -> None:
    """Turn alternates between WHITE and BLACK."""
    board = Board()
    assert board.turn == WHITE
    board.make_move(encode_move(12, 28, DOUBLE_PAWN))
    assert board.turn == BLACK
    board.make_move(encode_move(52, 36, DOUBLE_PAWN))
    assert board.turn == WHITE


# -----------------------------------------------------------------------
# Additional: Pawn attack direction
# -----------------------------------------------------------------------

def test_is_attacked_by_white_pawn() -> None:
    """White pawn attacks diagonally forward (higher rank)."""
    fen = "4k3/8/8/8/8/8/4P3/4K3 w - - 0 1"
    board = Board(fen)
    # White pawn on e2 (sq 12) attacks d3 (sq 19) and f3 (sq 21)
    assert board.is_attacked(19, WHITE)
    assert board.is_attacked(21, WHITE)
    # Does not attack forward
    assert not board.is_attacked(20, WHITE)


def test_is_attacked_by_black_pawn() -> None:
    """Black pawn attacks diagonally downward (lower rank)."""
    fen = "4k3/8/8/8/8/8/4p3/4K3 b - - 0 1"
    board = Board(fen)
    # Black pawn on e2 (sq 12) attacks d1 (sq 3) and f1 (sq 5)
    assert board.is_attacked(3, BLACK)
    assert board.is_attacked(5, BLACK)
