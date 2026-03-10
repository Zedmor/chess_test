# Roadmap

## Phase 1: Core Data Structures
Board representation + evaluation function. Two parallel tasks.

**Duration**: ~20 min per engineer (parallel)

### Tasks
1. **TASK-1**: `src/board.py` + `tests/test_board.py` — Board class, piece constants, FEN parsing, make_move, copy
2. **TASK-2**: `src/evaluation.py` + `tests/test_evaluation.py` — Material values, PST tables, evaluate()

**Milestone**: FEN round-trips work, evaluation of starting position ≈ 0

---

## Phase 2: Move Generation + Search Framework
Complete move generation and alpha-beta search. Two parallel tasks.

**Duration**: ~25 min per engineer (parallel)
**Depends on**: Phase 1 (both tasks merged to main)

### Tasks
3. **TASK-3**: `src/moves.py` + `tests/test_moves.py` — All pseudo-legal move generation, attack detection, legal move filtering
4. **TASK-4**: `src/search.py` + `tests/test_search.py` — Negamax alpha-beta, quiescence search, move ordering, iterative deepening, time management

**Milestone**: Legal move generation passes perft(1) for starting position (20 moves). Search finds mate-in-1.

---

## Phase 3: UCI Protocol + Perft Testing
Wire everything together with UCI. Two parallel tasks.

**Duration**: ~20 min per engineer (parallel)
**Depends on**: Phase 2 (both tasks merged to main)

### Tasks
5. **TASK-5**: `src/uci.py` + `main.py` — UCI protocol loop, position/go/bestmove handling, move format conversion
6. **TASK-6**: `tests/test_perft.py` — Perft test suite for move generation correctness (starting pos, kiwipete, other standard positions)

**Milestone**: Engine responds to UCI commands. Perft results match known values.

---

## Phase 4: Integration Testing & Bug Fixes
End-to-end testing, fix move generation bugs found by perft, test edge cases.

**Duration**: ~20 min per engineer (parallel)
**Depends on**: Phase 3

### Tasks
7. **TASK-7**: Full game playthrough testing — play complete games via UCI, test checkmate/stalemate/draw detection, fix bugs
8. **TASK-8**: Edge case testing — promotion in all variants, en passant edge cases, castling through/out of check, 50-move rule

**Milestone**: Engine plays complete legal games without crashing or illegal moves.

---

## Phase 5: Optimization & Tuning
Only if not hitting 50% winrate vs Stockfish 1200.

**Duration**: ~15 min per engineer
**Depends on**: Phase 4

### Tasks
9. **TASK-9**: Transposition table (simple dict with Zobrist hashing)
10. **TASK-10**: Move ordering improvements (killer moves, history heuristic)
11. **TASK-11**: Time management tuning, PST value tuning

**Milestone**: ≥50% winrate vs Stockfish 1200 in 10-game match.
