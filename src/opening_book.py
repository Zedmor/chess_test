"""Hardcoded opening book for common chess openings."""

from __future__ import annotations

import random

from src.board import Board
from src.constants import parse_uci_move


# Maps position FEN (without move counters) to list of UCI move strings.
# Positions include Italian Game, Ruy Lopez, Sicilian Defense, French Defense,
# Queen's Gambit, King's Indian, London System, Slav Defense, and more.
#
# FEN keys use get_position_fen() format: board + side + castling + ep square.
# After double pawn pushes the ep square is set (e.g. "e3" after 1.e4).
OPENING_BOOK: dict[str, list[str]] = {
    # ---- Starting position (White's first move) ----
    "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq -": [
        "e2e4", "d2d4", "c2c4", "g1f3",
    ],

    # ==================================================================
    # 1.e4 lines
    # ==================================================================

    # After 1.e4 (Black responds)
    "rnbqkbnr/pppppppp/8/8/4P3/8/PPPP1PPP/RNBQKBNR b KQkq e3": [
        "e7e5", "c7c5", "e7e6", "c7c6", "d7d5",
    ],

    # After 1.e4 e5 (ep from ...e5)
    "rnbqkbnr/pppp1ppp/8/4p3/4P3/8/PPPP1PPP/RNBQKBNR w KQkq e6": [
        "g1f3",
    ],

    # After 1.e4 e5 2.Nf3
    "rnbqkbnr/pppp1ppp/8/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R b KQkq -": [
        "b8c6", "g8f6",
    ],

    # After 1.e4 e5 2.Nf3 Nc6
    "r1bqkbnr/pppp1ppp/2n5/4p3/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq -": [
        "f1c4", "f1b5",
    ],

    # ---- Italian Game: 1.e4 e5 2.Nf3 Nc6 3.Bc4 ----
    "r1bqkbnr/pppp1ppp/2n5/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R b KQkq -": [
        "f8c5", "g8f6",
    ],

    # Italian: 3...Bc5
    "r1bqk1nr/pppp1ppp/2n5/2b1p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq -": [
        "c2c3", "d2d3",
    ],

    # Italian: 3...Nf6
    "r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq -": [
        "d2d3", "b1c3",
    ],

    # ---- Ruy Lopez: 1.e4 e5 2.Nf3 Nc6 3.Bb5 ----
    "r1bqkbnr/pppp1ppp/2n5/1B2p3/4P3/5N2/PPPP1PPP/RNBQK2R b KQkq -": [
        "a7a6", "g8f6", "f8c5",
    ],

    # Ruy Lopez: 3...a6 4.Ba4  (bishop retreats from b5)
    "r1bqkbnr/1ppp1ppp/p1n5/1B2p3/4P3/5N2/PPPP1PPP/RNBQK2R w KQkq -": [
        "b5a4",
    ],

    # Ruy Lopez: 4.Ba4 Nf6
    "r1bqkbnr/1ppp1ppp/p1n5/4p3/B3P3/5N2/PPPP1PPP/RNBQK2R b KQkq -": [
        "g8f6",
    ],

    # Ruy Lopez: 4...Nf6 5.O-O
    "r1bqkb1r/1ppp1ppp/p1n2n2/4p3/B3P3/5N2/PPPP1PPP/RNBQK2R w KQkq -": [
        "e1g1",
    ],

    # ---- Sicilian Defense: 1.e4 c5 ----  (ep from ...c5)
    "rnbqkbnr/pp1ppppp/8/2p5/4P3/8/PPPP1PPP/RNBQKBNR w KQkq c6": [
        "g1f3", "b1c3",
    ],

    # Sicilian: 2.Nf3
    "rnbqkbnr/pp1ppppp/8/2p5/4P3/5N2/PPPP1PPP/RNBQKB1R b KQkq -": [
        "d7d6", "b8c6", "e7e6",
    ],

    # Sicilian: 2...d6
    "rnbqkbnr/pp2pppp/3p4/2p5/4P3/5N2/PPPP1PPP/RNBQKB1R w KQkq -": [
        "d2d4",
    ],

    # Sicilian: 3.d4 cxd4
    "rnbqkbnr/pp2pppp/3p4/8/3pP3/5N2/PPP2PPP/RNBQKB1R w KQkq -": [
        "f3d4",
    ],

    # Sicilian Najdorf: 4.Nxd4 Nf6 5.Nc3
    "rnbqkb1r/pp2pppp/3p1n2/8/3NP3/8/PPP2PPP/RNBQKB1R w KQkq -": [
        "b1c3",
    ],

    # ---- French Defense: 1.e4 e6 ----
    "rnbqkbnr/pppp1ppp/4p3/8/4P3/8/PPPP1PPP/RNBQKBNR w KQkq -": [
        "d2d4",
    ],

    # French: 2.d4 (ep from d4)
    "rnbqkbnr/pppp1ppp/4p3/8/3PP3/8/PPP2PPP/RNBQKBNR b KQkq d3": [
        "d7d5",
    ],

    # French: 2...d5 (ep from ...d5)
    "rnbqkbnr/ppp2ppp/4p3/3p4/3PP3/8/PPP2PPP/RNBQKBNR w KQkq d6": [
        "b1c3", "b1d2", "e4e5",
    ],

    # ---- Caro-Kann: 1.e4 c6 ----
    "rnbqkbnr/pp1ppppp/2p5/8/4P3/8/PPPP1PPP/RNBQKBNR w KQkq -": [
        "d2d4",
    ],

    # Caro-Kann: 2.d4 (ep from d4)
    "rnbqkbnr/pp1ppppp/2p5/8/3PP3/8/PPP2PPP/RNBQKBNR b KQkq d3": [
        "d7d5",
    ],

    # ==================================================================
    # 1.d4 lines
    # ==================================================================

    # After 1.d4 (ep from d4)
    "rnbqkbnr/pppppppp/8/8/3P4/8/PPP1PPPP/RNBQKBNR b KQkq d3": [
        "d7d5", "g8f6", "e7e6",
    ],

    # After 1.d4 d5 (ep from ...d5)
    "rnbqkbnr/ppp1pppp/8/3p4/3P4/8/PPP1PPPP/RNBQKBNR w KQkq d6": [
        "c2c4", "g1f3",
    ],

    # Queen's Gambit: 2.c4 (ep from c4)
    "rnbqkbnr/ppp1pppp/8/3p4/2PP4/8/PP2PPPP/RNBQKBNR b KQkq c3": [
        "e7e6", "c7c6", "d5c4",
    ],

    # QGD: 2...e6
    "rnbqkbnr/ppp2ppp/4p3/3p4/2PP4/8/PP2PPPP/RNBQKBNR w KQkq -": [
        "b1c3", "g1f3",
    ],

    # Slav Defense: 2...c6
    "rnbqkbnr/pp2pppp/2p5/3p4/2PP4/8/PP2PPPP/RNBQKBNR w KQkq -": [
        "g1f3", "b1c3",
    ],

    # ---- King's Indian: 1.d4 Nf6 ----
    "rnbqkb1r/pppppppp/5n2/8/3P4/8/PPP1PPPP/RNBQKBNR w KQkq -": [
        "c2c4", "g1f3",
    ],

    # KID: 2.c4 (ep from c4)
    "rnbqkb1r/pppppppp/5n2/8/2PP4/8/PP2PPPP/RNBQKBNR b KQkq c3": [
        "g7g6", "e7e6",
    ],

    # KID: 2...g6 3.Nc3
    "rnbqkb1r/pppppp1p/5np1/8/2PP4/8/PP2PPPP/RNBQKBNR w KQkq -": [
        "b1c3",
    ],

    # KID: 3.Nc3 Bg7 4.e4
    "rnbqk2r/ppppppbp/5np1/8/2PP4/2N5/PP2PPPP/R1BQKBNR w KQkq -": [
        "e2e4",
    ],

    # ---- London System: 1.d4 d5 2.Nf3 ----
    "rnbqkbnr/ppp1pppp/8/3p4/3P4/5N2/PPP1PPPP/RNBQKB1R b KQkq -": [
        "g8f6",
    ],

    # London: 2...Nf6 3.Bf4
    "rnbqkb1r/ppp1pppp/5n2/3p4/3P4/5N2/PPP1PPPP/RNBQKB1R w KQkq -": [
        "c1f4", "c2c4",
    ],

    # ==================================================================
    # 1.c4 (English Opening) — ep from c4
    # ==================================================================
    "rnbqkbnr/pppppppp/8/8/2P5/8/PP1PPPPP/RNBQKBNR b KQkq c3": [
        "e7e5", "g8f6", "c7c5",
    ],

    # ==================================================================
    # 1.Nf3 (Reti Opening)
    # ==================================================================
    "rnbqkbnr/pppppppp/8/8/8/5N2/PPPPPPPP/RNBQKB1R b KQkq -": [
        "d7d5", "g8f6", "c7c5",
    ],
}


def get_book_move(board: Board) -> int | None:
    """Return an encoded book move, or None if position not in book.

    Picks randomly from available book moves. Validates
    the selected move by parsing it against the current board.
    """
    key = board.get_position_fen()
    if key not in OPENING_BOOK:
        return None
    uci_str = random.choice(OPENING_BOOK[key])
    return parse_uci_move(board, uci_str)
