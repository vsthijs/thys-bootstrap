from enum import Enum, auto
from typing import Any, Optional

from .lexer import TokenType


class VarType(Enum):
    Extern = auto()
    Let = auto()
    Const = auto()


class AstNode:
    def __init__(self, *children: "AstNode") -> None:
        self.children = list(children)

    def pretty(self, indent: int = 0) -> None:
        print(f"{' ' * indent}{str(self)}")
        for ii in self.children:
            ii.pretty(indent + 2)

    def __str__(self) -> str:
        return self.__class__.__name__


class Statement(AstNode):
    pass


class Expression(Statement):
    def __init__(self) -> None:
        super().__init__()
        self.__value = None

    @property
    def value(self) -> Any:
        return self.__value

    def __str__(self) -> str:
        return f"{self.__class__.__name__}({self.value})"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.value})"


class Number[T: int | float](Expression):
    def __init__(self, _value: T) -> None:
        super().__init__()
        self.__value = value

    @property
    def value(self) -> T:
        return self.__value


class Name(Expression):
    def __init__(self, _name: str) -> None:
        super().__init__()
        self.__value = _name

    @property
    def value(self) -> str:
        return self.__value


class String(Expression):
    def __init__(self, _value: str) -> None:
        super().__init__()
        self.__value = _value

    @property
    def value(self) -> str:
        return self.__value


class Type(Expression):
    def __init__(self, name: Optional[Name]) -> None:
        super().__init__()
        self.__value = name if name else "Function"

    @property
    def value(self) -> str:
        return self.__value.value if self.__value else None


class FunctionType(Type):
    # TODO: implement FunctionType
    def __init__(self, args: list[tuple[Name, Type]], return_type: Type) -> None:
        super().__init__(None)
        self.args = args
        self.return_type = return_type

    def __str__(self) -> str:
        return f"FunctionType({self.args}, {self.return_type})"


class VarAssignment(Expression):
    def __init__(self, _name: Name, _value: Expression) -> None:
        super().__init__()
        self.name = _name
        self.__value = _value

    def __str__(self) -> str:
        return f"{self.__class__.__name__}({self.name}, {self.value})"


class VarDeclaration(Statement):
    def __init__(self, _keyword: TokenType, _name: Name, _type: Type) -> None:
        super().__init__()
        self.type = {TokenType.KeywordConst: VarType.Const, TokenType.KeywordLet: VarType.Let,
                     TokenType.KeywordExtern: VarType.Extern}[_keyword]
        self.name = _name
        self.datatype = _type

    def __str__(self) -> str:
        return f"{self.__class__.__name__}({self.type}, {self.name}, {self.datatype})"


class VarDefinition(VarDeclaration):
    def __init__(self, _keyword: TokenType, _name: Name, _type: Type, _value: Expression) -> None:
        super().__init__(_keyword, _name, _type)
        self.__value = _value

    @classmethod
    def from_declaration(cls, declaration: VarDeclaration, _value: Expression) -> "VarDefinition":
        return cls({VarType.Const: TokenType.KeywordConst, VarType.Let: TokenType.KeywordLet,
                    VarType.Extern: TokenType.KeywordExtern}[declaration.type], declaration.name, declaration.datatype,
                   _value)

    @property
    def value(self) -> Expression:
        return self.__value

    def __str__(self) -> str:
        return f"{self.__class__.__name__}({self.type}, {self.name}, {self.datatype}, {self.value})"


class FunctionBody(Expression):
    def __init__(self, *statement: Statement, expr: Optional[Expression]) -> None:
        super().__init__()
        self.children = [*statement]
        if expr:
            self.children.append(expr)


class Function(Expression):
    def __init__(self, _type: FunctionType, _body: FunctionBody) -> None:
        super().__init__()
        self.children = [_type, _body]


class Code(AstNode):
    pass


__all__ = [
    "AstNode",
    "Code",

    # statements
    "Statement",
    "VarDeclaration",
    "VarDefinition",

    # expressions
    "Expression",
    "Number",
    "Name",
    "String",
    "Type",
    "VarAssignment",
    "FunctionType",
    "FunctionBody",
    "Function",
]
