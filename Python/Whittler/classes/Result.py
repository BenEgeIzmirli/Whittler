from Whittler.classes.MemoryCompressor import MaybeCompressedString
from Whittler.classes.RelevanceInterface import RelevanceInterface
from collections import OrderedDict
import hashlib
import re


class Result(dict, RelevanceInterface):

    FRIENDLY_NAME = NotImplemented
    
    ATTRIBUTES = []

    _init_run = False

    def __init__(self, resultdict=None):
        self.original_resultdict = resultdict
        self._cached_hash = 0
        self._cached_hash_valid = True
        self._frozen = False
        dict.__init__(self)
        self._relevant = True
        RelevanceInterface.__init__(self)

        if "whittler_filename" not in self.ATTRIBUTES:
            self.ATTRIBUTES.insert(0,"whittler_filename")
        if not resultdict is None:
            for k,v in resultdict.items():
                self[k] = v
        self._init_run = True

    def __setitem__(self, key, value):
        valtype = type(value)
        # if valtype is list:
        #     pass
        # elif valtype is dict:
        #     pass
        if not valtype is str:
            value = repr(value)
        
        # This check is just for pickling/unpickling objects... the pickle implementation first calls __setitem__ with each of the
        # key/value pairs in this dict subclass, then sets the variable values above - this causes AttributeErrors to pop up because
        # self.ATTRIBUTES, self._frozen, etc have not been initialized yet.
        if not self._init_run:
            self.__init__()
        if key not in self.ATTRIBUTES:
            raise Exception(f"Unrecognized key {key} in this result.")
        if self._frozen:
            raise Exception("Cannot modify this result after it has been added to the database!")
        if self.Config.REMOVE_ANSI_CONTROL_CHARACTERS:
            value = self.filter_ansi(value)
        self._cached_hash_valid = False
        dict.__setitem__(self, key, MaybeCompressedString(value))
    
    def __getitem__(self, key):
        return dict.__getitem__(self,key).value
    
    # def __reduce__(self):
    #     cls = self.__class__
    #     args = ()
    #     state = self.__dict__.copy()
    #     list_iterator = None
    #     dict_iterator = iter({key:self.Config.MemoryCompressor.decompress(value) for key,value in dict(self).items()}.items())
    #     return (cls,args,state,list_iterator,dict_iterator)

    def __hash__(self):
        if self._cached_hash_valid:
            return self._cached_hash
        new_hashval = 0
        for attr in sorted(self.ATTRIBUTES):
            if attr in self:
                # TODO: faster to hash the compressed values if memory compression enabled, would that break anything?
                new_hashval = int(hashlib.md5(bytes(str(new_hashval)+attr+self[attr],'utf-8')).hexdigest(),16)
        self._cached_hash = new_hashval
        self._cached_hash_valid = True
        return new_hashval
    
    def __eq__(self, other):
        if not isinstance(other, Result):
            return False
        return hash(self) == hash(other)
    
    def items(self):
        for k in dict.keys(self):
            yield (k,self[k])
    
    @staticmethod
    def give_result_dict_list(fname):
        raise NotImplementedError()
    
    @classmethod
    def _give_result_dict_list(cls, fname):
        ret = cls.give_result_dict_list(fname)
        for resultdict in ret:
            resultdict["whittler_filename"] = fname
        ret = [cls(result) for result in ret]
        _ = [hash(r) for r in ret] # cache the hashes (speeds things up during multiprocessing)
        return ret
    
    # https://stackoverflow.com/questions/14693701/how-can-i-remove-the-ansi-escape-sequences-from-a-string-in-python
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    
    # Takes a unicode string, and filters out all 7-bit ANSI escape characters.
    def filter_ansi(self, s):
        return self.ansi_escape.sub('', s)
    
    # "Just read the f*cking string from the file already!"
    @staticmethod
    def force_read_file_to_string(fname):
        with open(fname, "rb") as f:
            b = f.read()
        b.replace(b"\x00",b"\\x00")
        b = b"".join([( bytes(bt) if (bt < 0x80 and bt != 0x00)
                        else bytes("\\x{:0>2}".format(hex(bt)[2:]),'ascii')) for bt in b])
        return b.decode("ascii")
    
    # This returns an elegant representation of the result. By default, it does not print the "diff"
    # component itself because it is usually very long and clutters up the output.
    def pretty_repr(self, objectview=None):
        if objectview is None:
            objectview = self.objectview
        s = ""
        def adds(content):
            nonlocal s
            s += str(content) + "\n"
        for k,v in self.items():
            if not objectview["SOLO"] is None:
                if k != objectview["SOLO"]:
                    continue
                adds(v)
                break
            elif not objectview["solo"] is None:
                if k != objectview["solo"]:
                    continue
            if not v.strip():
                continue
            adds(k)
            if k in objectview["quiet"] and k != objectview["solo"]:
                adds("... silenced ...")
                adds("")
                continue
            adds("\n".join("    "+line for line in v.splitlines()))
            adds("")
        return s
    
    def display(self):
        print(self.pretty_repr())
    
    def __repr__(self):
        return f"{self.__class__.__name__}({dict.__repr__(self)})"
    

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
    
    def give_child_pointers(self):
        return OrderedDict({str(hash(self)):self.pointer_to_me})
    
    def size(self):
        return 1
    
    def all_result_objects(self):
        yield self

    def show_view(self, ct=0, objectview=None):
        return (self.pretty_repr(), self.pointer_to_me)
    
    def exportjson(self):
        yield {attr:self[attr] for attr in self.ATTRIBUTES}
        # return {**data, "whittler_filename":self["whittler_filename"]}

