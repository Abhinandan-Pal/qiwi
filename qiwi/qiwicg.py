from __future__ import annotations
from typing import Callable, cast, Optional

from . import qiwiast
import __main__
class QGate:
    name: str
    connections: list[int]

    def __init__(self, name, bits) -> None:
        self.name = name
        self.connections = bits

class QBlock:
    gates: list[QGate]
    output: list[int]

    def __init__(self) -> None:
        self.gates = []
        self.output = []

    def add(self, gate: QGate) -> None:
        self.gates.append(gate)

    def append(self, block: QBlock) -> None:
        self.gates += block.gates

    def generate_qasm(self, context: Context) -> str:
        asmcode = f"OPENQASM 2.0;\ninclude \"qelib1.inc\";\n\nqreg q[{context.used_qbits}];\n\n"
        for gate in self.gates:
            line = f"{gate.name}"
            
            for c in gate.connections:
                line += f" q[{c}],"

            line = line[:-1] + ";\n"
            
            asmcode += line

        return asmcode

class QFunction:
    definition: qiwiast.ASTFuncDef

    def __init__(self, function: qiwiast.ASTFuncDef) -> None:
        self.definition = function

    def generate(self, context: Context, args: list[list[int]]) -> QBlock:
        outerscope = context.scope
        context.scope = {}

        if len(self.definition.args) != len(args):
            raise RuntimeError(f"Function expected {len(self.definition.args)} arguments, {len(args)} provided")

        for n in range(len(args)):
            argdef = self.definition.args[n]
            if argdef[1].length == None:
                pass
            elif argdef[1].length != len(args[n]):
                raise RuntimeError(f"Argument size mismatch for {argdef[0].name} in function {self.definition.name}")
            context.set_variable(argdef[0].name, args[n])

        block = QBlock()
        for statement in self.definition.body[:-1]:
            block.append(statement.generate(context))
        last_exp_block = self.definition.body[-1].generate(context)
        block.append(last_exp_block)
        block.output = last_exp_block.output

        context.scope = outerscope

        return block

class QDynamicFunction:
    fn: Callable[[list[list[int]]], QBlock]
    def __init__(self, fn) -> None:
        self.fn = fn

def builtin_x(args: list[list[int]]) -> QBlock:
    block = QBlock()

    if len(args) != 1:
        raise RuntimeError(f"x expects 1 arguments, {len(args)} provided")
    for bit in args[0]:
        block.add(QGate('x', [bit]))

    block.output = args[0]
    
    return block

builtin_functions = {
    'x': QDynamicFunction(builtin_x),
}

class Context:
    functions: dict[(str,str), QFunction]      # name,name_space to function
    used_qbits: int
    scope: dict[str, list[int]]

    def __init__(self) -> None:
        self.functions = {}
        self.used_qbits = 0
        self.scope = {}

    def allocate_qbits(self, n: int) -> list[int]:
        bits = list(range(self.used_qbits, self.used_qbits + n))
        self.used_qbits += n
        return bits

    def add_function(self, name: str, function: QFunction):
        self.functions[(name, __main__.current_name_space)] = function

    def lookup_function(self, name: str , name_space: Optional[str] = "self" ) -> QFunction | QDynamicFunction:
        if builtin_functions.get(name):
            return builtin_functions[name]
        
        if self.functions.get((name,name_space)):
            return self.functions[(name,name_space)]

        raise RuntimeError(f"Cannot find function named: {name}")

    def set_variable(self, name: str, location: list[int]) -> None:
        self.scope[name] = location

    def lookup_variable(self, name: str) -> list[int]:
        if self.scope.get(name):
            return self.scope[name]

        raise RuntimeError(f"Cannot find variable named: {name}")

def generate(ast: list[qiwiast.ASTNode]) -> Context:
    context = Context()
    for node in ast:
        if isinstance(node, qiwiast.ASTFuncDef):
            cast(qiwiast.ASTFuncDef, node).generate(context)
        else:
            raise RuntimeError(f"Unknown top level declaration: {node}")

    return context