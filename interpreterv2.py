from brewparse import parse_program
from intbase import *

class Interpreter(InterpreterBase):
    program_vars = {}
   
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
            if (func.dict['name'] == 'main'):
                main_node = func
        if (main_node == None):
            super().error(
                ErrorType.NAME_ERROR,
                "No MAIN node found in program"
            )
        
        # Run MAIN node
        self.run_func(main_node)


    ''' ---- RUN FUNCTION ---- '''
    def run_func(self, func_node):
        if (func_node.elem_type != 'func' and func_node.elem_type != 'fcall'):
            super().error(
                ErrorType.TYPE_ERROR,
                "Non-function node passed into run_func"
            )
        
        node_dict = func_node.dict
        if (self.trace_output == True):
            print("\n-- Currently running function: ", node_dict['name'])

        
        func_name = node_dict['name']

        # Check that function has been defined
        # TODO: don't hard-code this when there are custom function calls
        allowable_functions = ['inputi', 'print', 'main']
        if func_name not in allowable_functions:
            super().error(
                ErrorType.NAME_ERROR,
                f"Function {node_dict['name']} has not been defined"
            )
        
        # If INPUTI function
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
            return self.printout(node_dict['args'])

        # IF not PRINT or INPUTI, go through statements (instead of returning value)
        ''' ---- Run statements in order ---- '''
        for statement_node in node_dict['statements']:
            self.run_statement( statement_node )
    

    ''' ---- RUN STATEMENT ---- '''
    def run_statement(self, statement_node):
        node_type = statement_node.elem_type

        # Run node's respective function
        match node_type:
            case 'vardef':
                if (self.trace_output == True):
                    print("\nRUN_STATEMENT: This node is a variable definition")
                self.run_vardef(statement_node)
            case '=':
                if (self.trace_output == True):
                    print("\nRUN_STATEMENT: This node is a variable assignment")
                self.run_assign(statement_node)
            case 'fcall':
                if (self.trace_output == True):
                    print("\nRUN_STATEMENT: This node is a function call")
                self.run_func(statement_node)
            case _:
                super().error(
                    ErrorType.NAME_ERROR,
                    f"Unrecognized statement of type {node_type}"
                )


    ''' ---- Running Statement Types ---- '''
    # VARDEF
    def run_vardef(self, node):
        if (self.trace_output == True):
            print("\tInside RUN_VARDEF")
        var_name = node.dict['name']

        # Check if variable has already been defined
        if var_name in self.program_vars:
            super().error(
                ErrorType.NAME_ERROR,
                f"Variable {var_name} defined more than once"
            )

        # Add new variable to PROGRAM_VARS           Initial value: None
        self.program_vars[var_name] = None
        if (self.trace_output == True):
            print("\t\tCurrent program_vars: ", self.program_vars)

    ''' ---- Variable Assignment ---- '''
    def run_assign(self, node):
        if (self.trace_output == True):
            print("\tInside RUN_ASSIGN")
        node_dict = node.dict
        var_name = node_dict['name']

        # Check that variable has been declared
        if var_name not in self.program_vars:
            super().error(
                ErrorType.NAME_ERROR,
                f"Variable {var_name} has not been declared"
            )


        # Calculate expression
        node_expression = node_dict['expression']
        node_type = node_expression.elem_type
        # If string value
        if (node_type == 'string'):
            self.program_vars[var_name] = self.get_value(node_expression)
            if (self.trace_output == True):
                print("\t\tUpdated program_vars: ", self.program_vars)
        
        # Operation to be computed
        elif (node_type in ['int', 'var', '+', '-', '*', '/']):
            self.program_vars[var_name] = self.run_operation(node_expression)
            if (self.trace_output == True):
                print("\t\tUpdated program_vars: ", self.program_vars)

        # Function call
        elif (node_type == 'fcall'):
            self.program_vars[var_name] = self.run_func(node.dict['expression'])    # TODO: check + replace w/ node_expression
            if (self.trace_output == True):
                print("\t\tUpdated program_vars: ", self.program_vars)
        else:
            super().error(
                    ErrorType.TYPE_ERROR,
                    f"Unrecognized expression \"{node_expression.elem_type}\" in variable assignment for {var_name}"
                ) 
        

    ''' ---- Evaluating Expressions / Operations ---- '''
        # Should return value of operation
        # If nested, call run_op on the nested one --> should return value of nested operation to be used in top level op
    def run_operation(self, node):
        if (self.trace_output == True):
            print("OPERATION: ", node.elem_type)

        node_type = node.elem_type

         # BASE: if operand is a VARIABLE --> return that variable's value
        if node_type == 'var':
            if node.dict['name'] not in self.program_vars:
                super().error(
                    ErrorType.NAME_ERROR,
                    f"Variable {node.dict['name']} has not been declared"
                )
            # Check that variable type isn't a string
            if (isinstance( self.program_vars[ node.dict['name'] ], str)):
                super().error(
                    ErrorType.TYPE_ERROR,
                    f"Incompatible types for arithmetic operation, attempted to use string (via existing variable {node.dict['name']} value)"
                )
            return self.program_vars[ node.dict['name'] ]

        # BASE: if operand is a VALUE --> return that value
        if node_type == 'int':
            return self.get_value(node)
        
        if node_type == 'fcall':
            if (self.trace_output == True):
                print("EXPRESSION USES A FUNCTION CALL")
            return self.run_func(node)
        
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
            return self.run_operation(op1) + self.run_operation(op2)
        if node_type == '-':
            op1 = node.dict['op1']
            op2 = node.dict['op2']
            return self.run_operation(op1) - self.run_operation(op2) 
        if node_type == '*':
            op1 = node.dict['op1']
            op2 = node.dict['op2']
            return self.run_operation(op1) * self.run_operation(op2)   
        if node_type == '/':            # TODO: change this to // b/c it's supposed to be INTEGER division
            op1 = node.dict['op1']
            op2 = node.dict['op2']
            return self.run_operation(op1) / self.run_operation(op2)


    # Return value of value nodes
    def get_value(self, node):
        return node.dict['val']         # Maybe TODO: if this is None, add a check or throw an error instead of returning
    
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
    def printout(self, lst=[]):
        # lst = list of strings to concatenate
        # TODO: loop over, concatenate, then print
            # Need to evaluate variables, expressions, + function calls
        string_to_output = ""       # TODO: check if 0 arguments should still print "" or just return
        for element in lst:
            if (self.trace_output == True):
                print("\t", element)
            node_type = element.elem_type
            if node_type == 'string':
                string_to_output += element.dict['val']
            elif (node_type in ['int', '+', '-', '*', '/']):
                string_to_output += str (self.run_operation(element))
            # elif node_type == 'int':
            #     string_to_output += str( element.dict['val'] )
            
            # # If variable, retrieve variable value
            elif node_type == 'var':
                if element.dict['name'] not in self.program_vars:
                    super().error(
                        ErrorType.NAME_ERROR,
                        f"Variable {element.dict['name']} has not been declared (in print statement)"
                    )
                string_to_output += str( self.program_vars[element.dict['name']])

        super().output(string_to_output)
        return None