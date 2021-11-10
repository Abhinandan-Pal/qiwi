'''from . import qiwicg
from typing import Callable, cast, Optional
def builtin_x(args: list[list[int]]) -> qiwicg.QBlock:
    block = qiwicg.QBlock()

    if len(args) != 1:
        raise RuntimeError(f"x expects 1 arguments, {len(args)} provided")
    for bit in args[0]:
        block.add(qiwicg.QGate('x', [bit]))

    block.output = args[0]
    
    return block

def builtin_h(args: list[list[int]]) -> qiwicg.QBlock:
    block = qiwicg.QBlock()

    if len(args) != 1:
        raise RuntimeError(f"h expects 1 arguments, {len(args)} provided")

    for bit in args[0]:
        block.add(qiwicg.QGate('h', [bit]))

    block.output = args[0]
    
    return block

def builtin_cx(args: list[list[int]]) -> qiwicg.QBlock:
    block = qiwicg.QBlock()

    if len(args) != 2:
        raise RuntimeError(f"CNOT expects 2 arguments, {len(args)} provided")
    if(len(args[0]) != len(args[1])):
        raise RuntimeError(f"CNOT expects 2 arguments of same size, {len(args[0])} and {len(args[1])} provided")
    for pos in len(args[0]):
        block.add(qiwicg.QGate('h', [args[0][pos],args[1][pos]]))

    block.output = args[1]      # IS THIS CORRECT?
    
    return block

def builtin_cx(args: list[list[int]]) -> qiwicg.QBlock:
    block = qiwicg.QBlock()

    if len(args) != 2:
        raise RuntimeError(f"CNOT expects 2 arguments, {len(args)} provided")
    if(len(args[0]) != len(args[1])):
        raise RuntimeError(f"CNOT expects 2 arguments of same size, {len(args[0])} and {len(args[1])} provided")
    for pos in len(args[0]):
        block.add(qiwicg.QGate('h', [args[0][pos],args[1][pos]]))

    block.output = args[1]      # IS THIS CORRECT?
    
    return block

def builtin_ccx(args: list[list[int]]) -> qiwicg.QBlock:
    block = qiwicg.QBlock()

    if len(args) != 3:
        raise RuntimeError(f"CNOT expects  arguments, {len(args)} provided")
    if(len(args[0]) != len(args[1])) & (len(args[0]) != len(args[2])):
        raise RuntimeError(f"CNOT expects 3 arguments of same size, {len(args[0])} , {len(args[1])} , {len(args[2])} qubit provided")
    for pos in len(args[0]):
        block.add(qiwicg.QGate('h', [args[0][pos],args[1][pos]]))

    block.output = args[1]      # IS THIS CORRECT?
    
    return block'''