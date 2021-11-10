from __future__ import annotations
from typing import Optional, Type

from . import qiwicg

class ASTNode:
    pass

class ASTExp(ASTNode):
    def generate(self, _: qiwicg.Context):
        raise NotImplementedError
    def count_var_use(self):
        raise NotImplementedError

class ASTTypeQ(ASTNode):
    length: int

    def __init__(self, length: int) -> None:
        self.length = length

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.length})"

    def count_var_use(self):
        raise NotImplementedError

    def generate(self, _: qiwicg.Context) -> qiwicg.QBlock:
        raise NotImplementedError

class ASTID(ASTExp):
    name: str
    def __init__(self, name: str) -> None:
        self.name = name

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.name})"

    def count_var_use(self):
        return [('R',self.name)]

    def generate(self, context: qiwicg.Context) -> qiwicg.QFunction | qiwicg.QDynamicFunction | qiwicg.QBlock:
        if context.lookup_variable(self.name):
            block = qiwicg.QBlock()
            block.output = context.lookup_variable(self.name)
            return block
        return context.lookup_function(self.name,self.name_space)

class ASTIndexedID(ASTExp):
    name: str

    def __init__(self, name: str, index: int) -> None:
        self.name = name
        self.index = index

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.name})"

    def count_var_use(self):
        return [('R',self.name)]

    def generate(self, context: qiwicg.Context) -> qiwicg.QBlock:
        block = qiwicg.QBlock()
        block.output = context.lookup_variable(self.name)
        return block

class ASTInt(ASTExp):
    value: int

    def __init__(self, value: int) -> None:
        self.value = value

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.value})"

    def count_var_use(self):
        return None

    def generate(self, _: qiwicg.Context) -> int:
        return self.value

class ASTExpBinary(ASTExp):
    operator: str
    left: Type[ASTExp]
    right: Type[ASTExp]

    def __init__(self, operator: str, left: Type[ASTExp], right: Type[ASTExp]) -> None:
        self.operator = operator
        self.left = left
        self.right = right

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.operator}, {self.left}, {self.right})"

    @staticmethod
    def majority_block(args: list[int]) -> qiwicg.QBlock:
        block = qiwicg.QBlock()

        block.add(qiwicg.QGate('cx', [args[2], args[1]]))
        block.add(qiwicg.QGate('cx', [args[2], args[0]]))
        block.add(qiwicg.QGate('ccx', [args[0], args[1], args[2]]))

        return block

    @staticmethod
    def unmajority_block(args: list[int]) -> qiwicg.QBlock:
        block = qiwicg.QBlock()

        block.add(qiwicg.QGate('ccx', [args[0], args[1], args[2]]))
        block.add(qiwicg.QGate('cx', [args[2], args[0]]))
        block.add(qiwicg.QGate('cx', [args[0], args[1]]))

        return block

    def count_var_use(self):
        result = []
        if(self.left.count_var_use() != None ):
            result += self.left.count_var_use()
        if(self.right.count_var_use() != None): 
            result += self.right.count_var_use()
        return result

    def generate(self, context: qiwicg.Context) -> qiwicg.QBlock:
        block = qiwicg.QBlock()

        a = self.left.generate(context)
        block.append(a)

        b = self.right.generate(context)
        block.append(b)

        if self.operator == '+':
            if(len(a.output) > len(b.output)):
                a,b = b,a

            c0 = context.allocate_qbits(1)[0]
            if(len(a.output) != len(b.output)): 
                an = context.allocate_qbits(1)[0]

            block.append(ASTExpBinary.majority_block([c0, b.output[0], a.output[0]]))
            
            for i in range(1, len(a.output)):
                block.append(ASTExpBinary.majority_block([a.output[i-1], b.output[i], a.output[i]]))
            
            if(len(a.output) != len(b.output)):    
                block.append(ASTExpBinary.majority_block([a.output[len(a.output)-1], b.output[len(a.output)], an]))

            for i in reversed(range(1, len(a.output))):
                block.append(ASTExpBinary.unmajority_block([a.output[i-1], b.output[i], a.output[i]]))
            
            if(len(a.output) != len(b.output)):
                block.append(ASTExpBinary.unmajority_block([a.output[len(a.output)-1], b.output[len(a.output)], an]))

            block.append(ASTExpBinary.majority_block([c0, b.output[0], a.output[0]]))

            block.output = b.output
        elif self.operator == '-':
            if(len(b.output) > len(a.output)):
                raise NotImplementedError("Negative Numbers not implemented")
            elif(len(a.output) > len(b.output)):
                b.output +=  context.allocate_qbits(len(a.output) - len(b.output))
            c0 = context.allocate_qbits(1)[0]

            # carry 1
            block.add(qiwicg.QGate('x', [c0]))
            
            # invert b
            for qb in b.output:
                block.add(qiwicg.QGate('x', [qb]))

            block.append(ASTExpBinary.majority_block([c0, b.output[0], a.output[0]]))
            
            for i in range(1, len(a.output)):
                block.append(ASTExpBinary.majority_block([a.output[i-1], b.output[i], a.output[i]]))
            
            for i in reversed(range(1, len(a.output))):
                block.append(ASTExpBinary.unmajority_block([a.output[i-1], b.output[i], a.output[i]]))
            
            block.append(ASTExpBinary.majority_block([c0, b.output[0], a.output[0]]))

            block.output = b.output

            pass
        else:
            raise RuntimeError("Unknown operator!")

        return block

class ASTStatement(ASTNode):
    def generate(self, _: qiwicg.Context, a: qiwicg.QFunction) -> qiwicg.QBlock:
        raise NotImplementedError

    def count_var_use(self):
        raise NotImplementedError

class ASTFuncDef(ASTNode):
    name: ASTID
    body: list[ASTStatement]
    return_type: Optional[ASTTypeQ]
    args: list[tuple[ASTID, ASTTypeQ]]

    def __init__(self, name: ASTID, return_type: Optional[ASTTypeQ], args: list[tuple[ASTID, ASTTypeQ]], body: list[ASTStatement]) -> None:
        self.name = name
        self.body = body
        self.return_type = return_type
        self.args = args

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.name}, {self.return_type}, {self.args}, {self.body})"

    def count_var_use(self):
        result: list[(str,str)]
        result = []
        for sta in self.body:
            result += sta.count_var_use()
        return result

    def generate(self, context: qiwicg.Context):
        context.add_function(self.name.name, qiwicg.QFunction(self))

class ASTFuncCall(ASTExp):
    name: ASTID
    name_space: str
    args: list[ASTExp]

    def __init__(self, name: ASTID, args: list[ASTExp],name_space: Optional[str] = "self") -> None:
        self.name = name
        self.args = args
        self.name_space = name_space

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.name_space}.{self.name}, {self.args})"

    def count_var_use(self):
        result : [(str,str)]
        result = []
        for arg in self.args:
            result+= arg.count_var_use()
        return result

    def generate(self, context: qiwicg.Context) -> qiwicg.QBlock:
        block = qiwicg.QBlock()
        
        argloc = []
        for arg in self.args:
            argblock = arg.generate(context)
            block.append(argblock)
            argloc.append(argblock.output)
        
        func = context.lookup_function(self.name.name, self.name_space)
        if isinstance(func, qiwicg.QFunction):
            body = func.generate(context, argloc)
        elif isinstance(func, qiwicg.QDynamicFunction):
            body = func.fn(argloc)
        else:
            raise RuntimeError("Unimplemented!")

        block.append(body)
        block.output = body.output

        return block

class ASTAssignment(ASTStatement):
    lhs: ASTID
    rhs: Type[ASTExp]

    def __init__(self, lhs: ASTID, rhs: Type[ASTExp], type: Optional[ASTTypeQ] = None) -> None:
        self.lhs = lhs
        self.rhs = rhs
        self.type = type

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.lhs}, {self.rhs})"

    def count_var_use(self):
        result: list[(str,str)]
        result = []
        if(self.rhs.count_var_use() != None):
            for var in self.rhs.count_var_use():
                result += [var]
        result += [("W",self.lhs.name)]
        return result


    def generate(self, context: qiwicg.Context, qf : qiwicg.QFunction) -> qiwicg.QBlock:
        block = qiwicg.QBlock()
        if(self.rhs.count_var_use() != None):
            for var in self.rhs.count_var_use():
                
                s1,s2 = var
                qf.var_list_remove(var)
                if(qf.var_can_kill(s2)):
                    print(f"Kill: {s2}")
                else:
                    print(f"Persist: {s2}")
                print("Now")
                print(qf.var_read_write)

        qf.var_list_remove(("W",self.lhs.name))
        if(qf.var_can_kill(self.lhs.name)):
            print(f"Dont create: {self.lhs.name}")
            return block
        rhs = self.rhs.generate(context)
        if isinstance(rhs, int): # constant integer
            binary = bin(rhs)[2:]

            # allocate qubits
            if isinstance(self.type, ASTTypeQ):
                size = self.type.length
                if len(binary) > size:
                    raise RuntimeError(f"Type {self.type} not large enough for {rhs}")
            else:
                size = len(binary)

            location = list(range(context.used_qbits, context.used_qbits + size))
            context.used_qbits += size
            
            # set 1 bits
            for i in range(0, size):
                if (rhs >> i) & 1 == 1:
                    block.add(qiwicg.QGate('x', [location[i]]))

        elif isinstance(rhs, list): # variable location reference
            location = rhs
        elif isinstance(rhs, qiwicg.QBlock):
            location = rhs.output
            block.append(rhs)
        else:
            raise RuntimeError("Unimplemented!")

        context.set_variable(self.lhs.name, location)
        return block
