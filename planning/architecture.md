# Chess Engine Architecture

## Overview
Minimal Python chess engine targeting ≥50% winrate vs Stockfish 1200 ELO. No external chess libraries. Pure Python with standard library only.

## Tech Stack
- Python 3.10+ (standard library only)
- pytest for testing
- UCI protocol for engine communication

## File Structure
```
chess_test/
├── src/
│   ├── __init__.py
│   ├── board.py          # Board representation, FEN, make_move
│   ├── moves.py          # Move generation, attack detection
│   ├── evaluation.py     # Material + piece-square table evaluation
│   ├── search.py         # Alpha-beta, quiescence, iterative deepening
│   └── uci.py            # UCI protocol handler
├── main.py               # Entry point: python main.py
├── tests/
│   ├── __init__.py
│   ├── test_board.py
│   ├── test_moves.py
│   ├── test_evaluation.py
│   ├── test_search.py
│   └── test_perft.py
├── planning/
│   ├── architecture.md
│   └── roadmap.md
└── CLAUDE.md
```

## Core Design Decisions

### Piece Encoding
Integer constants. White positive, black negative:
```python
EMPTY = 0
W_PAWN, W_KNIGHT, W_BISHOP, W_ROOK, W_QUEEN, W_KING = 1, 2, 3, 4, 5, 6
B_PAWN, B_KNIGHT, B_BISHOP, B_ROOK, B_QUEEN, B_KING = -1, -2, -3, -4, -5, -6
WHITE, BLACK = 0, 1
```

Helpers:
- `piece_color(piece)`: WHITE if piece > 0, BLACK if piece < 0
- `piece_type(piece)`: abs(piece)

### Board Representation
- Mailbox: 64-element `list[int]`
- Index mapping: `sq = rank * 8 + file` where a1=0, b1=1, ..., h1=7, a2=8, ..., h8=63
- `sq_rank(sq) = sq // 8`, `sq_file(sq) = sq % 8`
- `sq_to_alg(sq)`: e.g., 0 → "a1", 63 → "h8"
- `alg_to_sq(s)`: e.g., "e2" → 12

### Move Representation
Tuple: `(from_sq: int, to_sq: int, promo: int)`
- `promo = 0` for normal moves
- `promo = piece_type` for promotions (e.g., 5 for queen, 2 for knight). Color inferred from moving side.

Special move detection (inferred from board state, not encoded):
- **Castling**: king moves exactly 2 files (`abs(to_file - from_file) == 2` and piece is king)
- **En passant**: pawn captures diagonally to `board.ep_square`
- **Promotion**: `promo != 0`

### Board State
```python
class Board:
    squares: list[int]       # 64 elements
    side_to_move: int        # WHITE or BLACK
    castling: int            # 4-bit bitmask: K=1, Q=2, k=4, q=8
    ep_square: int           # target square or -1 if none
    halfmove: int            # halfmove clock (for 50-move rule)
    fullmove: int            # fullmove number
```

### Castling Rights Bitmask
```python
CASTLING_WK = 1   # White kingside  (K)
CASTLING_WQ = 2   # White queenside (Q)
CASTLING_BK = 4   # Black kingside  (k)
CASTLING_BQ = 8   # Black queenside (q)
```

### make_move(move)
Mutates board in-place. Steps:
1. Identify piece at from_sq, captured piece at to_sq
2. Move piece (clear from_sq, place on to_sq)
3. **Castling**: if king moves 2 files, also move the corresponding rook:
   - White kingside: rook h1(7) → f1(5)
   - White queenside: rook a1(0) → d1(3)
   - Black kingside: rook h8(63) → f8(61)
   - Black queenside: rook a8(56) → d8(59)
4. **En passant**: if pawn lands on ep_square, remove captured pawn from `to_sq + (-8 if white, +8 if black)`
5. **Promotion**: replace piece with `promo * (1 if white, -1 if black)`
6. **Update castling rights**: clear relevant bits when king/rook moves or rook square is captured:
   - sq 0 (a1) → clear CASTLING_WQ
   - sq 7 (h1) → clear CASTLING_WK
   - sq 4 (e1) → clear CASTLING_WK | CASTLING_WQ
   - sq 56 (a8) → clear CASTLING_BQ
   - sq 63 (h8) → clear CASTLING_BK
   - sq 60 (e8) → clear CASTLING_BK | CASTLING_BQ
7. **Set ep_square**: if pawn double-push (rank diff == 2), set to skipped square; else -1
8. **Halfmove**: reset to 0 on pawn move or capture, else increment
9. If BLACK just moved, increment fullmove
10. Toggle side_to_move

### Copy-Make Strategy
Search uses copy-make: `new_board = board.copy(); new_board.make_move(move)`. No unmake needed. `Board.copy()` shallow-copies the squares list and copies all scalar state fields.

## Move Generation

### Pseudo-Legal Generation
Generate all moves without checking if own king is left in check.

**Pawns** (most complex):
- Single push: +8 for white, -8 for black (target must be empty)
- Double push: from rank 1 (white) or rank 6 (black), both intermediate and target squares must be empty
- Captures: diagonal ±1 file, must have enemy piece or be ep_square
- Promotion: when reaching rank 7 (white) or rank 0 (black), generate 4 moves (Q=5, R=4, B=3, N=2)

**Knights**: 8 offsets from sq: +17, +15, +10, +6, -6, -10, -15, -17. Validate target is on board (0-63) and file distance ≤ 2. Must not land on own piece.

**King**: 8 offsets: +1, -1, +8, -8, +9, +7, -9, -7. Validate on board and file distance ≤ 1. Must not land on own piece. Plus castling (separate logic).

**Sliding pieces** (Bishop, Rook, Queen):
- Bishop directions: +9, +7, -9, -7
- Rook directions: +1, -1, +8, -8
- Queen: all 8 directions
- Slide in each direction until: board edge (file wraps or rank out of range), friendly piece (stop before), enemy piece (capture and stop)
- **Critical**: detect file wrap — when moving ±1, ±7, ±9, check that file changes by exactly 1 per step

**Castling** conditions (e.g., white kingside):
1. `castling & CASTLING_WK` is set
2. Squares f1(5) and g1(6) are empty
3. King (e1=4) is not in check
4. Squares f1(5) and g1(6) are not attacked by black
5. Generate move (4, 6, 0)

### Legal Move Generation
```python
def generate_legal_moves(board):
    moves = generate_pseudo_legal_moves(board)
    legal = []
    for move in moves:
        new_board = board.copy()
        new_board.make_move(move)
        if not is_in_check(new_board, board.side_to_move):
            legal.append(move)
    return legal
```

### Attack Detection
```python
def is_square_attacked(board, sq, by_color):
    """Check if any piece of by_color attacks sq."""
    # Check pawn attacks (reverse direction)
    # Check knight attacks (same offsets)
    # Check king attacks (same offsets)
    # Check sliding attacks: bishop/queen on diagonals, rook/queen on ranks/files
```

## Evaluation

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
Use the Simplified Evaluation Function tables (Tomasz Michniewski). One 64-element array per piece type, values in centipawns, defined from white's perspective with a1=index 0.

For black pieces, mirror vertically: `mirror_sq = sq ^ 56` (flips rank 0↔7, 1↔6, etc.)

**Pawn PST** — encourage center control and advancement:
```
  0,  0,  0,  0,  0,  0,  0,  0,    # rank 1 (never occupied)
  5, 10, 10,-20,-20, 10, 10,  5,    # rank 2
  5, -5,-10,  0,  0,-10, -5,  5,    # rank 3
  0,  0,  0, 20, 20,  0,  0,  0,    # rank 4
  5,  5, 10, 25, 25, 10,  5,  5,    # rank 5
 10, 10, 20, 30, 30, 20, 10, 10,    # rank 6
 50, 50, 50, 50, 50, 50, 50, 50,    # rank 7
  0,  0,  0,  0,  0,  0,  0,  0,    # rank 8 (never occupied)
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

### evaluate(board) → int
```python
def evaluate(board):
    score = 0  # from white's perspective
    for sq in range(64):
        piece = board.squares[sq]
        if piece > 0:   # white
            score += PIECE_VALUES[piece] + PST[piece][sq]
        elif piece < 0:  # black
            score -= PIECE_VALUES[-piece] + PST[-piece][sq ^ 56]
    # Return from side-to-move perspective (for negamax)
    return score if board.side_to_move == WHITE else -score
```

## Search

### Negamax with Alpha-Beta
```python
def negamax(board, depth, alpha, beta):
    if depth == 0:
        return quiescence(board, alpha, beta)

    moves = generate_legal_moves(board)
    if not moves:
        if is_in_check(board, board.side_to_move):
            return -MATE_SCORE  # checkmate
        return 0  # stalemate

    order_moves(moves, board)

    for move in moves:
        new_board = board.copy()
        new_board.make_move(move)
        score = -negamax(new_board, depth - 1, -beta, -alpha)
        if score >= beta:
            return beta  # beta cutoff
        if score > alpha:
            alpha = score
    return alpha
```

### Quiescence Search
Only search captures to avoid horizon effect:
```python
def quiescence(board, alpha, beta):
    stand_pat = evaluate(board)
    if stand_pat >= beta:
        return beta
    if stand_pat > alpha:
        alpha = stand_pat

    captures = get_capture_moves(board)
    order_moves(captures, board)

    for move in captures:
        new_board = board.copy()
        new_board.make_move(move)
        score = -quiescence(new_board, -beta, -alpha)
        if score >= beta:
            return beta
        if score > alpha:
            alpha = score
    return alpha
```

### Move Ordering (MVV-LVA)
Most Valuable Victim - Least Valuable Attacker:
```python
score = PIECE_VALUES[abs(captured)] * 10 - PIECE_VALUES[abs(attacker)]
```
Sort captures descending by score. Captures come before non-captures.

### Iterative Deepening
```python
def search(board, time_limit):
    best_move = None
    start = time.time()
    for depth in range(1, MAX_DEPTH + 1):
        score, move = negamax_root(board, depth)
        if move:
            best_move = move
        if time.time() - start > time_limit * 0.5:
            break  # not enough time for next depth
    return best_move
```

### Time Management
```python
time_for_move = remaining_time / 30 + increment * 0.8
# Never use more than remaining_time / 3
time_for_move = min(time_for_move, remaining_time / 3)
```

## UCI Protocol

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

Move format: UCI long algebraic — `e2e4`, `e7e8q` (promotion).

### Move ↔ UCI Conversion
```python
def move_to_uci(move):
    s = sq_to_alg(move[0]) + sq_to_alg(move[1])
    if move[2]:  # promotion
        s += "nbrq"[move[2] - 2]  # 2=N, 3=B, 4=R, 5=Q
    return s

def uci_to_move(board, uci_str):
    from_sq = alg_to_sq(uci_str[0:2])
    to_sq = alg_to_sq(uci_str[2:4])
    promo = 0
    if len(uci_str) == 5:
        promo = "nbrq".index(uci_str[4]) + 2
    return (from_sq, to_sq, promo)
```
