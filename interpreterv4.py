from brewparse import parse_program
from intbase import *
from element import Element
import copy

# Custom exception class to catch return values
class ReturnValue(Exception):
    def __init__(self, return_value):
        self.return_value = return_value

class BrewinException(Exception):
    def __init__(self, type):
        self.exception_type = type

class Expression():
    def __init__(self, expression, program_state):
        self.expression = expression
        self.program_state = program_state 

    def __str__(self):
        print("\n+Expression: \t", self.expression)
        return ""


NO_VALUE_DEFINED = object()

class Interpreter(InterpreterBase):
    defined_functions = {}      # should map function name to list of func nodes (for overloading)

    INT_OPERATIONS = ['+', '-', '*', '/', 'neg']
    BOOL_OPERATIONS = ['!', '||', '&&']
    EQUALITY_COMPARISONS = ['==', '!=']
    INTEGER_COMPARISONS = ['<', '<=', '>', '>=']
    OVERLOADED_OPERATIONS = ['+']
   
    def __init__(self, console_output=True, inp=None, trace_output=False):
        super().__init__(console_output, inp)   # call InterpreterBase's constructor
        self.trace_output = trace_output

    ''' ---- RUN PROGRAM ---- '''
    def run(self, program):
        self.defined_functions = {}
        ''' 
            program = array of strings containing program
            ast = AST generated by parser
            self.program_vars = map to hold variables + their values
        '''
        self.ast = parse_program(program)

        ''' ---- Find Main Node ---- '''
        # Check program validity
        if (self.ast.elem_type != 'program'):
            super().error(
                ErrorType.NAME_ERROR,
                "Initial element type is not 'program' "
            )

        
        # Search through program functions to find the MAIN node
        main_node = NO_VALUE_DEFINED
        for func in self.ast.dict['functions']:
            # Loop through all provided functions, add to dictionary of defined functions
            func_name = func.dict['name']
            if func_name not in self.defined_functions:
                self.defined_functions[func_name] = []
            self.defined_functions[func_name].append(func)
            
            # Identify main_node to run aftter
            if (func.dict['name'] == 'main'):
                main_node = func
        if (main_node is NO_VALUE_DEFINED):
            super().error(
                ErrorType.NAME_ERROR,
                "No MAIN node found in program"
            )
        
        # Run MAIN node
        try:
            return self.run_func(main_node, [])
        except BrewinException as exception:
            super().error(
                ErrorType.FAULT_ERROR,
                f"Error of type { {exception.exception_type} } was never caught in program"
            )

    def check_builtin_funcs(self, func_node, scope_stack):
        node_dict = func_node.dict
        func_name = node_dict['name']

        ''' PRINT + INPTUTI + INPUTS handling'''
        # Separate handling for: PRINT, INPUTI
        if func_name == 'inputi':
            if (len (node_dict['args']) > 1):
                super().error(
                    ErrorType.NAME_ERROR,
                    f"No inputi() function found that takes more than 1 parameter"
                )
            return self.inputi(scope_stack, node_dict['args'])
        
        if func_name == 'inputs':
            if (len (node_dict['args']) > 1):
                super().error(
                    ErrorType.NAME_ERROR,
                    f"No inputs() function found that takes more than 1 parameter"
                )
            return self.inputs(scope_stack, node_dict['args'])
        
        if func_name == 'print':
            return self.printout(scope_stack, node_dict['args'])
        ''' END OF SEPARATE HANDLING '''

        return NO_VALUE_DEFINED


    ''' ---- HANDLE fcall ---- '''
    def run_fcall(self, func_node, calling_func_vars):
        # calling_func_vars = variables defined by the calling function (where the statement was)
        node_dict = func_node.dict
        func_name = node_dict['name']
        func_args = node_dict['args']   # arguments passed into the function call


        # Check if Print, Inputi, or Inputs
        builtin = self.check_builtin_funcs(func_node, calling_func_vars)
        if builtin is not NO_VALUE_DEFINED:
            return builtin


        # For all other function calls: 
        if (func_name not in self.defined_functions):
            super().error(
                ErrorType.NAME_ERROR,
                f"Function {func_name} was not found / defined ",
            )

        # Based on the provided number of arguments in the function call
            # Identify the correct (possibly overloaded) function definition to run
        func_to_run = NO_VALUE_DEFINED
        defined_funcs_found = self.defined_functions[func_name]
        for func in defined_funcs_found:
            args = func.dict['args']
            if len(func_args) == len ( args ):
                func_to_run = func

        if (func_to_run is NO_VALUE_DEFINED):
            # Wrong number of arguments for this function
            super().error(
                ErrorType.NAME_ERROR, 
                f"Function { {func_name} } with { len(func_args)} parameters was not found"
            )

        func_arg_objs = []

        for arg in func_args:
            new_scope_stack = []
            for scope in calling_func_vars:
                new_scope = {}
                for var in scope:
                    new_scope[var] = scope[var]     # Point this new variable value at the old one
                new_scope_stack.append(new_scope)

            expr_object = Expression(arg, new_scope_stack)
            func_arg_objs.append(expr_object)


        return self.run_func( func_to_run , func_arg_objs )


    ''' ---- RUN FUNCTION ---- '''
    def run_func(self, func_node, func_args):
        # Should already be checked in run_fcall that function exists, but extra check just in case
        if (func_node.elem_type != 'func'):
            super().error(
                ErrorType.TYPE_ERROR,
                "Non-function node passed into run_func"
            )

        # Create dictionary to hold variables local to this function
        scope_stack = []
        func_vars = {}
        
        node_dict = func_node.dict
        node_params = node_dict['args']

        # Map argument values to the parameter names
        for var_name, expr_object in zip(node_params, func_args):
            func_vars[var_name.dict['name']] = expr_object

        # Base parameter:argument pairs are the ENCLOSING environment defined variables
        scope_stack.append( func_vars )

        # Loop through function statements in order
        for statement_node in node_dict['statements']:
            # Run each statement
            try:
                self.run_statement(statement_node, scope_stack)
            # If RETURN is found, should throw an exception
            except ReturnValue as rval:
                # Remove all added scopes from inside function
                while (len(scope_stack) > 1):
                    scope_stack.pop()

                return rval.return_value         # Returns an Expression instance

        # If exit list of statements without reaching a return statement, return NIL
        return Expression(Element("nil"), scope_stack)
    

    ''' ---- RUN STATEMENT ---- '''
    def run_statement(self, statement_node, func_vars):
        node_type = statement_node.elem_type

        # Run node's respective function
        match node_type:
            case 'vardef':
                self.run_vardef(statement_node, func_vars)
            case '=':
                self.run_assign(statement_node, func_vars)
            case 'fcall':
                self.run_fcall(statement_node, func_vars)
            case 'if':
                self.evaluate_if(statement_node, func_vars)
            case 'for':
                self.run_for_loop(statement_node, func_vars)
            case 'try':
                new_scope = {}
                func_vars.append( new_scope )
                for st in statement_node.dict['statements']:
                    try:
                        self.run_statement(st, func_vars)
                    except BrewinException as excpt:
                        func_vars.pop()
                        
                        exception_type = excpt.exception_type
                        
                        for catcher in statement_node.dict['catchers']:
                            catcher_type = catcher.dict['exception_type']
                            if (catcher_type == exception_type):
                                # Run statements in catcher
                                for statement in catcher.dict['statements']:
                                    self.run_statement(statement, func_vars)
                                return                                          # TODO: put a real return value or something I can check other times I'm calling run_statemnet
                            
                        raise BrewinException(exception_type)
                    
                func_vars.pop()
                
            case 'raise':
                exception_type = self.evaluate_expression(statement_node.dict['exception_type'], func_vars)       # Get actual string value
                if ( type(exception_type) is not str):
                    super().error(
                        ErrorType.TYPE_ERROR,
                        f"Attempted to raise NON-STRING { {exception_type} } in raise statement"
                    )
                raise BrewinException(exception_type)            
            
            case 'return':
                return_expression = statement_node.dict['expression']
                if (return_expression == None):
                    return_expression = Element("nil")

                new_scope_stack = []
                for scope in func_vars:
                    new_scope = {}
                    for var in scope:
                        new_scope[var] = scope[var]     # Point this new variable value at the old one
                    new_scope_stack.append(new_scope)
                
                expr_object = Expression(return_expression, new_scope_stack)

                raise ReturnValue(expr_object)

            case _:
                super().error(
                    ErrorType.NAME_ERROR,
                    f"Unrecognized statement of type {node_type}"
                )


    def evaluate_expression(self, node_expression, scope_stack):
        # Node expression should be an element, with an expression node
        
        node_type = node_expression.elem_type

        actual_value = NO_VALUE_DEFINED

        if (node_type in ['int', 'string', 'bool']):
            actual_value =  self.get_value(node_expression)
        
        elif (node_type == 'var'):
            actual_value = self.evaluate_var(node_expression, scope_stack)

        elif (node_type == 'fcall'):
            fcall_ret = self.run_fcall(node_expression, scope_stack)        # returns an Expression object
            returned_expression = fcall_ret.expression
            program_state = fcall_ret.program_state
            actual_value = self.evaluate_expression(returned_expression, program_state)
        
        elif (node_type in self.OVERLOADED_OPERATIONS):
            actual_value =  self.overloaded_operator(node_expression, scope_stack)
        
        elif (node_type in self.INT_OPERATIONS):
            actual_value = self.run_int_operation(node_expression, scope_stack)
        
        elif (node_type in self.BOOL_OPERATIONS):
            actual_value = self.run_bool_operation(node_expression, scope_stack)
        
        elif (node_type in self.EQUALITY_COMPARISONS):
            actual_value = self.check_equality(node_expression, scope_stack)
        
        elif (node_type in self.INTEGER_COMPARISONS):
            actual_value = self.integer_compare(node_expression, scope_stack)

        return actual_value

    def evaluate_var(self, node, scope_stack):
        
        var_name = node.dict['name']

        expr_object = self.get_variable_assignment(node, scope_stack)       # Always returns an expression class instance
        if type(expr_object) is not Expression:
            super().error(
                ErrorType.TYPE_ERROR,
                f" MY ERRR -- Non-expression node returned from get_var_assignmnet, must've missed a dictionary assignment somewhere"
            )

        var_expression = expr_object.expression
        program_state = expr_object.program_state

        actual_value = self.evaluate_expression(var_expression, program_state)

        if (actual_value is True or actual_value is False):
            value_type = 'bool'
        elif (type(actual_value) == int):
            value_type = 'int'
        elif (type(actual_value) == str):
            value_type = 'string'

        value_element = Element(value_type)
        value_element.dict['val'] = actual_value

        expr_object.expression = value_element

        return actual_value


    ''' ---- Running Statement Types ---- '''
    # VARDEF
    def run_vardef(self, node, scope_stack):
        var_name = node.dict['name']

        # Retrieves top-most scope (within inner-most block)
        latest_scope = scope_stack[-1]

        # Check if variable has already been defined in this scope
        if var_name in latest_scope:
            super().error(
                ErrorType.NAME_ERROR,
                f"Variable {var_name} defined more than once"
            )
        
        default_element = Element('string')
        default_element.dict['val'] = "DIS IS THE INITIAL VARIABLE VALUE"

        new_scope_stack = []
        for scope in scope_stack:
            new_scope = {}
            for var in scope:
                # print("Var = ", var, "\t Scope [var] = ", scope[var])
                new_scope[var] = scope[var]     # Point this new variable value at the old one
            new_scope_stack.append(new_scope)

        expr_object = Expression(default_element, new_scope_stack)

        # Add new variable to func_vars           Initial value: None
        latest_scope[var_name] = expr_object


    ''' ---- Variable Assignment ---- '''
    def run_assign(self, node, scope_stack):
        node_dict = node.dict
        var_name = node_dict['name']

        scope_to_update = NO_VALUE_DEFINED

        # Traverse stack in reverse order
        for scope in scope_stack[::-1]:
            # If variable exists in this scope, this is the one you want to update
            if var_name in scope:
                scope_to_update = scope
                break

        # If not found in any scope
        if scope_to_update is NO_VALUE_DEFINED:
            super().error(
                ErrorType.NAME_ERROR,
                f"Variable { {var_name} } not found in any scope"
            )


        # Calculate expression
        node_expression = node_dict['expression']

        new_scope_stack = []
        for scope in scope_stack:
            new_scope = {}
            for var in scope:
                # print("Var = ", var, "\t Scope [var] = ", scope[var])
                new_scope[var] = scope[var]     # Point this new variable value at the old one
            new_scope_stack.append(new_scope)


        expr_object = Expression(node_expression, new_scope_stack)

        scope_to_update[var_name] = expr_object


    ''' ---- If Statement ---- '''
    def check_condition(self, condition, func_vars):

        condition_type = condition.elem_type
        
        # If constant value
        if (condition_type == 'bool'):
            return self.get_value(condition)
        elif (condition_type == 'int' or condition_type == 'string' or condition_type == 'nil'):
            super().error(
                ErrorType.TYPE_ERROR,
                f"Cannot evaluate STRING or INT or NIL in 'if' statement condition"
            )
        
        # If variable value
        elif (condition_type == 'var'):
            # Check variable is defined
            val = self.evaluate_var(condition, func_vars)

            if (val is True) or (val is False):
                return val
            else:
                super().error(
                    ErrorType.TYPE_ERROR,
                    f"Cannot evaluate STRING or INT (or nil?) in 'if' statement condition, attempted (via existing variable {condition.dict['name']} value)"
                )

        # If fcall
        elif (condition_type == 'fcall'):
            fcall_ret = self.run_fcall(condition, func_vars)        # returns an Expression object
            returned_expression = fcall_ret.expression
            program_state = fcall_ret.program_state
            actual_value = self.evaluate_expression(returned_expression, program_state)
            
            if actual_value is True or actual_value is False:
                return actual_value
            else:
                super().error(
                    ErrorType.TYPE_ERROR,
                    f"Cannot evaluate STRING or INT (or nil?) in 'if' statement condition, attempted via fcall to {condition.dict['name']}"
                )

        elif (condition_type in self.EQUALITY_COMPARISONS):
            return self.check_equality(condition, func_vars)
        elif (condition_type in self.INTEGER_COMPARISONS):
            return self.integer_compare(condition, func_vars)
        elif (condition_type in self.BOOL_OPERATIONS):
            return self.run_bool_operation(condition, func_vars)
        
        else:
            super().error(
                    ErrorType.TYPE_ERROR,
                    f"Unrecognized expression type { {condition_type} } for 'if' condition: { {condition} }"
                )
            

    def evaluate_if(self, node, scope_stack):

        new_scope = {}
        scope_stack.append( new_scope )

        condition = node.dict['condition']
        statements = node.dict['statements']
        else_statements = node.dict['else_statements']

        eval_condition = self.check_condition(condition, scope_stack)

        if (eval_condition):
            # Loop through function statements in order
            for statement_node in statements:
                self.run_statement( statement_node , scope_stack)
        else:
            if else_statements != None:
                for statement_node in else_statements:
                    self.run_statement( statement_node, scope_stack)

        # Pop off new scope's variables
            # yup pop off
        scope_stack.pop()
        
    ''' --- For Loop ---- '''
    def run_for_loop(self, node, scope_stack):

        initialize = node.dict['init']
        condition = node.dict['condition']
        update = node.dict['update']
        statements = node.dict['statements']

        # Initialize counter variable in variable dictionary
        self.run_assign(initialize, scope_stack)

        # Check condition is true to begin with
        eval_condition = self.check_condition(condition, scope_stack)

        # While condition is true, execute statements
        while (eval_condition):
            # Initialize new scope for this loop iteration
            new_scope = {}
            scope_stack.append( new_scope )


            # Loop through function statements in order
            for statement_node in statements:
                self.run_statement( statement_node , scope_stack)

            # Pop off new scope's variables when done running statements
            scope_stack.pop()

            # Update counter variable value
            self.run_assign(update, scope_stack)

            # Check condition again
            eval_condition = self.check_condition(condition, scope_stack)



    ''' ---- Overloaded Operation ---- '''
    def overloaded_operator(self, node, func_vars):

        node_type = node.elem_type
        op1 = node.dict['op1']
        op2 = node.dict['op2']

        # Get operator values 
        op1_value = self.eval_op(op1, func_vars)
        op2_value = self.eval_op(op2, func_vars)

        operation_element = Element("+")        # its + b/c that's the only overloaded operator, but would need to change for any other operator

        # TODO: I think? Add NONE check to make sure not using a void function in operation

        # Check that operands are of the same type
        if ( type(op1_value) != type(op2_value)):
            super().error(
                ErrorType.TYPE_ERROR,
                f"Attempted to use {node_type} on different types { type(op1_value)} and { type(op2_value)}"
            )

        if node_type == '+':
            # '+' is defined for INT and STRING
            if type(op1_value) == int:
                op1_element = Element('int')
                op1_element.dict['val'] = op1_value
                op2_element = Element('int')
                op2_element.dict['val'] = op2_value

                operation_element.dict['op1'] = op1_element
                operation_element.dict['op2'] = op2_element
                
                return self.run_int_operation(operation_element, func_vars)
            if type(op1_value) == str:
                op1_element = Element('string')
                op1_element.dict['val'] = op1_value
                op2_element = Element('string')
                op2_element.dict['val'] = op2_value

                operation_element.dict['op1'] = op1_element
                operation_element.dict['op2'] = op2_element

                return self.run_string_operation(operation_element, func_vars)
            else:
                super().error(
                    ErrorType.TYPE_ERROR,
                    f"No {node_type} operation defined for { type(op1_value) }"
                )
    
    
    ''' ---- Evaluating Expressions / Operations ---- '''
        # Should return value of operation

    def run_int_operation(self, node, func_vars):
        node_type = node.elem_type

        if node_type == 'string' or node_type == 'bool' or node_type == 'nil':
            super().error(
                ErrorType.TYPE_ERROR,
                f"Attempted to use string or bool constant in integer operation"
            )
        
        # If int value
        if node_type == 'int':
            return self.get_value(node)
        
        # If variable
        if node_type == 'var':
            node_value = self.evaluate_var(node, func_vars)
            # print("\tPAssed in variable w/ value: ", node_value)
            if not (isinstance(node_value, int)) or node_value is True or node_value is False:
                super().error(
                ErrorType.TYPE_ERROR,
                f"Attempted to use string or bool or nil via existing variable {node.dict['name']} in integer operation"
            )
            
            # otherwise, it is an integer value
            return node_value 
        
        if node_type == 'fcall':
            fcall_ret = self.run_fcall(node, func_vars)        # returns an Expression object
            returned_expression = fcall_ret.expression
            program_state = fcall_ret.program_state
            actual_value = self.evaluate_expression(returned_expression, program_state)

            # print("\tPassed in function call with return value ", fcall_ret)
            if not (isinstance(actual_value, int)) or actual_value is True or actual_value is False:
                super().error(
                ErrorType.TYPE_ERROR,
                f"Attempted to use string or bool or nil via fcall in integer operation"
            )
                
            return actual_value

        allowable_types = ['int', 'var', 'fcall'] + self.INT_OPERATIONS
        
        # Unary negation
        if node_type == 'neg':
            op1 = node.dict['op1']
            if op1.elem_type not in allowable_types:
                super().error(
                    ErrorType.TYPE_ERROR,
                    f"Operand 1 is NOT of an allowable type for integer operation: op1 = {op1}"
                )
            return -( self.run_int_operation( node.dict['op1'], func_vars))
        
        # Operation
        op1 = node.dict['op1']
        op2 = node.dict['op2']

        if op1.elem_type not in allowable_types:
            super().error(
                ErrorType.TYPE_ERROR,
                f"Operand 1 is NOT of an allowable type for integer operation: op1 = {op1}"
            )
        if op2.elem_type not in allowable_types:
            super().error(
                ErrorType.TYPE_ERROR,
                f"Operand 2 is NOT of an allowable type for integer operation: op2 = {op2}"
            )

        if node_type == '+':
            return self.run_int_operation(op1, func_vars) + self.run_int_operation(op2, func_vars)
        if node_type == '-':
            return self.run_int_operation(op1, func_vars) - self.run_int_operation(op2, func_vars)
        if node_type == '*':
            return self.run_int_operation(op1, func_vars) * self.run_int_operation(op2, func_vars)
        if node_type == '/':
            first_op = self.run_int_operation(op1, func_vars)
            second_op = self.run_int_operation(op2, func_vars)
            if (second_op == 0):
                raise BrewinException("div0")
            else:
                return first_op // second_op


    def run_string_operation(self, node, func_vars):

        node_type = node.elem_type

        if node_type == 'bool' or node_type == 'int' or node_type == 'nil':
            super().error(
                    ErrorType.TYPE_ERROR,
                    f"Incompatible types for STRING operation, attempted to use boolean or integer constant value)"
                )
            
        if node_type == 'string':
            return self.get_value(node)

         # BASE: if operand is a VARIABLE --> return that variable's value
        if node_type == 'var':
            val = self.evaluate_var(node, func_vars)

            # Check if INT or BOOL
            if (isinstance( val , int)):
                super().error(
                    ErrorType.TYPE_ERROR,
                    f"Incompatible types for STRING operation, attempted to use INTEGER (via existing variable {node.dict['name']} value)"
                )

            if ( val is True or val is False):
                super().error(
                    ErrorType.TYPE_ERROR,
                    f"Incompatible types for STRING operation, attempted to use BOOLEAN (via existing variable {node.dict['name']} value)"
                )
            # Otherwise, return value
            return val

        
        # Function call
        if node_type == 'fcall':
            fcall_ret = self.run_fcall(node, func_vars)        # returns an Expression object
            returned_expression = fcall_ret.expression
            program_state = fcall_ret.program_state
            actual_value = self.evaluate_expression(returned_expression, program_state)

            return actual_value

        # String concatenation
        if node_type == '+':
            op1 = node.dict['op1']
            op2 = node.dict['op2']
            return ( self.run_string_operation(op1, func_vars) + self.run_string_operation(op2, func_vars) )


    ''' ---- Calculate BOOLEAN OPERATION ---- '''

    def run_bool_operation(self, node, func_vars):

        node_type = node.elem_type

        if node_type == 'int' or node_type == 'string' or node_type == 'nil':
            super().error(
                ErrorType.TYPE_ERROR,
                f"Attempted to use int, string, or nil constant in bool operation"
            )
        
        # If already a boolean --> return
        if node_type == 'bool':
            return self.get_value(node)
        
        # If variable
        if node_type == 'var':
            node_value = self.evaluate_var(node, func_vars)

            if node_value is not True and node_value is not False:
                super().error(
                    ErrorType.TYPE_ERROR,
                    f"Attempted to use int, string, or nil via existing variable {node.dict['name']} in BOOL operation"
                )
            
            # Return variable value
            return node_value
        
        
        # Function call
        if node_type == 'fcall':
            fcall_ret = self.run_fcall(node, func_vars)        # returns an Expression object
            returned_expression = fcall_ret.expression
            program_state = fcall_ret.program_state
            actual_value = self.evaluate_expression(returned_expression, program_state)

            if actual_value is not True and actual_value is not False:
                super().error(
                    ErrorType.TYPE_ERROR,
                    f"Attempted to use int, string, or nil via FCALL RETURN in BOOL operation"
                )

            return actual_value
        
        if node_type in self.EQUALITY_COMPARISONS:
            return self.check_equality(node, func_vars)
        if node_type in self.INTEGER_COMPARISONS:
            return self.integer_compare(node, func_vars)


        allowable_types = ['bool', 'var', 'fcall'] + self.BOOL_OPERATIONS + self.EQUALITY_COMPARISONS + self.INTEGER_COMPARISONS
        
        # Unary Boolean NOT
        if node_type == '!':
            op1 = node.dict['op1']
            if op1.elem_type not in allowable_types:
                super().error(
                    ErrorType.TYPE_ERROR,
                    f"Operand 1 is NOT of an allowable type for BOOL operation: op1 = {op1}"
                )
            return not (self.run_bool_operation( node.dict['op1'], func_vars))
        
        op1 = node.dict['op1']
        op2 = node.dict['op2']

        # If not an allowable boolean operation
        if op1.elem_type not in allowable_types:
            super().error(
                ErrorType.TYPE_ERROR,
                f"Operand 1 is NOT of an allowable type for BOOL operation: op1 = {op1}"
            )
        if op2.elem_type not in allowable_types:
            super().error(
                ErrorType.TYPE_ERROR,
                f"Operand 2 is NOT of an allowable type for BOOL operation: op2 = {op2}"
            )

        # Boolean operation
        if node_type == '||':
            return self.run_bool_operation(op1, func_vars) or self.run_bool_operation(op2, func_vars)
        
        if node_type == '&&':
            return self.run_bool_operation(op1, func_vars) and self.run_bool_operation(op2, func_vars)


    ''' ---- Comparison Operations ---- '''
    def eval_op(self, node, func_vars):
        op_type = node.elem_type

        # Get variable value
        if op_type == 'var':
            return self.evaluate_var(node, func_vars)

        # If value type
        if op_type == 'int' or op_type == 'string' or op_type == 'bool':
            return self.get_value(node)
        
        if op_type == 'fcall':
            # TODO: check return None
            fcall_ret = self.run_fcall(node, func_vars)        # returns an Expression object
            returned_expression = fcall_ret.expression
            program_state = fcall_ret.program_state
            actual_value = self.evaluate_expression(returned_expression, program_state)
            return actual_value
        
        if op_type == 'nil':
            return 'nil'
        
        if op_type in self.OVERLOADED_OPERATIONS:
            return self.overloaded_operator(node, func_vars)
        
        if op_type in self.INT_OPERATIONS:
            return self.run_int_operation(node, func_vars)
        
        if op_type in self.BOOL_OPERATIONS:
            return self.run_bool_operation(node, func_vars)
        
        if op_type in self.EQUALITY_COMPARISONS:
            return self.check_equality(node, func_vars)
        
        if op_type in self.INTEGER_COMPARISONS:
            return self.integer_compare(node, func_vars)
        
        return NO_VALUE_DEFINED
            

    def check_equality(self, node, func_vars):   
        
        node_type = node.elem_type
        op1 = node.dict['op1']
        op2 = node.dict['op2']

        # Get operator values 
        op1_value = self.eval_op(op1, func_vars)
        op2_value = self.eval_op(op2, func_vars)

        if (op1 is NO_VALUE_DEFINED) or (op2 is NO_VALUE_DEFINED):
            print("** ERR: EVAL_OP did not return anything\n___________________________\n")


        same = NO_VALUE_DEFINED

        if op1_value == 'nil' and op2_value == 'nil':
            same = True
        elif (op1_value == 'nil') or (op2_value == 'nil'):
            same = False


        # If both are bool
        elif ((op1_value is True) and (op2_value is True)) or ( (op1_value is False) and (op2_value is False)):
            same = True
        elif ( (op1_value is True) and (op2_value is False)) or ((op1_value is False) and (op2_value is True)):
            same = False

        
        # If different types
        elif ( type(op1_value) != type(op2_value) ):
            same = False
        else:
            same = (op1_value == op2_value)


        # Actually perform equality check
        if (same is not True) and (same is not False):
            super().error(
                ErrorType.TYPE_ERROR,
                f"Non-boolean value arose in equality check"
            )


        if node_type == '==':
            return same
        elif node_type == '!=':
            return not same
        else:
            super().error(
                ErrorType.NAME_ERROR,
                f"Unrecognized equality operation of type {node_type}"
            )

    def integer_compare(self, node, func_vars):

        node_type = node.elem_type
        op1 = node.dict['op1']
        op2 = node.dict['op2']

        # Get operator values 
        op1_value = self.run_int_operation(op1, func_vars)
        op2_value = self.run_int_operation(op2, func_vars)

        # If not integers --> type error
        if ( type(op1_value) != int) or (type(op2_value) != int):
            super().error(
                ErrorType.TYPE_ERROR, 
                f"Can't use operation {node_type} on non-integer values {op1_value} and {op2_value}"
            )

        if node_type == '<':
            return op1_value < op2_value
        if node_type == '<=':
            return op1_value <= op2_value
        if node_type == '>=':
            return op1_value >= op2_value
        if node_type == '>':
            return op1_value > op2_value


    # Return value of value nodes
    def get_value(self, node):
        return node.dict['val']
    

    def get_variable_assignment(self, node, scope_stack):
        
        var_name = node.dict['name']
        for scope in scope_stack[::-1]:
            # If variable exists in this scope, this is the value you want to return
            if var_name in scope:
                return scope[var_name]
        
        # If not found in any scope, error
        super().error(
                ErrorType.NAME_ERROR,
                f"Variable {var_name} has not been declared w/in function scope"
            )
        

    
    ''' ---- INPUTI function ---- '''
    def inputi(self, scope_stack, prompt=[]):
        if (prompt == []):
            user_input = super().get_input()
        else:
            arg = prompt[0]
            arg = self.evaluate_expression(arg, scope_stack)
            super().output(arg)
            user_input = super().get_input()

        result = int(user_input)
        result_elem = Element('int')
        result_elem.dict['val'] = result
        
        new_scope_stack = []
        for scope in scope_stack:
            new_scope = {}
            for var in scope:
                new_scope[var] = scope[var]     # Point this new variable value at the old one
            new_scope_stack.append(new_scope)
        
        expr_object = Expression(result_elem, new_scope_stack)

        return expr_object


    ''' ---- INPUTIS function ---- '''
    def inputs(self, scope_stack, prompt=[]):
        if (prompt == []):
            user_input = super().get_input()
        else:
            arg = prompt[0]
            arg = self.evaluate_expression(arg, scope_stack)
            super().output(arg)
            user_input = super().get_input()

        result = str(user_input)
        result_elem = Element('string')
        result_elem.dict['val'] = result

        new_scope_stack = []
        for scope in scope_stack:
            new_scope = {}
            for var in scope:
                new_scope[var] = scope[var]     # Point this new variable value at the old one
            new_scope_stack.append(new_scope)
        
        expr_object = Expression(result_elem, new_scope_stack)

        return expr_object

    ''' ---- PRINT function ---- '''
    def printout(self, func_vars, lst=[]):

        # lst = list of strings to concatenate
        string_to_output = ""       # TODO: check if 0 arguments should still print "" or just return
        for element in lst:
            node_type = element.elem_type
            if node_type == 'string':
                string_to_output += element.dict['val']
            elif node_type == 'bool':
                result = element.dict['val']
                if result is True:
                    string_to_output += "true"
                if result is False:
                    string_to_output += "false"
            elif node_type == 'int':
                string_to_output += str(element.dict['val'])
            # # If variable, retrieve variable value
            elif node_type == 'var':
                val = self.evaluate_var(element, func_vars)
                if val is True:
                    string_to_output += "true"
                elif val is False:
                    string_to_output += "false"
                else:
                    string_to_output += str (val)

            elif (node_type in self.OVERLOADED_OPERATIONS):
                # If BOOLS in overloaded operatos --> need to add the True False check
                string_to_output += str (self.overloaded_operator(element, func_vars))

            elif (node_type in self.INT_OPERATIONS):
                string_to_output += str (self.run_int_operation(element, func_vars))
            
            elif (node_type in self.BOOL_OPERATIONS):
                result = self.run_bool_operation(element, func_vars)
                if result is True:
                    string_to_output += "true"
                if result is False:
                    string_to_output += "false"

            elif (node_type in self.EQUALITY_COMPARISONS):
                result = self.check_equality(element, func_vars)
                if result is True:
                    string_to_output += "true"
                if result is False:
                    string_to_output += "false"

            elif (node_type in self.INTEGER_COMPARISONS):
                result = self.integer_compare(element, func_vars)
                if result is True:
                    string_to_output += "true"
                if result is False:
                    string_to_output += "false"

            elif node_type == 'fcall':
                fcall_ret = self.run_fcall(element, func_vars)        # returns an Expression object
                returned_expression = fcall_ret.expression
                program_state = fcall_ret.program_state
                actual_value = self.evaluate_expression(returned_expression, program_state)
                string_to_output += str(actual_value)

        super().output(string_to_output)
        return Expression(Element("nil"), func_vars)