"""Play the chess engine against Stockfish at ~1200 ELO and report results.

Usage:
    python scripts/stockfish_match.py [--games N] [--elo ELO] [--time SECONDS]

Defaults: 20 games, Stockfish ELO 1200, 1 second per move.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.board import Board
from src.constants import (
    WHITE, BLACK,
    move_to_uci, parse_uci_move,
)
from src.movegen import generate_legal_moves
from src.search import search
from src.opening_book import get_book_move


def start_stockfish(elo: int) -> subprocess.Popen:
    """Start Stockfish process configured at given ELO."""
    proc = subprocess.Popen(
        ["stockfish"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        bufsize=1,
    )
    _send(proc, "uci")
    _read_until(proc, "uciok")
    _send(proc, "setoption name UCI_LimitStrength value true")
    _send(proc, f"setoption name UCI_Elo value {elo}")
    _send(proc, "isready")
    _read_until(proc, "readyok")
    return proc


def _send(proc: subprocess.Popen, cmd: str) -> None:
    """Send a command to the engine."""
    assert proc.stdin is not None
    proc.stdin.write(cmd + "\n")
    proc.stdin.flush()


def _read_until(proc: subprocess.Popen, token: str) -> str:
    """Read lines until one starts with token. Return that line."""
    assert proc.stdout is not None
    while True:
        line = proc.stdout.readline().strip()
        if line.startswith(token):
            return line


def stockfish_move(proc: subprocess.Popen, move_list: list[str], movetime_ms: int) -> str:
    """Get Stockfish's best move for the given position."""
    if move_list:
        _send(proc, f"position startpos moves {' '.join(move_list)}")
    else:
        _send(proc, "position startpos")
    _send(proc, f"go movetime {movetime_ms}")
    line = _read_until(proc, "bestmove")
    return line.split()[1]


def engine_move(board: Board, time_limit: float) -> str:
    """Get our engine's move for the current position."""
    book_move = get_book_move(board)
    if book_move is not None:
        return move_to_uci(book_move)
    move = search(board, time_limit)
    return move_to_uci(move)


def play_game(
    sf_proc: subprocess.Popen,
    engine_is_white: bool,
    time_per_move: float,
) -> str:
    """Play a single game. Returns "engine_win", "engine_loss", or "draw"."""
    board = Board()
    move_list: list[str] = []
    max_moves = 200

    for _ in range(max_moves):
        legal = generate_legal_moves(board)
        if not legal:
            if board.is_in_check():
                # Checkmate — side to move lost
                if (board.turn == WHITE) == engine_is_white:
                    return "engine_loss"
                return "engine_win"
            return "draw"  # stalemate

        if board.is_fifty_move_draw() or board.is_repetition():
            return "draw"
        if board.is_insufficient_material():
            return "draw"

        is_engine_turn = (board.turn == WHITE) == engine_is_white

        if is_engine_turn:
            uci = engine_move(board, time_per_move)
        else:
            movetime_ms = int(time_per_move * 1000)
            uci = stockfish_move(sf_proc, move_list, movetime_ms)

        m = parse_uci_move(board, uci)
        if m not in legal:
            # If engine produced illegal move, count as loss
            if is_engine_turn:
                return "engine_loss"
            # Stockfish producing illegal move is very unusual; treat as draw
            return "draw"

        board.make_move(m)
        move_list.append(uci)

    return "draw"  # max moves reached


def main() -> None:
    parser = argparse.ArgumentParser(description="Play engine vs Stockfish")
    parser.add_argument("--games", type=int, default=20, help="Number of games")
    parser.add_argument("--elo", type=int, default=1200, help="Stockfish ELO")
    parser.add_argument("--time", type=float, default=1.0, help="Seconds per move")
    args = parser.parse_args()

    sf = start_stockfish(args.elo)

    wins = 0
    losses = 0
    draws = 0

    print(f"Playing {args.games} games vs Stockfish {args.elo} ELO "
          f"({args.time}s/move)")
    print("-" * 50)

    try:
        for game_num in range(1, args.games + 1):
            engine_is_white = (game_num % 2 == 1)
            color = "White" if engine_is_white else "Black"
            _send(sf, "ucinewgame")
            _send(sf, "isready")
            _read_until(sf, "readyok")

            result = play_game(sf, engine_is_white, args.time)

            if result == "engine_win":
                wins += 1
                symbol = "W"
            elif result == "engine_loss":
                losses += 1
                symbol = "L"
            else:
                draws += 1
                symbol = "D"

            total = wins + losses + draws
            winrate = (wins + 0.5 * draws) / total * 100
            print(
                f"Game {game_num:3d}: Engine={color:5s} Result={symbol} "
                f"| W:{wins} L:{losses} D:{draws} "
                f"| Score: {winrate:.1f}%"
            )
    finally:
        _send(sf, "quit")
        sf.wait(timeout=5)

    total = wins + losses + draws
    score = (wins + 0.5 * draws) / total * 100
    print("-" * 50)
    print(f"Final: {wins}W / {losses}L / {draws}D ({score:.1f}%)")
    if score >= 50:
        print("TARGET MET: >= 50% winrate!")
    else:
        print(f"TARGET NOT MET: {score:.1f}% < 50%")


if __name__ == "__main__":
    main()
