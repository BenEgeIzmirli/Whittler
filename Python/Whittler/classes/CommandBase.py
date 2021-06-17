from Whittler.classes.input_utils import *


class ArgumentBase:
    name = NotImplemented
    optional = False

    def __init__(self):
        self.resultdb = None
    
    def __repr__(self):
        if self.optional:
            return f"[[{self.name}]]"
        return f"[{self.name}]"
    
    def __str__(self):
        return f"[{self.name}]"

    # returns None on failure
    def interpret_arg(self, arg, quiet=False):
        raise NotImplementedError()

    def set_name(self, newname):
        self.name = newname
        return self
    
    def set_optional(self):
        self.optional = True
        return self

class ContextPointerArgument(ArgumentBase):
    name = "row"
    def interpret_arg(self, arg, quiet=False):
        if not isinstance(self.resultdb.context_pointers, dict):
            if not quiet:
                wprint(f"Can't dig deeper.")
            return None
        
        try:
            choice = int(arg)
            # The value supplied was an int, so should be looked up in the context_pointers dict
            if choice not in self.resultdb.context_pointers:
                if not quiet:
                    wprint(f"Could not recognize {choice} as one of the IDs listed above.\n")
                return None
            return self.resultdb.context_pointers[choice]
        except ValueError:
            # we couldn't parse it as an int, so it must be a string literal attribute value
            choice = arg
            for ptr in self.resultdb.context_pointers.values():
                # The attribute values will be the .value property of the Vertex object given by the last
                # get_by_index operation called on this pointer.
                if ptr.path[-1].value == arg:
                    return ptr
            if not quiet:
                wprint(f"Could not recognize \"{choice}\" as one of the attributes of this dataset.\n")
            return None
        

class ResultAttributeArgument(ArgumentBase):
    name = "attr"

class IntegerArgument(ArgumentBase):
    name = "int"
    def interpret_arg(self, resultdb, arg):
        try:
            argval = int(arg)
        except ValueError:
            return None
        return argval

class StringArgument(ArgumentBase):
    name = "str"

class FilenameArgument(ArgumentBase):
    name = "fname"


class CommandBase:
    name = NotImplemented
    arguments = []

    def __init__(self, resultdb):
        self.resultdb = resultdb
        for arg in self.arguments:
            arg.resultdb = resultdb

    def execute(self, *args):
        raise NotImplementedError()

    def interpret_args(self, *args):
        ret = []
        for i in range(len(self.arguments)):
            expected_argtype = self.arguments[i]
            if i >= len(args) and not expected_argtype.optional:
                return False
            ret.append(expected_argtype.interpret_arg(args[i]))
        return ret
    