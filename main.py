from th import parse, Script
from th.interpreter import new_scope

with open("tests/all.th") as f:
    script = Script.from_tree(parse(f.read()))

scope = new_scope()
for ii in script.statements:
    scope.compile(ii)
