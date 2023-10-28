import os
from sys import argv

from thyson_parser import Parser

DBG_AST: bool = False


def print_help():
    print("""thyson help
usage:
    thyson <file> [options] - run/compile a file.
    thyson ( -h | --help )  - display this help message.
    thyson ( -v | --version)- display the version of the compiler.
    thyson --test           - run all tests from a 'tests' directory.

options:
    --dbg-ast               - !! FOR DEBUG PURPOSES !!
                            parse the file and displays the ast.
""")


def test_file(file: str):
    with open(file, "r") as f:
        p = Parser(_file=(f.read(), f.name))
    try:
        print(f"[test] {file}: (p)", end="")
        p.parse_any()
        print("\b\b\bOk")
        return True
    except Exception as e:
        print(f"\b\b\bfailed: {e}")
        return False


def test_all():
    if "tests" in os.listdir() and os.path.isdir("tests"):  # test directory found
        results: list[int, int, int] = [0, 0, 0]
        for ii in os.listdir("tests"):
            path = os.path.join("tests", ii)
            results[0] += 1
            if test_file(path):
                results[1] += 1
            else:
                results[2] += 1
        print("[info] === results ===")
        print(f"[info] ran {results[0]} tests, of which {results[1]} where successful, and {results[2]} failed.")
    else:
        print("[fatal] tests directory not found")


def main() -> None:
    global DBG_AST
    prog, args = argv[0], argv[1:]

    opts = {
        "help": False,
        "file": None,
        "test": False,
        "dbg-ast": False,
    }
    for ii in args:
        if ii == "--test":
            opts["test"] = True
        elif ii in ["-h", "--help"]:
            opts["help"] = True
        elif ii == "--dbg-ast":
            opts["dbg-ast"] = True
        elif not opts["file"]:
            opts["file"] = ii

    if opts["dbg-ast"]:
        DBG_AST = True

    if opts["help"]:
        print_help()
    elif opts["test"]:
        test_all()
    elif not opts["file"]:
        print("[fatal] no input files given")


if __name__ == "__main__":
    main()
