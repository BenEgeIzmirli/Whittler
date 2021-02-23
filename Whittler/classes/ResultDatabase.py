from Whittler.classes.Result import RelevanceInterface, Result, ResultDictContainer, RelevanceFilteredResultList
from Whittler.classes.NestedObjectPointer import NestedObjectPointer, NestedObjectPointerInterface
from Whittler.classes.input_utils import wprint, winput
from Whittler.config import Config
from collections import OrderedDict
import time
import os
import json
import numpy as np
import pickle
import gzip

try:
    from pyxdameraulevenshtein import normalized_damerau_levenshtein_distance
except ImportError:
    print("Warning: pyxDamerauLevenshtein module not detected, fuzzy grouping logic will be impaired.")
    print("         To install it, run 'pip install pyxDamerauLevenshtein'.")
    normalized_damerau_levenshtein_distance = lambda reference, value: 1
import difflib

# import cProfile, pstats, io
# from pstats import SortKey


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
        self._construct_view_cache = None
        self._construct_view_cache_pointer = None
        self._construct_view_cache_params = None

        # self.pr = cProfile.Profile()
    
    def __getitem__(self, nestedobjectpointer):
        assert nestedobjectpointer.base_object is self
        return nestedobjectpointer.give_pointed_object()

    def add_result(self, result, lookup_set=None):
        assert isinstance(result,self.result_class)
        if lookup_set is None:
            pass
        else:
            result_hash = hash(result)
            if result_hash in lookup_set:
                return
            lookup_set.add(result_hash)
        result._frozen = True
        self.results.append(result)
        for attr in self.result_class.ATTRIBUTES:
            attrval = dict.__getitem__(result, attr) # gets the underlying CompressedBytes object if memory compression enabled
            self.categorized_results[attr][attrval].append(result)


    #########################
    #  Navigation functions
    #

    def construct_view(self, pointer=None, limit=None, show_irrelevant=False, sort_by=None, sort_numeric=False, sort_reverse=False):
        if pointer is None:
            pointer = self.current_pointer
        if self._construct_view_cache_pointer is not None and self._construct_view_cache_pointer == pointer:
            if self._construct_view_cache_params is not None and (limit,show_irrelevant,sort_by,sort_numeric,sort_reverse)==self._construct_view_cache_params:
                return self._construct_view_cache
        obj = pointer.give_pointed_object()
        viewstr, ptrdict = obj.show_view(pointer_to_me=pointer, limit=limit, show_irrelevant=show_irrelevant, sort_by=sort_by, sort_numeric=sort_numeric, sort_reverse=sort_reverse)
        self._construct_view_cache_pointer = pointer.copy()
        self._construct_view_cache = (viewstr, ptrdict)
        self._construct_view_cache_params = (limit,show_irrelevant,sort_by,sort_numeric,sort_reverse)
        return self._construct_view_cache
    
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
    
    @staticmethod
    def compute_distances(reference,values,exp=None):
        if exp is None:
            exp = Config.SIMILARITY_EXPONENT
        
        sm = difflib.SequenceMatcher()
        sm.set_seq2(reference)
        sm_distances = []
        dl_distances = []
        for val in values:
            sm.set_seq1(val)
            sm_distances.append(sm.ratio())
            dl_distances.append(1-normalized_damerau_levenshtein_distance(reference, val))
        sm_distances = np.array(sm_distances)
        dl_distances = np.array(dl_distances)
        dl_exp = np.power(dl_distances, exp)
        sm_exp = np.power(sm_distances, exp)
        dist_sum = dl_exp+sm_exp
        return np.power(dist_sum,1/exp)
    
    def find_similar_results(self, attrname, groupval):
        if not groupval.strip():
            all_results = (res[attrname].strip() for res in list.__iter__(self.results) if hasattr(res,attrname) and res[attrname].strip())
        else:
            all_results = (res[attrname].strip() for res in list.__iter__(self.results))
        return list(zip(self.results,self.compute_distances(groupval, all_results)))
    
    def register_grouped_results(self, attrname, groupval, result_group):
        for result in result_group:
            attrval = dict.__getitem__(result, attrname) # gets the underlying CompressedBytes object if memory compression enabled
            self.grouped_results[groupval][attrval].append(result)
        self.grouped_results.flush_pointer_cache()


    #################################
    #  Input file parsing functions
    #

    def parse_from_file(self,fname,hash_cache=None):
        result_dict_list = self.result_class.give_result_dict_list(fname)
        last_report = time.time()
        start = last_report
        ct = 0
        parsing_str = f"PARSING {fname} : "
        longest_str_length = 0
        for resultdict in result_dict_list:
            cur_time = time.time()
            if cur_time-last_report > 5:
                print_str = f"{parsing_str}{(int((ct/len(result_dict_list)*100)))}% done ({ct} out of {len(result_dict_list)})"
                if len(print_str)>longest_str_length:
                    longest_str_length = len(print_str)
                wprint(print_str, end='\r')
                last_report = cur_time
            resultdict["whittler_filename"] = fname
            self.add_result(self.result_class(resultdict), lookup_set=hash_cache)
            ct += 1
        if longest_str_length:
            timing = "{:.2f}".format(time.time()-start)
            final_report = f"{parsing_str}Done (took {timing}s)"
            wprint(final_report + " "*(len(final_report)-max(Config.MAX_OUTPUT_WIDTH,longest_str_length)))

    def parse_from_directory(self,dirname,hash_cache=None):
        files = os.listdir(dirname)
        last_report = time.time()
        start = last_report
        ct = 0
        parsing_str = f"FILES PARSED: "
        longest_str_length = 0
        wprint(f"Parsing from {dirname} ...")
        for output_file in files:
            cur_time = time.time()
            if cur_time-last_report > 5:
                print_str = f"{parsing_str}{(int((ct/len(files)*100)))}% ({ct} out of {len(files)})"
                if len(print_str)>longest_str_length:
                    longest_str_length = len(print_str)
                wprint(print_str, end='\r')
                last_report = cur_time
            try:
                self.parse_from_file(dirname+"/"+output_file, hash_cache=hash_cache)
            except PermissionError as e:
                wprint(f"WARNING: failed to open {dirname+'/'+output_file}: {e}")
            ct += 1
        timing = "{:.2f}".format(time.time()-start)
        final_report = f"Parsing from {dirname} done (took {timing}s)"
        wprint(final_report + " "*(len(final_report)-max(Config.MAX_OUTPUT_WIDTH,longest_str_length)))
    
    def parse_from_export(self,fname,hash_cache=None):
        importing_str = f"IMPORTING {os.path.basename(fname)} ... "
        last_report = time.time()
        start = last_report
        wprint(f"{importing_str}", end='\r')
        pickle_import = False
        # self.pr.enable()
        try:
            try:
                with gzip.GzipFile(fname, "rb") as f:
                    results = pickle.load(f)
                pickle_import = True
            except pickle.UnpicklingError:
                try:
                    with gzip.GzipFile(fname, "rb") as f:
                        results = json.loads(f.read().decode('utf-8'))
                except json.decoder.JSONDecodeError:
                    raise Exception("Failed to import file as either binary (pickle) or JSON data.")
        except:
            raise
        # self.pr.disable()
        # If we're importing from JSON, we need to make sure that the data keys are compatible with the specified module
        if not pickle_import:
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
            if pickle_import:
                self.add_result(result, lookup_set=hash_cache)
            else:
                self.add_result(self.result_class(result), lookup_set=hash_cache)
            ct += 1
        # s = io.StringIO()
        # sortby = SortKey.CUMULATIVE
        # ps = pstats.Stats(self.pr, stream=s).sort_stats(sortby)
        # ps.print_stats()
        # print(s.getvalue())
        tot_time = "{:.2f}".format(time.time()-start)
        done_str = f"{importing_str}Done (took {tot_time}s)"
        wprint(done_str+" "*max(biggest_status_str_len,Config.MAX_OUTPUT_WIDTH-len(done_str)))


    #######################################
    #  RelevanceInterface implementations
    #
    
    def real_iter_values(self):
        yield from self.results.real_iter_values()
    

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

    def exportjson(self):
        yield from self.results.exportjson()
    




























