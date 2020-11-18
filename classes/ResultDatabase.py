from classes.Result import RelevanceInterface, Result, ResultDictContainer, RelevanceFilteredResultList
from classes.NestedObjectPointer import NestedObjectPointer, NestedObjectPointerInterface
from config import Config
from collections import OrderedDict
import os
from pyxdameraulevenshtein import normalized_damerau_levenshtein_distance_ndarray
import numpy as np
import difflib


class ResultDatabase(RelevanceInterface):
    
    def __init__(self, result_class=Result):
        assert issubclass(result_class, Result)
        NestedObjectPointerInterface.__init__(self)
        RelevanceInterface.__init__(self)
        self.result_class = result_class
        self.results = RelevanceFilteredResultList()
        self.categorized_results = ResultDictContainer(self)
        self.grouped_results = ResultDictContainer(self)
        
        self.root_pointer = NestedObjectPointer(self)
        self.current_pointer = self.root_pointer.copy()
        self.context_pointers = OrderedDict()
    
    def __getitem__(self, nestedobjectpointer):
        assert nestedobjectpointer.base_object is self
        return nestedobjectpointer.give_pointed_object()

    def add_result(self, result):
        assert isinstance(result,self.result_class)
        if result in self.results:
            return
        result._frozen = True
        self.results.append(result)
        for attr in self.result_class.ATTRIBUTES:
            self.categorized_results[attr][result[attr]].append(result)


    #########################
    #  Navigation functions
    #

    def construct_view(self, pointer=None, limit=None):
        if pointer == None:
            pointer = self.current_pointer
        obj = pointer.give_pointed_object()
        viewstr, ptrdict = obj.show_view(pointer_to_me=pointer, limit=limit)
        return (viewstr, ptrdict)
    
    def update_current_view(self, limit=None):
        viewstr, ptrcontext = self.construct_view(self.current_pointer,limit=limit)
        self.context_pointers = ptrcontext
        return viewstr
    
    def navigate_view(self, pointer=None, limit=None):
        if pointer is None:
            self.current_pointer = self.root_pointer.copy()
        else:
            self.current_pointer = pointer.copy()
        return self.update_current_view(limit=limit)
    

    #######################
    #  Grouping functions
    #

    def group_attribute(self, attrname):
        raise NotImplementedError()
    
    @staticmethod
    def compute_distances(reference,values,exp=None):
        if exp is None:
            exp = Config.SIMILARITY_EXPONENT

        dh_distances = 1-normalized_damerau_levenshtein_distance_ndarray(reference, values)
        
        sm = difflib.SequenceMatcher()
        sm.set_seq2(reference)
        sm_distances = []
        for val in values:
            sm.set_seq1(val)
            sm_distances.append(sm.ratio())
        sm_distances = np.array(sm_distances)
        
        dh_exp = np.power(dh_distances, exp)
        sm_exp = np.power(sm_distances, exp)
        dist_sum = dh_exp+sm_exp
        return np.power(dist_sum,1/exp)
    
    def find_similar_results(self, attrname, groupval):
        all_results = [res for res in list.__iter__(self.results)]
        attrarray = np.array([res[attrname].strip() for res in all_results])
        normalized_distances = self.compute_distances(groupval, attrarray)
        return [res for res,_ in filter(lambda tup:tup[1]>Config.SIMILARITY_THRESHOLD, zip(all_results, normalized_distances))]
    
    def group_attribute_by_value(self, attrname, groupval):
        similar_results = self.find_similar_results(attrname, groupval)
        self.register_grouped_results(attrname, groupval, similar_results)

    def register_grouped_results(self, attrname, groupval, result_group):
        for result in result_group:
            self.grouped_results[groupval][result[attrname]].append(result)
        self.grouped_results.flush_pointer_cache()


    #################################
    #  Input file parsing functions
    #

    def parse_from_file(self,fname):
        for resultdict in self.result_class.give_result_dict_list(fname):
            resultdict["whittler_filename"] = fname
            self.add_result(self.result_class(resultdict))

    def parse_from_directory(self,dirname):
        for output_file in os.listdir(dirname):
            self.parse_from_file(dirname+"/"+output_file)


    #######################################
    #  RelevanceInterface implementations
    #
    
    def real_iter_values(self):
        return self.results.real_iter_values()
    

    #################################################
    #  NestedObjectPointerInterface implementations
    #
    
    def enumerate_child_pointers(self, pointer_to_me):
        ret = OrderedDict()
        
        ptr = self.root_pointer.copy()
        ptr.access_property("categorized_results")
        ret["categorized_results"] = ptr
        
        ptr = self.root_pointer.copy()
        ptr.access_property("grouped_results")
        ret["grouped_results"] = ptr
        
        self._cached_pointers = ret
        return ret
    
    def size(self):
        return self.results.size()
    
    def all_result_objects(self):
        return self.results.all_result_objects()
    
    def show_view(self, pointer_to_me=None, ct=0, limit=None):
        s = "\n"
        s += "+=================================+\n"
        s += "|  {:6d} total relevant results  |\n".format(len(self.results))
        s += "+=================================+\n"
        ret = OrderedDict()
        for childname, childptr in self.give_child_pointers(self.root_pointer).items():
            s += f"\n{childname}:\n"
            childobj = childptr.give_pointed_object()
            s2, resultdict = childobj.show_view(childptr, ct=ct, limit=limit)
            s += s2
            for k,v in resultdict.items():
                ret[k] = v
            ct += len(resultdict)
        return (s, ret)

    def export(self):
        return self.results.export()
    