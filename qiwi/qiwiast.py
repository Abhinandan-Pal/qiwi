from __future__ import annotations
from typing import Optional, Type

from . import qiwicg

class ASTNode:
    pass

class ASTExp(ASTNode):
    def generate(self, _: qiwicg.Context, qf : qiwicg.QFunction):
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

    def generate(self, _: qiwicg.Context, qf : qiwicg.QFunction) -> qiwicg.QBlock:
        raise NotImplementedError

class ASTID(ASTExp):
    name: str
    def __init__(self, name: str) -> None:
        self.name = name

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.name})"

    def count_var_use(self):
        return [('R',None,self.name)]

    def generate(self, context: qiwicg.Context, qf : qiwicg.QFunction) -> qiwicg.QFunction | qiwicg.QDynamicFunction | qiwicg.QBlock:
        if context.lookup_variable(self.name):
            block = qiwicg.QBlock()
            qf.var_list_remove(self.count_var_use()[0])
            block.append(create_temp_var(self,context,qf))
            block.output = context.lookup_variable(self.name)   
            replace_with_temp(self,context,qf)
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
        return [('R',self.index,self.name)]

    def generate(self, context: qiwicg.Context, qf : qiwicg.QFunction) -> qiwicg.QBlock:
        block = qiwicg.QBlock()
        qf.var_list_remove(self.count_var_use()[0])
        block.append(create_temp_var(self,context,qf))
        block.output = [context.lookup_variable(self.name)[self.index]]
        
        replace_with_temp(self,context,qf)
        return block

class ASTInt(ASTExp):
    value: int

    def __init__(self, value: int) -> None:
        self.value = value

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.value})"

    def count_var_use(self):
        return None

    def generate(self, context: qiwicg.Context, qf : qiwicg.QFunction) -> int:
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

class ASTStatement(ASTNode):
    def generate(self, _: qiwicg.Context, qf : qiwicg.QFunction) -> qiwicg.QBlock:
        raise NotImplementedError

    def count_var_use(self):
        raise NotImplementedError
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
        t_func_args = self.target_func.args
        if(self.target_func.count_var_use() != None):
            val += self.target_func.count_var_use()
        for arg in t_func_args:
            if (type(arg) == ASTIndexedID):
                val += [("W",arg.index,arg.name)]
            elif(type(arg) == ASTID):
                val += [("W",None,arg.name)]
        if(self.left_cond.count_var_use() != None):
            val += self.left_cond.count_var_use()
        if(self.left_cond.count_var_use() != None):
            for rw,index,name in self.left_cond.count_var_use():
                val += [("W",index,name)]

        if(self.right_cond != None):    
            if(self.right_cond.count_var_use() != None):
                val += self.right_cond.count_var_use()
            if(self.right_cond.count_var_use() != None):
                for rw,index,name in self.right_cond.count_var_use():
                    val += [("W",index,name)]
        
        

        return val

    def generate(self, context: qiwicg.Context, qf : qiwicg.QFunction) -> qiwicg.QBlock:
        block = qiwicg.QBlock()
        #if(self.target_func != Type[ASTFuncCall]):                 #FIX THIS ERROR ALERT
           # raise RuntimeError("Target of if_qc must be a Gate on a qubit")
        t_func_name = self.target_func.name
        t_func_args = self.target_func.args

        # Add cool syntax error detection stuff
        func = context.lookup_function(t_func_name.name, self.target_func.name_space)
        left_cond_block = self.left_cond.generate(context,qf)

        

        argloc = []
        for arg in t_func_args:
            argblock = arg.generate(context,qf)
            if(type(argblock) == int):
                raise RuntimeError("Only variables can be placed in function")
            block.append(argblock)
            argloc.append(argblock.output)
        t_func_name = t_func_name.name.lower()

        if(self.right_cond != None):
            right_cond_block = self.right_cond.generate(context,qf)
            block.append(right_cond_block)
        block.append(left_cond_block)

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

def kill_persist_fnc(context: qiwicg.Context, qf : qiwicg.QFunction,rhs1,rhs2: Optional[Type[ASTExp]] = None):
    block = qiwicg.QBlock()    
    #print(f"BEFORE IF \t: {qf.var_read_write}")
    temp = []
    if(rhs1.count_var_use() != None):
        for var in rhs1.count_var_use():
            qf.var_list_remove(var)
            temp.append(var)
    
    if(rhs2 != None):
        if(rhs2.count_var_use() != None):
            for var in rhs2.count_var_use():
                qf.var_list_remove(var)
                temp.append(var)    
    #print(f"MIDDLE IF \t: {qf.var_read_write}")               
    qf.var_read_write=temp+qf.var_read_write
    return (block,False)

class ASTIf_qm(ASTExp):
    cond: Type[ASTExp]
    lhs: Type[ASTExp]
    if_exp: Type[ASTExp]
    else_exp: Type[ASTExp]

    def __init__(self, cond,if_exp,else_exp: Optional[Type[ASTExp]] = None):
        self.cond = cond
        self.if_exp = if_exp
        self.else_exp = else_exp

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.cond},{self.if_exp},{self.else_exp})"

    def count_var_use(self):
        val = []
        if(self.if_exp.count_var_use() != None):
            val += self.if_exp.count_var_use()
        #val += [("W","if")]
        if(self.else_exp != None):    
            if(self.else_exp.count_var_use() != None):
                val += self.else_exp.count_var_use()
        #else:
            #if(self.lhs.count_var_use() != None):
                #val += self.lhs.count_var_use()
        #val += [("W","else")]
        if(self.cond.count_var_use() != None):
            val += self.cond.count_var_use()
        #val += [("R","if")]  
        #val += [("R","else")]
        return val
    
    def generate(self, context: qiwicg.Context, qf : qiwicg.QFunction) -> qiwicg.QBlock:
        block = qiwicg.QBlock()
        #blc,sta = kill_persist_fnc(context,qf,self.if_exp,self.else_exp)
        #if(sta):
            #return block
        #block.append(blc)
        
                   #TODO for indexed LHS also, also test without else
        if_assign = self.if_exp.generate(context,qf)
        if_loc = if_assign.output
        block.append(if_assign)
        temp_var = []
        for key in context.scope:
            if(key.endswith(":temp")):
                temp_var.append(key)

        for key in temp_var:
            loc = context.scope.pop(key)
            key = key[:key.index(":temp")]
            context.set_variable(key, loc)
        if(self.else_exp != None):
            else_assign = self.else_exp.generate(context,qf)
        else:
            else_assign = ASTInt(0).generate(context,qf)
        else_loc = else_assign.output
        block.append(else_assign) 
        
        cond = self.cond.generate(context,qf)
        block.append(cond)
        cond_loc = cond.output

        if(len(cond_loc)!= 1):
            raise RuntimeError(f"If condition must be 1 qubit")

        if(len(if_loc)!=len(else_loc)):
            print("WARNING: if and else block are of different size. Adding extra qubits to smaller")

        result_loc = context.allocate_qbits(max(len(if_loc),len(else_loc)))  
        
        for i in range(len(if_loc)):
            block.add(qiwicg.QGate('ccx', [if_loc[i], cond_loc[0], result_loc[i]]))
            block.add(qiwicg.QGate('reset', [if_loc[i]]))
        block.add(qiwicg.QGate('x', [cond_loc[0]]))
        for i in range(len(else_loc)):
            block.add(qiwicg.QGate('ccx', [else_loc[i], cond_loc[0], result_loc[i]]))
            block.add(qiwicg.QGate('reset', [else_loc[i]]))
        block.add(qiwicg.QGate('x', [cond_loc[0]]))
        block.add(qiwicg.QGate('reset', [cond_loc[0]]))

        context.free_location(if_loc);
        context.free_location(else_loc);
        context.free_location(cond_loc);
        '''context.free_variable(self.lhs.name);
        if(self.lhs_index != None):
            block.add(qiwicg.QGate('reset', [context.lookup_variable(self.lhs.name)[self.lhs.index]]))
        else:
            for loc in context.lookup_variable(self.lhs.name):
                block.add(qiwicg.QGate('reset', [loc]))'''


        #print(f"dtrfyghljnkm \t:{max(len(if_loc),len(else_loc))}->{result_loc}")
        '''if(self.lhs_index != None):
            context.set_var_index(self.lhs.name, result_loc[0], self.lhs_index)
        else:
            context.set_variable(self.lhs.name, result_loc)'''

        block.output = result_loc
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

    def generate(self, context: qiwicg.Context, qf : qiwicg.QFunction) -> qiwicg.QBlock:
        block = qiwicg.QBlock()

        a = self.left.generate(context,qf)
        #print(f'RESULT : {a}')
        block.append(a)

        b = self.right.generate(context,qf)
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

    def generate(self, context: qiwicg.Context, qf : qiwicg.QFunction) -> qiwicg.QBlock:
        block = qiwicg.QBlock()
        
        argloc = []
        for arg in self.args:
            argblock = arg.generate(context,qf)
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
            result += [("W",None,self.lhs.name)]
        else:
            result += [("W",self.index,self.lhs.name)]    #a particular index of name is rewritten
        return result


    def generate(self, context: qiwicg.Context, qf : qiwicg.QFunction) -> qiwicg.QBlock:
        rhs_block = qiwicg.QBlock()
        block = qiwicg.QBlock()
        print(f"BEFORE: {context.scope}->{qf.var_read_write}")
        flag = False
        rhs = self.rhs.generate(context,qf)
        if isinstance(rhs, int): # constant integer
            pass
        elif isinstance(rhs, list): # variable location reference
            location = rhs
        elif isinstance(rhs, qiwicg.QBlock):
            location = rhs.output
            rhs_block.append(rhs)
            if isinstance(self.type, ASTTypeQ):
                diff = self.type.length - len(location)
                if diff < 0:
                    raise RuntimeError(f"Type {self.type} not large enough to store {len(location)} qubits")
                else:
                    location += context.allocate_qbits(diff)
        else:
            raise RuntimeError("Unimplemented!")

        if(self.index == None):
            qf.var_list_remove(("W",None,self.lhs.name))
        else:
            qf.var_list_remove(("W",self.index,self.lhs.name))    #a particular index of name is rewritten
        
        if(qf.var_can_kill("W",self.lhs.name,self.index)):
            if(self.index == None):
                print(f"\tDont create: {self.lhs.name}")
            else:
                print(f"\tDon't create: {self.lhs.name}'s {self.index} qubit")
            return block
        else:
            if(self.index == None):
                print(f"\tCreate: {self.lhs.name}")
            else:
                print(f"\tCreate: {self.lhs.name}'s {self.index} qubit")
        block.append(rhs_block)
        if(self.index != None):
            if(len(location)!= 1):
                raise RuntimeError(f"1 qubit expected for indexed assignment.{len(location)} qubits provided")
            context.set_var_index(self.lhs.name, location[0], self.index)
        else:
            context.set_variable(self.lhs.name, location)
        block.output = location
        return block


def create_temp_var(id:ASTID,context: qiwicg.Context,qf : qiwicg.QFunction):
    block = qiwicg.QBlock()
    if(type(id) != ASTID) and (type(id) != ASTIndexedID):
        raise RuntimeError("Unimplemented: function is meant for ASTID")
    var_name = id.name
    if(type(id) == ASTIndexedID):
        var_index = str(id.index)
        if(qf.var_can_kill("R",var_name,id.index)):
            print(f"\tKill: {var_name}")
        else:
            var_loc = context.lookup_variable(var_name)[id.index]
            var_copy_loc = context.allocate_qbits(1)[0]
            block.add(qiwicg.QGate('cx', [var_loc, var_copy_loc]))
            context.set_variable((var_name+":temp"+"/"+var_index), var_copy_loc)        
            print(f"\tPersist: {var_name}")

    else:
        if(qf.var_can_kill("R",var_name,None)):
            print(f"\tKill: {var_name}")
        else:
            var_loc = context.lookup_variable(var_name)
            var_copy_loc = context.allocate_qbits(len(var_loc))
            for i in range(len(var_loc)):
                block.add(qiwicg.QGate('cx', [var_loc[i], var_copy_loc[i]]))
            context.set_variable((var_name+":temp"), var_copy_loc)
            print(f"\tPersist: {var_name}")
    print(f"MIDDLE: {context.scope}->{qf.var_read_write}")
    return block



def replace_with_temp(id:ASTID,context: qiwicg.Context,qf : qiwicg.QFunction):
    if(type(id) != ASTID) and (type(id) != ASTIndexedID):
        raise RuntimeError("Unimplemented: function is meant for ASTID")
    if(type(id) == ASTID):
        key = id.name+":temp"
        if key in context.scope.keys():
            loc = context.scope.pop(key)
            context.set_variable(id.name, loc)
    else:
        key = id.name+":temp"+"/"+str(id.index)
        if key in context.scope.keys():
            loc = context.scope.pop(key)
            context.set_var_index(id.name,loc,id.index)
    print(f"END: {id.name}->{qf.var_read_write}")
    