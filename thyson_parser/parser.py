"""
The grammar is not used by the parser, and therefore not precisely the correct grammar.
It is only used as reference for the developers
grammar: thyson.txt
"""

# TODO: improve Error usage
# TODO: rename project to 'thyson' for expansion to code generation
# TODO: run to see fixable errors

from typing import Optional, Tuple

from .lexer import Lexer, Token, TokenType
from .nodes import *


class Error:
    def __init__(self, msg: str, index: int, location: tuple[str, int, int]) -> None:
        self.msg = msg
        self.index = index
        self.location = location


class Parser:
    def __init__(self, /, _file: Optional[Tuple[str, str]] = None, _lexer: Optional[Lexer] = None) -> None:
        """
        initialize a parser instance. requires either _file, or _lexer.
        :param _file: a pair of (content, filename)
        :param _lexer: an initialized Lexer instance
        """
        if _lexer:
            self.lexer = _lexer
        elif _file:
            self.lexer = Lexer(_file[0], _file[1])
        else:
            raise ValueError('requires either _file or _lexer, but both are not given')

        self.tokens = list(self.lexer.tokens())
        self.index = 0
        self.undo_stack = []
        self.error_stack: list[Error] = []
        self.last_location = self.peek(0).location

    def set_err(self, msg: str) -> None:
        self.error_stack.append((Error(msg, self.index, self.last_location)))

    def _print_err(self, err: Error, indent: int = 0) -> None:
        print(f"{' ' * indent}{err.location[0]}:{err.location[1]}:{err.location[2]}: {err.msg}")
        print(f"{' ' * indent}  -> {self.tokens[err.index]}")

    def show_err(self, max_tb: int = 5) -> None:
        self._print_err(self.error_stack[0])
        for ii in range(1, min(max_tb, len(self.error_stack))):
            self._print_err(self.error_stack[ii], indent=4)
            print()

    def peek(self, offset: int = 1) -> Optional[Token]:
        """Return a specific token without modifying the index."""
        try:
            return self.tokens[self.index + offset]
        except IndexError:
            return

    def token(self) -> Optional[Token]:
        """Return the next token by incrementing the index."""
        tok = None
        try:
            if tok := self.tokens[self.index]:
                return tok
        except IndexError:
            return
        finally:
            if __debug__ and tok:
                print(f"token() -> {tok}")
            if tok:
                self.last_location = self.tokens[self.index].location
            self.index += 1

    def undo(self, err: Optional[str] = None) -> None:
        """Restores the state. Should be called when failing to parse"""
        if err:
            self.set_err(err)
        self.index = self.undo_stack.pop()

    def done(self) -> None:
        """Make the changes irreversible."""
        self.undo_stack.pop()

    def do(self) -> None:
        """Save the current state."""
        self.undo_stack.append(self.index)

    def expect(self, _type: TokenType) -> bool:
        """
        Check if token() is _type.
        WARNING: modifies the undo stack.

        :param _type: TokenType to look for
        :return: true if the token() is _type
        """
        if tok := self.token():
            if tok.type == _type:
                return True
            else:
                self.set_err(f"expected {_type}, got {tok}")
        return False

    def parse_any(self) -> Optional[Code]:
        """Parse Code."""
        statements = []
        while self.index < len(self.tokens):
            if out := self.parse_statement():
                statements.append(out)
            else:
                self.show_err()
                exit(1)
        return Code(*statements)

    def parse_statement(self) -> Optional[Statement]:
        """Parse a Statement."""
        self.do()
        if (expr := self.parse_expression()) and self.expect(TokenType.Semicolon):
            self.done()
            return Statement(expr)
        else:
            self.undo()

        self.do()
        if (var_declaration := self.parse_var_declaration()) and self.expect(TokenType.Semicolon):
            self.done()
            return Statement(var_declaration)
        else:
            self.undo()

        self.do()
        if (var_definition := self.parse_var_definition()) and self.expect(TokenType.Semicolon):
            self.done()
            return Statement(var_definition)
        else:
            self.undo()

    def parse_expression(self) -> Optional[Expression]:
        """Parse an Expression."""
        if number := self.parse_number():
            return number

        if name := self.parse_name():
            return name

        if string := self.parse_string():
            return string

        if _type := self.parse_type():
            return _type

        if var_assignment := self.parse_var_assignment():
            return var_assignment

        if function := self.parse_function():
            return function

    def parse_number(self) -> Optional[Number]:
        """Parse a Number."""
        self.do()
        if tok := self.token():
            if tok.type in [TokenType.IntegerNumber, TokenType.FloatingNumber]:
                self.done()
                return Number(tok.value)
        self.undo()

    def parse_name(self) -> Optional[Name]:
        """Parse a Name."""
        self.do()
        if tok := self.token():
            if tok.type == TokenType.Identifier:
                self.done()
                return Name(tok.value)
        self.undo("expected identifier (for name), got EOF")

    def parse_string(self) -> Optional[String]:
        """Parse a String."""
        self.do()
        if tok := self.token():
            if tok.type == TokenType.String:
                self.done()
                return String(tok.value)
            else:
                self.undo(f"expected string, got {tok.type}")
        else:
            self.undo("expected string, got EOF")

    def parse_type(self) -> Optional[Type]:
        """Parse a Type."""
        if name := self.parse_name():
            return Type(name)

        if function_type := self.parse_function_type():
            return function_type

        self.set_err("cant parse type")

    def parse_var_assignment(self) -> Optional[VarAssignment]:
        """Parse a VarAssignment."""
        self.do()
        if not (name := self.parse_name()):
            self.undo()
            return
        if not self.expect(TokenType.Eq):
            self.undo()
            return
        if not (value := self.parse_expression()):
            self.undo()
            return
        self.done()
        return VarAssignment(name, value)

    def parse_var_declaration(self) -> Optional[VarDeclaration]:
        """Parse a VarDeclaration."""
        self.do()
        if not (tok := self.token()):
            self.undo(f"expected 'const', 'let' or 'extern' for variable declaration")
            return
        definition_type = tok.type
        if definition_type not in [TokenType.KeywordConst, TokenType.KeywordExtern, TokenType.KeywordLet]:
            self.undo(f"expected 'const', 'let' or 'extern' for variable declaration, got {definition_type}")
            return
        if not (name := self.parse_name()):
            self.undo("expected name for variable declaration")
            return
        if not self.expect(TokenType.Colon):
            self.undo()
            return
        if not (variable_type := self.parse_type()):
            self.undo("expected type for variable declaration")
            return
        self.done()
        return VarDeclaration(definition_type, name, variable_type)

    def parse_var_definition(self) -> Optional[VarDefinition]:
        """Parse a VarDefinition."""
        self.do()
        if not (declaration := self.parse_var_declaration()):
            return
        if not self.expect(TokenType.Eq):
            self.undo()
            return
        if not (value := self.parse_expression()):
            self.undo()
            return
        self.done()
        return VarDefinition.from_declaration(declaration, value)

    def parse_function_type(self) -> Optional[FunctionType]:
        """Parse a FunctionType."""
        self.do()
        if not self.expect(TokenType.ParenOpen):
            self.set_err('trying to parse a not-function type')
            self.undo()
            return

        # parse args (unknown length)
        args: list[tuple[Name, Type]] = []
        while self.index < len(self.tokens):
            tok = self.peek(0)
            if tok.type == TokenType.ParenClose:
                self.index += 1  # consume the ParenClose
                if not (_rt := self.parse_type()):
                    self.undo("function type needs a return type")
                    return
                self.done()
                return FunctionType(args, _rt)

            _n = self.parse_name()
            if not self.expect(TokenType.Colon):
                self.set_err("expected ':' after argument name")
                self.undo()
                return
            _t = self.parse_type()
            args.append((_n, _t))

            tok = self.peek(0)
            if tok.type == TokenType.ParenClose:
                self.index += 1  # consume the ParenClose
                if not (_rt := self.parse_type()):
                    self.undo("function type needs a return type")
                    return
                self.done()
                return FunctionType(args, _rt)
            if tok.type != TokenType.Comma:
                self.set_err("function argument list stopped unterminated")
                self.undo()
                return

        self.set_err("unexpected EOF")
        self.undo()
        return

    def parse_function_body(self) -> Optional[FunctionBody]:
        self.do()
        if not self.expect(TokenType.BraceOpen):
            self.undo()
            return
        code = []
        while self.index < len(self.tokens):
            if statement := self.parse_statement():
                code.append(statement)
            else:
                expr = self.parse_expression()
                if not self.expect(TokenType.BraceClose):
                    self.undo()
                    return
                return FunctionBody(*code, expr=expr)

    def parse_function(self) -> Optional[Function]:
        if not (_type := self.parse_function_type()):
            return
        if not (_body := self.parse_function_body()):
            return
        return Function(_type, _body)
