# INCOMPLETE :(






from Whittler.classes.input_utils import *

class ArgumentBase:
    name = NotImplemented
    optional = False
    
    def __repr__(self):
        return f"[{'[' if self.optional else ''}{self.name}{']' if self.optional else ''}]"

    # returns None on failure
    def interpret_arg(self, resultdb, arg):
        raise NotImplementedError()

    def set_name(self, newname):
        self.name = newname
        return self
    
    def set_optional(self):
        self.optional = True
        return self

class ContextPointerArgument(ArgumentBase):
    name = "id"
    def interpret_arg(self, resultdb, arg):
        if not isinstance(resultdb.context_pointers, dict):
            if not quiet:
                wprint(f"Can't dig deeper.")
            return None
        
        choice = get_int_from_args(args, position=id_arg_position)
        
        # No value was supplied for this arg position
        if choice is False:
            return False
        
        # we couldn't parse it as an int, so it must be a string literal attribute value
        if choice is None:
            choice = args[id_arg_position]
            for ptr in resultdb.context_pointers.values():
                # The attribute values will be the .value property of the Vertex object given by the last
                # get_by_index operation called on this pointer.
                if ptr.path[-1].value == choice:
                    return ptr
            if not quiet:
                wprint(f"Could not recognize \"{choice}\" as one of the attributes of this dataset.\n")
            return None
        
        # The value supplied was an int, so should be looked up in the context_pointers dict
        elif choice not in resultdb.context_pointers:
            if not quiet:
                wprint(f"Could not recognize {choice} as one of the IDs listed above.\n")
            return None
        return resultdb.context_pointers[choice]

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

    def execute(self, resultdb, args):
        raise NotImplementedError()

    def interpret_args(self, resultdb, args):
        ret = []
        for i in range(len(self.arguments)):
            expected_argtype = self.arguments[i]
            if i >= len(args) and not expected_argtype.optional:
                return False
            ret.append(expected_argtype.interpret_arg(args[i]))
        return ret