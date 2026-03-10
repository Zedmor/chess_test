"""Chess engine entry point — starts the UCI protocol loop."""

from src.uci import uci_loop

if __name__ == "__main__":
    uci_loop()
