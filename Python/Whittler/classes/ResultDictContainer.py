from Whittler.classes.RelevanceInterface import RelevanceInterface
from Whittler.classes.RelevanceFilteredResultList import RelevanceFilteredResultList
from Whittler.classes.MemoryCompressor import MaybeCompressedString
from collections import defaultdict, OrderedDict, namedtuple
import re


class SortedResultListDict(defaultdict, RelevanceInterface):

    def __init__(self, default_type, pointer_to_me=None):
        defaultdict.__init__(self, default_type)
        RelevanceInterface.__init__(self, pointer_to_me)
        self._pointer_to_me = pointer_to_me
    
    ChildView = namedtuple("ChildView",[
        "child_key_abridged",
        "child_key_length",
        "total_child_result_count",
        "relevant_child_result_count",
        "child_value",
        "child_pointer"
    ])

    _numeric_tokenize = re.compile(r'(\d+)|(\D+)').findall
    def _numeric_sortkey(self,str):
        return tuple(int(num) if num else alpha for num,alpha in self._numeric_tokenize(str))

    def sorted_childviews(self, objectview=None):
        if objectview is None:
            objectview = self.objectview
        child_repr_values = {}
        for key, value in defaultdict.items(self):
            keylen = str(len(key)) # it needs to be a string to work with _numeric_sortkey
            abridged_key = key.value[:1000] # these can be huge and we won't see all of it anyway
            child_repr_values[key] = self.ChildView(
                child_key_abridged = abridged_key ,
                child_key_length = keylen ,
                total_child_result_count = value.real_length() ,
                relevant_child_result_count = len(value) ,
                child_value = value ,
                child_pointer = self.pointer_to_me.copy().get_by_index(key)
            )
        
        # "reversed" actually yields the expected (i.e. non-reversed-seeming) result...
        reverse = lambda iter: reversed(iter) if objectview["sort_reverse"] else iter
        if objectview["sort_by"] == "total":
            return OrderedDict(reverse(sorted(child_repr_values.items(),
                            key=lambda tup: tup[1].total_child_result_count)))
        elif objectview["sort_by"] == "length":
            if objectview["sort_numeric"]:
                return OrderedDict(reverse(sorted(child_repr_values.items(),
                                key=lambda tup: self._numeric_sortkey(tup[1].child_key_length))))
            else:
                return OrderedDict(reverse(sorted(child_repr_values.items(),
                                key=lambda tup: tup[1].child_key_length)))
        elif objectview["sort_by"] == "attribute value":
            if objectview["sort_numeric"]:
                return OrderedDict(reverse(sorted(child_repr_values.items(),
                                key=lambda tup: self._numeric_sortkey(tup[1].child_key_abridged))))
            else:
                return OrderedDict(reverse(sorted(child_repr_values.items(),
                                key=lambda tup: tup[1].child_key_abridged)))
        else: # elif self._sort_by == "relevant":
            return OrderedDict(reverse(sorted(child_repr_values.items(),
                            key=lambda tup: tup[1].relevant_child_result_count)))
    
    def items(self):
        for k,v in self.sorted_childviews().items():
            yield (k,v.child_value)
        
    def keys(self):
        yield from (k for k,v in self.items())
        
    def values(self):
        yield from (v for k,v in self.items())
    
    def __setitem__(self, key, value):
        assert isinstance(value, RelevanceInterface)
        key = MaybeCompressedString(key)
        child_pointer = self.pointer_to_me.copy().get_by_index(key)
        value.pointer_to_me = child_pointer
        defaultdict.__setitem__(self,key,value)
    
    def __getitem__(self, key):
        return defaultdict.__getitem__(self, MaybeCompressedString(key))
    
    def __delitem__(self, key):
        return defaultdict.__delitem__(self, MaybeCompressedString(key))

    def __len__(self):
        return len([obj for obj in defaultdict.values(self) if obj.relevant])
    

    #######################################
    #  RelevanceInterface implementations
    #
    
    def real_iter_values(self):
        yield from (self[key] for key in defaultdict.__iter__(self))
    

    #################################################
    #  NestedObjectPointerInterface implementations
    #
    
    def give_child_pointers(self):
        return OrderedDict((k,v.child_pointer) for k,v in self.items())
    
    def size(self):
        return sum(obj.size() for obj in self.values())
    
    def all_result_objects(self):
        for resultcontainer in self.values():
            yield from resultcontainer.all_result_objects()
    
    def show_view(self, ct=0, objectview=None):
        if objectview is None:
            objectview = self.objectview
        max_width = self.Config.MAX_OUTPUT_WIDTH
        ret = OrderedDict()
        lines = []
        for key,cv in self.sorted_childviews(objectview=objectview).items():
            value = cv.child_value
            ptr = cv.child_pointer
            if not objectview["show_irrelevant"] and not len(value):
                continue
            # convert each value to bytes and remove the "b''" to escape newlines and control chars etc
            sanitized_key = repr(key.value.strip().encode('utf-8'))[2:-1]
            # Then replace each newline and tab character with three spaces, for visual ease
            sanitized_key = sanitized_key.replace("\\n","   ").replace("\\t","   ")
            line = "| {:4d} | {:5d} | {:8d} | {:8d} | {}".format(ct, cv.total_child_result_count,
                        cv.relevant_child_result_count, int(cv.child_key_length), sanitized_key)
            if len(line) > max_width-2:
                line = line[:max_width-2-7]+" [...] "
            lines.append(line)
            ret[ct] = ptr
            ct += 1
            if not objectview["limit"] is None and len(lines) >= objectview["limit"]:
                break
        headertext = "|  id  | total | relevant |  length  | attribute value  "
        max_linelen = max(len(line) for line in lines) if len(lines) else 0
        max_linelen = len(headertext) if len(headertext) > max_linelen else max_linelen
        header_footer = "+" + "="*(max_linelen-1) + "+\n"
        divider = "|{:-<6}+{:-<7}+{:-<10}+{:-<10}+".format("","","","")
        divider = divider + "-"*(max_linelen-len(divider)) + "|\n"
        header = header_footer
        header += headertext + " "*(max_linelen-len(headertext)) + "|\n"
        header += divider
        s = header
        for line in lines:
            s += line + " "*(max_linelen-len(line)) + "|\n"
        s += header_footer
        return (s, ret)
    
    def exportjson(self):
        for value in self.values():
            if value.relevant:
                yield from value.exportjson()
    

class ResultDict(SortedResultListDict):
    def __init__(self, parent_rdc=None, pointer_to_me=None):
        SortedResultListDict.__init__(self, default_type=RelevanceFilteredResultList, pointer_to_me=pointer_to_me)
        self.parent_rdc = parent_rdc


class ResultDictContainer(SortedResultListDict):
    def __init__(self, resultdb, pointer_to_me=None):
        SortedResultListDict.__init__(self, default_type=lambda: ResultDict(parent_rdc=self), pointer_to_me=pointer_to_me)
        self.resultdb = resultdb
