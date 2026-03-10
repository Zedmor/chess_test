"""UCI protocol handler for the chess engine."""

from __future__ import annotations

import sys

from src.board import Board
from src.constants import move_to_uci, parse_uci_move
from src.movegen import generate_legal_moves
from src.opening_book import get_book_move
from src.search import search


ENGINE_NAME: str = "ChessEngine"
ENGINE_AUTHOR: str = "chess_test"


def _calculate_time(
    board: Board,
    wtime: int | None,
    btime: int | None,
    winc: int | None,
    binc: int | None,
    movetime: int | None,
    depth: int | None,
) -> tuple[float, int | None]:
    """Return (time_limit_seconds, max_depth_or_None)."""
    if movetime is not None:
        return movetime / 1000.0, None
    if depth is not None:
        return 300.0, depth
    if wtime is None and btime is None:
        return 5.0, None

    if board.turn == 0:  # WHITE
        remaining = (wtime or 0) / 1000.0
        inc = (winc or 0) / 1000.0
    else:
        remaining = (btime or 0) / 1000.0
        inc = (binc or 0) / 1000.0

    time_for_move = remaining / 30.0 + inc * 0.8
    time_for_move = min(time_for_move, remaining / 3.0)
    time_for_move = max(time_for_move, 0.05)
    return time_for_move, None


def _handle_position(tokens: list[str], board: Board) -> None:
    """Handle 'position' command: set up board and apply moves."""
    idx = 1
    if idx < len(tokens) and tokens[idx] == "startpos":
        board.set_fen(
            "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"
        )
        board.history.clear()
        board.position_history.clear()
        idx += 1
    elif idx < len(tokens) and tokens[idx] == "fen":
        idx += 1
        fen_parts: list[str] = []
        while idx < len(tokens) and tokens[idx] != "moves":
            fen_parts.append(tokens[idx])
            idx += 1
        board.set_fen(" ".join(fen_parts))
        board.history.clear()
        board.position_history.clear()

    if idx < len(tokens) and tokens[idx] == "moves":
        idx += 1
        while idx < len(tokens):
            move = parse_uci_move(board, tokens[idx])
            board.make_move(move)
            idx += 1


def _handle_go(tokens: list[str], board: Board) -> str:
    """Handle 'go' command. Returns bestmove UCI string."""
    wtime: int | None = None
    btime: int | None = None
    winc: int | None = None
    binc: int | None = None
    movetime: int | None = None
    depth: int | None = None

    i = 1
    while i < len(tokens):
        tok = tokens[i]
        if tok == "wtime" and i + 1 < len(tokens):
            wtime = int(tokens[i + 1])
            i += 2
        elif tok == "btime" and i + 1 < len(tokens):
            btime = int(tokens[i + 1])
            i += 2
        elif tok == "winc" and i + 1 < len(tokens):
            winc = int(tokens[i + 1])
            i += 2
        elif tok == "binc" and i + 1 < len(tokens):
            binc = int(tokens[i + 1])
            i += 2
        elif tok == "movetime" and i + 1 < len(tokens):
            movetime = int(tokens[i + 1])
            i += 2
        elif tok == "depth" and i + 1 < len(tokens):
            depth = int(tokens[i + 1])
            i += 2
        else:
            i += 1

    # Try opening book first
    book_move = get_book_move(board)
    if book_move is not None:
        legal = generate_legal_moves(board)
        if book_move in legal:
            return move_to_uci(book_move)

    time_limit, max_depth = _calculate_time(
        board, wtime, btime, winc, binc, movetime, depth
    )
    if max_depth is not None:
        time_limit = 300.0

    best = search(board, time_limit)
    return move_to_uci(best)


def uci_loop(input_stream: object = None) -> None:
    """Main UCI protocol loop.

    Args:
        input_stream: Optional iterable of command strings (for testing).
                     Defaults to sys.stdin.
    """
    board = Board()
    lines = input_stream if input_stream is not None else sys.stdin

    for raw_line in lines:
        line = raw_line.strip()
        if not line:
            continue
        tokens = line.split()
        cmd = tokens[0]

        if cmd == "uci":
            print(f"id name {ENGINE_NAME}")
            print(f"id author {ENGINE_AUTHOR}")
            print("uciok")
            sys.stdout.flush()

        elif cmd == "isready":
            print("readyok")
            sys.stdout.flush()

        elif cmd == "ucinewgame":
            board = Board()

        elif cmd == "position":
            _handle_position(tokens, board)

        elif cmd == "go":
            uci_move = _handle_go(tokens, board)
            print(f"bestmove {uci_move}")
            sys.stdout.flush()

        elif cmd == "quit":
            break
