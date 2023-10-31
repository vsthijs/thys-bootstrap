"""Checks the ast from lark, and converts it into something that the compiler and interpreter can understand"""
from typing import Optional

import lark


class TreeErr(Exception):
    pass


class TreeNode:
    @classmethod
    def from_tree(cls, node: lark.Tree[lark.Token]) -> "TreeNode":
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
        except ValueError:
            self.value = float(_value)

    @classmethod
    def from_tree(cls, node: lark.Tree[lark.Token]) -> "Integer":
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

    @classmethod
    def from_tree(cls, node: lark.Tree[lark.Token]) -> "FunType":
        global Type
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
    def __init__(self, op: str, left: "Expression", right: "Expression") -> None:
        self.op = op
        self.left = left
        self.right = right

    @classmethod
    def from_tree(cls, node: lark.Tree[lark.Token]) -> "BinaryOp":
        global Expression

        if node.children[1].type != "BINARY_OP":
            raise TreeErr()

        left_src, op_src, right_src = node.children
        left = Expression(left_src)
        right = Expression(right_src)
        return cls(op_src.value, left, right)

    def pretty(self) -> str:
        # FIXME: does not format correctly
        return f"{self.left.pretty()} {self.op} {self.right.pretty()}"


class Expression(TreeNode):
    child: String | Number | Name | Type | BinaryOp

    def __init__(self, child) -> None:
        self.child = child

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
            return cls(BinaryOp.from_tree(node))

        print(f"[unhandled] expression / {node.pretty()}")

    def pretty(self) -> str:
        return self.child.pretty()


class Statement(TreeNode):
    child: Expression

    def __init__(self, child: Expression):
        self.child = child

    @classmethod
    def from_tree(cls, node: lark.Tree[lark.Token]) -> "Statement":
        if node.data != "statement":
            raise TreeErr()

        n = node.children[0]
        if n.data == "expression":
            return cls(Expression.from_tree(n))

    def pretty(self) -> str:
        return self.child.pretty() + ";\n"


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
        return "".join(ii.pretty() for ii in self.statements)
