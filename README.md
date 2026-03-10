# Chess Engine

A pure Python chess engine built entirely from scratch with **zero external dependencies**. Achieves a **70% winrate against Stockfish at 1200 ELO**.

## Performance

```
Playing 10 games vs Stockfish 1200 ELO (0.5s/move)
--------------------------------------------------
Result: 6W 2L 2D — 70.0% winrate
Target was >= 50%. Exceeded by 20 points.
```

## Features

- **Board Representation**: 64-element array with make/unmake move stack, FEN parsing, attack detection, draw detection (repetition, 50-move rule, insufficient material)
- **Move Generation**: Pseudo-legal generation with legality filtering. Perft-validated against known values (starting position depth 4: 197,281 nodes; Kiwipete depth 3: 97,862 nodes)
- **Evaluation**: Material counting + Piece-Square Tables (Simplified Evaluation Function by Tomasz Michniewski)
- **Search**: Negamax with alpha-beta pruning, quiescence search, iterative deepening, time management
- **Move Ordering**: MVV-LVA (Most Valuable Victim - Least Valuable Attacker) for captures, killer move heuristic for quiet moves
- **Opening Book**: 30 hardcoded positions covering Italian Game, Ruy Lopez, Queen's Gambit, London System, Sicilian Defense, French Defense, King's Indian, and Slav Defense
- **UCI Protocol**: Full UCI support — works with any UCI-compatible GUI (Arena, CuteChess, etc.)

## Quick Start

```bash
# Run the engine (UCI mode)
python main.py

# Run all tests (242 tests)
python -m pytest tests/ -v

# Play against Stockfish (requires Stockfish installed)
python scripts/stockfish_match.py --games 20 --elo 1200 --time 1.0
```

### UCI Commands

```
uci                          → engine identification
isready                      → readyok
position startpos            → set starting position
position startpos moves e2e4 → apply moves
position fen <fen>           → set position from FEN
go movetime 5000             → search for 5 seconds
go wtime 300000 btime 300000 → search with clock
go depth 6                   → search to fixed depth
quit                         → exit
```

## Project Structure

```
chess_test/
├── src/
│   ├── constants.py      # Piece/square encoding, move encoding, pre-computed tables
│   ├── board.py          # Board state, make/unmake, FEN, attack detection
│   ├── movegen.py        # Legal move generation, perft
│   ├── evaluation.py     # Material + PST evaluation
│   ├── search.py         # Alpha-beta, quiescence, iterative deepening
│   ├── move_ordering.py  # MVV-LVA, killer moves
│   ├── opening_book.py   # Hardcoded opening book (30 positions)
│   └── uci.py            # UCI protocol handler
├── tests/                # 242 tests across 9 test files
├── scripts/
│   └── stockfish_match.py  # Automated Stockfish match runner
├── main.py               # Entry point
└── planning/
    ├── architecture.md   # Technical design specification
    └── roadmap.md        # Development phases and status
```

**~4,900 lines of code** (1,540 engine + 3,130 tests + 190 match script).

## How It Was Built: Multi-Agent Development with Batty

This engine was built in a single session using [Batty](https://github.com/battysh/batty), a multi-agent orchestration tool that coordinates multiple Claude Code instances working in parallel via git worktrees.

### The Team

| Role | Agent | Responsibility |
|------|-------|----------------|
| **Architect** | `architect` | Owned the roadmap and architecture. Defined phases, milestones, success criteria. Directed the manager. Never wrote code. |
| **Manager** | `manager` | Owned the kanban board. Broke directives into tasks, wrote specs, assigned work to engineers, reviewed and merged code. Never wrote code. |
| **Engineer 1** | `eng-1-1` | Wrote code in a git worktree. Implemented constants, evaluation, movegen, search, integration tests, match runner. |
| **Engineer 2** | `eng-1-2` | Wrote code in a separate git worktree. Implemented board, board tests, move ordering, opening book, UCI protocol. |

### How It Works

Batty uses a **Maildir-style inbox system** for inter-agent communication. Each agent runs as an independent Claude Code instance with its own context. They communicate via `batty send <role> "<message>"` and check their inbox for new messages.

The engineers work in **isolated git worktrees** — parallel branches that share the same repo but have independent working directories. This allows two engineers to write code simultaneously without merge conflicts. The manager merges completed work to `main` when tests pass.

### Development Phases

The project was completed in 5 phases, with parallelism wherever possible:

```
Phase 1: Board Representation
  └── constants.py (eng-1-1) → board.py + tests (eng-1-2)

Phase 2: Three tasks in parallel
  ├── movegen.py (eng-1-1) ─── critical path
  ├── evaluation.py (eng-1-1, then eng-1-2)
  └── move_ordering.py (eng-1-2)

Phase 3: Search Engine
  └── search.py (eng-1-1)

Phase 4: Two tasks in parallel
  ├── opening_book.py (eng-1-2) ─── started early, independent
  └── uci.py (eng-1-2)

Phase 5: Integration + Match
  ├── match runner (eng-1-1)
  └── integration tests (eng-1-1)
```

### Key Decisions Made During Development

- **Early parallelism**: Opening book was pulled forward from Phase 4 into Phase 3 since it only depended on `board.py`, not on `search.py`. This kept both engineers busy.
- **Fast course correction**: The first evaluation module (eng-1-1) used `python-chess` — an external dependency that violated the zero-dependencies constraint. It was caught, reverted, and rewritten from scratch using the correct encoding.
- **Stale code cleanup**: Move ordering was written early with tuple-based moves instead of 16-bit encoded moves. It was identified as stale, removed, and rewritten from scratch.
- **Match runner independence**: The Stockfish match runner was developed in parallel with UCI by testing with Stockfish-vs-Stockfish games first, then swapping in our engine after UCI merged.

## Technical Details

### Move Encoding

Moves are packed into 16-bit integers for efficiency:
- Bits 0-5: source square (0-63)
- Bits 6-11: target square (0-63)
- Bits 12-15: flags (quiet, capture, castling, en passant, promotion variants)

### Piece Encoding

Pieces are integers where `piece_type = p & 7` and `piece_color = p >> 3`:
- White pieces: 1-6 (pawn through king)
- Black pieces: 9-14

### Search Algorithm

```
Iterative Deepening
  └── Negamax + Alpha-Beta Pruning
        ├── Move Ordering (MVV-LVA + Killer Moves)
        ├── Quiescence Search (captures only)
        └── Draw Detection (repetition, 50-move, insufficient material)
```

## Test Coverage

| Module | Tests | Key Validations |
|--------|-------|-----------------|
| Board | 67 | FEN roundtrip, make/unmake all move types, attack detection, draw rules |
| Movegen | 41 | Perft at depth 4, Kiwipete, all piece types, edge cases |
| Search | 27 | Mate-in-1, mate-in-2, quiescence, draw detection, board integrity |
| UCI | 31 | Protocol commands, time management, position parsing, book integration |
| Integration | 29 | Self-play, checkmate/stalemate/draw, book-to-search transition |
| Evaluation | 13 | Material balance, PST, side-to-move perspective |
| Opening Book | 20 | All 8 opening lines, FEN-based lookup, legal move validation |
| Move Ordering | 14 | MVV-LVA scoring, killer moves, in-place sort |

## License

MIT
