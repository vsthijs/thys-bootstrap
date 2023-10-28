"""
Simple lexer.

tokens:
- Identifier
- Integer - base 2, 16 and 10
- Float
- String
- Literals and Keywords - See TokenType
"""

from enum import Enum, auto
from typing import Tuple, Any, Optional, Generator


class LexErr(Exception):
    def __init__(self, loc: Tuple[str, int, int], msg: str) -> None:
        super().__init__(f'[err] {loc[0]}:{loc[1]}:{loc[2]}: {msg}')


class TokenType(Enum):
    # dynamic tokens
    Identifier = auto()
    IntegerNumber = auto()
    FloatingNumber = auto()
    String = auto()
    Comment = auto()  # not included in ast

    # keywords
    KeywordConst = auto()  # const
    KeywordExtern = auto()  # extern
    KeywordLet = auto()  # let

    # literal tokens
    ParenOpen = auto()  # (
    ParenClose = auto()  # )
    BracketOpen = auto()  # [
    BracketClose = auto()  # ]
    BraceOpen = auto()  # {
    BraceClose = auto()  # }

    Eq = auto()  # =
    Semicolon = auto()  # ;
    Colon = auto()  # :
    Comma = auto()  # ,


# dynamically map keywords to tokens
KEYWORDS = {
    'const': TokenType.KeywordConst,
    'extern': TokenType.KeywordExtern,
    'let': TokenType.KeywordLet,
}

# dynamically map literals to tokens
LITERALS = {
    '(': TokenType.ParenOpen,
    ')': TokenType.ParenClose,
    '[': TokenType.BracketOpen,
    ']': TokenType.BracketClose,
    '{': TokenType.BraceOpen,
    '}': TokenType.BraceClose,
    '=': TokenType.Eq,
    ';': TokenType.Semicolon,
    ':': TokenType.Colon,
    ',': TokenType.Comma,
}


class Token[T]:
    location: Tuple[str, int, int]
    type: TokenType
    src: str
    value: T

    def __init__(self, _location: Tuple[str, int, int], _type: TokenType, _src: str, _value: T) -> None:
        self.location = _location
        self.type = _type
        self.src = _src
        self.value = _value

    def __str__(self):
        return f'{self.type}<{self.location}, {self.src}, {self.value}>'


class Lexer:
    def __init__(self, data: str, file: str):
        self.file = file
        self.src = data
        self.index = 0

    def index2loc(self, index: Optional[int] = None) -> Tuple[str, int, int]:
        if not index:
            index = self.index
        if index > len(self.src):
            raise ValueError(f'[err] index2loc({index}) index out of bounds')

        ci = index
        for line_count, line in enumerate(self.src.splitlines(True)):
            if ci - len(line) <= 0:
                return self.file, line_count, ci
            else:
                ci -= len(line)

    def peek(self, lookahead: int = 1) -> str:
        return self.src[self.index + lookahead]

    def undo(self) -> None:
        self.index -= 1

    def char(self) -> str:
        self.index += 1
        return self.src[self.index - 1]

    def tokens(self) -> Generator[Token, Any, None]:
        try:
            for ii in self._tokens():
                yield ii
        except LexErr as e:
            print(e)
            exit(1)
        except Exception as e:
            loc = self.index2loc()
            print(f"lex err: {loc[0]}:{loc[1]}:{loc[2]}: {e}")

    def _tokens(self) -> Generator[Token, Any, None]:
        while self.index < len(self.src):
            try:
                c = self.char()
                while c.isspace():
                    c = self.char()
            except IndexError:
                return

            if c.isalpha():  # identifier
                if out := self.next_identifier(c):
                    yield out
                else:
                    raise LexErr(self.index2loc(), 'expected identifier, got error')
            elif c.isnumeric():  # number
                if out := self.next_number(c):
                    yield out
                else:
                    raise LexErr(self.index2loc(), 'expected numeric, got error')
            elif c == '"':  # string
                if out := self.next_string(c):
                    yield out
                else:
                    raise LexErr(self.index2loc(), 'expected string, got error')
            elif c == '/' and self.peek(0) == '*':  # comment
                if self.next_comment(c):
                    pass
                else:
                    raise LexErr(self.index2loc(), 'expected comment, got error')
            elif c in LITERALS:
                yield Token(self.index2loc(), LITERALS[c], c, c)
            else:
                raise LexErr(self.index2loc(), f'unexpected character: "{c}"')

    def next_identifier(self, start: str) -> Optional[Token[str]]:
        """tokenizes to TokenType.Identifier or TokenType.Keyword"""
        loc = self.index2loc()
        if not start.isalpha():
            return

        identifier = start
        while (c := self.char()).isalnum() or c in "_":
            identifier += c
        self.undo()

        if identifier in KEYWORDS:
            return Token(loc, KEYWORDS[identifier], identifier, identifier)
        else:
            return Token(loc, TokenType.Identifier, identifier, identifier)

    def next_number(self, start: str) -> Optional[Token[float | int]]:
        loc = self.index2loc()
        if not start.isnumeric():
            return

        number = start
        while self.peek() in '0123456789_.abcdefxABCDEF':
            number += self.char()

        if '.' in number:  # floating point number
            try:
                return Token(loc, TokenType.FloatingNumber, number, float(number))
            except ValueError:
                raise LexErr(loc, 'invalid float')
        elif number.startswith('0x') and any(a in number for a in 'abcdef'):
            try:
                return Token(loc, TokenType.IntegerNumber, number, int(number[2:], base=16))
            except ValueError:
                raise LexErr(loc, 'invalid hexadecimal notation')
        elif number.startswith('0b') and all(a in '01' for a in number[2:]):
            try:
                return Token(loc, TokenType.IntegerNumber, number, int(number[2:], base=2))
            except ValueError:
                raise LexErr(loc, 'invalid binary notation')
        else:
            try:
                return Token(loc, TokenType.IntegerNumber, number, int(number))
            except ValueError:
                raise LexErr(loc, 'invalid integer')

    def next_string(self, start: str) -> Optional[Token]:
        if start != '"':
            return

        src = start
        inner = ''
        escaping: bool = False
        while self.index < len(self.src):
            c = self.char()
            src += c
            if escaping:
                if c == '\\':
                    inner += c
                elif c == 'n':
                    inner += '\n'
                elif c == 'r':
                    inner += '\r'
                elif c == 't':
                    inner += '\t'
                elif c == '"':
                    inner += c
                elif c == '\n':
                    inner += '\n'
                else:
                    raise LexErr(self.index2loc(), 'unused escape symbol')
                escaping = False
            else:
                if c == '\\':
                    escaping = True
                elif c == '\n':
                    raise LexErr(self.index2loc(), 'unterminated string. use \\ to include a newline')
                elif c == '"':
                    return Token(self.index2loc(), TokenType.String, src, inner)
                else:
                    inner += c

        raise LexErr(self.index2loc(), 'unterminated string')

    def next_comment(self, c: str):
        if c != '/' or self.char() != '*':
            raise LexErr(self.index2loc(), 'expected a comment, got error (this is a bug)')
        while self.index < len(self.src):
            if self.char() == '*' and self.char() == '/':
                return Token(self.index2loc(), TokenType.Comment, "<ignored>", None)
