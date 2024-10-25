from brewparse import parse_program
from intbase import *
from element import Element

class Interpreter(InterpreterBase):
    program_vars = {}
    defined_functions = {}      # should map function name to list of func nodes (for overloading)
   
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
        ''' PRINT + INPTUTI handling'''
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

        # TODO: for each argument
            # if variable - check calling_func_args
            # if op, call run_operation
        for arg in func_args:
            # If it is already a value, add that value
            if arg.elem_type in ['string', 'int', 'bool']:
                func_arg_values.append( self.get_value (arg) )
            elif arg.elem_type == 'var':
                # Check variable is defining within calling function + get value if so
                func_arg_values.append( self.get_variable_value (arg, calling_func_vars))
            else:
                # TODO: if error, likely is in missing a case here
                func_arg_values.append( self.run_operation (arg, calling_func_vars) )



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
        # TODO: add cases for 'if', 'for', 'return'
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
                
                # If returning an OPERATION
                if (return_exp_type in ['+', '-', '*', '/']):
                    return self.run_operation( return_expression, func_vars )
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
        func_vars[var_name] = None
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
        
        # Operation to be computed
        elif (node_type in ['var', '+', '-', '*', '/']):
            func_vars[var_name] = self.run_operation(node_expression, func_vars)
            if (self.trace_output == True):
                print("\t\tUpdated func_vars: ", func_vars)

        # Function call
        elif (node_type == 'fcall'):
            func_vars[var_name] = self.run_fcall(node_expression, func_vars)
            if (self.trace_output == True):
                print("\t\tUpdated func_vars: ", func_vars)
        else:
            super().error(
                    ErrorType.TYPE_ERROR,
                    f"Unrecognized expression \"{node_expression.elem_type}\" in variable assignment for {var_name}"
                ) 
        

    ''' ---- Evaluating Expressions / Operations ---- '''
        # Should return value of operation
        # If nested, call run_op on the nested one --> should return value of nested operation to be used in top level op
    def run_operation(self, node, func_vars):
        if (self.trace_output == True):
            print("OPERATION: ", node.elem_type)

        # print("-- Running operation: ", node)

        node_type = node.elem_type

         # BASE: if operand is a VARIABLE --> return that variable's value
        if node_type == 'var':
            self.get_variable_value(node, func_vars)
            # Check that variable type isn't a string
            if (isinstance( func_vars[ node.dict['name'] ], str)):
                super().error(
                    ErrorType.TYPE_ERROR,
                    f"Incompatible types for arithmetic operation, attempted to use string (via existing variable {node.dict['name']} value)"
                )
            # Check that variable type isn't a boolean
            if (isinstance( func_vars[ node.dict['name'] ], bool)):
                super().error(
                    ErrorType.TYPE_ERROR,
                    f"Incompatible types for arithmetic operation, attempted to use boolean (via existing variable {node.dict['name']} value)"
                )
            return func_vars[ node.dict['name'] ]

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

        # Try operation types, recursively call on operands
        if node_type == '+':
            op1 = node.dict['op1']
            op2 = node.dict['op2']
            return self.run_operation(op1, func_vars) + self.run_operation(op2, func_vars)
        if node_type == '-':
            op1 = node.dict['op1']
            op2 = node.dict['op2']
            return self.run_operation(op1, func_vars) - self.run_operation(op2, func_vars) 
        if node_type == '*':
            op1 = node.dict['op1']
            op2 = node.dict['op2']
            return self.run_operation(op1, func_vars) * self.run_operation(op2, func_vars)   
        if node_type == '/':
            op1 = node.dict['op1']
            op2 = node.dict['op2']
            return self.run_operation(op1, func_vars) // self.run_operation(op2, func_vars)


    # Return value of value nodes
    def get_value(self, node):
        return node.dict['val']         # Maybe TODO: if this is None, add a check or throw an error instead of returning
    

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
            elif (node_type in ['int', '+', '-', '*', '/']):
                string_to_output += str (self.run_operation(element, func_vars))
            
            # # If variable, retrieve variable value
            elif node_type == 'var':
                # will raise error if variable hasn't been defined
                val = self.get_variable_value(element, func_vars)
                # Separate handling to print true / false in all lower case
                if val == True:
                    string_to_output += "true"
                elif val == False:
                    string_to_output += "false"
                else:
                    string_to_output += str( val )

            # TODO: print FCALL

        super().output(string_to_output)
        return Element("nil")