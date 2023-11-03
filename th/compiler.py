"""
Replaces ptree.py

compiles the AST (from lark) to llvm ir (with llvmlite)
"""

from dataclasses import dataclass
from typing import Optional

import lark
from llvmlite import ir

FUNCTION_COUNTER: int = 0

BUILTIN_TYPES: dict[str, ir.Type] = {
    "u8": ir.IntType(8),
    "i8": ir.IntType(8),
    "u16": ir.IntType(16),
    "i16": ir.IntType(16),
    "u32": ir.IntType(32),
    "i32": ir.IntType(32),
    "u64": ir.IntType(64),
    "i64": ir.IntType(64),
    "f16": ir.HalfType(),
    "f32": ir.FloatType(),
    "f64": ir.DoubleType(),
    "none": ir.VoidType(),
}


@dataclass
class Value:
    value: ir.Value
    type: ir.Type
    const: bool = False


class Function:
    def __init__(self, ast: lark.Tree[lark.Token]) -> None:
        self.ast = ast
        self.name: Optional[str] = None
        self.module: Optional[ir.Module] = None
        self.locals: dict[str, Value] = {}

    def llvm_type(self) -> ir.FunctionType:
        fun_type = self.function_type()
        return ir.FunctionType(fun_type[1], [pair[1] for pair in fun_type[0]])

    def function_type(self) -> tuple[list[tuple[str, ir.Type]], ir.Type]:
        declaration = self.ast.children[0]
        self.name, fun_type = declaration.children[0].children[0].value, declaration.children[1]
        argument_list = fun_type.children.copy()
        args: list[tuple[str, ir.Type]] = []
        return_type: ir.Type = ir.VoidType()
        while len(argument_list) > 0:
            if (tok_name := argument_list.pop(0)).data == "name":
                args.append((tok_name.children[0].value, self.resolve_type(argument_list.pop(0))))
            elif tok_name.data == "type":  # return type
                return_type = self.resolve_type(tok_name)

        return args, return_type

    def resolve_type(self, tok_type: lark.Tree[lark.Token]) -> ir.Type:
        type_name = tok_type.children[0].children[0].value
        if type_name in BUILTIN_TYPES.keys():
            return BUILTIN_TYPES[type_name]
        # elif self.module:  # TODO: lookup user-defined type
        else:
            raise Exception(f"unknown type '{type_name}'")

    def resolve_name(self, name: str) -> Value:
        if name in self.locals.keys():
            return self.locals[name]
        elif self.module and name in [_n.name for _n in self.module.functions]:
            for fn in self.module.functions:
                if fn.name == name:
                    return Value(fn.type, fn)
        else:
            raise Exception(f"unknown name '{name}'")

    def as_value(self, builder: ir.IRBuilder, expr: lark.Tree[lark.Token]) -> Value:
        """Parse the expression and return a value that llvm understands."""
        mod: ir.Module = builder.module
        fn: ir.Function = builder.function
        if expr.data != "expression":
            raise Exception(f"require expression, got {expr.pretty()}")

        if expr.children[0].data == "string":
            raise NotImplementedError()
        elif expr.children[0].data == "integer":
            tok_int = expr.children[0]
            _int = tok_int.children[0].value
            return Value(ir.Constant(BUILTIN_TYPES["i32"], int(_int)), BUILTIN_TYPES["i32"])
        elif expr.children[0].data == "decimal":
            raise NotImplementedError()
        elif expr.children[0].data == "fun_call":
            print(expr.pretty())
            _name = expr.children[0].children[0].children[0].value
            _args = self._ast_fun_call_args(builder, expr.children[0])  # TODO: implement Function._ast_fun_call_args
            _func: ir.Function = self.resolve_name(_name).type  # type: ignore
            print(f"{_name}({_args})")
            return Value(_func.ftype.return_type, builder.call(_func, _args))
        elif expr.children[0].data == "name":
            _name = expr.children[0].children[0].value
            return self.resolve_name(_name)
        elif expr.children[0].data == "type":
            raise NotImplementedError()
        elif expr.children[0].data == "expression" and len(expr.children) == 1:
            return self.as_value(builder, expr.children[0])
        elif expr.children[0].data == "expression" and len(expr.children) == 3:
            _left = self.as_value(builder, expr.children[0])
            _right = self.as_value(builder, expr.children[2])
            match expr.children[1].value:
                case "+":
                    if isinstance(_left.type, ir.IntType):
                        return Value(builder.add(_left.value, _right.value), _left.type)
                    else:
                        raise NotImplementedError()
                case "-":
                    if isinstance(_left.type, ir.IntType):
                        return Value(builder.sub(_left.value, _right.value), _left.type)
                    else:
                        raise NotImplementedError()

    def compile(self, module: ir.Module) -> None:
        global FUNCTION_COUNTER
        FUNCTION_COUNTER += 1

        _llvm_type = self.llvm_type()
        _func_type = self.function_type()
        self.module = module
        func = ir.Function(module, _llvm_type, self.name)
        block = func.append_basic_block("entry")

        for _index, (_name, _type) in enumerate(_func_type[0]):
            self.locals[_name] = Value(func.args[_index], _type)
            # print(f"{_name} {_type} = {func.args[_index]}")

        builder = ir.IRBuilder(block)
        body = self.ast.children[1:]
        for ii in body:
            if ii.data == "statement":
                if ii.children[0].data == "expression":
                    self.as_value(builder, ii.children[0])
                elif ii.children[0].data == "var_dec_let":
                    tok_name, tok_type = ii.children[0].children
                    _name = tok_name.children[0].value
                    _type = self.resolve_type(tok_type)
                    self.locals[_name] = Value(builder.alloca(_type, name=_name), _type)
                elif ii.children[0].data == "var_def_expl":
                    tok_name, tok_type, tok_expr = ii.children[0].children
                    _name = tok_name.children[0].value
                    _type = self.resolve_type(tok_type)
                    _expr = self.as_value(builder, tok_expr)
                    self.locals[_name] = Value(builder.alloca(_type, name=_name), _type)
                    builder.store(_expr, self.locals[_name])
                elif ii.children[0].data == "const_def":
                    tok_name, tok_type, tok_expr = ii.children[0].children
                    _name = tok_name.children[0].value
                    _type = self.resolve_type(tok_type)
                    _expr = self.as_value(builder, tok_expr)
                    self.locals[_name] = Value(_expr, _type, True)
                else:
                    raise NotImplementedError()
            elif ii.data == "expression":
                builder.ret(self.as_value(builder, ii).value)
                return
        builder.ret_void()


def compile_module(name: str, ast: lark.Tree[lark.Token]) -> ir.Module:
    ll_mod = ir.Module(name)

    for ii in ast.children:
        node = ii.children[0]
        match node.data:
            case "fun_def":
                fn = Function(node)
                fn.compile(ll_mod)

            case unhandled:
                print(f"[unhandled][compiler] {unhandled}")

    return ll_mod
