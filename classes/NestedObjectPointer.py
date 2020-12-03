from collections import namedtuple, OrderedDict
from config import ConfigurableInterface

Vertex = namedtuple("Vertex", ["operation","value"])

class NestedObjectPointer:
    def __init__(self, base_object):
        self.base_object = base_object
        # A list of Vertex objects that will be used to find the pointed object from the base object.
        self.path = []
        self._pointed_object = None
    
    def is_base_pointer(self):
        return not len(self.path)

    def access_property(self, propname):
        self.path.append(Vertex("__getattribute__", propname))
        self.flush_object_cache()
    
    def get_by_index(self, key):
        self.path.append(Vertex("__getitem__", key))
        self.flush_object_cache()
    
    def give_pointed_object(self):
        if not self._pointed_object is None:
            return self._pointed_object
        o = self.base_object
        for operation, value in self.path:
            o = getattr(o,operation)(value)
        self._pointed_object = o
        return o
    
    def flush_object_cache(self):
        self._pointed_object = None
    
    def go_up_level(self):
        self.flush_object_cache()
        return self.path.pop()
    
    def __repr__(self):
        return " -> ".join(["base"]+[vertex.value for vertex in self.path])
    
    def copy(self):
        ret = type(self)(self.base_object)
        ret.path = [e for e in self.path]
        ret._pointed_object = self._pointed_object
        return ret


class NestedObjectPointerInterface(ConfigurableInterface):
    def __init__(self):
        self._cached_pointers = None
    
    def flush_pointer_cache(self):
        self._cached_pointers = None
    
    def give_child_pointers(self, pointer_to_me):
        if not self._cached_pointers is None:
            return self._cached_pointers
        return self.enumerate_child_pointers(pointer_to_me)
    
    def enumerate_child_pointers(self, pointer_to_me):
        raise NotImplementedError()

    def size(self):
        raise NotImplementedError()

    def all_result_objects(self):
        raise NotImplementedError()
    
    def show_view(self, pointer_to_me=None, ct=0, limit=None, show_irrelevant=False, sort_by=None):
        raise NotImplementedError()

    def export(self):
        raise NotImplementedError()


# ParentRelationship = namedtuple("ParentRelationship",["parent","vertex"])

# class NestedObjectPointerInterface:
#     def __init__(self):
#         self._parent_pointers = {}

#     def declare_parent_relationship(self, parent, vertex):
#         parent_relationship = ParentRelationship(parent,vertex)
#         self._parent_pointers[parent_relationship] = self.give_pointers_to_self(parent_relationship)

#     def give_pointers_to_self(self, parent_relationship=None):
#         if parent_relationship is None:
#             return list(self._parent_pointers.values())
#         if parent_relationship in self._parent_pointers:
#             return self._parent_pointers[parent_relationship]
        
#         parents = [parent_relationship["parent"]]
#         if not parents:
#             return NestedObjectPointer(self)
#         pointers = parent.give_pointers_to_self()
#         pointer.path.append(self.give_parent_to_self_vertex())
#         return pointer


# class ResultDatabasePointer:
#     all_result_sets = [
#         "categorized",
#         "grouped"
#     ]
#     def __init__(self, resultdb):
#         self.resultdb = resultdb
#         self.resultset = None
#         self.pointer = []
    
#     def switch_to_resultset(self, resultset=None):
#         assert resultset is None or resultset in self.all_result_sets
#         self.resultset = resultset
    
#     def switch_to_root_context(self):
#         self.switch_to_resultset()
#         self.pointer = []
    
#     def give_pointed_object(self):
#         if self.resultset is None:
#             return self.resultdb
#         context = getattr(self.resultdb, self.resultset)
#         for ptr in self.pointer:
#             context = context[ptr]
#         return context
    
#     def switch_to_parent_context(self):
#         assert self.resultset is not None
#         if not len(self.pointer):
#             self.resultset = None
#             return
#         self.pointer.pop()
    
#     def switch_to_deeper_context(self,key_or_resultset):
#         if self.resultset is None:
#             self.switch_to_resultset(key_or_resultset)
#         else:
#             self.pointer.append(key_or_resultset)
    
#     def copy(self):
#         ret = type(self)(self.resultdb)
#         ret.resultset = self.resultset
#         ret.pointer = [e for e in self.pointer]
#         return ret
