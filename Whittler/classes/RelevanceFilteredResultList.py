from Whittler.classes.RelevanceInterface import RelevanceInterface
from collections import OrderedDict
import re


class RelevanceFilteredResultList(list, RelevanceInterface):
    def __init__(self, iterable=None, pointer_to_me=None):
        list.__init__(self)
        RelevanceInterface.__init__(self, pointer_to_me)
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
    
    def give_child_pointers(self):
        ret = OrderedDict()
        for i in range(self.real_length()):
            if self[i].relevant:
                ret[i] = self.pointer_to_me.copy().get_by_index(i)
        return ret
    
    def size(self):
        return len(self)
    
    def all_result_objects(self):
        yield from (result for result in self)

    _numeric_tokenize = re.compile(r'(\d+)|(\D+)').findall
    def _numeric_sortkey(self,str):
        return tuple(int(num) if num else alpha for num,alpha in self._numeric_tokenize(str))

    def show_view(self, ct=0, objectview=None):
        if objectview is None:
            objectview = self.objectview
        ret = OrderedDict()
        s = ""
        def adds(string, prefix=""):
            nonlocal s
            s += prefix + string + "\n"
        child_ptrdict = self.give_child_pointers()
        if not objectview["sort_by"] is None:
            # "reversed" actually yields the expected (i.e. non-reversed-seeming) result...
            reverse = lambda iter: reversed(iter) if objectview["sort_reverse"] else iter
            if objectview["sort_numeric"]:
                child_ptrdict = OrderedDict(reverse(sorted(child_ptrdict.items(),
                    key=lambda tup: self._numeric_sortkey(self[tup[0]][objectview["sort_by"]]))))
            else:
                child_ptrdict = OrderedDict(reverse(sorted(child_ptrdict.items(),
                    key=lambda tup: self[tup[0]][objectview["sort_by"]])))
        for key, ptr in child_ptrdict.items():
            result = self[key]
            if not objectview["show_irrelevant"] and not result.relevant:
                continue
            result_id = str(hash(result))[:9]
            if not objectview["SOLO"] is None:
                adds(result.pretty_repr())
            else:
                adds("~~~~~~~~~~~~~~~~~~~~~~~~~")
                adds(f"  Result with ID {result_id}    ")
                adds("~~~~~~~~~~~~~~~~~~~~~~~~~")
                for line in result.pretty_repr().split("\n"):
                    adds(line, prefix="| ")
                s += "\n\n"
            ret[int(result_id)] = ptr
            if not objectview["limit"] is None and len(ret) >= objectview["limit"]:
                break
        return (s, ret)
    
    def exportjson(self):
        for result in self:
            yield from result.exportjson()
    
