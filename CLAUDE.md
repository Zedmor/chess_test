# Chess Engine — Project Conventions

## Tech Stack
- Python 3.10+ (standard library only, no external chess libs)
- pytest for testing

## Commands
- Run engine: `python main.py`
- Run all tests: `python -m pytest tests/ -v`
- Run single test file: `python -m pytest tests/test_board.py -v`
- Run single test: `python -m pytest tests/test_board.py::test_fen_roundtrip -v`

## Project Structure
```
src/
  __init__.py
  board.py          # Board class, piece constants, FEN, make_move
  moves.py          # Move generation, attack detection, legal moves
  evaluation.py     # Material + PST evaluation
  search.py         # Alpha-beta, quiescence, iterative deepening
  uci.py            # UCI protocol handler
main.py             # Entry point
tests/
  __init__.py
  test_board.py
  test_moves.py
  test_evaluation.py
  test_search.py
  test_perft.py
```

## Key Interfaces

### Piece Constants (defined in `src/board.py`, imported everywhere)
```python
EMPTY = 0
W_PAWN, W_KNIGHT, W_BISHOP, W_ROOK, W_QUEEN, W_KING = 1, 2, 3, 4, 5, 6
B_PAWN, B_KNIGHT, B_BISHOP, B_ROOK, B_QUEEN, B_KING = -1, -2, -3, -4, -5, -6
WHITE, BLACK = 0, 1
CASTLING_WK, CASTLING_WQ, CASTLING_BK, CASTLING_BQ = 1, 2, 4, 8
```

### Square Indexing
- 64-element list, `sq = rank * 8 + file`
- a1=0, b1=1, ..., h1=7, a2=8, ..., h8=63
- `sq_rank(sq) = sq // 8`, `sq_file(sq) = sq % 8`

### Move Format
Tuple: `(from_sq: int, to_sq: int, promo: int)` where promo=0 for normal, piece type (2-5) for promotion.

### Board Class (`src/board.py`)
```python
class Board:
    squares: list[int]    # 64 elements
    side_to_move: int     # WHITE or BLACK
    castling: int         # bitmask: K=1, Q=2, k=4, q=8
    ep_square: int        # en passant target or -1
    halfmove: int
    fullmove: int

    @classmethod
    def from_fen(cls, fen: str) -> "Board": ...
    def to_fen(self) -> str: ...
    def copy(self) -> "Board": ...
    def make_move(self, move: tuple[int, int, int]) -> None: ...
```

### Function Signatures
```python
# evaluation.py
def evaluate(board: Board) -> int:  # centipawns, side-to-move perspective

# moves.py
def generate_legal_moves(board: Board) -> list[tuple[int, int, int]]: ...
def is_in_check(board: Board, color: int) -> bool: ...
def is_square_attacked(board: Board, sq: int, by_color: int) -> bool: ...

# search.py
def search(board: Board, time_limit: float) -> tuple[int, int, int]: ...

# uci.py
def uci_loop() -> None: ...
```

## Coding Rules
- No external dependencies (no python-chess, no numpy)
- Type hints on all function signatures
- Use constants from `src/board.py` — never magic numbers for pieces
- Keep functions under 50 lines
- No classes except Board
- Copy-make in search: `board.copy()` then `make_move()`, no unmake
- Tests required for every module — untested code will be rejected
- See `planning/architecture.md` for full design spec and PST values
