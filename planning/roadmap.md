# Roadmap

## Phase 1: Board Representation — DONE (constants), IN PROGRESS (board)
Foundation — everything depends on this.

**Status**: constants.py is complete and merged to main. board.py + test_board.py is in progress (eng-1-2).

### Tasks
1. **TASK-1**: `src/constants.py` — DONE. Merged to main.
2. **TASK-2**: `src/board.py` + `tests/test_board.py` — IN PROGRESS (eng-1-2). Board class with FEN, make/unmake, is_attacked, game state queries, position history.

**Milestone**: Board loads FEN, makes/unmakes moves correctly, detects attacks. FEN roundtrip test passes. Make/unmake with no corruption.

---

## Phase 2: Move Generation + Evaluation + Move Ordering (parallel after Phase 1)
Once board.py is merged, three tasks can run concurrently. Evaluation and move ordering depend only on constants.py + board.py — they do NOT need movegen. This allows maximum parallelism.

### Tasks (assign as soon as board.py is merged)
3. **TASK-3**: `src/movegen.py` + `tests/test_movegen.py` — Pseudo-legal move generation (pawn pushes/captures/EP/promotion, knight, bishop, rook, queen, king, castling), legal move filtering, perft function, `generate_legal_captures()`. Tests MUST include perft validation against known values (starting position depth 1-4, Kiwipete depth 1-3). **CRITICAL PATH** — search depends on this.
4. **TASK-4**: `src/evaluation.py` + `tests/test_evaluation.py` — Material values, PST tables, evaluate() returning centipawns from side-to-move perspective. Can use encode_move for test setup without movegen.
5. **TASK-5**: `src/move_ordering.py` + `tests/test_move_ordering.py` — MVV-LVA capture scoring, killer move storage, order_moves and order_captures functions. Can use encode_move for test setup without movegen.

**Assignment strategy**: eng-1-1 gets movegen (critical path, largest task). eng-1-2 gets evaluation, then move_ordering sequentially (both are small).

**Milestone**: Perft matches depth 4 starting position (197,281 nodes). Evaluation ~0 for starting position. Captures sorted by MVV-LVA.

---

## Phase 3: Search Engine
Depends on movegen + evaluation + move_ordering all being merged.

### Tasks
6. **TASK-6**: `src/search.py` + `tests/test_search.py` — Negamax alpha-beta, quiescence search, iterative deepening, time management.

**Milestone**: Engine finds mate-in-1 and mate-in-2. Search reaches depth 4-5 in reasonable time (<5s).

---

## Phase 4: Opening Book + UCI Protocol (parallel)
Two parallel tasks. Depends on search being merged.

### Tasks
7. **TASK-7**: `src/opening_book.py` + `tests/test_opening_book.py` — Hardcoded opening book (20-30 positions), book lookup function
8. **TASK-8**: `src/uci.py` + `main.py` + `tests/test_uci.py` — UCI protocol loop, position/go/bestmove handling, book + search integration

**Milestone**: Engine responds correctly to UCI commands. Book moves returned for known positions. `python main.py` starts the engine.

---

## Phase 5: Integration Testing + Stockfish Match
Full system testing and performance measurement.

### Tasks
9. **TASK-9**: Full game integration testing — play complete games via UCI, verify checkmate/stalemate/draw detection, fix bugs found
10. **TASK-10**: Stockfish match — configure Stockfish at ~1200 ELO, play 20+ games, measure winrate. Target: ≥50%.

**Milestone**: Engine plays complete legal games. ≥50% winrate vs Stockfish ~1200 ELO.

---

## Phase 6: Optimization (if needed)
Only if not hitting 50% winrate target.

### Tasks
11. **TASK-11**: Transposition table (simple dict with Zobrist hashing)
12. **TASK-12**: Search improvements (null move pruning, late move reductions)
13. **TASK-13**: Evaluation improvements (mobility, pawn structure, king safety)

**Milestone**: ≥50% winrate vs Stockfish 1200 in 20-game match.
