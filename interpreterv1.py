# yay I <3 nterpreter
from brewparse import parse_program
from intbase import *

class Interpreter(InterpreterBase):
    program_vars = {}
   
    def __init__(self, console_output=True, inp=None, trace_output=False):
        super().__init__(console_output, inp)   # call InterpreterBase's constructor

    def run(self, program):
        ''' 
            program = array of strings containing program
        '''
        ast = parse_program(program)
        self.program_vars = {}