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
        #print(f"Gate Init:{self.name}({self.connections})")

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
        asmcode = f"\n\n\nOPENQASM 2.0;\ninclude \"qelib1.inc\";\n\nqreg q[{context.used_qbits}];\n\n"
        for gate in self.gates:
            line = f"{gate.name}"
            
            for c in gate.connections:
                line += f" q[{c}],"

            line = line[:-1] + ";\n"
            
            asmcode += line

        return asmcode


class QFunction:
    definition: qiwiast.ASTFuncDef
    var_read_write: List[(str,str)]

    def __init__(self, function: qiwiast.ASTFuncDef) -> None:
        self.definition = function
        self.var_read_write = function.count_var_use()
        print(f"var_read_write:[{self.definition.name.name}]")
        print(self.var_read_write)

    def var_can_kill(self,var:str):
        for entry in self.var_read_write:
            if(entry == ('W',var)):
                return True 
            elif(entry == ('R',var)):
                return False
        return True 

    def var_list_remove(self,element:(str,str)):
        self.var_read_write.remove(element)

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
            block.append(statement.generate(context,self))
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

def builtin_h(args: list[list[int]]) -> QBlock:
    block = QBlock()

    if len(args) != 1:
        raise RuntimeError(f"h expects 1 arguments, {len(args)} provided")

    for bit in args[0]:
        block.add(QGate('h', [bit]))

    block.output = args[0]
    
    return block

def builtin_cx(args: list[list[int]]) -> QBlock:
    block = QBlock()

    if len(args) != 2:
        raise RuntimeError(f"CNOT expects 2 arguments, {len(args)} provided")
    if(len(args[0]) != len(args[1])):
        raise RuntimeError(f"CNOT expects 2 arguments of same size, {len(args[0])} and {len(args[1])} provided")
    for pos in len(args[0]):
        block.add(QGate('h', [args[0][pos],args[1][pos]]))

    block.output = args[1]      # IS THIS CORRECT?
    
    return block


def builtin_ccx(args: list[list[int]]) -> QBlock:
    block = QBlock()

    if len(args) != 3:
        raise RuntimeError(f"CNOT expects  arguments, {len(args)} provided")
    if(len(args[0]) != len(args[1])) & (len(args[0]) != len(args[2])):
        raise RuntimeError(f"CNOT expects 3 arguments of same size, {len(args[0])} , {len(args[1])} , {len(args[2])} qubit provided")
    for pos in len(args[0]):
        block.add(QGate('h', [args[0][pos],args[1][pos]]))

    block.output = args[2]      # IS THIS CORRECT?
    
    return block

builtin_functions = {
    'X': QDynamicFunction(builtin_x),
    'H': QDynamicFunction(builtin_h),
    'CX': QDynamicFunction(builtin_h),
    'CXX': QDynamicFunction(builtin_h),
}


class Context:
    functions: dict[(str,str), QFunction]      # name,name_space to function
    used_qbits: int
    scope: dict[str, list[int]]
    current_name_space: str

    def __init__(self) -> None:
        self.functions = {}
        self.used_qbits = 0
        self.scope = {}

    def allocate_qbits(self, n: int) -> list[int]:
        bits = list(range(self.used_qbits, self.used_qbits + n))
        self.used_qbits += n
        return bits

    def add_function(self, name: str, function: QFunction):
        self.functions[(name, self.current_name_space)] = function

    def lookup_function(self, name: str , name_space: Optional[str] = "self" ) -> QFunction | QDynamicFunction:
        if builtin_functions.get(name):
            return builtin_functions[name]
        
        if self.functions.get((name,name_space)):
            return self.functions[(name,name_space)]

        raise RuntimeError(f"Cannot find function named: {name}")

    def set_variable(self, name: str, location: list[int]) -> None:
        self.scope[name] = location

    def set_var_index(self, name: str, loc_num: int, loc_pos:int) -> None:
        print(f"SCOPEcq: {self.scope} loc_num = {loc_num} loc_pos = {loc_pos}")
        mod = self.scope[name]
        mod[loc_pos] = loc_num
        self.scope[name] = mod
        print(f"SCOPEcq: {self.scope} loc_num = {loc_num} loc_pos = {loc_pos}")
    
    def free_variable(self,name):
        pass
    def free_location(self,name):
        pass
    def delete_variable(self, name: str) -> None:
        del self.scope[name]

    def lookup_variable(self, name: str) -> list[int]:
        if self.scope.get(name):
            return self.scope[name]

        raise RuntimeError(f"Cannot find variable named: {name}")

def generate(ast: list[qiwiast.ASTNode], context: Context):
    for node in ast:
        if isinstance(node, qiwiast.ASTFuncDef):
            cast(qiwiast.ASTFuncDef, node).generate(context)
        else:
            raise RuntimeError(f"Unknown top level declaration: {node}")
