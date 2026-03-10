"""Alpha-beta search with quiescence, iterative deepening, and time management."""

from __future__ import annotations

import time

from src.constants import is_capture
from src.board import Board
from src.evaluation import MATE_SCORE, evaluate
from src.movegen import generate_legal_moves, generate_legal_captures
from src.move_ordering import (
    create_killer_table,
    update_killers,
    order_moves,
    order_captures,
)

MAX_DEPTH: int = 64


class SearchTimeout(Exception):
    """Raised when search time limit is reached."""


def quiescence(
    board: Board, alpha: int, beta: int, deadline: float
) -> int:
    """Quiescence search: evaluate captures until position is quiet."""
    if time.time() > deadline:
        raise SearchTimeout

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


def _ply(board: Board) -> int:
    """Return the current ply (half-move depth from root)."""
    return len(board.history)


def negamax(
    board: Board,
    depth: int,
    alpha: int,
    beta: int,
    killer_moves: list,
    deadline: float,
    root_ply: int,
) -> int:
    """Negamax with alpha-beta pruning."""
    if time.time() > deadline:
        raise SearchTimeout

    if board.is_fifty_move_draw() or board.is_repetition():
        return 0

    legal_moves = generate_legal_moves(board)
    if len(legal_moves) == 0:
        if board.is_in_check():
            return -MATE_SCORE + (_ply(board) - root_ply)
        return 0  # stalemate

    if depth == 0:
        return quiescence(board, alpha, beta, deadline)

    order_moves(legal_moves, board, killer_moves, depth)

    for move in legal_moves:
        board.make_move(move)
        score = -negamax(
            board, depth - 1, -beta, -alpha, killer_moves, deadline, root_ply
        )
        board.unmake_move()
        if score >= beta:
            if not is_capture(move):
                update_killers(killer_moves, move, depth)
            return beta
        if score > alpha:
            alpha = score
    return alpha


def negamax_root(
    board: Board,
    depth: int,
    killer_moves: list,
    deadline: float,
) -> tuple[int, int | None]:
    """Root-level negamax returning (score, best_move)."""
    root_ply = _ply(board)
    legal_moves = generate_legal_moves(board)
    if not legal_moves:
        if board.is_in_check():
            return -MATE_SCORE, None
        return 0, None

    order_moves(legal_moves, board, killer_moves, depth)

    best_score = -MATE_SCORE - 1
    best_move: int | None = None
    alpha = -MATE_SCORE - 1
    beta = MATE_SCORE + 1

    for move in legal_moves:
        board.make_move(move)
        score = -negamax(
            board, depth - 1, -beta, -alpha, killer_moves, deadline, root_ply
        )
        board.unmake_move()
        if score > best_score:
            best_score = score
            best_move = move
        if score > alpha:
            alpha = score
    return best_score, best_move


def search(board: Board, time_limit: float) -> int:
    """Iterative deepening search. Returns the best encoded move."""
    best_move: int | None = None
    start = time.time()
    deadline = start + time_limit
    killer_moves = create_killer_table()
    hist_len = len(board.history)

    for depth in range(1, MAX_DEPTH + 1):
        try:
            score, move = negamax_root(board, depth, killer_moves, deadline)
            if move is not None:
                best_move = move
        except SearchTimeout:
            # Unwind any partial moves left on the board
            while len(board.history) > hist_len:
                board.unmake_move()
            break

        elapsed = time.time() - start
        remaining = time_limit - elapsed
        if remaining < elapsed:
            break  # not enough time for next iteration

    if best_move is None:
        legal_moves = generate_legal_moves(board)
        if legal_moves:
            best_move = legal_moves[0]
    return best_move  # type: ignore[return-value]
