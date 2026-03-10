# Chess Engine — Project Conventions

## Tech Stack
- Python 3.10+ (NO external packages — everything from scratch)
- pytest for testing
- Only Stockfish is installed externally (for match testing)

## Commands
- Install test deps: `pip install pytest`
- Run engine: `python main.py`
- Run all tests: `python -m pytest tests/ -v`
- Run single test file: `python -m pytest tests/test_board.py -v`
- Run single test: `python -m pytest tests/test_board.py::test_fen_roundtrip -v`

## Project Structure
```
src/
  __init__.py
  constants.py      # Piece/color/square constants, pre-computed tables, move encoding
  board.py          # Board class: state, make/unmake, FEN, is_attacked
  movegen.py        # Legal move generation, perft
  evaluation.py     # Material + PST evaluation
  search.py         # Alpha-beta, quiescence, iterative deepening
  move_ordering.py  # MVV-LVA, killer moves, capture ordering
  opening_book.py   # Hardcoded opening book
  uci.py            # UCI protocol handler
main.py             # Entry point
tests/
  __init__.py
  test_board.py
  test_movegen.py
  test_evaluation.py
  test_search.py
  test_move_ordering.py
  test_opening_book.py
  test_uci.py
```

## Key Types

### Piece Encoding (integers)
```python
EMPTY = 0
PAWN = 1; KNIGHT = 2; BISHOP = 3; ROOK = 4; QUEEN = 5; KING = 6
WHITE = 0; BLACK = 1
# White pieces: 1-6, Black pieces: 9-14
# piece_type(p) = p & 7
# piece_color(p) = p >> 3
# make_piece(color, type) = type | (color << 3)
```

### Square Indexing
```
a1=0, b1=1, ..., h1=7, a2=8, ..., h8=63
rank(sq) = sq >> 3
file(sq) = sq & 7
mirror(sq) = sq ^ 56  (flip rank for black PST)
```

### Move Encoding (16-bit integer)
```python
# bits 0-5: from_sq, bits 6-11: to_sq, bits 12-15: flags
encode_move(from_sq, to_sq, flags) -> int
decode_from(move) -> int
decode_to(move) -> int
decode_flags(move) -> int
is_capture(move) -> bool
is_promotion(move) -> bool
```

### Board Class
```python
from src.board import Board
board = Board()                    # starting position
board = Board("fen string here")   # from FEN
board.make_move(move)              # apply move
board.unmake_move()                # undo last move
board.is_attacked(sq, by_color)    # attack detection
board.is_in_check()                # current side in check?
board.get_fen()                    # current FEN string
board.get_position_fen()           # FEN without move counters (for book/repetition)
```

## Function Signatures
```python
# constants.py
def encode_move(from_sq: int, to_sq: int, flags: int = 0) -> int: ...
def decode_from(move: int) -> int: ...
def decode_to(move: int) -> int: ...
def decode_flags(move: int) -> int: ...
def is_capture(move: int) -> bool: ...
def is_promotion(move: int) -> bool: ...
def promo_piece_type(move: int) -> int: ...
def move_to_uci(move: int) -> str: ...
def parse_uci_move(board, uci_str: str) -> int: ...

# board.py
class Board:
    def __init__(self, fen: str | None = None): ...
    def set_fen(self, fen: str) -> None: ...
    def get_fen(self) -> str: ...
    def get_position_fen(self) -> str: ...
    def make_move(self, move: int) -> None: ...
    def unmake_move(self) -> None: ...
    def is_attacked(self, sq: int, by_color: int) -> bool: ...
    def is_in_check(self) -> bool: ...

# movegen.py
def generate_legal_moves(board: Board) -> list[int]: ...
def generate_legal_captures(board: Board) -> list[int]: ...
def perft(board: Board, depth: int) -> int: ...

# evaluation.py
MATE_SCORE = 100000
def evaluate(board: Board) -> int: ...  # centipawns, side-to-move perspective

# move_ordering.py
def order_moves(moves: list[int], board: Board,
                killer_moves: list, depth: int) -> None: ...  # in-place sort
def order_captures(moves: list[int], board: Board) -> None: ...  # in-place sort

# search.py
def search(board: Board, time_limit: float) -> int: ...  # returns encoded move

# opening_book.py
def get_book_move(board: Board) -> int | None: ...

# uci.py
def uci_loop() -> None: ...
```

## Coding Rules
- **ZERO external dependencies** — no pip packages, everything from scratch
- Board state: 64-element list of ints, make/unmake with undo stack
- Moves: 16-bit integers (encode_move/decode_from/decode_to/decode_flags)
- Use `board.make_move()`/`board.unmake_move()` — no copy-make
- Type hints on all function signatures
- Keep functions under 50 lines
- Tests required for every module — untested code will be rejected
- Perft tests are mandatory for movegen — must match known values
- See `planning/architecture.md` for full design spec, PST values, and algorithms
