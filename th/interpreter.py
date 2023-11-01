from .ptree import *


class CompileErr(Exception):
    pass


Unreachable = Exception("Unreachable")


class InstructionType(Enum):
    DeclareVariable = auto()
    DeclareExtern = auto()
    DefineVariable = auto()


class Instruction:
    def __init__(self, action: InstructionType, *args):
        self.action = action
        self.args = list(args)


class Scope:
    locals: dict[str, DataType]
    globals: dict[str, DataType]
    instructions: list[Instruction]

    def __init__(self, **_globals: DataType) -> None:
        self.globals = dict(**_globals)
        self.locals = {}
        self.instructions = []

    def declare_local(self, _name: str, _type: DataType) -> None:
        self.locals[_name] = _type

    def add_instruction(self, _instruction: Instruction) -> None:
        self.instructions.append(_instruction)
        match _instruction.action:
            case InstructionType.DeclareVariable:
                self.declare_local(*_instruction.args)
            case InstructionType.DeclareExtern:
                self.declare_local(*_instruction.args)
            case InstructionType.DefineVariable:
                self.declare_local(_instruction.args[0], _instruction.args[1])

    def new_sub_scope(self) -> "Scope":
        return self.__class__(**self.globals, **self.locals)

    def __getitem__(self, item: str) -> DataType:
        if item in self.locals.keys():
            return self.locals[item]
        elif item in self.globals.keys():
            return self.globals[item]
        raise KeyError(item)

    def compile(self, *_statements: Statement) -> None:
        for statement in _statements:
            match statement.child.__class__.__name__:
                case "Expression":  # compile expression
                    pass
                case "VarDecLet":
                    _node: VarDecLet = statement.child
                    self.add_instruction(
                        Instruction(
                            InstructionType.DeclareVariable,
                            _node.name.value,
                            _node.type.type,
                        )
                    )
                case "VarDecExt":
                    _node: VarDecExt = statement.child
                    self.add_instruction(
                        Instruction(
                            InstructionType.DeclareExtern,
                            _node.name.value,
                            _node.type.type,
                        )
                    )
                case "VarDefExpl":
                    _node: VarDefExpl = statement.child
                    self.add_instruction(
                        Instruction(
                            InstructionType.DefineVariable,
                            _node.name.value,
                            _node.type.type,
                            _node.expr,
                        )
                    )
                case "VarDefImpl":
                    raise NotImplementedError()  # TODO: implement
                case "ConstDef":
                    raise NotImplementedError()  # TODO: implement
                case "FunDec":
                    raise NotImplementedError()  # TODO: implement
                case "FunDef":
                    raise NotImplementedError()  # TODO: implement
                case "FunDefNN":
                    raise NotImplementedError()  # TODO: implement
                case _:
                    raise Unreachable


def new_scope() -> Scope:
    return Scope(int=DataType.builtin(BuiltinType.type))
