"""Board representation, piece constants, and helpers."""

# Piece constants: white positive, black negative
EMPTY = 0
W_PAWN, W_KNIGHT, W_BISHOP, W_ROOK, W_QUEEN, W_KING = 1, 2, 3, 4, 5, 6
B_PAWN, B_KNIGHT, B_BISHOP, B_ROOK, B_QUEEN, B_KING = -1, -2, -3, -4, -5, -6

# Side constants
WHITE, BLACK = 0, 1

# Castling bitmask
CASTLING_WK, CASTLING_WQ, CASTLING_BK, CASTLING_BQ = 1, 2, 4, 8


def piece_type(piece: int) -> int:
    """Return piece type (1-6) regardless of color."""
    return abs(piece)


def piece_color(piece: int) -> int:
    """Return WHITE if piece > 0, BLACK if piece < 0."""
    return WHITE if piece > 0 else BLACK


def sq_rank(sq: int) -> int:
    """Return rank (0-7) for a square index."""
    return sq // 8


def sq_file(sq: int) -> int:
    """Return file (0-7) for a square index."""
    return sq % 8


def sq_to_alg(sq: int) -> str:
    """Convert square index to algebraic notation (e.g. 0 -> 'a1')."""
    return chr(ord('a') + sq_file(sq)) + str(sq_rank(sq) + 1)


def alg_to_sq(s: str) -> int:
    """Convert algebraic notation to square index (e.g. 'e2' -> 12)."""
    return (ord(s[0]) - ord('a')) + (int(s[1]) - 1) * 8


class Board:
    """Chess board state."""

    def __init__(self) -> None:
        self.squares: list[int] = [EMPTY] * 64
        self.side_to_move: int = WHITE
        self.castling: int = 0
        self.ep_square: int = -1
        self.halfmove: int = 0
        self.fullmove: int = 1

    def copy(self) -> "Board":
        """Return a shallow copy of the board."""
        b = Board()
        b.squares = self.squares[:]
        b.side_to_move = self.side_to_move
        b.castling = self.castling
        b.ep_square = self.ep_square
        b.halfmove = self.halfmove
        b.fullmove = self.fullmove
        return b
