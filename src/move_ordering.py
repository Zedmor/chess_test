"""Move ordering for search efficiency: MVV-LVA and killer moves."""

from src.board import EMPTY, Board, piece_type

# Material values (centipawns) for MVV-LVA scoring
PIECE_VALUES: dict[int, int] = {
    1: 100,    # pawn
    2: 320,    # knight
    3: 330,    # bishop
    4: 500,    # rook
    5: 900,    # queen
    6: 20000,  # king
}

# Move type alias
Move = tuple[int, int, int]

# Pre-compute MVV-LVA scores for all (victim_type, attacker_type) pairs
# Score = PIECE_VALUES[victim] * 10 - PIECE_VALUES[attacker]
# Higher score = better capture to search first
MVV_LVA_SCORES: dict[tuple[int, int], int] = {}
for _vt in range(1, 7):
    for _at in range(1, 7):
        MVV_LVA_SCORES[(_vt, _at)] = PIECE_VALUES[_vt] * 10 - PIECE_VALUES[_at]

MAX_KILLER_DEPTH = 64


def create_killer_table() -> list[list[Move | None]]:
    """Return killer_moves[depth] = [None, None] for each depth."""
    return [[None, None] for _ in range(MAX_KILLER_DEPTH)]


def update_killers(
    killer_moves: list[list[Move | None]], move: Move, depth: int
) -> None:
    """Insert move at [depth][0], shift old [0] to [1]."""
    if killer_moves[depth][0] != move:
        killer_moves[depth][1] = killer_moves[depth][0]
        killer_moves[depth][0] = move


def _is_capture(move: Move, board: Board) -> bool:
    """Check if a move is a capture (including en passant)."""
    from_sq, to_sq, _ = move
    if board.squares[to_sq] != EMPTY:
        return True
    # En passant: pawn moves to ep_square
    piece = board.squares[from_sq]
    if piece_type(piece) == 1 and to_sq == board.ep_square != -1:
        return True
    return False


def _capture_score(move: Move, board: Board) -> int:
    """Return MVV-LVA score for a capture move."""
    from_sq, to_sq, _ = move
    captured = board.squares[to_sq]
    attacker = board.squares[from_sq]
    if captured == EMPTY:
        # En passant — victim is a pawn
        victim_t = 1
    else:
        victim_t = piece_type(captured)
    attacker_t = piece_type(attacker)
    return MVV_LVA_SCORES.get((victim_t, attacker_t), 0)


def order_moves(
    moves: list[Move],
    board: Board,
    killer_moves: list[list[Move | None]],
    depth: int,
) -> list[Move]:
    """Sort moves: captures by MVV-LVA first, then killers, then rest."""
    scored: list[tuple[int, Move]] = []
    for move in moves:
        if _is_capture(move, board):
            score = 10000 + _capture_score(move, board)
        elif move == killer_moves[depth][0]:
            score = 9000
        elif move == killer_moves[depth][1]:
            score = 8000
        else:
            score = 0
        scored.append((score, move))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [m for _, m in scored]


def order_captures(moves: list[Move], board: Board) -> list[Move]:
    """Return capture moves sorted by MVV-LVA for quiescence."""
    captures: list[tuple[int, Move]] = []
    for move in moves:
        if _is_capture(move, board):
            score = _capture_score(move, board)
            captures.append((score, move))
    captures.sort(key=lambda x: x[0], reverse=True)
    return [m for _, m in captures]
