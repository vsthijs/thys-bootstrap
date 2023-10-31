import os

from lark import Lark, Tree, Token

GRAMMAR_SOURCE: str = os.path.join(os.path.dirname(__file__), "thyson.lark")
GRAMMAR: Lark | None = None


def grammar() -> Lark:
    """Lazy load the parser"""
    global GRAMMAR
    if not GRAMMAR:
        with open(GRAMMAR_SOURCE) as f:
            GRAMMAR = Lark(f.read(), start="script")
    return GRAMMAR


def parse(src: str) -> Tree[Token]:
    return grammar().parse(src)


__all__ = ["parse"]
