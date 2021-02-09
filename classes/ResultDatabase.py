from classes.Result import RelevanceInterface, Result, ResultDictContainer, RelevanceFilteredResultList, ValueLengthSortedResultDict
from classes.NestedObjectPointer import NestedObjectPointer, NestedObjectPointerInterface
from classes.input_utils import wprint
from config import Config
from collections import OrderedDict
import time
import os
import json
import numpy as np
import pickle

try:
    from pyxdameraulevenshtein import normalized_damerau_levenshtein_distance_ndarray
except ImportError:
    print("Warning: pyxDamerauLevenshtein module not detected, fuzzy grouping logic will be impaired.")
    print("         To install it, run 'pip install pyxDamerauLevenshtein'.")
    normalized_damerau_levenshtein_distance_ndarray = lambda reference, values: np.array([1 for v in values])
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

    def construct_view(self, pointer=None, limit=None, show_irrelevant=False, sort_by=None, sort_numeric=False, sort_reverse=False):
        if pointer == None:
            pointer = self.current_pointer
        obj = pointer.give_pointed_object()
        viewstr, ptrdict = obj.show_view(pointer_to_me=pointer, limit=limit, show_irrelevant=show_irrelevant, sort_by=sort_by, sort_numeric=sort_numeric, sort_reverse=sort_reverse)
        return (viewstr, ptrdict)
    
    def update_current_view(self, limit=None, sort_by=None, sort_numeric=False, sort_reverse=False):
        viewstr, ptrcontext = self.construct_view(self.current_pointer, limit=limit, sort_by=sort_by, sort_numeric=sort_numeric, sort_reverse=sort_reverse)
        self.context_pointers = ptrcontext
        return viewstr
    
    def navigate_view(self, pointer=None, limit=None, sort_by=None, sort_numeric=False, sort_reverse=False):
        if pointer is None:
            self.current_pointer = self.root_pointer.copy()
        else:
            self.current_pointer = pointer.copy()
        return self.update_current_view(limit=limit, sort_by=sort_by, sort_numeric=sort_numeric, sort_reverse=sort_reverse)
    

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
    
    def find_similar_results(self, attrname, groupval, similarity_threshold=None):
        if similarity_threshold is None:
            similarity_threshold = self.Config.SIMILARITY_THRESHOLD
        if not groupval.strip():
            all_results = [res for res in list.__iter__(self.results) if hasattr(res,attrname) and res[attrname].strip()]
        else:
            all_results = [res for res in list.__iter__(self.results)]
        attrarray = np.array([res[attrname].strip() for res in all_results])
        normalized_distances = self.compute_distances(groupval, attrarray)
        return [res for res,_ in filter(lambda tup:tup[1]>similarity_threshold, zip(all_results, normalized_distances))]
    
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
        result_dict_list = self.result_class.give_result_dict_list(fname)
        last_report = time.time()
        ct = 0
        for resultdict in result_dict_list:
            cur_time = time.time()
            if cur_time-last_report > 5:
                wprint(f"PARSING {fname} : {(int((ct/len(result_dict_list)*100)))}% done ({ct} out of {len(result_dict_list)})")
                last_report = cur_time
            resultdict["whittler_filename"] = fname
            self.add_result(self.result_class(resultdict))
            ct += 1

    def parse_from_directory(self,dirname):
        files = os.listdir(dirname)
        last_report = time.time()
        ct = 0
        wprint(f"Parsing from {dirname} ...")
        for output_file in files:
            cur_time = time.time()
            if cur_time-last_report > 5:
                wprint(f"FILES PARSED: {(int((ct/len(files)*100)))}% ({ct} out of {len(files)})")
                last_report = cur_time
            try:
                self.parse_from_file(dirname+"/"+output_file)
            except PermissionError as e:
                wprint(f"WARNING: failed to open {dirname+'/'+output_file}: {e}")
            ct += 1
    
    def parse_from_export(self,fname):
        importing_str = f"IMPORTING {os.path.basename(fname)} ... "
        wprint(f"{importing_str}", end='\r')
        try:
            try:
                with open(fname, "rb") as f:
                    results = pickle.load(f)
            except pickle.UnpicklingError:
                try:
                    with open(fname, "r") as f:
                        results = json.loads(f.read())
                except json.decoder.JSONDecodeError:
                    raise Exception("Failed to import file as either binary (pickle) or JSON data.")
        except:
            raise
        first_result_keys = set(results[0].keys())
        for result in results:
            if first_result_keys ^ set(result.keys()): # check symmetric difference, basically ensure that they're equal
                raise Exception(f"invalid Whittler export file {fname} ... all results dicts in the JSON must have the same "+\
                                f"set of keys, but the keys in the result:\n{result}\ndid not match the expected keys:\n"+\
                                f"{first_result_keys}")
        if not isinstance(self.result_class.ATTRIBUTES, list):
            self.result_class.ATTRIBUTES = []
        attrs = self.result_class.ATTRIBUTES
        for key in results[0].keys(): # don't use first_result_keys because the json is ordered whereas sets are not
            if key not in attrs:
                attrs.append(key)
        last_report = time.time()
        ct = 0
        biggest_status_str_len = 0
        for result in results:
            cur_time = time.time()
            if cur_time-last_report > 5:
                status_str = f"{importing_str}{(int((ct/len(results)*100)))}% done ({ct} out of {len(results)})"
                if len(status_str) > biggest_status_str_len:
                    biggest_status_str_len = len(status_str)
                wprint(status_str, end='\r')
                last_report = cur_time
            self.add_result(self.result_class(result))
            ct += 1
        wprint(f"{importing_str}Done."+" "*max(biggest_status_str_len,Config.MAX_OUTPUT_WIDTH-len(importing_str)-5))


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
    
    def show_view(self, pointer_to_me=None, ct=0, limit=None, show_irrelevant=False, sort_by=None, sort_numeric=False, sort_reverse=False):
        s = "\n"
        s += "+=================================+\n"
        s += "|  {:6d} total relevant results  |\n".format(len(self.results))
        s += "+=================================+\n"
        ret = OrderedDict()
        for childname, childptr in self.give_child_pointers(self.root_pointer).items():
            s += f"\n{childname}:\n"
            childobj = childptr.give_pointed_object()
            s2, resultdict = childobj.show_view(childptr, ct=ct, limit=limit, show_irrelevant=show_irrelevant, sort_by=sort_by, sort_numeric=sort_numeric, sort_reverse=sort_reverse)
            s += s2
            for k,v in resultdict.items():
                ret[k] = v
            ct += len(resultdict)
        return (s, ret)

    def export(self):
        return self.results.export()
    