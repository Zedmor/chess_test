"""Board class with make/unmake, attack detection, and FEN handling."""

from __future__ import annotations

from src.constants import (
    EMPTY, PAWN, KNIGHT, BISHOP, ROOK, QUEEN, KING,
    WHITE, BLACK,
    WHITE_PAWN, WHITE_ROOK, WHITE_KING,
    BLACK_PAWN, BLACK_ROOK, BLACK_KING,
    CASTLE_WK, CASTLE_WQ, CASTLE_BK, CASTLE_BQ,
    QUIET, DOUBLE_PAWN, CASTLE_KING, CASTLE_QUEEN, CAPTURE, EP_CAPTURE,
    piece_type, piece_color, make_piece,
    sq_file,
    encode_move, decode_from, decode_to, decode_flags,
    is_promotion, promo_piece_type,
    FEN_TO_PIECE, PIECE_TO_FEN,
    KNIGHT_MOVES, KING_MOVES,
    RAYS, BISHOP_DIRS, ROOK_DIRS,
    CASTLING_MASK,
)


class Board:
    """Chess board state."""

    __slots__ = (
        'squares', 'turn', 'castling', 'ep_square',
        'halfmove', 'fullmove', 'king_sq', 'history', 'position_history',
    )

    def __init__(self, fen: str | None = None) -> None:
        self.history: list[tuple[int, int, int, int, int]] = []
        self.position_history: list[str] = []
        if fen:
            self.set_fen(fen)
        else:
            self.set_fen(
                'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1'
            )

    def set_fen(self, fen: str) -> None:
        """Parse FEN string and populate board state."""
        parts = fen.split()
        self.squares: list[int] = [EMPTY] * 64
        self.king_sq: list[int] = [0, 0]
        rank, file = 7, 0
        for ch in parts[0]:
            if ch == '/':
                rank -= 1
                file = 0
            elif ch.isdigit():
                file += int(ch)
            else:
                sq = rank * 8 + file
                piece = FEN_TO_PIECE[ch]
                self.squares[sq] = piece
                if piece_type(piece) == KING:
                    self.king_sq[piece_color(piece)] = sq
                file += 1
        self.turn: int = WHITE if parts[1] == 'w' else BLACK
        self.castling: int = 0
        if parts[2] != '-':
            for ch in parts[2]:
                if ch == 'K':
                    self.castling |= CASTLE_WK
                elif ch == 'Q':
                    self.castling |= CASTLE_WQ
                elif ch == 'k':
                    self.castling |= CASTLE_BK
                elif ch == 'q':
                    self.castling |= CASTLE_BQ
        if parts[3] == '-':
            self.ep_square: int = -1
        else:
            self.ep_square = (
                (ord(parts[3][0]) - ord('a')) + (int(parts[3][1]) - 1) * 8
            )
        self.halfmove: int = int(parts[4])
        self.fullmove: int = int(parts[5])

    def get_fen(self) -> str:
        """Generate FEN string from current state."""
        rows: list[str] = []
        for rank in range(7, -1, -1):
            row = ''
            empty = 0
            for file in range(8):
                piece = self.squares[rank * 8 + file]
                if piece == EMPTY:
                    empty += 1
                else:
                    if empty:
                        row += str(empty)
                        empty = 0
                    row += PIECE_TO_FEN[piece]
            if empty:
                row += str(empty)
            rows.append(row)
        board_str = '/'.join(rows)
        side = 'w' if self.turn == WHITE else 'b'
        c = ''
        if self.castling & CASTLE_WK:
            c += 'K'
        if self.castling & CASTLE_WQ:
            c += 'Q'
        if self.castling & CASTLE_BK:
            c += 'k'
        if self.castling & CASTLE_BQ:
            c += 'q'
        castling = c or '-'
        if self.ep_square == -1:
            ep = '-'
        else:
            ep = (
                chr(ord('a') + (self.ep_square & 7))
                + str((self.ep_square >> 3) + 1)
            )
        return f'{board_str} {side} {castling} {ep} {self.halfmove} {self.fullmove}'

    def get_position_fen(self) -> str:
        """FEN without halfmove/fullmove (for repetition detection)."""
        parts = self.get_fen().split()
        return ' '.join(parts[:4])

    def copy(self) -> Board:
        """Return a copy of the board."""
        b = Board.__new__(Board)
        b.squares = self.squares[:]
        b.turn = self.turn
        b.castling = self.castling
        b.ep_square = self.ep_square
        b.halfmove = self.halfmove
        b.fullmove = self.fullmove
        b.king_sq = self.king_sq[:]
        b.history = self.history[:]
        b.position_history = self.position_history[:]
        return b

    def make_move(self, move: int) -> None:
        """Apply encoded move, save undo info to history."""
        from_sq = decode_from(move)
        to_sq = decode_to(move)
        flags = decode_flags(move)
        piece = self.squares[from_sq]
        captured = self.squares[to_sq]
        self.history.append(
            (move, captured, self.castling, self.ep_square, self.halfmove)
        )
        self.squares[from_sq] = EMPTY
        self.squares[to_sq] = piece
        if flags == CASTLE_KING:
            r_from, r_to = (7, 5) if self.turn == WHITE else (63, 61)
            self.squares[r_from] = EMPTY
            self.squares[r_to] = make_piece(self.turn, ROOK)
        elif flags == CASTLE_QUEEN:
            r_from, r_to = (0, 3) if self.turn == WHITE else (56, 59)
            self.squares[r_from] = EMPTY
            self.squares[r_to] = make_piece(self.turn, ROOK)
        elif flags == EP_CAPTURE:
            cap_sq = to_sq - 8 if self.turn == WHITE else to_sq + 8
            self.squares[cap_sq] = EMPTY
        if is_promotion(move):
            self.squares[to_sq] = make_piece(self.turn, promo_piece_type(move))
        if flags == DOUBLE_PAWN:
            self.ep_square = (
                from_sq + 8 if self.turn == WHITE else from_sq - 8
            )
        else:
            self.ep_square = -1
        if piece_type(piece) == KING:
            self.king_sq[self.turn] = to_sq
        self.castling &= CASTLING_MASK[from_sq] & CASTLING_MASK[to_sq]
        if piece_type(piece) == PAWN or captured != EMPTY or flags == EP_CAPTURE:
            self.halfmove = 0
        else:
            self.halfmove += 1
        if self.turn == BLACK:
            self.fullmove += 1
        self.turn ^= 1
        self.position_history.append(self.get_position_fen())

    def unmake_move(self) -> None:
        """Pop from history, restore all state."""
        move, captured, castling, ep_square, halfmove = self.history.pop()
        from_sq = decode_from(move)
        to_sq = decode_to(move)
        flags = decode_flags(move)
        self.turn ^= 1
        if self.turn == BLACK:
            self.fullmove -= 1
        piece = self.squares[to_sq]
        if is_promotion(move):
            piece = make_piece(self.turn, PAWN)
        self.squares[to_sq] = captured
        self.squares[from_sq] = piece
        if flags == CASTLE_KING:
            r_from, r_to = (7, 5) if self.turn == WHITE else (63, 61)
            self.squares[r_to] = EMPTY
            self.squares[r_from] = make_piece(self.turn, ROOK)
        elif flags == CASTLE_QUEEN:
            r_from, r_to = (0, 3) if self.turn == WHITE else (56, 59)
            self.squares[r_to] = EMPTY
            self.squares[r_from] = make_piece(self.turn, ROOK)
        elif flags == EP_CAPTURE:
            cap_sq = to_sq - 8 if self.turn == WHITE else to_sq + 8
            self.squares[cap_sq] = make_piece(self.turn ^ 1, PAWN)
        if piece_type(piece) == KING:
            self.king_sq[self.turn] = from_sq
        self.castling = castling
        self.ep_square = ep_square
        self.halfmove = halfmove
        self.position_history.pop()

    def is_attacked(self, sq: int, by_color: int) -> bool:
        """Check if square is attacked by given color."""
        squares = self.squares
        if by_color == WHITE:
            for d in (-7, -9):
                psq = sq + d
                if 0 <= psq < 64 and abs(sq_file(psq) - sq_file(sq)) == 1:
                    if squares[psq] == WHITE_PAWN:
                        return True
        else:
            for d in (7, 9):
                psq = sq + d
                if 0 <= psq < 64 and abs(sq_file(psq) - sq_file(sq)) == 1:
                    if squares[psq] == BLACK_PAWN:
                        return True
        enemy_knight = make_piece(by_color, KNIGHT)
        for tsq in KNIGHT_MOVES[sq]:
            if squares[tsq] == enemy_knight:
                return True
        enemy_king = make_piece(by_color, KING)
        for tsq in KING_MOVES[sq]:
            if squares[tsq] == enemy_king:
                return True
        enemy_bishop = make_piece(by_color, BISHOP)
        enemy_queen = make_piece(by_color, QUEEN)
        for d in BISHOP_DIRS:
            for rsq in RAYS[sq][d]:
                p = squares[rsq]
                if p == EMPTY:
                    continue
                if p == enemy_bishop or p == enemy_queen:
                    return True
                break
        enemy_rook = make_piece(by_color, ROOK)
        for d in ROOK_DIRS:
            for rsq in RAYS[sq][d]:
                p = squares[rsq]
                if p == EMPTY:
                    continue
                if p == enemy_rook or p == enemy_queen:
                    return True
                break
        return False

    def is_in_check(self) -> bool:
        """Check if current side's king is in check."""
        return self.is_attacked(self.king_sq[self.turn], self.turn ^ 1)

    def is_insufficient_material(self) -> bool:
        """K vs K, K+N vs K, K+B vs K."""
        pieces: list[int] = []
        for sq in range(64):
            p = self.squares[sq]
            if p != EMPTY and piece_type(p) != KING:
                pieces.append(p)
                if len(pieces) > 1:
                    return False
        if not pieces:
            return True
        pt = piece_type(pieces[0])
        return pt == KNIGHT or pt == BISHOP

    def is_fifty_move_draw(self) -> bool:
        """Check if fifty-move rule applies."""
        return self.halfmove >= 100

    def is_repetition(self) -> bool:
        """Check if current position appeared 3+ times."""
        if not self.position_history:
            return False
        current = self.position_history[-1]
        return self.position_history.count(current) >= 3
