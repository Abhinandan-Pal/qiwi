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
    index: int

    def __init__(self, name: str, index: int) -> None:
        self.name = name
        self.index = index

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.name}_[{self.index}])"

    def count_var_use(self):
        return [('R',str(self.index)+self.name)]

    def generate(self, context: qiwicg.Context) -> qiwicg.QBlock:
        block = qiwicg.QBlock()
        block.output = [context.lookup_variable(self.name)[self.index]]
        return block

class ASTInt(ASTExp):
    value: int

    def __init__(self, value: int) -> None:
        self.value = value

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.value})"

    def count_var_use(self):
        return None

    def generate(self, context: qiwicg.Context) -> int:
        binary = bin(self.value)[2:]
        size = len(binary)
        block = qiwicg.QBlock()
        location = list(range(context.used_qbits, context.used_qbits + size))
        context.used_qbits += size
            # set 1 bits
        for i in range(0, size):
            if (self.value >> i) & 1 == 1:
                block.add(qiwicg.QGate('x', [location[i]]))
        block.output = location
        return block

class ASTIf_qc(ASTExp):
    left_cond: Type[ASTIndexedID]
    right_cond: Type[ASTIndexedID]
    op_cond: str
    target_func: Type[ASTFuncCall]

    def __init__(self, control_tuple, target_func):
        self.left_cond,self.op_cond,self.right_cond = control_tuple
        self.target_func = target_func

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.left_cond},{self.op_cond},{self.right_cond},{self.target_func})"

    def count_var_use(self):
        val = []
        if(self.left_cond.count_var_use() != None):
            val += self.left_cond.count_var_use()
        if(self.right_cond != None):    
            if(self.right_cond.count_var_use() != None):
                val += self.right_cond.count_var_use()
        if(self.target_func.count_var_use() != None):
            val += self.target_func.count_var_use()
        return val
    def generate(self, context: qiwicg.Context, qf : qiwicg.QFunction) -> qiwicg.QBlock:
        block = qiwicg.QBlock()
        #if(self.target_func != Type[ASTFuncCall]):                 #FIX THIS ERROR ALERT
           # raise RuntimeError("Target of if_qc must be a Gate on a qubit")
        t_func_name = self.target_func.name
        t_func_args = self.target_func.args

        # Add cool syntax error detection stuff
        func = context.lookup_function(t_func_name.name, self.target_func.name_space)
        left_cond_block = self.left_cond.generate(context)
        if(self.right_cond != None):
            right_cond_block = self.right_cond.generate(context)
            block.append(right_cond_block)
        block.append(left_cond_block)
        

        argloc = []
        for arg in t_func_args:
            argblock = arg.generate(context)
            if(type(argblock) == int):
                raise RuntimeError("Only variables can be placed in function")
            block.append(argblock)
            argloc.append(argblock.output)
        t_func_name = t_func_name.name.lower()

        if len(argloc) != 1:
            raise RuntimeError(f"Target expects 1 arguments, {len(argloc)} provided")
        
        if len(argloc[0]) != 1 :
            raise RuntimeError(f"Target argument expected to be 1 qubit, {len(argloc[0])} provided")
        
        if(self.op_cond == 'SINGLE'):
            cgate = 'c'+t_func_name   
            block.add(qiwicg.QGate(cgate, [left_cond_block.output[0],argloc[0][0]]))

        if(self.op_cond == 'xor'):
            cgate = 'c'+t_func_name   
            block.add(qiwicg.QGate(cgate, [left_cond_block.output[0],argloc[0][0]]))
            block.add(qiwicg.QGate(cgate, [right_cond_block.output[0],argloc[0][0]]))

        if(self.op_cond == 'xnor'):
            cgate = 'c'+t_func_name   
            block.add(qiwicg.QGate(cgate, [left_cond_block.output[0],argloc[0][0]]))
            block.add(qiwicg.QGate(cgate, [right_cond_block.output[0],argloc[0][0]]))
            block.add(qiwicg.QGate('x',[argloc[0][0]]))

        if(self.op_cond == 'and'):
            cgate = 'cc'+t_func_name   
            block.add(qiwicg.QGate(cgate, [left_cond_block.output[0],right_cond_block.output[0],argloc[0][0]]))
        
        if(self.op_cond == 'or'):
            cgate = 'cc'+t_func_name  
            block.add(qiwicg.QGate('x',[left_cond_block.output[0]])) 
            block.add(qiwicg.QGate('x',[right_cond_block.output[0]]))  
            block.add(qiwicg.QGate(cgate, [left_cond_block.output[0],right_cond_block.output[0],argloc[0][0]]))
            block.add(qiwicg.QGate('x',[left_cond_block.output[0]])) 
            block.add(qiwicg.QGate('x',[right_cond_block.output[0]]))
            block.add(qiwicg.QGate('x',[argloc[0][0]]))
        
        if(self.op_cond == 'nor'):
            cgate = 'cc'+t_func_name 
            block.add(qiwicg.QGate('x',[left_cond_block.output[0]])) 
            block.add(qiwicg.QGate('x',[right_cond_block.output[0]])) 
            block.add(qiwicg.QGate(cgate, [left_cond_block.output[0],right_cond_block.output[0],argloc[0][0]]))
            block.add(qiwicg.QGate('x',[left_cond_block.output[0]])) 
            block.add(qiwicg.QGate('x',[right_cond_block.output[0]])) 

        if(self.op_cond == 'nand'):
            cgate = 'cc'+t_func_name   
            block.add(qiwicg.QGate(cgate, [left_cond_block.output[0],right_cond_block.output[0],argloc[0][0]]))
            block.add(qiwicg.QGate('x',[argloc[0][0]]))
            block.output = argloc[0]
        return block

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
        #print(f'RESULT : {a}')
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
            if(sta.count_var_use() != None):
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
            if(arg.count_var_use() != None):
                result+= arg.count_var_use()
        return result

    def generate(self, context: qiwicg.Context) -> qiwicg.QBlock:
        block = qiwicg.QBlock()
        
        argloc = []
        for arg in self.args:
            argblock = arg.generate(context)
            if(type(argblock) == int):
                raise RuntimeError("Only variables can be placed in function")
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
    type: Type[ASTTypeQ]
    index: int
    def __init__(self, lhs: ASTID, rhs: Type[ASTExp], index: int = None ,type: Optional[ASTTypeQ] = None) -> None:
        self.lhs = lhs
        self.rhs = rhs
        self.type = type
        self.index = index

    def __repr__(self) -> str:
        if(self.index != None):
            return f"{self.__class__.__name__}({self.lhs}, {self.rhs},{self.index},{self.type})"
        else:
            return f"{self.__class__.__name__}({self.lhs}, {self.rhs},{self.type})"

    def count_var_use(self):
        result: list[(str,str)]
        result = []
        if(self.rhs.count_var_use() != None):
            for var in self.rhs.count_var_use():
                result += [var]
        if(self.index == None):
            result += [("W",self.lhs.name)]
        else:
            result += [("PW",str(self.index)+self.lhs.name)]    #a particular index of name is rewritten
        return result


    def generate(self, context: qiwicg.Context, qf : qiwicg.QFunction) -> qiwicg.QBlock:
        block = qiwicg.QBlock()
        print(f"BEFORE: {context.scope}->{qf.var_read_write}")
        flag = False
        if(self.rhs.count_var_use() != None):
            for var in self.rhs.count_var_use():
                qf.var_list_remove(var)
        if(self.index == None):
            qf.var_list_remove(("W",self.lhs.name))
        else:
            qf.var_list_remove(("PW",str(self.index)+self.lhs.name))    #a particular index of name is rewritten
        
        if(qf.var_can_kill(self.lhs.name)):
            if(self.index == None):
                print(f"Dont create: {self.lhs.name}")
            else:
                print(f"Don't create: {self.lhs.name}'s {self.index} qubit")
            return block
        else:
            if(self.index == None):
                print(f"Create: {self.lhs.name}")
            else:
                print(f"Create: {self.lhs.name}'s {self.index} qubit")

        if(self.rhs.count_var_use() != None):
            for var in self.rhs.count_var_use():
                
                r_w,var_name = var
                if(qf.var_can_kill(var_name)):
                    print(f"Kill: {var_name}")
                elif(var_name == self.lhs.name):
                    print(f"Update: {var_name}")
                else:
                    var_loc = context.lookup_variable(var_name)
                    var_copy_loc = context.allocate_qbits(len(var_loc))
                    for i in range(len(var_loc)):
                        block.add(qiwicg.QGate('cx', [var_loc[i], var_copy_loc[i]]))
                    context.set_variable((var_name+":temp"), var_copy_loc)
                    print(f"Persist: {var_name}")
        print(f"MIDDLE: {context.scope}->{qf.var_read_write}")


        rhs = self.rhs.generate(context)
        if isinstance(rhs, int): # constant integer
            pass
        elif isinstance(rhs, list): # variable location reference
            location = rhs
        elif isinstance(rhs, qiwicg.QBlock):
            location = rhs.output
            block.append(rhs)
            if isinstance(self.type, ASTTypeQ):
                diff = self.type.length - len(location)
                if diff < 0:
                    raise RuntimeError(f"Type {self.type} not large enough to store {len(location)} qubits")
                else:
                    location += context.allocate_qbits(diff)
        else:
            raise RuntimeError("Unimplemented!")

        if(self.index != None):
            if(len(location)!= 1):
                raise RuntimeError(f"1 qubit expected for indexed assignment.{len(location)} qubits provided")
            context.set_var_index(self.lhs.name, location[0], self.index)
        else:
            context.set_variable(self.lhs.name, location)
        temp_var = []
        for key in context.scope:
            if(key.endswith(":temp")):
                temp_var.append(key)

        for key in temp_var:
            loc = context.scope.pop(key)
            key = key[:key.index(":temp")]
            context.set_variable(key, loc)
        print(f"END: {context.scope}->{qf.var_read_write}")
        return block

