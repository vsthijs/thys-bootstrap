"""
This module lets llvm generate object code from the IR
"""

import llvmlite.binding as llvm


def initialize():
    llvm.initialize()
    llvm.initialize_all_targets()
    llvm.initialize_native_target()
    llvm.initialize_all_asmprinters()
    llvm.initialize_native_target()


def compile_ir(_ir: str) -> bytes:
    mod = llvm.parse_assembly(_ir)
    mod.verify()

    target = llvm.Target.from_default_triple()  # compile for self
    machine = target.create_target_machine()
    return machine.emit_object(mod)


def shutdown():
    llvm.shutdown()
