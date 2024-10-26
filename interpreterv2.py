from brewparse import parse_program
from intbase import *
from element import Element

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
        self.program_vars = {}

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

        # TODO: put these outside this function
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
            return self.printout(calling_func_vars, node_dict['args'])
        ''' END OF SEPARATE HANDLING '''


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


        func_arg_values = []

            # if variable - check calling_func_args
            # if op, call run_operation
        for arg in func_args:
            # If it is already a value, add that value
            if arg.elem_type in ['string', 'int', 'bool']:
                func_arg_values.append( self.get_value (arg) )
            elif arg.elem_type == 'var':
                # Check variable is defining within calling function + get value if so
                func_arg_values.append( self.get_variable_value (arg, calling_func_vars))
            
            # Passed in EXPRESION
                # Overloaded operation
            elif arg.elem_type in self.OVERLOADED_OPERATIONS:
                func_arg_values.append( self.overloaded_operator (arg, calling_func_vars) )
                # Integer operation
            elif arg.elem_type in self.INT_OPERATIONS:
                func_arg_values.append( self.run_int_operation (arg, calling_func_vars) )
                # Boolean operation
            elif arg.elem_type in self.BOOL_OPERATIONS:
                func_arg_values.append( self.run_bool_operation (arg, calling_func_vars) )
                # Equality comparison
            elif arg.elem_type in self.EQUALITY_COMPARISONS:
                func_arg_values.append( self.check_equality (arg, calling_func_vars) )
                # Integer comparison
            elif arg.elem_type in self.INTEGER_COMPARISONS:
                func_arg_values.append( self.integer_compare (arg, calling_func_vars) )
            else:
                print("***********************\n\t IN RUN_FCALL, don't know how to process arguments: ", arg)
                # TODO: if error, likely is in missing a case here


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



        # Loop through function statements in order
        for statement_node in node_dict['statements']:
            if (statement_node.elem_type == 'return'):
                return self.run_statement (statement_node, func_vars)
            
            # Otherwise, just execute the statement
            self.run_statement( statement_node , func_vars)

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
                if return_expression == None or return_expression.elem_type == "nil":
                    return Element("nil")
                return_exp_type = return_expression.elem_type

                # If returning a CONSTANT value
                if (return_exp_type in ['int', 'string', 'bool']):
                    return self.get_value(return_expression)
                
                # If returning a VARIABLE value
                if (return_exp_type == 'var'):
                    return self.get_variable_value(return_expression, func_vars)
                
                # If using an OVERLOADED OPERATOR 
                if (return_exp_type in self.OVERLOADED_OPERATIONS):
                    return self.overloaded_operator(return_expression, func_vars)
                
                # If returning an OPERATION
                if (return_exp_type in self.INT_OPERATIONS):
                    return self.run_int_operation( return_expression, func_vars )
                
                # If returning result of BOOLEAN operation
                if (return_exp_type in self.BOOL_OPERATIONS):
                    return self.run_bool_operation( return_expression, func_vars )
                
                # If returning result of EQUALITY comparison operation
                if (return_exp_type in self.EQUALITY_COMPARISONS):
                    return self.check_equality( return_expression, func_vars )
                
                # If returning result of INTEGER COMPARISON
                if (return_exp_type in self.INTEGER_COMPARISONS):
                    return self.integer_compare( return_expression, func_vars )
                

                else:
                    print("THIS IS WHERE I LEFT OFF< NOT DONE YET")

            case _:
                super().error(
                    ErrorType.NAME_ERROR,
                    f"Unrecognized statement of type {node_type}"
                )


    ''' ---- Running Statement Types ---- '''
    # VARDEF
    def run_vardef(self, node, func_vars):
        if (self.trace_output == True):
            print("\tInside RUN_VARDEF")
        var_name = node.dict['name']

        # Check if variable has already been defined
        if var_name in func_vars:
            super().error(
                ErrorType.NAME_ERROR,
                f"Variable {var_name} defined more than once"
            )

        # Add new variable to func_vars           Initial value: None
        func_vars[var_name] = "DIS IS THE INITIAL VARIABLE VALUE"
        if (self.trace_output == True):
            print("\t\tCurrent func_vars: ", func_vars)


    ''' ---- Variable Assignment ---- '''
    def run_assign(self, node, func_vars):
        if (self.trace_output == True):
            print("\tInside RUN_ASSIGN")
        node_dict = node.dict
        var_name = node_dict['name']

        # Check that variable has been declared
        self.get_variable_value(node, func_vars)

        # Calculate expression
        node_expression = node_dict['expression']
        node_type = node_expression.elem_type
        # If string, int, or boolean value
        if (node_type == 'string' or node_type == 'int' or node_type == 'bool'):
            func_vars[var_name] = self.get_value(node_expression)
            if (self.trace_output == True):
                print("\t\tUpdated func_vars: ", func_vars)

        # Using an OVERLOADED operator
        elif (node_type in self.OVERLOADED_OPERATIONS):
            func_vars[var_name] = self.overloaded_operator(node_expression, func_vars)
            if (self.trace_output == True):
                print("\t\tUpdated func_vars: ", func_vars)
        
        # Integer Operation to be computed
        elif (node_type in self.INT_OPERATIONS):
            func_vars[var_name] = self.run_int_operation(node_expression, func_vars)
            if (self.trace_output == True):
                print("\t\tUpdated func_vars: ", func_vars)

        # Boolean Operation to be computed
        elif (node_type in self.BOOL_OPERATIONS):
            func_vars[var_name] = self.run_bool_operation(node_expression, func_vars)
            if (self.trace_output == True):
                print("\t\tUpdated func_vars: ", func_vars)

        # Equality comparison
        elif (node_type in self.EQUALITY_COMPARISONS):
            func_vars[var_name] = self.check_equality(node_expression, func_vars)
            if (self.trace_output == True):
                print("\t\tUpdated func_vars: ", func_vars)

        # Integer value comparison
        elif (node_type in self.INTEGER_COMPARISONS):
            func_vars[var_name] = self.integer_compare(node_expression, func_vars)
            if (self.trace_output == True):
                print("\t\tUpdated func_vars: ", func_vars)

        # Function call
        elif (node_type == 'fcall'):
            func_vars[var_name] = self.run_fcall(node_expression, func_vars)
            if (self.trace_output == True):
                print("\t\tUpdated func_vars: ", func_vars)
        
        # Nil value
        elif (node_type == 'nil'):
            func_vars[var_name] = Element("nil")
            if (self.trace_output == True):
                print("\t\tUpdated func_vars: ", func_vars)
        else:
            super().error(
                    ErrorType.TYPE_ERROR,
                    f"Unrecognized expression \"{node_expression.elem_type}\" in variable assignment for {var_name}"
                ) 
        
    ''' ---- If Statement ---- '''
    def check_condition(self, condition, func_vars):
        # If constant or variable
        if (condition.elem_type == 'bool'):
            eval_statements =  self.get_value(condition)
        elif (condition.elem_type == 'int' or condition.elem_type == 'string'):
            super().error(
                ErrorType.TYPE_ERROR,
                f"Cannot evaluate STRING or INT in 'if' statement condition"
            )
        
        # If variable value
        elif (condition.elem_type == 'var'):
            # Check variable is defined
            self.get_variable_value(condition, func_vars)

            val = func_vars[ condition.dict['name'] ]
            if (val is True) or (val is False):
                eval_statements = func_vars[ condition.dict['name'] ]
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

        return eval_statements

    def evaluate_if(self, node, func_vars):
        if self.trace_output:
            print("** Inside EVALUATE_IF\tNode: ", node)

        condition = node.dict['condition']
        statements = node.dict['statements']
        else_statements = node.dict['else_statements']

        eval_condition = self.check_condition(condition, func_vars)

        if (eval_condition):
            # Loop through function statements in order
            for statement_node in statements:
                if (statement_node.elem_type == 'return'):
                    return self.run_statement (statement_node, func_vars)
                
                # Otherwise, just execute the statement
                self.run_statement( statement_node , func_vars)
        else:
            if else_statements != None:
                for statement_node in else_statements:
                    if (statement_node.elem_type == 'return'):
                        return self.run_statement (statement_node, func_vars)
                    
                    # Otherwise, just execute the statement
                    self.run_statement( statement_node , func_vars)
        
    ''' --- For Loop ---- '''
    def run_for_loop(self, node, func_vars):
        if self.trace_output:
            print("** Inside RUN FOR LOOP\tNode: ", node)

        initialize = node.dict['init']
        condition = node.dict['condition']
        update = node.dict['update']
        statements = node.dict['statements']

        # Initialize counter variable in variable dictionary
        self.run_assign(initialize, func_vars)

        # Check condition is true to begin with
        eval_condition = self.check_condition(condition, func_vars)

        # While condition is true, execute statements
        while (eval_condition):
            # Loop through function statements in order
            for statement_node in statements:
                if (statement_node.elem_type == 'return'):
                    return self.run_statement (statement_node, func_vars)
                
                # Otherwise, just execute the statement
                self.run_statement( statement_node , func_vars)

            # Update counter variable value
            self.run_assign(update, func_vars)

            # Check condition again
            eval_condition = self.check_condition(condition, func_vars)


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
    
    
    ''' ---- Evaluating Expressions / Operations ---- '''
        # Should return value of operation
        # If nested, call run_op on the nested one --> should return value of nested operation to be used in top level op
    def run_int_operation(self, node, func_vars):
        if (self.trace_output == True):
            print("INT OPERATION: ", node.elem_type)

        node_type = node.elem_type

         # BASE: if operand is a VARIABLE --> return that variable's value
        if node_type == 'var':
            self.get_variable_value(node, func_vars)
            # Check that variable type isn't a string
            val = func_vars[ node.dict['name'] ]
            if (isinstance( val,  str)):
                super().error(
                    ErrorType.TYPE_ERROR,
                    f"Incompatible types for arithmetic operation, attempted to use string (via existing variable {node.dict['name']} value)"
                )
            # Check if boolean
            if (val is True) or (val is False):
                super().error(
                    ErrorType.TYPE_ERROR,
                    f"Incompatible types for arithmetic operation, attempted to use boolean (via existing variable {node.dict['name']} value)"
                )
            return val

        # BASE: if operand is a VALUE --> return that value
        if node_type == 'int':
            return self.get_value(node)
        
        if node_type == 'fcall':
            if (self.trace_output == True):
                print("EXPRESSION USES A FUNCTION CALL")
            return self.run_fcall(node, func_vars)
        
        # If try to operate on a string --> error
        if node_type == 'string':
            super().error(
                ErrorType.TYPE_ERROR,
                "Incompatible types for arithmetic operation, attempted to use string"
            )

        # UNARY operation (integer negation)
        if node_type == 'neg':
            return -( self.run_int_operation( node.dict['op1'], func_vars))

        # Try operation types, recursively call on operands
        if node_type == '+':
            op1 = node.dict['op1']
            op2 = node.dict['op2']
            return self.run_int_operation(op1, func_vars) + self.run_int_operation(op2, func_vars)
        if node_type == '-':
            op1 = node.dict['op1']
            op2 = node.dict['op2']
            return self.run_int_operation(op1, func_vars) - self.run_int_operation(op2, func_vars) 
        if node_type == '*':
            op1 = node.dict['op1']
            op2 = node.dict['op2']
            return self.run_int_operation(op1, func_vars) * self.run_int_operation(op2, func_vars)   
        if node_type == '/':
            op1 = node.dict['op1']
            op2 = node.dict['op2']
            return self.run_int_operation(op1, func_vars) // self.run_int_operation(op2, func_vars)

    def run_string_operation(self, node, func_vars):
        if (self.trace_output == True):
            print("STRING OPERATION: ", node.elem_type)

        node_type = node.elem_type

         # BASE: if operand is a VARIABLE --> return that variable's value
        if node_type == 'var':
            self.get_variable_value(node, func_vars)

            # Check if INT or BOOL
            if (isinstance( func_vars[node.dict['name']], int)):
                super().error(
                    ErrorType.TYPE_ERROR,
                    f"Incompatible types for STRING operation, attempted to use INTEGER (via existing variable {node.dict['name']} value)"
                )

            if ( func_vars[ node.dict['name']] is True or func_vars[ node.dict['name']] is False):
                super().error(
                    ErrorType.TYPE_ERROR,
                    f"Incompatible types for STRING operation, attempted to use BOOLEAN (via existing variable {node.dict['name']} value)"
                )
            # Otherwise, return value
            return func_vars[ node.dict['name'] ]
        
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
        if (self.trace_output == True):
            print("OPERATION: ", node.elem_type)

        node_type = node.elem_type

         # BASE: if operand is a VARIABLE --> return that variable's value
        if node_type == 'var':
            self.get_variable_value(node, func_vars)

            if (isinstance( func_vars[ node.dict['name'] ], str)):
                super().error(
                    ErrorType.TYPE_ERROR,
                    f"Incompatible types for BOOLEAN operation, attempted to use string (via existing variable {node.dict['name']} value)"
                )

            # CHECK: this should check for integers, and even exlude 0 and 1
            if ( func_vars[ node.dict['name']] is not True) and ( func_vars[ node.dict['name']] is not False):
                super().error(
                    ErrorType.TYPE_ERROR,
                    f"Incompatible types for BOOLEAN operation, attempted to use string (via existing variable {node.dict['name']} value)"
                )
            return func_vars[ node.dict['name'] ]
        
        if node_type == 'string' or node_type == 'int':
            super().error(
                    ErrorType.TYPE_ERROR,
                    f"Incompatible types for BOOLEAN operation, attempted to use string or integer constant value)"
                )
            
        if node_type == 'bool':
            return self.get_value(node)
        
        # Function call
        if node_type == 'fcall':
            if (self.trace_output == True):
                print("EXPRESSION USES A FUNCTION CALL")
            return self.run_fcall(node, func_vars)
            
        # Unary Boolean NOT
        if node_type == '!':
            return not (self.run_bool_operation( node.dict['op1'], func_vars))
        
        # Boolean OR
        if node_type == '||':
            op1 = node.dict['op1']
            op2 = node.dict['op2']
            return ( self.run_bool_operation(op1, func_vars) or self.run_bool_operation(op2, func_vars) )
        
        # Boolean AND
        if node_type == '&&':
            op1 = node.dict['op1']
            op2 = node.dict['op2']
            return ( self.run_bool_operation(op1, func_vars) and self.run_bool_operation(op2, func_vars) )


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

        same = None

        # SPECIAL case: 'nil' values
        if (op1_value == 'nil') and (op2_value == 'nil'):
            same = True
        elif (op1_value == 'nil') or (op2_value == 'nil'):
            same = False

        # If both are bool
        elif ((op1_value is True) and (op2_value is True)) or ( (op1_value is False) and (op2_value is False)):
            same = True
        elif ( (op1_value is True) and (op2_value is False)) or ((op1_value is False) and (op2_value is True)):
            same = False
        
        # If different types
        if ( type(op1_value) != type(op2_value) ):
            if (self.trace_output == True):
                print("\t False -- different types for ", op1_value, " and ", op2_value)
            same = False
        else:
            same = (op1_value == op2_value)

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
        op1_value = self.eval_op(op1, func_vars)
        op2_value = self.eval_op(op2, func_vars)

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
    

    # TODO: This is probably where most of the shadowing logic will need to happen
    def get_variable_value(self, node, defined_vars):
        var_name = node.dict['name']
        if var_name not in defined_vars:
            super().error(
                ErrorType.NAME_ERROR,
                f"Variable {var_name} has not been declared w/in function scope"
            )
        return defined_vars[var_name]
    
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