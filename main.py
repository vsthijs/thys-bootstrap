from th import parse, Script


with open("tests/all.th") as f:
    print(Script.from_tree(parse(f.read())).pretty())
