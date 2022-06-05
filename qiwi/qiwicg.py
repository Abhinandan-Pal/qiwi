from __future__ import annotations
from typing import Callable, cast, Optional

from . import qiwiast
import __main__
from collections import deque

class QGate:
    name: str
    connections: list[int]

    def __init__(self, name, bits) -> None:
        self.name = name
        self.connections = bits

class QGraph:
    
    def __init__(self):
        self.graph = dict()
    
    def addEdge(self,dependent,dependency):
        if not self.graph.get(dependent):
            self.graph[dependent] = [dependency]
        else:
            self.graph[dependent].append(dependency)
    
    def getAllDependencies(self,dependents):
        visited = []
        queue = deque()
        for dependent in dependents:
            queue.append(dependent)
            visited.append(dependent)
        dependencies = dict()
        count = 0
        while (len(queue) > 0):      
            u = queue.popleft()
            dependencies[u] = count
            count += 1
            if(self.graph.get(u) == None):
                continue;
            for itr in self.graph[u]:
                if (itr not in visited):    
                    visited.append(itr)
                    queue.append(itr)
        return dependencies

class QBlock:
    gates: list[QGate]
    output: list[int]
    graph: QGraph

    def __init__(self) -> None:
        self.gates = []
        self.output = []
        self.graph = QGraph()

    def add(self, gate: QGate) -> None:
        self.gates.append(gate)

    def append(self, block: QBlock) -> None:
        self.gates += block.gates
    
    def buildGraph(self):
        for gate in self.gates:
            for loc in gate.connections[:-1]:
                self.graph.addEdge(gate.connections[-1],loc)

    def generate_qasm(self, context: Context) -> str:
        asmcode = f"OPENQASM 2.0;\ninclude \"qelib1.inc\";\n\nqreg q[{context.used_qbits}];\n\n"
        for gate in self.gates:
            line = f"{gate.name}"

            for c in gate.connections:
                line += f" q[{c}],"

            line = line[:-1] + ";\n"

            asmcode += line

        return asmcode


    def generate_qasm_with_infection(self, context: Context, output_lines: list[int]) -> str:
        
        self.buildGraph()
        newQline = self.graph.getAllDependencies(output_lines)
        asmcode = f"OPENQASM 2.0;\ninclude \"qelib1.inc\";\n\nqreg q[{len(newQline)}];\n\n"
        print(f"Mapping --> {newQline}")
        for gate in self.gates:
            line = f"{gate.name}"
            deleteCmd = False
            
            for c in gate.connections:
                if newQline.get(c)==None:
                    deleteCmd = True
                    break
                line += f" q[{newQline[c]}],"
            if deleteCmd:
                continue
            line = line[:-1] + ";\n"

            asmcode += line
        new_output_lines = []
        for output_line in output_lines:
            new_output_lines.append( newQline[output_line])
        return asmcode, new_output_lines


class QFunction:
    definition: qiwiast.ASTFuncDef
    var_read_write: List[(str, int, str)]

    def __init__(self, function: qiwiast.ASTFuncDef) -> None:
        self.definition = function
        self.var_read_write = function.count_var_use()
        __main__.log(f"var_read_write:[{self.definition.name.name}]")
        __main__.log(self.var_read_write)

    def var_can_kill(self, r_w, var: str, index: int):
        #__main__.log(f" {self.var_read_write} [{(r_w,index,var)}]")
        for entry in self.var_read_write:
            r_w_v, index_v, var_v = entry
            if(r_w == 'R' and index == None):
                if(entry == ('W', None, var)):
                    return True
                elif((r_w_v, var_v) == ('R', var)):
                    return False
            elif(r_w == 'W' and index == None):
                if(entry == ('W', None, var)):
                    return True
                elif((r_w_v, var_v) == ('R', var)):
                    return False
            elif(r_w == 'R' and index != None):
                if(entry == ('W', None, var)):
                    return True
                elif(entry == ('R', None, var)):
                    return False
                elif(entry == ('W', index, var)):
                    return True
                elif(entry == ('R', index, var)):
                    return False
            elif(r_w == 'W' and index != None):
                if(entry == ('W', None, var)):
                    return True
                elif(entry == ('R', None, var)):
                    return False
                elif(entry == ('W', index, var)):
                    return True
                elif(entry == ('R', index, var)):
                    return False
        return True

    def var_list_remove(self, element):
        self.var_read_write.remove(element)

    def generate(self, context: Context, args: list[list[int]], name_space = "self") -> QBlock:
        outerscope = context.scope
        outerName_space = context.current_name_space
        outerTypeQnotC = context.type_qnc
        context.scope = {}
        context.type_qnc = {}
        context.current_name_space = name_space

        if len(self.definition.args) != len(args):
            raise RuntimeError(
                f"Function expected {len(self.definition.args)} arguments, {len(args)} provided")

        for n in range(len(args)):
            argdef = self.definition.args[n]
            if argdef[1].length == None:
                pass
            elif argdef[1].length != len(args[n]):
                raise RuntimeError(
                    f"Argument size mismatch for {argdef[0].name} in function {self.definition.name}")
            context.set_variable(argdef[0].name, args[n])
            context.addTypeQnotC(argdef[0].name, argdef[1].QnotC)
            self.var_read_write += [('R',None,argdef[0].name)]

        block = QBlock()
        for statement in self.definition.body[:-1]:
            block.append(statement.generate(context, self))
        last_exp_block = self.definition.body[-1].generate(context, self)
        block.append(last_exp_block)
        block.output = last_exp_block.output

        context.scope = outerscope
        context.type_qnc = outerTypeQnotC
        context.current_name_space = outerName_space
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
        raise RuntimeError(
            f"CNOT expects 2 arguments of same size, {len(args[0])} and {len(args[1])} provided")
    for pos in len(args[0]):
        block.add(QGate('h', [args[0][pos], args[1][pos]]))

    block.output = args[1]      # IS THIS CORRECT?

    return block


def builtin_ccx(args: list[list[int]]) -> QBlock:
    block = QBlock()

    if len(args) != 3:
        raise RuntimeError(f"CNOT expects  arguments, {len(args)} provided")
    if(len(args[0]) != len(args[1])) & (len(args[0]) != len(args[2])):
        raise RuntimeError(
            f"CNOT expects 3 arguments of same size, {len(args[0])} , {len(args[1])} , {len(args[2])} qubit provided")
    for pos in len(args[0]):
        block.add(QGate('h', [args[0][pos], args[1][pos]]))

    block.output = args[2]      # IS THIS CORRECT?

    return block


builtin_functions = {
    'X': QDynamicFunction(builtin_x),
    'H': QDynamicFunction(builtin_h),
    'CX': QDynamicFunction(builtin_h),
    'CXX': QDynamicFunction(builtin_h),
}


class Context:
    # name,name_space to function
    functions: dict[(str, str), list(QFunction)]
    used_qbits: int
    scope: dict[str, list[int]]
    type_qnc: dict[str, bool]  # change to bool for optimization
    current_name_space: str

    def __init__(self) -> None:
        self.functions = {}
        self.used_qbits = 0
        self.scope = {}
        self.type_qnc = {}

    def allocate_qbits(self, n: int) -> list[int]:
        bits = list(range(self.used_qbits, self.used_qbits + n))
        self.used_qbits += n
        return bits

    def add_function(self, name: str, function: QFunction):
        if self.functions.get((name, self.current_name_space)):
            self.functions[(name, self.current_name_space)].append(function)
        else:
            self.functions[(name, self.current_name_space)] = [function]

    def lookup_function(self, name: str, args_call: list(int, bool), name_space: Optional[str] = "self") -> QFunction | QDynamicFunction:
        if builtin_functions.get(name):
            return builtin_functions[name]

        if self.functions.get((name, name_space)):
            scores = []
            fn_index = 0
            for fnc in self.functions.get((name, name_space)):
                score = 0
                arg_index = 0
                for arg in fnc.definition.args:
                    if(arg[2] != args_call[arg_index][1]):
                        if(arg[1].length != None):
                            score -= arg[1].length
                        else:
                            score -= args_call[arg_index][0]
                    else:
                        if(arg[1].length != None):
                            score += arg[1].length
                        else:
                            score += args_call[arg_index][0]
                    arg_index += 1
                scores.append(score)
            __main__.log(f"{name} SCORES: {scores}")
            max_index = scores.index(max(scores))
            return self.functions.get((name, name_space))[max_index]

        raise RuntimeError(f"Cannot find function named: {name}")

    def set_variable(self, name: str, location: list[int]) -> None:
        self.scope[name] = location

    def set_var_index(self, name: str, loc_num: int, loc_pos: int) -> None:
        __main__.log(
            f"SCOPEcq: {self.scope} name = {name} loc_num = {loc_num} loc_pos = {loc_pos}")
        mod = self.scope[name]
        mod[loc_pos] = loc_num
        self.scope[name] = mod
        __main__.log(f"SCOPEcq: {self.scope} loc_num = {loc_num} loc_pos = {loc_pos}")

    def free_variable(self, name):
        pass

    def free_location(self, name):
        pass

    def delete_variable(self, name: str) -> None:
        del self.scope[name] 

    def lookup_variable(self, name: str ) -> list[int]:
        if self.scope.get(name):
            return self.scope[name]

        raise RuntimeError(f"Cannot find variable named: {name} in {self.current_name_space}")

    def addTypeQnotC(self, name: str, val: bool) -> None:
        self.type_qnc[name] = val

    def lookupTypeQnotC(self,name):
        if not self.type_qnc.get(name) == None:
            return self.type_qnc[name]
        raise RuntimeError(f"Cannot find variable named: \'{name}\' in \'{self.current_name_space}\'")

def generate(ast: list[qiwiast.ASTNode], context: Context):
    for node in ast:
        if isinstance(node, qiwiast.ASTFuncDef):
            cast(qiwiast.ASTFuncDef, node).generate(context)
        else:
            raise RuntimeError(f"Unknown top level declaration: {node}")

