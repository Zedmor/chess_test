"""Chess engine constants, move encoding, and pre-computed tables."""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Piece encoding
# White pieces: 1-6, Black pieces: 9-14
# piece = piece_type | (color << 3)
# ---------------------------------------------------------------------------
EMPTY: int = 0

PAWN: int = 1
KNIGHT: int = 2
BISHOP: int = 3
ROOK: int = 4
QUEEN: int = 5
KING: int = 6

WHITE: int = 0
BLACK: int = 1

WHITE_PAWN: int = 1
WHITE_KNIGHT: int = 2
WHITE_BISHOP: int = 3
WHITE_ROOK: int = 4
WHITE_QUEEN: int = 5
WHITE_KING: int = 6

BLACK_PAWN: int = 9
BLACK_KNIGHT: int = 10
BLACK_BISHOP: int = 11
BLACK_ROOK: int = 12
BLACK_QUEEN: int = 13
BLACK_KING: int = 14


def piece_type(p: int) -> int:
    """Extract piece type (1-6) from a piece value."""
    return p & 7


def piece_color(p: int) -> int:
    """Extract color (WHITE=0, BLACK=1) from a piece value."""
    return p >> 3


def make_piece(color: int, ptype: int) -> int:
    """Create a piece value from color and type."""
    return ptype | (color << 3)


# ---------------------------------------------------------------------------
# Square helpers
# sq = rank * 8 + file, a1=0, b1=1, ..., h1=7, a2=8, ..., h8=63
# ---------------------------------------------------------------------------
def sq_rank(sq: int) -> int:
    """Return rank (0-7) of a square."""
    return sq >> 3


def sq_file(sq: int) -> int:
    """Return file (0-7) of a square."""
    return sq & 7


def make_sq(rank: int, file: int) -> int:
    """Create a square index from rank and file."""
    return (rank << 3) | file


def mirror(sq: int) -> int:
    """Vertically mirror a square (flip rank 0<->7, 1<->6, etc.)."""
    return sq ^ 56


# ---------------------------------------------------------------------------
# Castling constants (4-bit bitmask)
# ---------------------------------------------------------------------------
CASTLE_WK: int = 1   # White kingside  (K)
CASTLE_WQ: int = 2   # White queenside (Q)
CASTLE_BK: int = 4   # Black kingside  (k)
CASTLE_BQ: int = 8   # Black queenside (q)

# ---------------------------------------------------------------------------
# Move encoding (16-bit integer)
# bits 0-5: from_sq, bits 6-11: to_sq, bits 12-15: flags
# ---------------------------------------------------------------------------
QUIET: int = 0
DOUBLE_PAWN: int = 1
CASTLE_KING: int = 2
CASTLE_QUEEN: int = 3
CAPTURE: int = 4
EP_CAPTURE: int = 5
PROMO_KNIGHT: int = 8
PROMO_BISHOP: int = 9
PROMO_ROOK: int = 10
PROMO_QUEEN: int = 11
PROMO_KNIGHT_CAP: int = 12
PROMO_BISHOP_CAP: int = 13
PROMO_ROOK_CAP: int = 14
PROMO_QUEEN_CAP: int = 15


def encode_move(from_sq: int, to_sq: int, flags: int = 0) -> int:
    """Encode a move as a 16-bit integer."""
    return from_sq | (to_sq << 6) | (flags << 12)


def decode_from(move: int) -> int:
    """Extract from-square from an encoded move."""
    return move & 0x3F


def decode_to(move: int) -> int:
    """Extract to-square from an encoded move."""
    return (move >> 6) & 0x3F


def decode_flags(move: int) -> int:
    """Extract flags from an encoded move."""
    return (move >> 12) & 0xF


def is_capture(move: int) -> bool:
    """Return True if the move is a capture (bit 2 of flags is set)."""
    return bool((move >> 12) & 4)


def is_promotion(move: int) -> bool:
    """Return True if the move is a promotion (bit 3 of flags is set)."""
    return bool((move >> 12) & 8)


def promo_piece_type(move: int) -> int:
    """Return the promotion piece type (KNIGHT-QUEEN)."""
    return ((move >> 12) & 3) + KNIGHT


# ---------------------------------------------------------------------------
# FEN piece mapping
# ---------------------------------------------------------------------------
FEN_TO_PIECE: dict[str, int] = {
    'P': 1, 'N': 2, 'B': 3, 'R': 4, 'Q': 5, 'K': 6,
    'p': 9, 'n': 10, 'b': 11, 'r': 12, 'q': 13, 'k': 14,
}
PIECE_TO_FEN: dict[int, str] = {v: k for k, v in FEN_TO_PIECE.items()}

# ---------------------------------------------------------------------------
# Pre-computed attack tables (built at module load time)
# ---------------------------------------------------------------------------

# Knight move offsets as (rank_delta, file_delta)
_KNIGHT_DELTAS: list[tuple[int, int]] = [
    (-2, -1), (-2, 1), (-1, -2), (-1, 2),
    (1, -2), (1, 2), (2, -1), (2, 1),
]

# King move offsets as (rank_delta, file_delta)
_KING_DELTAS: list[tuple[int, int]] = [
    (-1, -1), (-1, 0), (-1, 1),
    (0, -1),           (0, 1),
    (1, -1),  (1, 0),  (1, 1),
]


def _build_jump_table(
    deltas: list[tuple[int, int]],
) -> tuple[tuple[int, ...], ...]:
    """Build a table of valid target squares for each source square."""
    table: list[tuple[int, ...]] = []
    for sq in range(64):
        r, f = sq >> 3, sq & 7
        targets: list[int] = []
        for dr, df in deltas:
            nr, nf = r + dr, f + df
            if 0 <= nr < 8 and 0 <= nf < 8:
                targets.append((nr << 3) | nf)
        table.append(tuple(targets))
    return tuple(table)


KNIGHT_MOVES: tuple[tuple[int, ...], ...] = _build_jump_table(_KNIGHT_DELTAS)
KING_MOVES: tuple[tuple[int, ...], ...] = _build_jump_table(_KING_DELTAS)

# ---------------------------------------------------------------------------
# Ray directions: N=0, NE=1, E=2, SE=3, S=4, SW=5, W=6, NW=7
# ---------------------------------------------------------------------------
_RAY_DELTAS: list[tuple[int, int]] = [
    (1, 0),    # N
    (1, 1),    # NE
    (0, 1),    # E
    (-1, 1),   # SE
    (-1, 0),   # S
    (-1, -1),  # SW
    (0, -1),   # W
    (1, -1),   # NW
]

BISHOP_DIRS: tuple[int, ...] = (1, 3, 5, 7)  # NE, SE, SW, NW
ROOK_DIRS: tuple[int, ...] = (0, 2, 4, 6)    # N, E, S, W


def _build_rays() -> tuple[tuple[tuple[int, ...], ...], ...]:
    """Build ray table: RAYS[sq][dir] = tuple of squares along that ray."""
    rays: list[tuple[tuple[int, ...], ...]] = []
    for sq in range(64):
        r, f = sq >> 3, sq & 7
        dirs: list[tuple[int, ...]] = []
        for dr, df in _RAY_DELTAS:
            ray: list[int] = []
            cr, cf = r + dr, f + df
            while 0 <= cr < 8 and 0 <= cf < 8:
                ray.append((cr << 3) | cf)
                cr += dr
                cf += df
            dirs.append(tuple(ray))
        rays.append(tuple(dirs))
    return tuple(rays)


RAYS: tuple[tuple[tuple[int, ...], ...], ...] = _build_rays()

# ---------------------------------------------------------------------------
# Castling mask: board.castling &= CASTLING_MASK[sq] on king/rook move
# ---------------------------------------------------------------------------
CASTLING_MASK: list[int] = [15] * 64
CASTLING_MASK[0] = 15 & ~CASTLE_WQ    # a1: clear WQ  -> 13
CASTLING_MASK[4] = 15 & ~(CASTLE_WK | CASTLE_WQ)  # e1: clear WK+WQ -> 12
CASTLING_MASK[7] = 15 & ~CASTLE_WK    # h1: clear WK  -> 14
CASTLING_MASK[56] = 15 & ~CASTLE_BQ   # a8: clear BQ  -> 7
CASTLING_MASK[60] = 15 & ~(CASTLE_BK | CASTLE_BQ)  # e8: clear BK+BQ -> 3
CASTLING_MASK[63] = 15 & ~CASTLE_BK   # h8: clear BK  -> 11

# ---------------------------------------------------------------------------
# UCI move conversion
# ---------------------------------------------------------------------------


def move_to_uci(move: int) -> str:
    """Convert an encoded move to UCI long algebraic notation."""
    f = decode_from(move)
    t = decode_to(move)
    s = chr((f & 7) + ord('a')) + str((f >> 3) + 1)
    s += chr((t & 7) + ord('a')) + str((t >> 3) + 1)
    if is_promotion(move):
        s += {KNIGHT: 'n', BISHOP: 'b', ROOK: 'r', QUEEN: 'q'}[
            promo_piece_type(move)
        ]
    return s


def parse_uci_move(board: object, uci_str: str) -> int:
    """Parse a UCI move string into an encoded move.

    Args:
        board: Object with .squares (list[int]) and .ep_square (int) attrs.
        uci_str: UCI long algebraic string, e.g. "e2e4", "e7e8q".

    Returns:
        Encoded 16-bit move integer.
    """
    from_sq = (int(uci_str[1]) - 1) * 8 + (ord(uci_str[0]) - ord('a'))
    to_sq = (int(uci_str[3]) - 1) * 8 + (ord(uci_str[2]) - ord('a'))
    promo = (
        {'n': KNIGHT, 'b': BISHOP, 'r': ROOK, 'q': QUEEN}.get(uci_str[4])
        if len(uci_str) == 5
        else None
    )

    squares: list[int] = board.squares  # type: ignore[attr-defined]
    ep_square: int = board.ep_square  # type: ignore[attr-defined]
    piece = squares[from_sq]
    pt = piece & 7
    is_cap = squares[to_sq] != EMPTY

    # Castling
    if pt == KING and abs((from_sq & 7) - (to_sq & 7)) == 2:
        flag = CASTLE_KING if to_sq > from_sq else CASTLE_QUEEN
        return encode_move(from_sq, to_sq, flag)

    # Pawn specials
    if pt == PAWN:
        if to_sq == ep_square:
            return encode_move(from_sq, to_sq, EP_CAPTURE)
        if abs((from_sq >> 3) - (to_sq >> 3)) == 2:
            return encode_move(from_sq, to_sq, DOUBLE_PAWN)
        if promo is not None:
            base = (promo - KNIGHT) + (
                PROMO_KNIGHT_CAP if is_cap else PROMO_KNIGHT
            )
            return encode_move(from_sq, to_sq, base)

    return encode_move(from_sq, to_sq, CAPTURE if is_cap else QUIET)
