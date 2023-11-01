"""Checks the ast from lark, and converts it into something that the compiler and interpreter can understand"""
import struct
from enum import Enum, auto
from typing import Optional

import lark


class TreeErr(Exception):
    pass


class BuiltinType(Enum):
    """Builtin data types"""

    byte = auto()
    u8 = auto()
    u16 = auto()
    u32 = auto()
    u64 = auto()
    i8 = auto()
    i16 = auto()
    i32 = auto()
    i64 = auto()
    usize = auto()
    isize = auto()
    uint = auto()
    int = auto()
    f32 = auto()
    f64 = auto()
    str = auto()
    ptr = auto()
    type = auto()
    none = auto()
    unknown = auto()


BUILTINS: dict[BuiltinType, int] = {
    BuiltinType.byte: 1,
    BuiltinType.u8: 1,
    BuiltinType.i8: 1,
    BuiltinType.u16: 2,
    BuiltinType.i16: 2,
    BuiltinType.u32: 4,
    BuiltinType.i32: 4,
    BuiltinType.u64: 8,
    BuiltinType.i64: 8,
    BuiltinType.usize: len(struct.pack("N", 0)),
    BuiltinType.isize: len(struct.pack("N", 0)),
    BuiltinType.uint: len(struct.pack("I", 0)),
    BuiltinType.int: len(struct.pack("I", 0)),
    BuiltinType.f32: 4,
    BuiltinType.f64: 8,
    BuiltinType.ptr: len(struct.pack("P", 0)),
    BuiltinType.none: 0,
}


class DataType:
    __type: (
        tuple["function", list[tuple[str, "DataType"]], "DataType"]
        | tuple["struct", list[tuple[str, "DataType"]]]
        | tuple["builtin", BuiltinType]
    )

    def __init__(self, **kwargs) -> None:
        if kwargs.get("_type") == "function":
            self.__type = ("function", [*kwargs["_args"]], kwargs["_return_type"])
        elif kwargs.get("_type") == "struct":
            self.__type = ("struct", [*kwargs["_fields"]])
        elif kwargs.get("_type") == "builtin":
            self.__type = ("builtin", kwargs["_builtin_type"])
        else:
            raise ValueError("invalid arguments for datatype construction")

    @classmethod
    def function(
        cls, arguments: list[tuple[str, "DataType"]], return_type: "DataType"
    ) -> "DataType":
        return cls(_type="function", _args=arguments, _return_type=return_type)

    @classmethod
    def struct(cls, fields: list[tuple[str, "DataType"]]) -> "DataType":
        return cls(_type="struct", _fields=fields)

    @classmethod
    def builtin(cls, _type: BuiltinType) -> "DataType":
        return cls(_type="builtin", _builtin_type=_type)

    def __str__(self) -> str:
        match self.__type:
            case ["builtin", _t]:
                return _t.name
            case _:
                return super().__str__()

    def __eq__(self, other):
        if other.__class__ == self.__class__:
            return self.__type == other.__type
        return False


class TreeNode:
    @classmethod
    def from_tree(cls, *args, **kwargs) -> "TreeNode":
        pass

    def pretty(self) -> str:
        return "TreeNode"


class String(TreeNode):
    def __init__(self, _value: str) -> None:
        self.value = _value.removeprefix('"').removesuffix('"')

    @classmethod
    def from_tree(cls, node: lark.Tree[lark.Token]) -> "String":
        if node.data != "string":
            raise TreeErr()

        return cls(node.children[0].value)

    def pretty(self) -> str:
        return f'"{self.value}"'


class Number(TreeNode):
    value: int | float

    def __init__(self, _value: str) -> None:
        try:
            self.value = int(_value)
            self.type = DataType.builtin(BuiltinType.int)
        except ValueError:
            self.value = float(_value)
            self.type = DataType.builtin(BuiltinType.f64)

    @classmethod
    def from_tree(cls, node: lark.Tree[lark.Token]) -> "Number":
        if node.data not in ["integer", "decimal"]:
            raise TreeErr()

        return cls(node.children[0].value)

    def pretty(self) -> str:
        return str(self.value)


class Name(TreeNode):
    value: str

    def __init__(self, _value: str) -> None:
        self.value = _value

    @classmethod
    def from_tree(cls, node: lark.Tree[lark.Token]) -> "Name":
        if node.data != "name":
            raise TreeErr()

        return cls(node.children[0].value)

    def pretty(self) -> str:
        return self.value


class FunType(TreeNode):
    def __init__(
        self, _signature: tuple[list[tuple[Name, "Type"]], Optional["Type"]]
    ) -> None:
        self.signature = _signature
        self.type = DataType.function(
            [(_n.value, _t) for (_n, _t) in self.signature[0]],
            self.signature[1].type
            if self.signature[1]
            else DataType.builtin(BuiltinType.none),
        )

    @classmethod
    def from_tree(cls, node: lark.Tree[lark.Token]) -> "FunType":
        # _Type = locals().get("Type")
        args: list[tuple[Name, "Type"]] = []
        curr_arg = None
        for ii in node.children:
            if ii.data == "name" and not curr_arg:
                curr_arg = Name.from_tree(ii)
            elif ii.data == "type" and curr_arg:
                args.append((curr_arg, Type.from_tree(ii)))
                curr_arg = None
            elif ii.data == "type" and not curr_arg:
                return cls((args, Type.from_tree(ii)))
        return cls((args, None))

    def pretty(self) -> str:
        return (
            "("
            + ", ".join(" ".join((b.pretty() for b in a)) for a in self.signature[0])
            + ")"
            + ((" " + self.signature[1].pretty()) if self.signature[1] else "")
        )


class Type(TreeNode):
    value: str

    def __init__(self, _value: str) -> None:
        self.value = _value
        try:
            self.type = BuiltinType[self.value]
        except KeyError:
            self.type = BuiltinType.unknown

    @classmethod
    def from_tree(cls, node: lark.Tree[lark.Token]) -> "Type | FuncType":
        if node.data != "type":
            raise TreeErr()
        elif node.children[0].data == "fun_type":
            return FunType.from_tree(node.children[0])
        elif node.children[0].data == "name":
            return cls(node.children[0].children[0].value)

        print(f"[unhandled] type / {node.children[0].data}")

    def pretty(self) -> str:
        return self.value


class BinaryOp(TreeNode):
    op: str
    left: "Expression"
    right: "Expression"

    type: DataType

    def __init__(self, op: str, left: "Expression", right: "Expression") -> None:
        self.op = op
        if self.op not in [
            "+",
            "-",
            "*",
            "/",
            "%",
            "<",
            ">",
            "<=",
            ">=",
            "|",
            "&",
            "**",
        ]:
            raise ValueError()
        self.left = left
        self.right = right

        if (
            self.left.type == BuiltinType.unknown
            or self.right.type == BuiltinType.unknown
        ):
            self.type = DataType.builtin(BuiltinType.unknown)
            self.value = None
        elif self.left.type == self.right.type:
            self.type = self.left.type
            self.value = None
            try:
                if type(self.left.value) is int and type(self.right.value) is int:
                    self.value = eval(f"{self.left.value} {self.op} {self.right.value}")
                    print(
                        f"[optimize] `{self.left.pretty()} {self.op} {self.right.pretty()}` -> `{self.value}`"
                    )
            except AttributeError:
                pass
        else:
            # TODO: check if they are both int types (e.g. `u8 + usize` should be possible)
            self.type = DataType.builtin(BuiltinType.unknown)
            self.value = None

    @classmethod
    def from_tree(
        cls, left: "Expression", right: "Expression", op: lark.Token
    ) -> "BinaryOp":
        return cls(op.value, left, right)

    def pretty(self) -> str:
        if self.value:
            return f"{self.value}"
        else:
            return f"{self.left.pretty()} {self.op} {self.right.pretty()}"


class Expression(TreeNode):
    child: String | Number | Name | Type | BinaryOp
    type: DataType

    def __init__(self, child) -> None:
        self.child = child
        if hasattr(self.child, "type"):
            self.type = self.child.type
        else:
            self.type = DataType.builtin(BuiltinType.unknown)
        if hasattr(self.child, "value"):
            self.value = self.child.value
        else:
            self.value = None

    @classmethod
    def from_tree(cls, node: lark.Tree[lark.Token]) -> "Expression":
        if node.data != "expression":
            raise TreeErr()

        n = node.children[0]
        if n.data == "string":
            return cls(String.from_tree(n))
        elif n.data in ["integer", "decimal"]:
            return cls(Number.from_tree(n))
        elif n.data == "name":
            return cls(Name.from_tree(n))
        elif n.data == "type":
            return cls(Type.from_tree(n))
        elif n.data == "expression" and len(node.children) == 1:
            return cls.from_tree(n)
        elif n.data == "expression" and len(node.children) == 3:
            return cls(
                BinaryOp.from_tree(
                    cls.from_tree(node.children[0]),
                    cls.from_tree(node.children[2]),
                    node.children[1],
                )
            )

        print(f"[unhandled] expression / {node.pretty()}")

    def pretty(self) -> str:
        return self.child.pretty()


class VarDecLet(TreeNode):
    def __init__(self, _name: Name, _type: Type) -> None:
        self.name = _name
        self.type = _type

    @classmethod
    def from_tree(cls, node: lark.Tree[lark.Token]) -> "VarDecLet":
        if node.data != "var_dec_let":
            raise TreeErr()
        _name, _type = node.children
        if _name.data != "name":
            raise TreeErr()
        if _type.data != "type":
            raise TreeErr()
        return cls(Name.from_tree(_name), Type.from_tree(_type))

    def pretty(self) -> str:
        return f"let {self.name.pretty()} {self.type.pretty()}"


class VarDecExt(TreeNode):
    def __init__(self, _name: Name, _type: Type) -> None:
        self.name = _name
        self.type = _type

    @classmethod
    def from_tree(cls, node: lark.Tree[lark.Token]) -> "VarDecExt":
        if node.data != "var_dec_ext":
            raise TreeErr()
        _name, _type = node.children
        if _name.data != "name":
            raise TreeErr()
        if _type.data != "type":
            raise TreeErr()
        return cls(Name.from_tree(_name), Type.from_tree(_type))

    def pretty(self) -> str:
        return f"ext {self.name.pretty()} {self.type.pretty()}"


class VarDefExpl(TreeNode):
    def __init__(self, _name: Name, _type: Type, _expr: Expression) -> None:
        self.name = _name
        self.type = _type
        self.expr = _expr

    @classmethod
    def from_tree(cls, node: lark.Tree[lark.Token]) -> "VarDefExpl":
        if node.data != "var_def_expl":
            raise TreeErr()
        _name, _type, _expr = node.children
        if _name.data != "name":
            raise TreeErr()
        if _type.data != "type":
            raise TreeErr()
        elif _expr.data != "expression":
            raise TreeErr()

        return cls(
            Name.from_tree(_name), Type.from_tree(_type), Expression.from_tree(_expr)
        )

    def pretty(self) -> str:
        return f"let {self.name.pretty()} {self.type.pretty()} = {self.expr.pretty()}"


class VarDefImpl(TreeNode):
    def __init__(self, _name: Name, _expr: Expression) -> None:
        self.name = _name
        self.expr = _expr

    @classmethod
    def from_tree(cls, node: lark.Tree[lark.Token]) -> "VarDefImpl":
        if node.data != "var_def_impl":
            raise TreeErr()
        _name, _expr = node.children
        if _name.data != "name":
            raise TreeErr()
        elif _expr.data != "expression":
            raise TreeErr()

        return cls(Name.from_tree(_name), Expression.from_tree(_expr))

    def pretty(self) -> str:
        return f"let {self.name.pretty()} = {self.expr.pretty()}"


class ConstDef(TreeNode):
    def __init__(self, _name, _type, _expr: Expression) -> None:
        self.name = _name
        self.type = _type
        self.expr = _expr

    @classmethod
    def from_tree(cls, node: lark.Tree[lark.Token]) -> "ConstDef":
        if node.data != "const_def":
            raise TreeErr()
        _name, _type, _expr = node.children
        if _name.data != "name":
            raise TreeErr()
        if _type.data != "type":
            raise TreeErr()
        if _expr.data != "expression":
            raise TreeErr()
        return cls(
            Name.from_tree(_name), Type.from_tree(_type), Expression.from_tree(_expr)
        )

    def pretty(self) -> str:
        return f"const {self.name.pretty()} {self.type.pretty()} = {self.expr.pretty()}"


class FunDec(TreeNode):
    def __init__(self, _name: Name, _type: FunType) -> None:
        self.name = _name
        self.type = _type

    @classmethod
    def from_tree(cls, node: lark.Tree[lark.Token]) -> "FunDec":
        if node.data != "fun_dec":
            raise TreeErr()
        _name, _fun_type = node.children
        if _name.data != "name":
            raise TreeErr()
        if _fun_type.data != "fun_type":
            raise TreeErr()
        return cls(Name.from_tree(_name), FunType.from_tree(_fun_type))

    def pretty(self) -> str:
        return f"func {self.name.pretty()} {self.type.pretty()}"


class FunDef(TreeNode):
    def __init__(self, _dec: FunDec, _body: list["Statement | Expression"]) -> None:
        self.declaration = _dec
        self.body = _body

    @classmethod
    def from_tree(cls, node: lark.Tree[lark.Token]) -> "FunDef":
        if node.data != "fun_def":
            raise TreeErr()
        _dec = FunDec.from_tree(node.children[0])
        _body = node.children[1:]
        _body_n = []
        _expr_given = False
        for ii in _body:
            if _expr_given:
                raise TreeErr()
            if ii.data == "statement":
                _body_n.append(Statement.from_tree(ii))
            elif ii.data == "expression":
                _expr_given = True
                _body_n.append(Expression.from_tree(ii))
            else:
                raise TreeErr()
        return cls(_dec, _body_n)

    def pretty(self) -> str:
        if len(self.body) > 0:
            b = "{"
            for ii in self.body:
                b += "\n    " + ii.pretty()
            b += "\n}"
            return self.declaration.pretty() + " " + b
        else:
            return self.declaration.pretty() + " {}"


class FunDefNN(TreeNode):
    def __init__(self, _type: FunType, _body: list["Statement | Expression"]) -> None:
        self.type = _type
        self.body = _body

    @classmethod
    def from_tree(cls, node: lark.Tree[lark.Token]) -> "FunDefNN":
        _type = FunType.from_tree(node.children[0].children[0])
        _body = node.children[1:]
        _body_n = []
        _expr_given = False
        for ii in _body:
            if _expr_given:
                raise TreeErr()
            if ii.data == "statement":
                _body_n.append(Statement.from_tree(ii))
            elif ii.data == "expression":
                _expr_given = True
                _body_n.append(Expression.from_tree(ii))
            else:
                raise TreeErr()
        return cls(_type, _body_n)

    def pretty(self) -> str:
        if len(self.body) > 0:
            b = "{"
            for ii in self.body:
                b += "\n    " + ii.pretty()
            b += "\n}"
            return "func " + self.type.pretty() + " " + b
        else:
            return "func " + self.type.pretty() + " {}"


class Statement(TreeNode):
    child: Expression | VarDecLet | VarDecExt | VarDefExpl | VarDefImpl | ConstDef | FunDec | FunDef | FunDefNN

    def __init__(self, child):
        self.child = child

    @classmethod
    def from_tree(cls, node: lark.Tree[lark.Token]) -> "Statement":
        if node.data != "statement":
            raise TreeErr()

        n = node.children[0]
        if n.data == "expression":
            return cls(Expression.from_tree(n))
        elif n.data == "var_dec_let":
            return cls(VarDecLet.from_tree(n))
        elif n.data == "var_dec_ext":
            return cls(VarDecExt.from_tree(n))
        elif n.data == "var_def_expl":
            return cls(VarDefExpl.from_tree(n))
        elif n.data == "var_def_impl":
            return cls(VarDefImpl.from_tree(n))
        elif n.data == "const_def":
            return cls(ConstDef.from_tree(n))
        elif n.data == "fun_dec":
            return cls(FunDec.from_tree(n))
        elif n.data == "fun_def":
            return cls(FunDef.from_tree(n))
        elif n.data == "fun_def_nn":
            return cls(FunDefNN.from_tree(n))
        else:
            raise Exception("Unreachable")

    def pretty(self) -> str:
        return self.child.pretty() + ";"


class Script(TreeNode):
    def __init__(self, *statement: Statement):
        self.statements = list(statement)

    @classmethod
    def from_tree(cls, node: lark.Tree[lark.Token]) -> "Script":
        if node.data != "script":
            raise TreeErr()

        children = []
        for statement in node.children:
            if not isinstance(statement, lark.Tree):  # type checks
                raise TreeErr()

            if statement.data == "statement":
                children.append(Statement.from_tree(statement))
            else:
                raise TreeErr()
        return cls(*children)

    def pretty(self) -> str:
        return "".join(ii.pretty() + "\n" for ii in self.statements)
