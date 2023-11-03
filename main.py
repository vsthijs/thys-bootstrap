from th import *


def compile_file(_if: str, _of: str) -> None:
    with open(_if) as f:
        obj = compile_ir(str(compile_module(_if, parse(f.read()))))
    with open(_of, "wb") as f:
        f.write(obj)


compile_file("tests/basic.th", "basic.o")
shutdown()
