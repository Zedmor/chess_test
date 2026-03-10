"""Legal move generation and perft validation."""

from __future__ import annotations

from src.constants import (
    EMPTY, PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING,
    WHITE, BLACK,
    piece_type, piece_color, make_piece,
    sq_rank, sq_file,
    QUIET, DOUBLE_PAWN, CASTLE_KING, CASTLE_QUEEN, CAPTURE, EP_CAPTURE,
    PROMO_KNIGHT, PROMO_BISHOP, PROMO_ROOK, PROMO_QUEEN,
    PROMO_KNIGHT_CAP, PROMO_BISHOP_CAP, PROMO_ROOK_CAP, PROMO_QUEEN_CAP,
    CASTLE_WK, CASTLE_WQ, CASTLE_BK, CASTLE_BQ,
    encode_move, is_capture,
    KNIGHT_MOVES, KING_MOVES, RAYS, BISHOP_DIRS, ROOK_DIRS,
)
from src.board import Board

from typing import Generator


def _pawn_moves(board: Board, sq: int, color: int) -> Generator[int, None, None]:
    """Generate pawn pushes, double pushes, captures, en passant, promotions."""
    squares = board.squares
    if color == WHITE:
        forward = 8
        start_rank = 1
        promo_rank = 7
        cap_offsets = (7, 9)
    else:
        forward = -8
        start_rank = 6
        promo_rank = 0
        cap_offsets = (-9, -7)

    target = sq + forward
    f = sq_file(sq)

    # Single push
    if 0 <= target < 64 and squares[target] == EMPTY:
        if sq_rank(target) == promo_rank:
            yield encode_move(sq, target, PROMO_QUEEN)
            yield encode_move(sq, target, PROMO_ROOK)
            yield encode_move(sq, target, PROMO_BISHOP)
            yield encode_move(sq, target, PROMO_KNIGHT)
        else:
            yield encode_move(sq, target, QUIET)
            # Double push
            if sq_rank(sq) == start_rank:
                target2 = sq + 2 * forward
                if squares[target2] == EMPTY:
                    yield encode_move(sq, target2, DOUBLE_PAWN)

    # Captures
    for offset in cap_offsets:
        csq = sq + offset
        if csq < 0 or csq >= 64:
            continue
        cf = sq_file(csq)
        if abs(cf - f) != 1:
            continue
        if csq == board.ep_square:
            yield encode_move(sq, csq, EP_CAPTURE)
        elif squares[csq] != EMPTY and piece_color(squares[csq]) != color:
            if sq_rank(csq) == promo_rank:
                yield encode_move(sq, csq, PROMO_QUEEN_CAP)
                yield encode_move(sq, csq, PROMO_ROOK_CAP)
                yield encode_move(sq, csq, PROMO_BISHOP_CAP)
                yield encode_move(sq, csq, PROMO_KNIGHT_CAP)
            else:
                yield encode_move(sq, csq, CAPTURE)


def _knight_moves(board: Board, sq: int, color: int) -> Generator[int, None, None]:
    """Generate knight moves."""
    squares = board.squares
    for tsq in KNIGHT_MOVES[sq]:
        target = squares[tsq]
        if target == EMPTY:
            yield encode_move(sq, tsq, QUIET)
        elif piece_color(target) != color:
            yield encode_move(sq, tsq, CAPTURE)


def _sliding_moves(
    board: Board, sq: int, color: int, dirs: tuple[int, ...],
) -> Generator[int, None, None]:
    """Generate sliding piece moves along given ray directions."""
    squares = board.squares
    for d in dirs:
        for rsq in RAYS[sq][d]:
            target = squares[rsq]
            if target == EMPTY:
                yield encode_move(sq, rsq, QUIET)
            else:
                if piece_color(target) != color:
                    yield encode_move(sq, rsq, CAPTURE)
                break


def _king_moves(board: Board, sq: int, color: int) -> Generator[int, None, None]:
    """Generate king moves (non-castling)."""
    squares = board.squares
    for tsq in KING_MOVES[sq]:
        target = squares[tsq]
        if target == EMPTY:
            yield encode_move(sq, tsq, QUIET)
        elif piece_color(target) != color:
            yield encode_move(sq, tsq, CAPTURE)


def _castling_moves(board: Board) -> Generator[int, None, None]:
    """Generate castling moves if available."""
    turn = board.turn
    squares = board.squares

    if turn == WHITE:
        king_sq = 4  # e1
        if board.castling & CASTLE_WK:
            if (squares[5] == EMPTY and squares[6] == EMPTY
                    and not board.is_attacked(4, BLACK)
                    and not board.is_attacked(5, BLACK)
                    and not board.is_attacked(6, BLACK)):
                yield encode_move(king_sq, 6, CASTLE_KING)
        if board.castling & CASTLE_WQ:
            if (squares[1] == EMPTY and squares[2] == EMPTY
                    and squares[3] == EMPTY
                    and not board.is_attacked(4, BLACK)
                    and not board.is_attacked(3, BLACK)
                    and not board.is_attacked(2, BLACK)):
                yield encode_move(king_sq, 2, CASTLE_QUEEN)
    else:
        king_sq = 60  # e8
        if board.castling & CASTLE_BK:
            if (squares[61] == EMPTY and squares[62] == EMPTY
                    and not board.is_attacked(60, WHITE)
                    and not board.is_attacked(61, WHITE)
                    and not board.is_attacked(62, WHITE)):
                yield encode_move(king_sq, 62, CASTLE_KING)
        if board.castling & CASTLE_BQ:
            if (squares[57] == EMPTY and squares[58] == EMPTY
                    and squares[59] == EMPTY
                    and not board.is_attacked(60, WHITE)
                    and not board.is_attacked(59, WHITE)
                    and not board.is_attacked(58, WHITE)):
                yield encode_move(king_sq, 58, CASTLE_QUEEN)


def generate_pseudo_legal(board: Board) -> Generator[int, None, None]:
    """Yield all pseudo-legal moves as encoded integers."""
    turn = board.turn
    squares = board.squares
    all_dirs = BISHOP_DIRS + ROOK_DIRS

    for sq in range(64):
        piece = squares[sq]
        if piece == EMPTY or piece_color(piece) != turn:
            continue
        pt = piece_type(piece)
        if pt == PAWN:
            yield from _pawn_moves(board, sq, turn)
        elif pt == KNIGHT:
            yield from _knight_moves(board, sq, turn)
        elif pt == BISHOP:
            yield from _sliding_moves(board, sq, turn, BISHOP_DIRS)
        elif pt == ROOK:
            yield from _sliding_moves(board, sq, turn, ROOK_DIRS)
        elif pt == QUEEN:
            yield from _sliding_moves(board, sq, turn, all_dirs)
        elif pt == KING:
            yield from _king_moves(board, sq, turn)

    yield from _castling_moves(board)


def generate_legal_moves(board: Board) -> list[int]:
    """Return list of legal moves for the current position."""
    legal: list[int] = []
    turn = board.turn
    enemy = turn ^ 1
    for move in generate_pseudo_legal(board):
        board.make_move(move)
        if not board.is_attacked(board.king_sq[turn], enemy):
            legal.append(move)
        board.unmake_move()
    return legal


def generate_legal_captures(board: Board) -> list[int]:
    """Return list of legal capture moves (for quiescence search)."""
    captures: list[int] = []
    turn = board.turn
    enemy = turn ^ 1
    for move in generate_pseudo_legal(board):
        if not is_capture(move):
            continue
        board.make_move(move)
        if not board.is_attacked(board.king_sq[turn], enemy):
            captures.append(move)
        board.unmake_move()
    return captures


def perft(board: Board, depth: int) -> int:
    """Count leaf nodes at given depth for move generation validation."""
    if depth == 0:
        return 1
    count = 0
    for move in generate_legal_moves(board):
        board.make_move(move)
        count += perft(board, depth - 1)
        board.unmake_move()
    return count
