# Chess Engine Architecture

## Overview
Pure Python chess engine targeting ≥50% winrate vs Stockfish at ~1200 ELO. **Zero external dependencies** — board representation, move generation, evaluation, search, and UCI protocol all implemented from scratch. Only Stockfish is installed externally (for testing).

## Tech Stack
- Python 3.10+ (no external packages)
- pytest for testing
- UCI protocol for engine communication

## File Structure
```
chess_test/
├── src/
│   ├── __init__.py
│   ├── constants.py      # Piece/color/square constants, pre-computed tables
│   ├── board.py          # Board class: state, make/unmake, FEN, is_attacked
│   ├── movegen.py        # Legal move generation, perft
│   ├── evaluation.py     # Material + PST evaluation
│   ├── search.py         # Alpha-beta, quiescence, iterative deepening
│   ├── move_ordering.py  # MVV-LVA, killer moves, capture ordering
│   ├── opening_book.py   # Hardcoded opening book
│   └── uci.py            # UCI protocol handler
├── main.py               # Entry point: python main.py
├── tests/
│   ├── __init__.py
│   ├── test_board.py
│   ├── test_movegen.py
│   ├── test_evaluation.py
│   ├── test_search.py
│   ├── test_move_ordering.py
│   ├── test_opening_book.py
│   └── test_uci.py
├── planning/
│   ├── architecture.md
│   └── roadmap.md
└── CLAUDE.md
```

---

## Constants & Encoding (`constants.py`)

### Piece Encoding
```python
EMPTY = 0
PAWN = 1; KNIGHT = 2; BISHOP = 3; ROOK = 4; QUEEN = 5; KING = 6
WHITE = 0; BLACK = 1

# White pieces: 1-6, Black pieces: 9-14
# piece_color(p) = p >> 3       → 0=WHITE, 1=BLACK
# piece_type(p)  = p & 7        → 1=PAWN..6=KING
# make_piece(color, type) = type | (color << 3)

WHITE_PAWN = 1; WHITE_KNIGHT = 2; WHITE_BISHOP = 3
WHITE_ROOK = 4; WHITE_QUEEN = 5; WHITE_KING = 6
BLACK_PAWN = 9; BLACK_KNIGHT = 10; BLACK_BISHOP = 11
BLACK_ROOK = 12; BLACK_QUEEN = 13; BLACK_KING = 14
```

### Square Indexing
```
a1=0, b1=1, ..., h1=7
a2=8, b2=9, ..., h2=15
...
a8=56, b8=57, ..., h8=63

rank(sq) = sq >> 3      (0-7, rank 1-8)
file(sq) = sq & 7       (0-7, a-h)
make_sq(rank, file) = (rank << 3) | file
mirror(sq) = sq ^ 56    (flip rank for black PST lookup)
```

### Castling Rights (bitmask)
```python
CASTLE_WK = 1   # White kingside  (K)
CASTLE_WQ = 2   # White queenside (Q)
CASTLE_BK = 4   # Black kingside  (k)
CASTLE_BQ = 8   # Black queenside (q)
```

### Move Encoding (16-bit integer)
```python
# bits 0-5:   from_square (0-63)
# bits 6-11:  to_square (0-63)
# bits 12-15: flags

QUIET = 0
DOUBLE_PAWN = 1
CASTLE_KING = 2
CASTLE_QUEEN = 3
CAPTURE = 4
EP_CAPTURE = 5
# 6, 7 unused
PROMO_KNIGHT = 8
PROMO_BISHOP = 9
PROMO_ROOK = 10
PROMO_QUEEN = 11
PROMO_KNIGHT_CAP = 12
PROMO_BISHOP_CAP = 13
PROMO_ROOK_CAP = 14
PROMO_QUEEN_CAP = 15

def encode_move(from_sq, to_sq, flags=0):
    return from_sq | (to_sq << 6) | (flags << 12)

def decode_from(move):  return move & 0x3F
def decode_to(move):    return (move >> 6) & 0x3F
def decode_flags(move):  return (move >> 12) & 0xF
def is_capture(move):    return bool((move >> 12) & 4)   # flag bit 2
def is_promotion(move):  return bool((move >> 12) & 8)   # flag bit 3
def promo_piece_type(move):  return ((move >> 12) & 3) + KNIGHT  # 2=N,3=B,4=R,5=Q
```

### FEN Piece Mapping
```python
FEN_TO_PIECE = {
    'P': 1, 'N': 2, 'B': 3, 'R': 4, 'Q': 5, 'K': 6,
    'p': 9, 'n': 10, 'b': 11, 'r': 12, 'q': 13, 'k': 14,
}
PIECE_TO_FEN = {v: k for k, v in FEN_TO_PIECE.items()}
```

### Pre-computed Attack Tables
```python
# Computed once at module load

KNIGHT_MOVES = tuple(
    tuple(target for dr, df in [(-2,-1),(-2,1),(-1,-2),(-1,2),
                                 (1,-2),(1,2),(2,-1),(2,1)]
          if 0 <= (r := sq // 8 + dr) < 8 and 0 <= (f := sq % 8 + df) < 8
          for target in [r * 8 + f])
    for sq in range(64)
)

KING_MOVES = tuple(
    tuple(target for dr, df in [(-1,-1),(-1,0),(-1,1),(0,-1),
                                 (0,1),(1,-1),(1,0),(1,1)]
          if 0 <= (r := sq // 8 + dr) < 8 and 0 <= (f := sq % 8 + df) < 8
          for target in [r * 8 + f])
    for sq in range(64)
)

# RAYS[sq][dir] = tuple of squares along ray (ordered outward from sq)
# 8 directions: N(0), NE(1), E(2), SE(3), S(4), SW(5), W(6), NW(7)
# dir offsets (rank_delta, file_delta):
#   N=(1,0), NE=(1,1), E=(0,1), SE=(-1,1), S=(-1,0), SW=(-1,-1), W=(0,-1), NW=(1,-1)
BISHOP_DIRS = (1, 3, 5, 7)  # NE, SE, SW, NW
ROOK_DIRS = (0, 2, 4, 6)    # N, E, S, W

# Castling rights update mask (AND with both from_sq and to_sq)
CASTLING_MASK = [15] * 64
CASTLING_MASK[0] = 13    # a1: clear WQ
CASTLING_MASK[4] = 12    # e1: clear WK+WQ
CASTLING_MASK[7] = 14    # h1: clear WK
CASTLING_MASK[56] = 7    # a8: clear BQ
CASTLING_MASK[60] = 3    # e8: clear BK+BQ
CASTLING_MASK[63] = 11   # h8: clear BK
```

### UCI Move Conversion
```python
def move_to_uci(move):
    f = decode_from(move)
    t = decode_to(move)
    s = chr(f & 7 + ord('a')) + str((f >> 3) + 1)
    s += chr(t & 7 + ord('a')) + str((t >> 3) + 1)
    if is_promotion(move):
        s += {KNIGHT: 'n', BISHOP: 'b', ROOK: 'r', QUEEN: 'q'}[promo_piece_type(move)]
    return s

def parse_uci_move(board, uci_str):
    """Parse UCI string using board context to determine flags."""
    from_sq = (int(uci_str[1]) - 1) * 8 + (ord(uci_str[0]) - ord('a'))
    to_sq = (int(uci_str[3]) - 1) * 8 + (ord(uci_str[2]) - ord('a'))
    promo = {'n': KNIGHT, 'b': BISHOP, 'r': ROOK, 'q': QUEEN}.get(uci_str[4]) if len(uci_str) == 5 else None

    piece = board.squares[from_sq]
    pt = piece & 7
    is_cap = board.squares[to_sq] != EMPTY

    if pt == KING and abs((from_sq & 7) - (to_sq & 7)) == 2:
        return encode_move(from_sq, to_sq, CASTLE_KING if to_sq > from_sq else CASTLE_QUEEN)
    if pt == PAWN:
        if to_sq == board.ep_square:
            return encode_move(from_sq, to_sq, EP_CAPTURE)
        if abs((from_sq >> 3) - (to_sq >> 3)) == 2:
            return encode_move(from_sq, to_sq, DOUBLE_PAWN)
        if promo:
            base = (promo - KNIGHT) + (PROMO_KNIGHT_CAP if is_cap else PROMO_KNIGHT)
            return encode_move(from_sq, to_sq, base)
    return encode_move(from_sq, to_sq, CAPTURE if is_cap else QUIET)
```

---

## Board Representation (`board.py`)

### Board Class
```python
class Board:
    __slots__ = ('squares', 'turn', 'castling', 'ep_square',
                 'halfmove', 'fullmove', 'king_sq', 'history')

    def __init__(self, fen=None):
        if fen:
            self.set_fen(fen)
        else:
            self.set_fen("rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1")
```

### State
- `squares`: `list[int]` — 64 elements, piece encoding (0=empty)
- `turn`: `int` — WHITE(0) or BLACK(1)
- `castling`: `int` — bitmask (CASTLE_WK | CASTLE_WQ | CASTLE_BK | CASTLE_BQ)
- `ep_square`: `int` — en passant target square, or -1
- `halfmove`: `int` — halfmove clock (for 50-move rule)
- `fullmove`: `int` — fullmove counter
- `king_sq`: `list[int]` — [white_king_sq, black_king_sq]
- `history`: `list[tuple]` — undo stack for unmake

### FEN Parsing (`set_fen`) and Generation (`get_fen`)
- Parse FEN string → populate all board state
- Generate FEN string from current state
- `get_position_fen()` → FEN without halfmove/fullmove (for opening book + repetition)

### Make/Unmake Move
```python
def make_move(self, move):
    """Apply move, push undo info to history stack."""
    from_sq = decode_from(move)
    to_sq = decode_to(move)
    flags = decode_flags(move)
    captured = self.squares[to_sq]

    # Save undo state
    self.history.append((move, captured, self.castling, self.ep_square, self.halfmove))

    piece = self.squares[from_sq]
    self.squares[to_sq] = piece
    self.squares[from_sq] = EMPTY

    # En passant target
    self.ep_square = ((from_sq + to_sq) >> 1) if flags == DOUBLE_PAWN else -1

    # Special moves
    if flags == EP_CAPTURE:
        self.squares[to_sq + (-8 if self.turn == WHITE else 8)] = EMPTY
    elif flags == CASTLE_KING:
        r = 0 if self.turn == WHITE else 56
        self.squares[r + 5] = self.squares[r + 7]  # rook f1/f8
        self.squares[r + 7] = EMPTY
    elif flags == CASTLE_QUEEN:
        r = 0 if self.turn == WHITE else 56
        self.squares[r + 3] = self.squares[r + 0]  # rook d1/d8
        self.squares[r + 0] = EMPTY

    if is_promotion(move):
        self.squares[to_sq] = promo_piece_type(move) | (self.turn << 3)

    if (piece & 7) == KING:
        self.king_sq[self.turn] = to_sq

    # Castling rights update
    self.castling &= CASTLING_MASK[from_sq] & CASTLING_MASK[to_sq]

    # Halfmove clock
    if (piece & 7) == PAWN or is_capture(move):
        self.halfmove = 0
    else:
        self.halfmove += 1

    if self.turn == BLACK:
        self.fullmove += 1
    self.turn ^= 1

def unmake_move(self):
    """Pop last move from history, restore board state."""
    move, captured, castling, ep, halfmove = self.history.pop()
    self.turn ^= 1
    if self.turn == BLACK:
        self.fullmove -= 1

    from_sq = decode_from(move)
    to_sq = decode_to(move)
    flags = decode_flags(move)

    piece = self.squares[to_sq]
    if is_promotion(move):
        piece = PAWN | (self.turn << 3)
    self.squares[from_sq] = piece
    self.squares[to_sq] = captured

    if flags == EP_CAPTURE:
        victim_sq = to_sq + (-8 if self.turn == WHITE else 8)
        self.squares[victim_sq] = PAWN | ((self.turn ^ 1) << 3)
        self.squares[to_sq] = EMPTY
    elif flags == CASTLE_KING:
        r = 0 if self.turn == WHITE else 56
        self.squares[r + 7] = self.squares[r + 5]
        self.squares[r + 5] = EMPTY
    elif flags == CASTLE_QUEEN:
        r = 0 if self.turn == WHITE else 56
        self.squares[r + 0] = self.squares[r + 3]
        self.squares[r + 3] = EMPTY

    if (piece & 7) == KING:
        self.king_sq[self.turn] = from_sq

    self.castling = castling
    self.ep_square = ep
    self.halfmove = halfmove
```

### Attack Detection
```python
def is_attacked(self, sq, by_color):
    """Return True if sq is attacked by any piece of by_color."""
    # Check in order: pawns, knights, king, bishops/queens, rooks/queens
    # Uses pre-computed KNIGHT_MOVES, KING_MOVES, RAYS tables
    # For sliding pieces: walk rays, stop at first piece, check if matching type
    ...
```

### Game State Queries
```python
def is_in_check(self):
    return self.is_attacked(self.king_sq[self.turn], self.turn ^ 1)

def is_checkmate(self):
    return self.is_in_check() and len(generate_legal_moves(self)) == 0

def is_stalemate(self):
    return not self.is_in_check() and len(generate_legal_moves(self)) == 0

def is_insufficient_material(self):
    # K vs K, K+B vs K, K+N vs K
    ...

def is_fifty_move_draw(self):
    return self.halfmove >= 100
```

---

## Move Generation (`movegen.py`)

### Approach
1. Generate pseudo-legal moves (ignoring pins/check)
2. Filter: make each move, check if own king is attacked, unmake

```python
def generate_pseudo_legal(board):
    """Yield all pseudo-legal moves as encoded integers."""
    turn = board.turn
    own_color = turn
    enemy_color = turn ^ 1
    squares = board.squares

    for sq in range(64):
        piece = squares[sq]
        if piece == EMPTY or (piece >> 3) != own_color:
            continue
        pt = piece & 7
        if pt == PAWN:
            yield from _pawn_moves(board, sq, own_color)
        elif pt == KNIGHT:
            yield from _knight_moves(board, sq, own_color)
        elif pt == BISHOP:
            yield from _sliding_moves(board, sq, own_color, BISHOP_DIRS)
        elif pt == ROOK:
            yield from _sliding_moves(board, sq, own_color, ROOK_DIRS)
        elif pt == QUEEN:
            yield from _sliding_moves(board, sq, own_color, BISHOP_DIRS + ROOK_DIRS)
        elif pt == KING:
            yield from _king_moves(board, sq, own_color)
    yield from _castling_moves(board)

def generate_legal_moves(board):
    """Return list of legal moves."""
    moves = []
    for move in generate_pseudo_legal(board):
        board.make_move(move)
        if not board.is_attacked(board.king_sq[board.turn ^ 1], board.turn):
            moves.append(move)
        board.unmake_move()
    return moves
```

### Pawn Move Generation
```python
def _pawn_moves(board, sq, color):
    """Generate pawn pushes, double pushes, captures, en passant, promotions."""
    # White: forward = +8, start rank = 1, promo rank = 7
    # Black: forward = -8, start rank = 6, promo rank = 0
    # Single push: sq + forward (if empty)
    # Double push: sq + 2*forward (if both empty, on start rank)
    # Captures: sq + forward ± 1 (if enemy piece, with file bounds check)
    # En passant: if target == board.ep_square
    # Promotion: if target rank == promo rank, generate 4 promo moves instead
    ...
```

### Castling
```python
def _castling_moves(board):
    """Generate castling moves if legal."""
    # Kingside: king on e1/e8, squares f,g empty, king not in check,
    #           f,g not attacked, castling right available
    # Queenside: king on e1/e8, squares b,c,d empty, c,d not attacked,
    #            king not in check, castling right available
    ...
```

### Perft (Testing/Validation)
```python
def perft(board, depth):
    """Count leaf nodes at given depth. For validating move generation."""
    if depth == 0:
        return 1
    count = 0
    for move in generate_legal_moves(board):
        board.make_move(move)
        count += perft(board, depth - 1)
        board.unmake_move()
    return count
```

**Known Perft Values (starting position):**
| Depth | Nodes      |
|-------|------------|
| 1     | 20         |
| 2     | 400        |
| 3     | 8,902      |
| 4     | 197,281    |
| 5     | 4,865,609  |

**Kiwipete** (`r3k2r/p1ppqpb1/bn2pnp1/3PN3/1p2P3/2N2Q1p/PPPBBPPP/R3K2R w KQkq -`):
| Depth | Nodes   |
|-------|---------|
| 1     | 48      |
| 2     | 2,039   |
| 3     | 97,862  |

---

## Evaluation (`evaluation.py`)

### Material Values (centipawns)
| Piece  | Value |
|--------|-------|
| Pawn   | 100   |
| Knight | 320   |
| Bishop | 330   |
| Rook   | 500   |
| Queen  | 900   |
| King   | 20000 |

### Piece-Square Tables
Use the Simplified Evaluation Function tables (Tomasz Michniewski). One 64-element tuple per piece type, values in centipawns. Defined from white's perspective with a1=index 0.

For black: use `mirror(sq) = sq ^ 56` to flip rank.

**Pawn PST** — encourage center control and advancement:
```
  0,  0,  0,  0,  0,  0,  0,  0,    # rank 1
  5, 10, 10,-20,-20, 10, 10,  5,    # rank 2
  5, -5,-10,  0,  0,-10, -5,  5,    # rank 3
  0,  0,  0, 20, 20,  0,  0,  0,    # rank 4
  5,  5, 10, 25, 25, 10,  5,  5,    # rank 5
 10, 10, 20, 30, 30, 20, 10, 10,    # rank 6
 50, 50, 50, 50, 50, 50, 50, 50,    # rank 7
  0,  0,  0,  0,  0,  0,  0,  0,    # rank 8
```

**Knight PST** — encourage center, penalize edges:
```
-50,-40,-30,-30,-30,-30,-40,-50,
-40,-20,  0,  5,  5,  0,-20,-40,
-30,  5, 10, 15, 15, 10,  5,-30,
-30,  0, 15, 20, 20, 15,  0,-30,
-30,  5, 15, 20, 20, 15,  5,-30,
-30,  0, 10, 15, 15, 10,  0,-30,
-40,-20,  0,  0,  0,  0,-20,-40,
-50,-40,-30,-30,-30,-30,-40,-50,
```

**Bishop PST** — encourage long diagonals, penalize corners:
```
-20,-10,-10,-10,-10,-10,-10,-20,
-10,  5,  0,  0,  0,  0,  5,-10,
-10, 10, 10, 10, 10, 10, 10,-10,
-10,  0, 10, 10, 10, 10,  0,-10,
-10,  5,  5, 10, 10,  5,  5,-10,
-10,  0,  5, 10, 10,  5,  0,-10,
-10,  0,  0,  0,  0,  0,  0,-10,
-20,-10,-10,-10,-10,-10,-10,-20,
```

**Rook PST** — encourage 7th rank and open files:
```
  0,  0,  0,  5,  5,  0,  0,  0,
 -5,  0,  0,  0,  0,  0,  0, -5,
 -5,  0,  0,  0,  0,  0,  0, -5,
 -5,  0,  0,  0,  0,  0,  0, -5,
 -5,  0,  0,  0,  0,  0,  0, -5,
 -5,  0,  0,  0,  0,  0,  0, -5,
  5, 10, 10, 10, 10, 10, 10,  5,
  0,  0,  0,  0,  0,  0,  0,  0,
```

**Queen PST** — slight center preference, avoid early development:
```
-20,-10,-10, -5, -5,-10,-10,-20,
-10,  0,  5,  0,  0,  0,  0,-10,
-10,  5,  5,  5,  5,  5,  0,-10,
  0,  0,  5,  5,  5,  5,  0, -5,
 -5,  0,  5,  5,  5,  5,  0, -5,
-10,  0,  5,  5,  5,  5,  0,-10,
-10,  0,  0,  0,  0,  0,  0,-10,
-20,-10,-10, -5, -5,-10,-10,-20,
```

**King PST (middlegame)** — encourage castled position, penalize center:
```
 20, 30, 10,  0,  0, 10, 30, 20,
 20, 20,  0,  0,  0,  0, 20, 20,
-10,-20,-20,-20,-20,-20,-20,-10,
-20,-30,-30,-40,-40,-30,-30,-20,
-30,-40,-40,-50,-50,-40,-40,-30,
-30,-40,-40,-50,-50,-40,-40,-30,
-30,-40,-40,-50,-50,-40,-40,-30,
-30,-40,-40,-50,-50,-40,-40,-30,
```

### evaluate() Function
```python
MATE_SCORE = 100000

def evaluate(board) -> int:
    """Return eval in centipawns from side-to-move perspective."""
    score = 0  # from white's perspective
    for sq in range(64):
        piece = board.squares[sq]
        if piece == EMPTY:
            continue
        pt = piece & 7
        color = piece >> 3
        val = PIECE_VALUES[pt] + PST[pt][sq if color == WHITE else sq ^ 56]
        if color == WHITE:
            score += val
        else:
            score -= val
    return score if board.turn == WHITE else -score
```

---

## Search (`search.py`)

### Negamax with Alpha-Beta
```python
def negamax(board, depth, alpha, beta, killer_moves, deadline):
    if time.time() > deadline:
        raise TimeoutError

    if board.is_fifty_move_draw() or board.is_repetition():
        return 0

    legal_moves = generate_legal_moves(board)
    if len(legal_moves) == 0:
        if board.is_in_check():
            return -MATE_SCORE + board.ply()  # prefer shorter mates
        return 0  # stalemate

    if depth == 0:
        return quiescence(board, alpha, beta, deadline)

    order_moves(legal_moves, board, killer_moves, depth)

    for move in legal_moves:
        board.make_move(move)
        score = -negamax(board, depth - 1, -beta, -alpha, killer_moves, deadline)
        board.unmake_move()
        if score >= beta:
            if not is_capture(move):
                update_killers(killer_moves, move, depth)
            return beta
        if score > alpha:
            alpha = score
    return alpha
```

### Quiescence Search
```python
def quiescence(board, alpha, beta, deadline):
    stand_pat = evaluate(board)
    if stand_pat >= beta:
        return beta
    if stand_pat > alpha:
        alpha = stand_pat

    captures = generate_legal_captures(board)
    order_captures(captures, board)

    for move in captures:
        board.make_move(move)
        score = -quiescence(board, -beta, -alpha, deadline)
        board.unmake_move()
        if score >= beta:
            return beta
        if score > alpha:
            alpha = score
    return alpha
```

### Iterative Deepening
```python
MAX_DEPTH = 64

def search(board, time_limit):
    best_move = None
    deadline = time.time() + time_limit
    killer_moves = [[None, None] for _ in range(MAX_DEPTH)]

    for depth in range(1, MAX_DEPTH + 1):
        try:
            score, move = negamax_root(board, depth, killer_moves, deadline)
            if move is not None:
                best_move = move
        except TimeoutError:
            break
        elapsed = time.time() - start
        if time.time() + elapsed > deadline:
            break  # not enough time for next depth
    return best_move
```

### Time Management
```python
time_for_move = remaining_time / 30 + increment * 0.8
time_for_move = min(time_for_move, remaining_time / 3)
```

---

## Move Ordering (`move_ordering.py`)

### Priority
1. **Captures** — sorted by MVV-LVA (Most Valuable Victim - Least Valuable Attacker)
2. **Killer moves** (2 per depth) — non-captures that caused beta cutoff at same depth
3. **Remaining quiet moves**

### MVV-LVA
```python
# Score = victim_value * 10 - attacker_value
# Higher score = better capture to try first
# PxQ = 900*10 - 100 = 8900 (great)
# QxP = 100*10 - 900 = 100  (poor)
```

### Killer Moves
```python
# killer_moves[depth] = [move1, move2]
# On beta cutoff for non-capture: shift [0] → [1], insert new at [0]
```

---

## Opening Book (`opening_book.py`)

Hardcoded dict: position FEN (without clocks) → list of UCI move strings.
Include ~20-30 common opening positions.

### Included Openings (White)
- **Italian Game**: 1.e4 e5 2.Nf3 Nc6 3.Bc4
- **Ruy Lopez**: 1.e4 e5 2.Nf3 Nc6 3.Bb5
- **Queen's Gambit**: 1.d4 d5 2.c4
- **London System**: 1.d4 d5 2.Nf3 Nf6 3.Bf4

### Included Openings (Black)
- **Sicilian Defense**: 1.e4 c5
- **French Defense**: 1.e4 e6
- **King's Indian Defense**: 1.d4 Nf6 2.c4 g6
- **Slav Defense**: 1.d4 d5 2.c4 c6

### Book Lookup
```python
def get_book_move(board):
    key = board.get_position_fen()
    if key in OPENING_BOOK:
        uci_str = random.choice(OPENING_BOOK[key])
        move = parse_uci_move(board, uci_str)
        if move in generate_legal_moves(board):
            return move
    return None
```

---

## UCI Protocol (`uci.py`)

Minimal implementation supporting:
```
→ uci
← id name ChessEngine
← id author chess_test
← uciok

→ isready
← readyok

→ position startpos
→ position startpos moves e2e4 e7e5
→ position fen <fen>
→ position fen <fen> moves e2e4

→ go wtime 300000 btime 300000 winc 0 binc 0
→ go depth 6
→ go movetime 5000
← bestmove e2e4

→ ucinewgame
→ quit
```

The UCI handler creates a `Board`, applies moves via `parse_uci_move`, calls `search()` or `get_book_move()`, and outputs `bestmove`.

---

## Draw Detection

### Repetition
Track position hashes in a list. A position is a draw if it has occurred 3 times. For simplicity, use `board.get_position_fen()` as the hash key. Store in `board.position_history`.

### 50-Move Rule
`board.halfmove >= 100` → draw.

### Insufficient Material
K vs K, K+N vs K, K+B vs K → draw.
