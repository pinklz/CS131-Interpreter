from brewparse import parse_program
from intbase import *
from element import Element

# Custom exception class to catch return values
class ReturnValue(Exception):
    def __init__(self, return_value):
        self.return_value = return_value
    def get_ret_value(self):
        return self.return_value


class Interpreter(InterpreterBase):
    program_vars = {}
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
        main_node = None
        for func in self.ast.dict['functions']:
            # Loop through all provided functions, add to dictionary of defined functions
            func_name = func.dict['name']
            if func_name not in self.defined_functions:
                self.defined_functions[func_name] = []
            self.defined_functions[func_name].append(func)
            
            # Identify main_node to run aftter
            if (func.dict['name'] == 'main'):
                main_node = func
        if (main_node == None):
            super().error(
                ErrorType.NAME_ERROR,
                "No MAIN node found in program"
            )
        
        # Run MAIN node
        return self.run_func(main_node, [])

    def check_builtin_funcs(self, func_node, scope_stack):
        node_dict = func_node.dict
        func_name = node_dict['name']

        ''' PRINT + INPTUTI + INPUTS handling'''
        # Separate handling for: PRINT, INPUTI
        if func_name == 'inputi':
            if (self.trace_output == True):
                print("\tCalling inputi function")
            if (len (node_dict['args']) > 1):
                super().error(
                    ErrorType.NAME_ERROR,
                    f"No inputi() function found that takes more than 1 parameter"
                )
            return self.inputi(node_dict['args'])
        
        if func_name == 'inputs':
            if (self.trace_output == True):
                print("\tCalling inputs function")
            if (len (node_dict['args']) > 1):
                super().error(
                    ErrorType.NAME_ERROR,
                    f"No inputs() function found that takes more than 1 parameter"
                )
            return self.inputs(node_dict['args'])
        
        if func_name == 'print':
            return self.printout(scope_stack, node_dict['args'])
        ''' END OF SEPARATE HANDLING '''

        return None


    ''' ---- HANDLE fcall ---- '''
    def run_fcall(self, func_node, calling_func_vars):
        # calling_func_vars = variables defined by the calling function (where the statement was)
        node_dict = func_node.dict
        func_name = node_dict['name']
        func_args = node_dict['args']   # arguments passed into the function call

        if (self.trace_output):
            if (func_args == []):
                print("** RUN FCALL -- NO args provided")
            else:
                print("** RUN FCALL")
                print("\tProvided arguments: ")
                for arg in func_args:
                    print("\t\t", arg)

        # Check if Print, Inputi, or Inputs
        builtin = self.check_builtin_funcs(func_node, calling_func_vars)
        if builtin != None:
            return builtin


        # For all other function calls: 
        if (func_name not in self.defined_functions):
            super().error(
                ErrorType.NAME_ERROR,
                f"Function {func_name} was not found / defined ",
            )

        # Based on the provided number of arguments in the function call
            # Identify the correct (possibly overloaded) function definition to run
        func_to_run = None
        defined_funcs_found = self.defined_functions[func_name]
        for func in defined_funcs_found:
            args = func.dict['args']
            if len(func_args) == len ( args ):
                func_to_run = func

        if (func_to_run == None):
            # Wrong number of arguments for this function
            super().error(
                ErrorType.NAME_ERROR, 
                f"Function { {func_name} } with { len(func_args)} parameters was not found"
            )


        # func_arg_values = []

        #     # if variable - check calling_func_args
        #     # if op, call run_operation
        # for arg in func_args:
        #     # If it is already a value, add that value
        #     if arg.elem_type in ['string', 'int', 'bool']:
        #         func_arg_values.append( self.get_value (arg) )
        #     elif arg.elem_type == 'var':
        #         # Check variable is defining within calling function + get value if so
        #         func_arg_values.append( self.get_variable_value (arg, calling_func_vars))
            
        #     # Passed in EXPRESION
        #         # Overloaded operation
        #     elif arg.elem_type in self.OVERLOADED_OPERATIONS:
        #         func_arg_values.append( self.overloaded_operator (arg, calling_func_vars) )
        #         # Integer operation
        #     elif arg.elem_type in self.INT_OPERATIONS:
        #         func_arg_values.append( self.run_int_operation (arg, calling_func_vars) )
        #         # Boolean operation
        #     elif arg.elem_type in self.BOOL_OPERATIONS:
        #         func_arg_values.append( self.run_bool_operation (arg, calling_func_vars) )
        #         # Equality comparison
        #     elif arg.elem_type in self.EQUALITY_COMPARISONS:
        #         func_arg_values.append( self.check_equality (arg, calling_func_vars) )
        #         # Integer comparison
        #     elif arg.elem_type in self.INTEGER_COMPARISONS:
        #         func_arg_values.append( self.integer_compare (arg, calling_func_vars) )
        #     elif arg.elem_type == 'nil':
        #         func_arg_values.append( arg )
        #     else:
        #         print("***********************\n\t IN RUN_FCALL, don't know how to process arguments: ", arg)
        #         # TODO: if error, likely is in missing a case here


        return self.run_func( func_to_run , func_arg_values )


    ''' ---- RUN FUNCTION ---- '''
    def run_func(self, func_node, func_args):
        # Should already be checked in run_fcall that function exists
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
        if (self.trace_output == True):
            print("--------------------------------------------------------")
            print("INSIDE RUN_FUNC: Currently running function: ", node_dict['name'])

            if node_params == []:
                print("\tThis function has NO parameters")
            else:
                print("\tThis function has the following paramters: ")
                for arg in node_params:
                    print("\t\t", arg)

        # Map argument values to the parameter names
        if (node_params != []):
            for (var_name, var_value) in zip(node_params, func_args):
                func_vars[var_name.dict['name']] = var_value

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

                return rval.return_value

        # If exit list of statements without reaching a return statement, return NIL
        return Element("nil")
    

    ''' ---- RUN STATEMENT ---- '''
    def run_statement(self, statement_node, func_vars):
        node_type = statement_node.elem_type

        # Run node's respective function
        match node_type:
            case 'vardef':
                if (self.trace_output == True):
                    print("\nRUN_STATEMENT: This node is a variable definition")
                self.run_vardef(statement_node, func_vars)
            case '=':
                if (self.trace_output == True):
                    print("\nRUN_STATEMENT: This node is a variable assignment")
                self.run_assign(statement_node, func_vars)
            case 'fcall':
                if (self.trace_output == True):
                    print("\nRUN_STATEMENT: This node is a function call")
                self.run_fcall(statement_node, func_vars)
            case 'if':
                if (self.trace_output == True):
                    print("\nRUN_STATEMENT: This node is an IF statement")
                self.evaluate_if(statement_node, func_vars)
            case 'for':
                if (self.trace_output == True):
                    print("\nRUN_STATEMENT: This node is an FOR loop")
                self.run_for_loop(statement_node, func_vars)
            case 'return':
                return_expression = statement_node.dict['expression']

                return_val = None

                if return_expression == None or return_expression.elem_type == "nil":
                    return_val = Element("nil")
                else:
                    return_exp_type = return_expression.elem_type


                    # If returning a CONSTANT value
                    if (return_exp_type in ['int', 'string', 'bool']):
                        return_val = self.get_value(return_expression)
                    
                    # If returning a VARIABLE value
                    elif (return_exp_type == 'var'):
                        return_val = self.get_variable_value(return_expression, func_vars)
                    
                    # If using an OVERLOADED OPERATOR 
                    elif (return_exp_type in self.OVERLOADED_OPERATIONS):
                        return_val = self.overloaded_operator(return_expression, func_vars)
                    
                    # If returning an OPERATION
                    elif (return_exp_type in self.INT_OPERATIONS):
                        return_val = self.run_int_operation( return_expression, func_vars )
                    
                    # If returning result of BOOLEAN operation
                    elif (return_exp_type in self.BOOL_OPERATIONS):
                        return_val = self.run_bool_operation( return_expression, func_vars )
                    
                    # If returning result of EQUALITY comparison operation
                    elif (return_exp_type in self.EQUALITY_COMPARISONS):
                        return_val = self.check_equality( return_expression, func_vars )
                    
                    # If returning result of INTEGER COMPARISON
                    elif (return_exp_type in self.INTEGER_COMPARISONS):
                        return_val = self.integer_compare( return_expression, func_vars )

                    if (return_val == None):  
                        print("ERR: no return value set")

                raise ReturnValue(return_val)

            case _:
                super().error(
                    ErrorType.NAME_ERROR,
                    f"Unrecognized statement of type {node_type}"
                )


    ''' ---- Running Statement Types ---- '''
    # VARDEF
    def run_vardef(self, node, scope_stack):
        if (self.trace_output == True):
            print("\tInside RUN_VARDEF")
        var_name = node.dict['name']
        # print("\n-- Inside RUN_VARDEF\tnode: ", node)
        # print("\tPassed in scope_stack: ", scope_stack)

        # Retrieves top-most scope (within inner-most block)
        latest_scope = scope_stack[-1]

        # Check if variable has already been defined in this scope
        if var_name in latest_scope:
            super().error(
                ErrorType.NAME_ERROR,
                f"Variable {var_name} defined more than once"
            )

        # Add new variable to func_vars           Initial value: None
        latest_scope[var_name] = "DIS IS THE INITIAL VARIABLE VALUE"
        if (self.trace_output == True):
            print("\t\tCurrent func_vars: ", latest_scope)


    ''' ---- Variable Assignment ---- '''
    def run_assign(self, node, scope_stack):
        if (self.trace_output == True):
            print("\tInside RUN_ASSIGN")
        node_dict = node.dict
        var_name = node_dict['name']

        # Check that variable has been declared
        # self.get_variable_value(node, scope_stack)

        scope_to_update = None

        # Traverse stack in reverse order
        for scope in scope_stack[::-1]:
            # If variable exists in this scope, this is the one you want to update
            # ONLY EDIT TOPMOST SCOPE
            if var_name in scope:
                scope_to_update = scope
                break

        # If not found in any scope
        if scope_to_update == None:
            super().error(
                ErrorType.NAME_ERROR,
                f"Variable { {var_name} }not found in any scope"
            )


        # Calculate expression
        node_expression = node_dict['expression']
        node_type = node_expression.elem_type
        # If string, int, or boolean value
        if (node_type == 'string' or node_type == 'int' or node_type == 'bool'):
            scope_to_update[var_name] = self.get_value(node_expression)
            if (self.trace_output == True):
                print("\t\tUpdated scope_stack: ", scope_stack)

        # # If another variable
        elif (node_type == 'var'):
            scope_to_update[var_name] = self.get_variable_value(node_expression, scope_stack)
            if (self.trace_output == True):
                print("\t\tUpdated scope_stack: ", scope_stack)

        # Using an OVERLOADED operator
        elif (node_type in self.OVERLOADED_OPERATIONS):
            scope_to_update[var_name] = self.overloaded_operator(node_expression, scope_stack)
            if (self.trace_output == True):
                print("\t\tUpdated scope_stack: ", scope_stack)
        
        # Integer Operation to be computed
        elif (node_type in self.INT_OPERATIONS):
            scope_to_update[var_name] = self.run_int_operation(node_expression, scope_stack)
            if (self.trace_output == True):
                print("\t\tUpdated scope_stack: ", scope_stack)

        # Boolean Operation to be computed
        elif (node_type in self.BOOL_OPERATIONS):
            scope_to_update[var_name] = self.run_bool_operation(node_expression, scope_stack)
            if (self.trace_output == True):
                print("\t\tUpdated scope_stack: ", scope_stack)

        # Equality comparison
        elif (node_type in self.EQUALITY_COMPARISONS):
            scope_to_update[var_name] = self.check_equality(node_expression, scope_stack)
            if (self.trace_output == True):
                print("\t\tUpdated scope_stack: ", scope_stack)

        # Integer value comparison
        elif (node_type in self.INTEGER_COMPARISONS):
            scope_to_update[var_name] = self.integer_compare(node_expression, scope_stack)
            if (self.trace_output == True):
                print("\t\tUpdated scope_stack: ", scope_stack)

        # Function call
        elif (node_type == 'fcall'):
            scope_to_update[var_name] = self.run_fcall(node_expression, scope_stack)
            if (self.trace_output == True):
                print("\t\tUpdated scope_stack: ", scope_stack)
        
        # Nil value
        elif (node_type == 'nil'):
            scope_to_update[var_name] = Element("nil")
            if (self.trace_output == True):
                print("\t\tUpdated scope_stack: ", scope_stack)
        else:
            super().error(
                    ErrorType.TYPE_ERROR,
                    f"Unrecognized expression \"{node_type}\" in variable assignment for {var_name}"
                ) 


    ''' ---- If Statement ---- '''
    def check_condition(self, condition, func_vars):
        
        # If constant value
        if (condition.elem_type == 'bool'):
            eval_statements =  self.get_value(condition)
        elif (condition.elem_type == 'int' or condition.elem_type == 'string' or condition.elem_type == 'nil'):
            super().error(
                ErrorType.TYPE_ERROR,
                f"Cannot evaluate STRING or INT or NIL in 'if' statement condition"
            )
        
        # If variable value
        elif (condition.elem_type == 'var'):
            # Check variable is defined
            val = self.get_variable_value(condition, func_vars)

            if (val is True) or (val is False):
                eval_statements = val
            else:
                super().error(
                    ErrorType.TYPE_ERROR,
                    f"Cannot evaluate STRING or INT (or nil?) in 'if' statement condition, attempted (via existing variable {condition.dict['name']} value)"
                )

        # If fcall
        elif (condition.elem_type == 'fcall'):
            fcall_return = self.run_fcall(condition, func_vars)
            if fcall_return is True or fcall_return is False:
                eval_statements = fcall_return
            else:
                super().error(
                    ErrorType.TYPE_ERROR,
                    f"Cannot evaluate STRING or INT (or nil?) in 'if' statement condition, attempted via fcall to {condition.dict['name']}"
                )

        elif (condition.elem_type in self.EQUALITY_COMPARISONS):
            eval_statements = self.check_equality(condition, func_vars)
        elif (condition.elem_type in self.INTEGER_COMPARISONS):
            eval_statements = self.integer_compare(condition, func_vars)
        elif (condition.elem_type in self.BOOL_OPERATIONS):
            eval_statements = self.run_bool_operation(condition, func_vars)
        
        # CHECK : IF none of these, is likely an integer expression
        else:
            super().error(
                    ErrorType.TYPE_ERROR,
                    f"Unrecognized expression type { {condition.elem_type} } for 'if' condition: { {condition} }"
                )

        if (eval_statements is not True and eval_statements is not False):
            super().error(
                ErrorType.TYPE_ERROR,
                f"Condition did not evaluate to boolean value { { eval_statements } }"
            )
        return eval_statements

    def evaluate_if(self, node, scope_stack):
        if self.trace_output:
            print("** Inside EVALUATE_IF\tNode: ", node)

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
        # TODO: also need to pop off if return early
            # yup pop off
        scope_stack.pop()
        
    ''' --- For Loop ---- '''
    def run_for_loop(self, node, scope_stack):
        if self.trace_output:
            print("** Inside RUN FOR LOOP\tNode: ", node)

        # print("\n-- Inside RUN_FOR_LOOP\tnode: ", node)
        # print("\tPassed in scope stack: ", scope_stack)

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
            # TODO: pop off when return early
            scope_stack.pop()

            # Update counter variable value
            self.run_assign(update, scope_stack)

            # Check condition again
            eval_condition = self.check_condition(condition, scope_stack)



    ''' ---- Overloaded Operation ---- '''
    def overloaded_operator(self, node, func_vars):
        if (self.trace_output):
            print("IN OVERLOADED OPERATOR function")

        node_type = node.elem_type
        op1 = node.dict['op1']
        op2 = node.dict['op2']

        # Get operator values 
        op1_value = self.eval_op(op1, func_vars)
        op2_value = self.eval_op(op2, func_vars)

        # Check that operands are of the same type
        if ( type(op1_value) != type(op2_value)):
            super().error(
                ErrorType.TYPE_ERROR,
                f"Attempted to use {node_type} on different types { type(op1_value)} and { type(op2_value)}"
            )

        if node_type == '+':
            # '+' is defined for INT and STRING
            if type(op1_value) == int:
                return self.run_int_operation(node, func_vars)
            if type(op1_value) == str:
                return self.run_string_operation(node, func_vars)
            else:
                super().error(
                    ErrorType.TYPE_ERROR,
                    f"No {node_type} operation defined for { type(op1_value) }"
                )
    
    
    ''' ---- Evaluating Expressions / Operations ---- '''
        # Should return value of operation
        # If nested, call run_op on the nested one --> should return value of nested operation to be used in top level op

    def run_int_operation(self, node, func_vars):
        # print("\n INSIDE RUN_INT_OP: ", node)

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
            node_value = self.get_variable_value(node, func_vars)
            # print("\tPAssed in variable w/ value: ", node_value)
            if not (isinstance(node_value, int)) or node_value is True or node_value is False:
                super().error(
                ErrorType.TYPE_ERROR,
                f"Attempted to use string or bool or nil via existing variable {node.dict['name']} in integer operation"
            )
            
            # otherwise, it is an integer value
            return node_value 
        
        if node_type == 'fcall':
            fcall_ret = self.run_fcall(node, func_vars)
            # print("\tPassed in function call with return value ", fcall_ret)
            if not (isinstance(fcall_ret, int)) or fcall_ret is True or fcall_ret is False:
                super().error(
                ErrorType.TYPE_ERROR,
                f"Attempted to use string or bool or nil via fcall in integer operation"
            )
                
            return fcall_ret

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
            return self.run_int_operation(op1, func_vars) // self.run_int_operation(op2, func_vars)


    def run_string_operation(self, node, func_vars):
        if (self.trace_output == True):
            print("STRING OPERATION: ", node.elem_type)

        node_type = node.elem_type

        # TODO: if add more string ops, need to check for NIL

         # BASE: if operand is a VARIABLE --> return that variable's value
        if node_type == 'var':
            val = self.get_variable_value(node, func_vars)

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
        
        if node_type == 'bool' or node_type == 'int':
            super().error(
                    ErrorType.TYPE_ERROR,
                    f"Incompatible types for STRING operation, attempted to use boolean or integer constant value)"
                )
            
        if node_type == 'string':
            return self.get_value(node)
        
        # Function call
        if node_type == 'fcall':
            if (self.trace_output == True):
                print("EXPRESSION USES A FUNCTION CALL")
            return self.run_fcall(node, func_vars)

        # String concatenation
        if node_type == '+':
            op1 = node.dict['op1']
            op2 = node.dict['op2']
            return ( self.run_string_operation(op1, func_vars) + self.run_string_operation(op2, func_vars) )


    ''' ---- Calculate BOOLEAN OPERATION ---- '''

    def run_bool_operation(self, node, func_vars):
        # print("\n-- INSIDE RUN BOOL OP:  node = ", node)

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
            node_value = self.get_variable_value(node, func_vars)

            if node_value is not True and node_value is not False:
                super().error(
                    ErrorType.TYPE_ERROR,
                    f"Attempted to use int, string, or nil via existing variable {node.dict['name']} in BOOL operation"
                )
            
            # Return variable value
            return node_value
        
        
        # Function call
        if node_type == 'fcall':
            fcall_ret = self.run_fcall(node, func_vars)

            if fcall_ret is not True and fcall_ret is not False:
                super().error(
                    ErrorType.TYPE_ERROR,
                    f"Attempted to use int, string, or nil via FCALL RETURN in BOOL operation"
                )

            return fcall_ret
        
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
            op1_value = self.run_bool_operation(op1, func_vars)
            op2_value = self.run_bool_operation(op2, func_vars)
            return op1_value or op2_value
        
        if node_type == '&&':
            op1_value = self.run_bool_operation(op1, func_vars)
            op2_value = self.run_bool_operation(op2, func_vars)
            return op1_value and op2_value


    ''' ---- Comparison Operations ---- '''
    def eval_op(self, node, func_vars):
            op_type = node.elem_type

            # Get variable value
            if op_type == 'var':
                return self.get_variable_value(node, func_vars)

            # If value type
            if op_type == 'int' or op_type == 'string' or op_type == 'bool':
                return self.get_value(node)
            
            if op_type == 'fcall':
                return self.run_fcall(node, func_vars)
            
            if op_type == 'nil':
                return Element("nil")
            
            if op_type in self.OVERLOADED_OPERATIONS:
                return self.overloaded_operator(node, func_vars)
            
            if op_type in self.INT_OPERATIONS:
                return self.run_int_operation(node, func_vars)
            
            if op_type in self.BOOL_OPERATIONS:
                return self.run_bool_operation(node, func_vars)
            
            if op_type in self.EQUALITY_COMPARISONS:
                return self.check_equality(node, func_vars)
            

    def check_equality(self, node, func_vars):   
        if (self.trace_output == True):
            print("CHECKING EQUALITY: ", node.elem_type)

        node_type = node.elem_type
        op1 = node.dict['op1']
        op2 = node.dict['op2']

        # Get operator values 
        op1_value = self.eval_op(op1, func_vars)
        op2_value = self.eval_op(op2, func_vars)


        # print(" -- In CHECK_EQUALITY: \tOp1 value: ", op1_value, "\tOp2 value: ", op2_value)
        # print("\t\tTypes: ", type (op1_value), type(op2_value))

        same = None


        # If both are bool
        if ((op1_value is True) and (op2_value is True)) or ( (op1_value is False) and (op2_value is False)):
            same = True
        elif ( (op1_value is True) and (op2_value is False)) or ((op1_value is False) and (op2_value is True)):
            same = False

        
        # If different types
        elif ( type(op1_value) != type(op2_value) ):
            if (self.trace_output == True):
                print("\t False -- different types for ", op1_value, " and ", op2_value)
            same = False
        else:
            same = (op1_value == op2_value)

        op1_type = None
        op2_type = None
        try:
            op1_type = op1_value.elem_type
        except:
            pass

        try:
            op2_type = op2_value.elem_type
        except:
            pass

        if (op1_type == 'nil' and op2_type == 'nil'):
            same = True
        elif (op1_type == 'nil') or (op2_type == 'nil'):
            same = False


        # Actually perform equality check
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
        if (self.trace_output == True):
            print("CHECKING EQUALITY: ", node.elem_type)

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
    

    def get_variable_value(self, node, scope_stack):
        
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
    def inputi(self, prompt=[]):
        if (prompt == []):
            user_input = super().get_input()
        else:
            prompt_string = prompt[0].dict['val']
            super().output(prompt_string)
            user_input = super().get_input()

        return int(user_input)
        # CHECK - may need to check in future versions before converting to integer

    ''' ---- INPUTIS function ---- '''
    def inputs(self, prompt=[]):
        if (prompt == []):
            user_input = super().get_input()
        else:
            prompt_string = prompt[0].dict['val']
            super().output(prompt_string)
            user_input = super().get_input()

        return str(user_input)

    ''' ---- PRINT function ---- '''
    def printout(self, func_vars, lst=[]):
        if (self.trace_output):
            print("\tINSIDE PRINTOUT")

        # lst = list of strings to concatenate
        string_to_output = ""       # TODO: check if 0 arguments should still print "" or just return
        for element in lst:
            if (self.trace_output == True):
                print("\t", element)
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
                # will raise error if variable hasn't been defined
                val = self.get_variable_value(element, func_vars)
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
                string_to_output += str(self.run_fcall(element, func_vars))

        super().output(string_to_output)
        return Element("nil")