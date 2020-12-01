from classes.NestedObjectPointer import NestedObjectPointerInterface
from config import Config
from collections import defaultdict, OrderedDict
import hashlib
import re


class RelevanceInterface(NestedObjectPointerInterface):

    @property
    def relevant(self):
        return any(result.relevant for result in self.real_iter_values())

    def mark_irrelevant(self):
        for obj in self.real_iter_values():
            obj.mark_irrelevant()

    def mark_relevant(self):
        for obj in self.real_iter_values():
            obj.mark_relevant()

    def real_length(self):
        return len([e for e in self.real_iter_values()])

    def real_iter_values(self):
        raise NotImplementedError()


class Result(dict, RelevanceInterface):

    FRIENDLY_NAME = NotImplemented
    
    ATTRIBUTES = []
    SILENCED_ATTRIBUTES = set()
    SOLO_ATTRIBUTE = None
    SUPER_SOLO_ATTRIBUTE = None

    def __init__(self,resultdict):
        self.original_resultdict = resultdict
        self._cached_hash = 0
        self._cached_hash_valid = True
        self._frozen = False
        dict.__init__(self)
        self._relevant = True
        RelevanceInterface.__init__(self)

        if "whittler_filename" not in self.ATTRIBUTES:
            self.ATTRIBUTES.insert(0,"whittler_filename")
        for k,v in resultdict.items():
            self[k] = v
    
    def __setitem__(self, key, value):
        if key not in self.ATTRIBUTES:
            raise Exception(f"Unrecognized key {key} in this result.")
        if type(value) != str:
            value = str(value)
            #raise Exception(f"To support hashing and sorting logic, only unicode strings are allowed as values (got {type(value)}).")
        if self._frozen:
            raise Exception("Cannot modify this result after it has been added to the database!")
        if self.Config.REMOVE_ANSI_CONTROL_CHARACTERS:
            value = self.filter_ansi(value)
        self._cached_hash_valid = False
        super().__setitem__(key,value)
    
    def __hash__(self):
        if self._cached_hash_valid:
            return self._cached_hash
        new_hashval = 0
        for attr in self.ATTRIBUTES:
            if attr in self:
                new_hashval = int(hashlib.md5(bytes(str(new_hashval)+attr+self[attr],'utf-8')).hexdigest(),16)
        self._cached_hash = new_hashval
        self._cached_hash_valid = True
        return new_hashval
    
    def __eq__(self, other):
        if not isinstance(other, Result):
            return False
        return hash(self) == hash(other)
    
    @staticmethod
    def give_result_dict_list(fname):
        raise NotImplementedError()
    
    # https://stackoverflow.com/questions/14693701/how-can-i-remove-the-ansi-escape-sequences-from-a-string-in-python
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    
    # Takes a unicode string, and filters out all 7-bit ANSI escape characters.
    def filter_ansi(self, s):
        return self.ansi_escape.sub('', s)
    
    # This returns an elegant representation of the result. By default, it does not print the "diff"
    # component itself because it is usually very long and clutters up the output.
    def pretty_repr(self):
        s = ""
        def adds(content):
            nonlocal s
            s += str(content) + "\n"
        for k,v in self.items():
            if not self.SUPER_SOLO_ATTRIBUTE is None:
                if k != self.SUPER_SOLO_ATTRIBUTE:
                    continue
                adds(v)
                break
            elif not self.SOLO_ATTRIBUTE is None:
                if k != self.SOLO_ATTRIBUTE:
                    continue
            if not v.strip():
                continue
            adds(k)
            if k in self.SILENCED_ATTRIBUTES and k != self.SOLO_ATTRIBUTE:
                adds("... silenced ...")
                adds("")
                continue
            adds("\n".join("    "+line for line in v.splitlines()))
            adds("")
        return s
    
    def display(self):
        print(self.pretty_repr())
    

    #######################################
    #  RelevanceInterface implementations
    #

    @property
    def relevant(self):
        return self._relevant
    
    def mark_irrelevant(self):
        self._relevant = False

    def mark_relevant(self):
        self._relevant = True
    
    def real_iter_values(self):
        return [self]
    

    #################################################
    #  NestedObjectPointerInterface implementations
    #
    
    def enumerate_child_pointers(self, pointer_to_me):
        return OrderedDict({str(hash(self)):pointer_to_me})
    
    def size(self):
        return 1
    
    def all_result_objects(self):
        return [self]

    def show_view(self, pointer_to_me=None, ct=0, limit=None, show_irrelevant=False):
        return (self.pretty_repr(), pointer_to_me)
    
    def export(self):
        return {**self.original_resultdict, "whittler_filename":self["whittler_filename"]}
    

class RelevanceFilteredResultList(list, RelevanceInterface):
    def __init__(self,iterable=None):
        list.__init__(self)
        RelevanceInterface.__init__(self)
        if not iterable is None:
            for e in iterable:
                self.append(e)
    
    def __setitem__(self, index, value):
        assert isinstance(value, RelevanceInterface)
        list.__setitem__(self,index,value)
    
    def __iter__(self):
        yield from (e for e in self.real_iter_values() if e.relevant)
    
    def __len__(self):
        return len([e for e in self])
    
    # todo: speed up "result in RFRLobj" lookups - most of the time is spent checking "if result in self.results" in ResultDatabase.add_result
    
    def append(self, newitem):
        assert isinstance(newitem, RelevanceInterface)
        list.append(self,newitem)
    
    def extend(self, iterable):
        for e in iterable:
            self.append(e)
    
    def yield_irrelevant(self):
        yield from (e for e in list.__iter__(self) if not e.relevant)
    
    def get_by_id(self, result_id):
        return list(filter(self.real_iter_values(),key=lambda result:str(hash(result))[:6] == result_id))[0]
    

    #######################################
    #  RelevanceInterface implementations
    #
    
    def real_iter_values(self):
        yield from list.__iter__(self)


    #################################################
    #  NestedObjectPointerInterface implementations
    #
    
    def enumerate_child_pointers(self, pointer_to_me):
        ret = OrderedDict()
        for i in range(self.real_length()):
            if self[i].relevant:
                if not pointer_to_me is None:
                    ptr = pointer_to_me.copy()
                    ptr.get_by_index(i)
                    ret[i] = ptr
                else:
                    ret[i] = None
        if not pointer_to_me is None:
            self._cached_pointers = ret
        return ret
    
    def size(self):
        return len(self)
    
    def all_result_objects(self):
        return [result for result in self]

    def show_view(self, pointer_to_me=None, ct=0, limit=None, show_irrelevant=False):
        ret = OrderedDict()
        s = ""
        def adds(string, prefix=""):
            nonlocal s
            s += prefix + string + "\n"
        for key, ptr in self.give_child_pointers(pointer_to_me).items():
            result = self[key]
            if not show_irrelevant and not result.relevant:
                continue
            result_id = str(hash(result))[:6]
            if not result.SUPER_SOLO_ATTRIBUTE is None:
                adds(result.pretty_repr())
            else:
                adds("~~~~~~~~~~~~~~~~~~~~~~~~~")
                adds(f"  Result with ID {result_id}    ")
                adds("~~~~~~~~~~~~~~~~~~~~~~~~~")
                for line in result.pretty_repr().split("\n"):
                    adds(line, prefix="| ")
                s += "\n\n"
            ret[int(result_id)] = ptr
            if not limit is None and len(ret) >= limit:
                break
        return (s, ret)
    
    def export(self):
        return [result.export() for result in self]
    

class ValueLengthSortedResultDict(defaultdict, RelevanceInterface):

    def __init__(self, *args, **kwargs):
        defaultdict.__init__(self, *args, **kwargs)
        RelevanceInterface.__init__(self)
        NestedObjectPointerInterface.__init__(self)
    
    def items(self):
        yield from reversed(sorted(defaultdict.items(self),key=lambda tup:len(tup[1])))
        
    def keys(self):
        yield from (k for k,v in self.items())
        
    def values(self):
        yield from (v for k,v in self.items())
    
    def __setitem__(self, key, value):
        assert isinstance(value, RelevanceInterface)
        defaultdict.__setitem__(self,key,value)
    
    def __len__(self):
        return len([obj for obj in self.values() if obj.relevant])
    

    #######################################
    #  RelevanceInterface implementations
    #
    
    def real_iter_values(self):
        yield from (self[key] for key in defaultdict.__iter__(self))
    

    #################################################
    #  NestedObjectPointerInterface implementations
    #
    
    def enumerate_child_pointers(self, pointer_to_me):
        ret = OrderedDict()
        for k in self.keys():
            ptr = pointer_to_me.copy()
            ptr.get_by_index(k)
            ret[k] = ptr
        self._cached_pointers = ret
        return ret
    
    def size(self):
        return sum(obj.size() for obj in self.values())
    
    def all_result_objects(self):
        ret = []
        for resultcontainer in self.values():
            ret.extend(resultcontainer.all_result_objects())
        return ret

    def show_view(self, pointer_to_me=None, ct=0, limit=None, show_irrelevant=False):
        max_width = self.Config.MAX_OUTPUT_WIDTH
        ret = OrderedDict()
        lines = []
        for key, ptr in self.give_child_pointers(pointer_to_me).items():
            value = self[key]
            if not show_irrelevant and not len(value):
                continue
            sanitized_key = key.strip().replace("\n","\\n")
            line = "| {:4d} | {:5d} | {:8d} | {}".format(ct,value.real_length(),len(value),sanitized_key)
            if len(line) > max_width-2:
                line = line[:max_width-2-7]+" [...] "
            lines.append(line)
            ret[ct] = ptr
            ct += 1
            if not limit is None and len(lines) >= limit:
                break
        headertext = "|  id  | total | relevant | attribute value  "
        max_linelen = max(len(line) for line in lines) if len(lines) else 0
        max_linelen = len(headertext) if len(headertext) > max_linelen else max_linelen
        header_footer = "+" + "="*(max_linelen-1) + "+\n"
        divider = "|{:-<6}+{:-<7}+{:-<10}+".format("","","")
        divider = divider + "-"*(max_linelen-len(divider)) + "|\n"
        header = header_footer
        header += headertext + " "*(max_linelen-len(headertext)) + "|\n"
        header += divider
        s = header
        for line in lines:
            s += line + " "*(max_linelen-len(line)) + "|\n"
        s += header_footer
        return (s, ret)
    
    def export(self):
        ret = []
        for value in self.values():
            if value.relevant:
                ret.extend(value.export())
        return ret
    

class ResultDict(ValueLengthSortedResultDict):
    def __init__(self, parent_rdc=None):
        super().__init__(RelevanceFilteredResultList)
        self.parent_rdc = parent_rdc


class ResultDictContainer(ValueLengthSortedResultDict):
    def __init__(self, resultdb):
        super().__init__(lambda: ResultDict(self))
        self.resultdb = resultdb
