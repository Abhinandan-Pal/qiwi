from __future__ import annotations
from typing import Optional, cast, Type
from . import qiwicg
import copy
import __main__


class ASTNode:
    pass


class ASTExp(ASTNode):
    QnotC: bool

    def generate(self, _: qiwicg.Context, qf: qiwicg.QFunction):
        del qf
        raise NotImplementedError

    def count_var_use(self):
        raise NotImplementedError


class ASTTypeQ(ASTNode):
    length: int
    QnotC: bool

    def __init__(self, QnotC: bool, length: int) -> None:
        self.length = length
        self.QnotC = QnotC

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.QnotC}{self.length})"

    def count_var_use(self):
        raise NotImplementedError

    def generate(self, context: qiwicg.Context, qf: qiwicg.QFunction) -> qiwicg.QBlock:
        del context, qf
        raise NotImplementedError


class ASTID(ASTExp):
    name: str
    persist_status: str
    QnotC: Optional[bool]
    c_value: Optional[int]

    def __init__(self, name: str) -> None:
        self.name = name
        self.persist_status = "UnKnown"
        self.QnotC = None
        self.c_value = None

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.name})"

    def count_var_use(self):
        return [('R', None, self.name)]

    def generate(self, context: qiwicg.Context, qf: qiwicg.QFunction) -> qiwicg.QFunction | qiwicg.QDynamicFunction | qiwicg.QBlock:
        if context.lookup_variable(self.name):
            block = qiwicg.QBlock()
            self.QnotC = context.lookupTypeQnotC(self.name)
            qf.var_list_remove(self.count_var_use()[0])
            if not self.QnotC:
                self.c_value = context.lookup_variable(self.name)[0]
                int_block = ASTInt(self.c_value).generate(context, qf)
                block.append(int_block)
                block.output = int_block.output
                return block
            block.append(create_temp_var(self, context, qf))
            block.output = context.lookup_variable(self.name)
            replace_with_temp(self, context, qf)  # SHOULD THIS CALL BE HERE?
            return block
        elif context.lookup_function(self.name, self.name_space):
            return context.lookup_function(self.name, self.name_space)
        else:
            raise RuntimeError(f"ID {self.name} used but not defined")


class ASTlen(ASTExp):
    id: ASTID
    c_value: Optional[int]

    def __init__(self, id) -> None:
        self.id = id
        self.c_value = None

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.id})"

    def count_var_use(self):
        return self.id.count_var_use()

    def generate(self, context: qiwicg.Context, qf: qiwicg.QFunction):
        block = qiwicg.QBlock()
        len_var = cast(qiwicg.QBlock, self.id.generate(context, qf))
        self.QnotC = False
        self.c_value = len(len_var.output)
        int_block = ASTInt(self.c_value).generate(context, qf)
        block.append(int_block)
        block.output = int_block.output
        return block


class ASTIndexedID(ASTExp):
    name: str
    index: int
    persist_status: str
    QnotC: bool

    def __init__(self, name: str, index: int) -> None:
        self.name = name
        self.index = index
        self.persist_status = "UnKnown"

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.name}_[{self.index}])"

    def count_var_use(self):
        return [('R', self.index, self.name)]

    def generate(self, context: qiwicg.Context, qf: qiwicg.QFunction) -> qiwicg.QBlock:
        block = qiwicg.QBlock()
        self.QnotC = context.lookupTypeQnotC(self.name)
        if not self.QnotC:
            raise RuntimeError("Only Quantum data is (qu)bit accessable")
        qf.var_list_remove(self.count_var_use()[0])
        block.append(create_temp_var(self, context, qf))
        block.output = [context.lookup_variable(self.name)[self.index]]

        replace_with_temp(self, context, qf)
        return block


class ASTInt(ASTExp):
    value: int  # combine both the variables as one
    c_value: int

    def __init__(self, value: int) -> None:
        self.value = value
        self.c_value = value

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.value})"

    def count_var_use(self):
        return None

    def generate(self, context: qiwicg.Context, qf: qiwicg.QFunction) -> qiwicg.QBlock:
        del qf
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
    def generate(self, _: qiwicg.Context, qf: qiwicg.QFunction) -> qiwicg.QBlock:
        del qf
        raise NotImplementedError

    def count_var_use(self):
        raise NotImplementedError


class ASTFor_c(ASTExp):
    iter_id: ASTID
    start: Type[ASTExp]
    end: Type[ASTExp]
    step: Type[ASTExp]
    statements: list[ASTStatement]

    def __init__(self, iter_id: ASTID, start: Type[ASTExp], end: Type[ASTExp], step: Type[ASTExp], statements):
        self.iter_id = iter_id
        self.start = start
        self.end = end
        self.step = step
        self.statements = statements

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.iter_id},{self.start},{self.end},{self.step},{self.statements})"

    def count_var_use(self):
        val = []
        if self.start.count_var_use() is not None:
            val += self.start.count_var_use()
        if self.end.count_var_use() is not None:
            val += self.end.count_var_use()
        if self.step.count_var_use() is not None:
            val += self.step.count_var_use()
        val += [('W', None, self.iter_id.name)]
        for statement in self.statements:
            if statement.count_var_use() is not None:
                val += statement.count_var_use()

        return val

    def generate(self, context: qiwicg.Context, qf: qiwicg.QFunction) -> qiwicg.QBlock:
        block = qiwicg.QBlock()
        # block.append(self.iter_id.generate(context,qf))    #dont exceute this as generate is for read
        self.start.generate(context, qf)
        self.end.generate(context, qf)
        self.step.generate(context, qf)
        context.addTypeQnotC(self.iter_id.name, False)
        loop_rw = []
        qf.var_list_remove(('W', None, self.iter_id.name))
        for statement in self.statements:
            if statement.count_var_use() != None:
                loop_rw += statement.count_var_use()

        for i in range(self.start.c_value, self.end.c_value-1, self.step.c_value):
            qf.var_read_write = loop_rw + qf.var_read_write

        for i in range(self.start.c_value, self.end.c_value, self.step.c_value):
            context.set_variable(self.iter_id.name, i)
            for statement in self.statements:
                statement = statement.generate(context, qf)
                block.append(statement)
        return block

class ASTFor_qc(ASTExp):
    def __init__(self, iterVarExp, target_func):
        self.iterVarExp = iterVarExp
        self.target_func = target_func

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.iterVarExp},{self.target_func})"

    def count_var_use(self):
        val = []
        t_func_args = self.target_func.args
        if self.target_func.count_var_use() is not None:
            val += self.target_func.count_var_use()
        for arg in t_func_args:
            if (type(arg) == ASTIndexedID):
                val += [("W", arg.index, arg.name)]
            elif(type(arg) == ASTID):
                val += [("W", None, arg.name)]
        if self.iterVarExp.count_var_use() is not None:
            val += self.iterVarExp.count_var_use()
        return val

    def generate(self, context: qiwicg.Context, qf: qiwicg.QFunction) -> qiwicg.QBlock:
        block = qiwicg.QBlock()
        # if(self.target_func != ASTFuncCall):                 #FIX THIS ERROR ALERT
        # raise RuntimeError("Target of if_qc must be a Gate on a qubit")
        t_func_name = self.target_func.name
        t_func_args = self.target_func.args

        # Add cool syntax error detection stuff
        func = context.lookup_function(
            t_func_name.name, self.target_func.name_space)
        iterVarExp = self.iterVarExp.generate(context, qf)

        argloc = []
        for arg in t_func_args:
            argblock = arg.generate(context, qf)
            if(type(argblock) == int):
                raise RuntimeError("Only variables can be placed in function")
            block.append(argblock)
            argloc.append(argblock.output)
        t_func_name = t_func_name.name.lower()

        block.append(iterVarExp)

        if len(argloc) != 1:
            raise RuntimeError(
                f"Target expects 1 arguments, {len(argloc)} provided")
       
        cgate = 'c'+t_func_name
        for term in range(len(iterVarExp.output)):
            for i in range(2**term):
                for argline in argloc[0]:
                    block.add(qiwicg.QGate(
                        cgate, [iterVarExp.output[term], argline]))

        return block

class ASTIf_c(ASTExp):
    cond: ASTExp
    if_statements: list[ASTStatement]
    else_statements: list[ASTStatement]

    def __init__(self, cond, if_statements, else_statements):
        self.cond = cond
        self.if_statements = if_statements
        self.else_statements = else_statements

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.cond},{self.if_statements},{self.else_statements})"

    def count_var_use(self):
        val = []
        if self.cond.count_var_use() is not None:
            val += self.cond.count_var_use()
        for if_statement in self.if_statements:
            if if_statement.count_var_use() is not None:
                val += if_statement.count_var_use()
        if(self.else_statements is not None):
            for else_statement in self.else_statements:
                if else_statement.count_var_use() is not None:
                    val += else_statement.count_var_use()
        return val

    def generate(self, context: qiwicg.Context, qf: qiwicg.QFunction) -> qiwicg.QBlock:
        block = qiwicg.QBlock()
        self.cond.generate(context, qf)
        __main__.log(f"IF_C: \t\t {self.cond.c_value}")
        if(self.cond.c_value):
            for statement in self.if_statements:
                statement = statement.generate(context, qf)
                block.append(statement)
            if(self.else_statements is not None):
                for else_statement in self.else_statements:
                    if else_statement.count_var_use() is not None:
                        for val in else_statement.count_var_use():
                            qf.var_list_remove(val)
        else:
            for if_statement in self.if_statements:
                if if_statement.count_var_use() is not None:
                    for val in if_statement.count_var_use():
                        qf.var_list_remove(val)
            if(self.else_statements is not None):
                for statement in self.else_statements:
                    statement = statement.generate(context, qf)
                    block.append(statement)
        return block


class ASTIf_qc(ASTExp):
    left_cond: ASTIndexedID
    right_cond: ASTIndexedID
    op_cond: str
    target_func: ASTFuncCall

    def __init__(self, control_tuple, target_func):
        self.left_cond, self.op_cond, self.right_cond = control_tuple
        self.target_func = target_func

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.left_cond},{self.op_cond},{self.right_cond},{self.target_func})"

    def count_var_use(self):
        val = []
        t_func_args = self.target_func.args
        if self.target_func.count_var_use() is not None:
            val += self.target_func.count_var_use()
        for arg in t_func_args:
            if (type(arg) == ASTIndexedID):
                val += [("W", arg.index, arg.name)]
            elif(type(arg) == ASTID):
                val += [("W", None, arg.name)]
        if self.left_cond.count_var_use() is not None:
            val += self.left_cond.count_var_use()
        if self.left_cond.count_var_use() is not None:
            for rw, index, name in self.left_cond.count_var_use():
                val += [("W", index, name)]

        if self.right_cond is not None:
            if self.right_cond.count_var_use() is not None:
                val += self.right_cond.count_var_use()
            if self.right_cond.count_var_use() is not None:
                for rw, index, name in self.right_cond.count_var_use():
                    val += [("W", index, name)]

        return val

    def generate(self, context: qiwicg.Context, qf: qiwicg.QFunction) -> qiwicg.QBlock:
        block = qiwicg.QBlock()
        # if(self.target_func != ASTFuncCall):                 #FIX THIS ERROR ALERT
        # raise RuntimeError("Target of if_qc must be a Gate on a qubit")
        t_func_name = self.target_func.name
        t_func_args = self.target_func.args

        # Add cool syntax error detection stuff
        func = context.lookup_function(
            t_func_name.name, self.target_func.name_space)
        left_cond_block = self.left_cond.generate(context, qf)

        argloc = []
        for arg in t_func_args:
            argblock = arg.generate(context, qf)
            if(type(argblock) == int):
                raise RuntimeError("Only variables can be placed in function")
            block.append(argblock)
            argloc.append(argblock.output)
        t_func_name = t_func_name.name.lower()

        if self.right_cond is not None:
            right_cond_block = self.right_cond.generate(context, qf)
            block.append(right_cond_block)
        block.append(left_cond_block)

        if len(argloc) != 1:
            raise RuntimeError(
                f"Target expects 1 arguments, {len(argloc)} provided")

        if len(argloc[0]) != 1:
            raise RuntimeError(
                f"Target argument expected to be 1 qubit, {len(argloc[0])} provided")

        if(self.op_cond == 'SINGLE'):
            cgate = 'c'+t_func_name
            block.add(qiwicg.QGate(
                cgate, [left_cond_block.output[0], argloc[0][0]]))

        if(self.op_cond == 'xor'):
            cgate = 'c'+t_func_name
            block.add(qiwicg.QGate(
                cgate, [left_cond_block.output[0], argloc[0][0]]))
            block.add(qiwicg.QGate(
                cgate, [right_cond_block.output[0], argloc[0][0]]))

        if(self.op_cond == 'xnor'):
            cgate = 'c'+t_func_name
            block.add(qiwicg.QGate(
                cgate, [left_cond_block.output[0], argloc[0][0]]))
            block.add(qiwicg.QGate(
                cgate, [right_cond_block.output[0], argloc[0][0]]))
            block.add(qiwicg.QGate('x', [argloc[0][0]]))

        if(self.op_cond == 'and'):
            cgate = 'cc'+t_func_name
            block.add(qiwicg.QGate(
                cgate, [left_cond_block.output[0], right_cond_block.output[0], argloc[0][0]]))

        if(self.op_cond == 'or'):
            cgate = 'cc'+t_func_name
            block.add(qiwicg.QGate('x', [left_cond_block.output[0]]))
            block.add(qiwicg.QGate('x', [right_cond_block.output[0]]))
            block.add(qiwicg.QGate(
                cgate, [left_cond_block.output[0], right_cond_block.output[0], argloc[0][0]]))
            block.add(qiwicg.QGate('x', [left_cond_block.output[0]]))
            block.add(qiwicg.QGate('x', [right_cond_block.output[0]]))
            block.add(qiwicg.QGate('x', [argloc[0][0]]))

        if(self.op_cond == 'nor'):
            cgate = 'cc'+t_func_name
            block.add(qiwicg.QGate('x', [left_cond_block.output[0]]))
            block.add(qiwicg.QGate('x', [right_cond_block.output[0]]))
            block.add(qiwicg.QGate(
                cgate, [left_cond_block.output[0], right_cond_block.output[0], argloc[0][0]]))
            block.add(qiwicg.QGate('x', [left_cond_block.output[0]]))
            block.add(qiwicg.QGate('x', [right_cond_block.output[0]]))

        if(self.op_cond == 'nand'):
            cgate = 'cc'+t_func_name
            block.add(qiwicg.QGate(
                cgate, [left_cond_block.output[0], right_cond_block.output[0], argloc[0][0]]))
            block.add(qiwicg.QGate('x', [argloc[0][0]]))
            block.output = argloc[0]
        return block


def kill_persist_fnc(context: qiwicg.Context, qf: qiwicg.QFunction, rhs1, rhs2: Optional[ASTExp] = None):
    block = qiwicg.QBlock()
    #__main__.log(f"BEFORE IF \t: {qf.var_read_write}")
    temp = []
    if rhs1.count_var_use() is not None:
        for var in rhs1.count_var_use():
            qf.var_list_remove(var)
            temp.append(var)

    if rhs2 is not None:
        if rhs2.count_var_use() is not None:
            for var in rhs2.count_var_use():
                qf.var_list_remove(var)
                temp.append(var)
    #__main__.log(f"MIDDLE IF \t: {qf.var_read_write}")
    qf.var_read_write = temp+qf.var_read_write
    return (block, False)


class ASTIf_qm(ASTExp):
    cond: ASTExp
    lhs: ASTExp
    if_exp: ASTExp
    else_exp: ASTExp
    QnotC: Optional[bool]

    def __init__(self, cond, if_exp, else_exp: Optional[ASTExp] = None):
        self.cond = cond
        self.if_exp = if_exp
        self.else_exp = else_exp
        self.QnotC = True

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.cond},{self.if_exp},{self.else_exp})"

    def count_var_use(self):
        val = []
        if self.if_exp.count_var_use() is not None:
            val += self.if_exp.count_var_use()
        if self.else_exp is not None:
            if self.else_exp.count_var_use() is not None:
                val += self.else_exp.count_var_use()
        if self.cond.count_var_use() is not None:
            val += self.cond.count_var_use()
        return val

    def generate(self, context: qiwicg.Context, qf: qiwicg.QFunction) -> qiwicg.QBlock:
        block = qiwicg.QBlock()
        if_assign = self.if_exp.generate(context, qf)
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
        if self.else_exp is not None:
            else_assign = self.else_exp.generate(context, qf)
        else:
            else_assign = ASTInt(0).generate(context, qf)
        else_loc = else_assign.output
        block.append(else_assign)

        cond = self.cond.generate(context, qf)
        block.append(cond)
        cond_loc = cond.output

        if(len(cond_loc) != 1):
            raise RuntimeError(f"If condition must be 1 qubit")

        if(len(if_loc) != len(else_loc)):
            __main__.log(
                "WARNING: if and else block are of different size. Adding extra qubits to smaller")

        result_loc = context.allocate_qbits(max(len(if_loc), len(else_loc)))

        for i in range(len(if_loc)):
            block.add(qiwicg.QGate(
                'ccx', [if_loc[i], cond_loc[0], result_loc[i]]))
        block.add(qiwicg.QGate('x', [cond_loc[0]]))
        for i in range(len(else_loc)):
            block.add(qiwicg.QGate(
                'ccx', [else_loc[i], cond_loc[0], result_loc[i]]))
        block.add(qiwicg.QGate('x', [cond_loc[0]]))

        context.free_location(if_loc)
        context.free_location(else_loc)
        context.free_location(cond_loc)

        block.output = result_loc
        return block


class ASTRelational(ASTExp):
    operator: str
    left: ASTExp
    right: ASTExp
    QnotC: Optional[bool]
    c_value: Optional[int]

    def __init__(self, operator: str, left: ASTExp, right: ASTExp) -> None:
        self.operator = operator
        self.left = left
        self.right = right
        self.QnotC = None
        self.c_value = None

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.operator}, {self.left}, {self.right})"

    def count_var_use(self):
        result = []
        if self.left.count_var_use() is not None:
            result += self.left.count_var_use()
        if self.right.count_var_use() is not None:
            result += self.right.count_var_use()
        return result

    def generate(self, context: qiwicg.Context, qf: qiwicg.QFunction) -> qiwicg.QBlock:

        a = self.left.generate(context, qf)
        b = self.right.generate(context, qf)
        block = qiwicg.QBlock()
        if (type(self.left) == ASTInt) or (self.left.QnotC == False):
            if (type(self.right) != ASTInt) and (self.right.QnotC == True):
                raise RuntimeError(
                    f"Two both sides of an expr should be Quantum or classical {self}")
            self.QnotC = False
            if(self.operator == '>'):
                self.c_value = int(self.left.c_value > self.right.c_value)
            if(self.operator == '<'):
                self.c_value = int(self.left.c_value < self.right.c_value)
            if(self.operator == '<='):
                self.c_value = int(self.left.c_value <= self.right.c_value)
            if(self.operator == '>='):
                self.c_value = int(self.left.c_value >= self.right.c_value)
            if(self.operator == '=='):
                self.c_value = int(self.left.c_value == self.right.c_value)
            if(self.operator == '!='):
                self.c_value = int(self.left.c_value != self.right.c_value)

            int_block = ASTInt(self.c_value).generate(context, qf)
            block.append(int_block)
            block.output = int_block.output
            return block
        self.QnotC = True
        block = qiwicg.QBlock()
        block.append(a)
        block.append(b)
        raise NotImplementedError


class ASTExpBinary(ASTExp):
    operator: str
    left: ASTExp
    right: ASTExp
    QnotC: Optional[bool]
    c_value: Optional[int]

    def __init__(self, operator: str, left: ASTExp, right: ASTExp) -> None:
        self.operator = operator
        self.left = left
        self.right = right
        self.QnotC = None
        self.c_value = None

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
        if self.left.count_var_use() is not None:
            result += self.left.count_var_use()
        if self.right.count_var_use() is not None:
            result += self.right.count_var_use()
        return result

    def generate(self, context: qiwicg.Context, qf: qiwicg.QFunction) -> qiwicg.QBlock:

        a = self.left.generate(context, qf)
        b = self.right.generate(context, qf)
        block = qiwicg.QBlock()
        if (type(self.left) == ASTInt) or (not self.left.QnotC):
            if (type(self.right) != ASTInt) and (self.right.QnotC == True):
                raise RuntimeError(
                    f"Two both sides of an expr should be Quantum or classical {self}")
            self.QnotC = False
            if self.operator == '+':
                self.c_value = self.left.c_value + self.right.c_value
            if self.operator == '-':
                self.c_value = self.left.c_value - self.right.c_value
            if self.operator == '*':
                self.c_value = self.left.c_value * self.right.c_value
            if self.operator == '/':
                self.c_value = int(self.left.c_value / self.right.c_value)
            # __main__.log(f"self->{self}:-:{ASTInt(self.c_value).generate(context,qf)}")
            int_block = ASTInt(self.c_value).generate(context, qf)
            block.append(int_block)
            block.output = int_block.output
            return block
        self.QnotC = True
        block = qiwicg.QBlock()
        block.append(a)
        block.append(b)

        if self.operator == '+':
            if(len(a.output) > len(b.output)):
                a, b = b, a

            c0 = context.allocate_qbits(1)[0]
            if(len(a.output) != len(b.output)):
                an = context.allocate_qbits(1)[0]

            block.append(ASTExpBinary.majority_block(
                [c0, b.output[0], a.output[0]]))

            for i in range(1, len(a.output)):
                block.append(ASTExpBinary.majority_block(
                    [a.output[i-1], b.output[i], a.output[i]]))

            if(len(a.output) != len(b.output)):
                block.append(ASTExpBinary.majority_block(
                    [a.output[len(a.output)-1], b.output[len(a.output)], an]))

            for i in reversed(range(1, len(a.output))):
                block.append(ASTExpBinary.unmajority_block(
                    [a.output[i-1], b.output[i], a.output[i]]))

            if(len(a.output) != len(b.output)):
                block.append(ASTExpBinary.unmajority_block(
                    [a.output[len(a.output)-1], b.output[len(a.output)], an]))

            block.append(ASTExpBinary.majority_block(
                [c0, b.output[0], a.output[0]]))

            block.output = b.output
        elif self.operator == '-':
            if(len(b.output) > len(a.output)):
                raise NotImplementedError("Negative Numbers not implemented")
            elif(len(a.output) > len(b.output)):
                b.output += context.allocate_qbits(
                    len(a.output) - len(b.output))
            c0 = context.allocate_qbits(1)[0]

            # carry 1
            block.add(qiwicg.QGate('x', [c0]))

            # invert b
            for qb in b.output:
                block.add(qiwicg.QGate('x', [qb]))

            block.append(ASTExpBinary.majority_block(
                [c0, b.output[0], a.output[0]]))

            for i in range(1, len(a.output)):
                block.append(ASTExpBinary.majority_block(
                    [a.output[i-1], b.output[i], a.output[i]]))

            for i in reversed(range(1, len(a.output))):
                block.append(ASTExpBinary.unmajority_block(
                    [a.output[i-1], b.output[i], a.output[i]]))

            block.append(ASTExpBinary.majority_block(
                [c0, b.output[0], a.output[0]]))

            block.output = b.output

            pass
        else:
            raise RuntimeError("Unknown operator!")

        return block


class ASTFuncDef(ASTNode):
    name: ASTID
    body: list[ASTStatement]
    return_type: Optional[ASTTypeQ]
    args: list[tuple[ASTID, ASTTypeQ, bool]]

    def __init__(self, name: ASTID, return_type: Optional[ASTTypeQ], args: list[tuple[ASTID, ASTTypeQ]], body: list[ASTStatement]) -> None:
        self.name = name
        self.body = body
        self.return_type = return_type
        self.args = args

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.name}, {self.return_type}, {self.args}, {self.body})"

    def count_var_use(self):
        result: list[(str, str)]
        result = []
        for sta in self.body:
            if sta.count_var_use() is not None:
                result += sta.count_var_use()
        return result

    def generate(self, context: qiwicg.Context):
        context.add_function(self.name.name, qiwicg.QFunction(self))


class ASTFuncCall(ASTExp):
    name: ASTID
    name_space: str
    args: list[ASTExp]
    QnotC: bool

    def __init__(self, name: ASTID, args: list[ASTExp], name_space: Optional[str] = "self") -> None:
        self.name = name
        self.args = args
        self.name_space = name_space
        self.QnotC = True  # For now all functions are qunatumn

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}({self.name_space}.{self.name}, {self.args})"

    def count_var_use(self):
        result: [(str, str)]
        result = []
        for arg in self.args:
            if arg.count_var_use() is not None:
                result += arg.count_var_use()
        return result

    def generate(self, context: qiwicg.Context, qf: qiwicg.QFunction) -> qiwicg.QBlock:
        block = qiwicg.QBlock()

        argloc = []
        persist_info = []
        for arg in self.args:
            argblock = arg.generate(context, qf)
            if(type(argblock) == int):
                raise RuntimeError("Only variables can be placed in function")
            block.append(argblock)
            argloc.append(argblock.output)
            if(type(arg) != ASTID and type(arg) != ASTIndexedID):
                persist_info.append((False, len(argblock.output)))
            else:
                if (arg.persist_status == "UnKnown"):
                    raise RuntimeError("Debug Line: Should never occur")
                persist_info.append(
                    ((arg.persist_status == "PERSIST"), len(argblock.output)))
        func = context.lookup_function(
            self.name.name, persist_info, self.name_space)
        if isinstance(func, qiwicg.QFunction):
            body = func.generate(context, argloc,self.name_space)
        elif isinstance(func, qiwicg.QDynamicFunction):
            body = func.fn(argloc)
        else:
            raise RuntimeError("Unimplemented!")

        block.append(body)
        block.output = body.output

        return block


class ASTAssignment(ASTStatement):
    lhs: ASTID
    rhs: ASTExp
    type: ASTTypeQ
    index: int

    def __init__(self, lhs: ASTID, rhs: ASTExp, index: int = None, type: Optional[ASTTypeQ] = None) -> None:
        self.lhs = lhs
        self.rhs = rhs
        self.type = type
        self.index = index

    def __repr__(self) -> str:
        if self.index is not None:
            return f"{self.__class__.__name__}({self.lhs}, {self.rhs},{self.index},{self.type})"
        else:
            return f"{self.__class__.__name__}({self.lhs}, {self.rhs},{self.type})"

    def count_var_use(self):
        result: list[(str, str)]
        result = []
        if self.rhs.count_var_use() is not None:
            for var in self.rhs.count_var_use():
                result += [var]
        if(self.index == None):
            result += [("W", None, self.lhs.name)]
        else:
            # a particular index of name is rewritten
            result += [("W", self.index, self.lhs.name)]
        return result

    def generate(self, context: qiwicg.Context, qf: qiwicg.QFunction) -> qiwicg.QBlock:
        __main__.log(f"{self}")
        block = qiwicg.QBlock()

        if self.type is not None:
            if(self.type.QnotC == False):
                rhs = self.rhs.generate(context, qf)
                context.set_variable(self.lhs.name, [self.rhs.c_value])
                context.addTypeQnotC(self.lhs.name, False)
                qf.var_list_remove(("W", None, self.lhs.name))
                return block

        rhs_block = qiwicg.QBlock()

        __main__.log(f"BEFORE: {context.scope}:{context.type_qnc}->{qf.var_read_write}")
        flag = False

        qf_copy = copy.deepcopy(qf)
        if self.rhs.count_var_use() is not None:
            for var in self.rhs.count_var_use():
                qf_copy.var_list_remove(var)
        if(self.index == None):
            qf_copy.var_list_remove(("W", None, self.lhs.name))
        else:
            # a particular index of name is rewritten
            qf_copy.var_list_remove(("W", self.index, self.lhs.name))

        if(qf_copy.var_can_kill("W", self.lhs.name, self.index)):
            if(self.index == None):
                __main__.log(f"\tDont create: {self.lhs.name}")
            else:
                __main__.log(f"\tDon't create: {self.lhs.name}'s {self.index} qubit")
            if self.rhs.count_var_use() is not None:
                for var in self.rhs.count_var_use():
                    qf.var_list_remove(var)
            return block
        else:
            if(self.index == None):
                __main__.log(f"\tCreate: {self.lhs.name}")
            else:
                __main__.log(f"\tCreate: {self.lhs.name}'s {self.index} qubit")

        rhs = self.rhs.generate(context, qf)
        if isinstance(rhs, int):  # constant integer
            pass
        elif isinstance(rhs, list):  # variable location reference
            location = rhs
        elif isinstance(rhs, qiwicg.QBlock):
            location = rhs.output
            rhs_block.append(rhs)
            if isinstance(self.type, ASTTypeQ) and (self.type.length != None):
                diff = self.type.length - len(location)
                if diff < 0:
                    raise RuntimeError(
                        f"Type {self.type} not large enough to store {len(location)} qubits")
                else:
                    location += context.allocate_qbits(diff)
        else:
            raise RuntimeError("Unimplemented!")
        if(self.index == None):
            qf.var_list_remove(("W", None, self.lhs.name))
        else:
            # a particular index of name is rewritten
            qf.var_list_remove(("W", self.index, self.lhs.name))

        if(type(self.rhs) != ASTInt and self.rhs.QnotC == False):
            context.set_variable(self.lhs.name, [self.rhs.c_value])
            context.addTypeQnotC(self.lhs.name, False)
            return block
        block.append(rhs_block)
        if self.index is not None:
            if(len(location) != 1):
                raise RuntimeError(
                    f"1 qubit expected for indexed assignment.{len(location)} qubits provided")
            context.set_var_index(self.lhs.name, location[0], self.index)
        else:
            context.set_variable(self.lhs.name, location)
        context.addTypeQnotC(self.lhs.name, True)
        block.output = location
        __main__.log(f"END: {context.scope}:{context.type_qnc}->{qf.var_read_write}")
        return block


def create_temp_var(id: ASTID | ASTIndexedID, context: qiwicg.Context, qf: qiwicg.QFunction):
    block = qiwicg.QBlock()
    if(type(id) != ASTID) and (type(id) != ASTIndexedID):
        raise RuntimeError("Unimplemented: function is meant for ASTID")
    var_name = id.name
    if(type(id) == ASTIndexedID):
        var_index = str(id.index)
        if(qf.var_can_kill("R", var_name, id.index)):
            __main__.log(f"\tKill: {var_name}:{id.index}")
            id.persist_status = "KILL"
        else:
            var_loc = context.lookup_variable(var_name)[id.index]
            var_copy_loc = context.allocate_qbits(1)[0]
            block.add(qiwicg.QGate('cx', [var_loc, var_copy_loc]))
            context.set_variable(
                (var_name+":temp"+"/"+var_index), var_copy_loc)
            __main__.log(f"\tPersist: {var_name}:{id.index}")
            id.persist_status = "PERSIST"

    else:
        if(qf.var_can_kill("R", var_name, None)):
            __main__.log(f"\tKill: {var_name}")
            id.persist_status = "KILL"
        else:
            var_loc = context.lookup_variable(var_name)
            var_copy_loc = context.allocate_qbits(len(var_loc))
            for i in range(len(var_loc)):
                block.add(qiwicg.QGate('cx', [var_loc[i], var_copy_loc[i]]))
            context.set_variable((var_name+":temp"), var_copy_loc)
            __main__.log(f"\tPersist: {var_name}")
            id.persist_status = "PERSIST"
    __main__.log(f"MIDDLE: {context.scope}:{context.type_qnc}->{qf.var_read_write}")
    return block


def replace_with_temp(id: ASTID | ASTIndexedID, context: qiwicg.Context, qf: qiwicg.QFunction):
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
            context.set_var_index(id.name, loc, id.index)
    __main__.log(f"END: {id.name}->{qf.var_read_write}")

