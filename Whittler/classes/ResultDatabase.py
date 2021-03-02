from Whittler.classes.Result import Result
from Whittler.classes.RelevanceInterface import RelevanceInterface
from Whittler.classes.ResultDictContainer import ResultDictContainer
from Whittler.classes.RelevanceFilteredResultList import RelevanceFilteredResultList
from Whittler.classes.input_utils import wprint
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
    normalized_damerau_levenshtein_distance = lambda reference, value: 1.
import difflib

# import cProfile, pstats, io
# from pstats import SortKey


class ResultDatabase(RelevanceInterface):
    
    def __init__(self, result_class=Result, pointer_to_me=None):
        assert issubclass(result_class, Result)
        RelevanceInterface.__init__(self, pointer_to_me)

        self.result_class = result_class

        result_pointer = self.pointer_to_me.copy().access_property("results")
        self.results = RelevanceFilteredResultList(pointer_to_me=result_pointer)

        categorized_results_pointer = self.pointer_to_me.copy().access_property("categorized_results")
        self.categorized_results = ResultDictContainer(self, pointer_to_me=categorized_results_pointer)

        grouped_results_pointer = self.pointer_to_me.copy().access_property("grouped_results")
        self.grouped_results = ResultDictContainer(self, pointer_to_me=grouped_results_pointer)
        
        self.current_pointer = self.pointer_to_me.copy()
        self.context_pointers = OrderedDict()

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

    def construct_view(self, pointer=None, override_options={}):
        if pointer is None:
            pointer = self.current_pointer
        obj = pointer.give_pointed_object()
        if override_options:
            options = {k:v for k,v in obj.objectview.items()}
            options.update(override_options)
        else:
            options = None
        return obj.show_view(objectview=options)
    
    def update_current_view(self, override_options={}):
        viewstr, ptrcontext = self.construct_view(self.current_pointer, override_options=override_options)
        self.context_pointers = ptrcontext
        return viewstr
    
    def navigate_view(self, pointer=None, override_options={}):
        if pointer is None:
            self.current_pointer = self.pointer_to_me.copy()
        else:
            self.current_pointer = pointer.copy()
        return self.update_current_view(override_options=override_options)


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

    def parse_from_directory(self,dirname,hash_cache=None,multiprocessing_import=False):
        files = os.listdir(dirname)
        last_report = time.time()
        start = last_report
        ct = 0
        parsing_str = f"FILES PARSED: "
        longest_str_length = 0
        wprint(f"Parsing from {dirname} ...")
        try:
            if multiprocessing_import:
                import multiprocessing as mp
                p = mp.Pool()
                # # do this to support KeyboardInterrupt
                # # https://stackoverflow.com/questions/1408356/keyboard-interrupts-with-pythons-multiprocessing-pool
                # resultdictlist_generator = (resultdict for resultdict in p.map_async(
                #     self.result_class._give_result_dict_list,
                #     (dirname+"/"+fname for fname in files),
                #     chunksize=20).get(999999))
                resultdictlist_generator = p.imap_unordered(
                    self.result_class._give_result_dict_list,
                    (dirname+"/"+fname for fname in files),
                    chunksize=20)
                p.close()
            else:
                resultdictlist_generator = (self.parse_from_file(dirname+"/"+fname, hash_cache=hash_cache) for fname in files)
            for resultdictlist in resultdictlist_generator:
                cur_time = time.time()
                if cur_time-last_report > 5:
                    print_str = f"{parsing_str}{(int((ct/len(files)*100)))}% ({ct} out of {len(files)})"
                    if len(print_str)>longest_str_length:
                        longest_str_length = len(print_str)
                    wprint(print_str, end='\r')
                    last_report = cur_time
                if multiprocessing_import:
                    for result in resultdictlist:
                        self.add_result(result, lookup_set=hash_cache)
                ct += 1
        finally:
            if multiprocessing_import:
                p.terminate()
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
                    pickle.load(f)
                def result_gen():
                    with gzip.GzipFile(fname, "rb") as f:
                        while True:
                            try:
                                yield pickle.load(f)
                            except EOFError:
                                break
                results = result_gen()
                results_len = None
                pickle_import = True
            except pickle.UnpicklingError:
                try:
                    with gzip.GzipFile(fname, "rb") as f:
                        results = json.loads(f.read().decode('utf-8'))
                        results_len = len(results)
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
                if results_len:
                    progress_str = f"{(int((ct/results_len*100)))}% done ({ct} out of {results_len})"
                else:
                    progress_str = f"{ct} done"
                status_str = f"{importing_str}{progress_str}"
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
    
    def give_child_pointers(self):
        ret = OrderedDict()
        
        ptr = self.pointer_to_me.copy().access_property("categorized_results")
        ret["categorized_results"] = ptr
        
        ptr = self.pointer_to_me.copy().access_property("grouped_results")
        ret["grouped_results"] = ptr
        
        return ret
    
    def size(self):
        return self.results.size()
    
    def all_result_objects(self):
        yield from self.results.all_result_objects()
    
    def show_view(self, ct=0, objectview=None):
        if objectview is None:
            objectview = self.objectview
        s = "\n"
        s += "+=================================+\n"
        s += "|  {:6d} total relevant results  |\n".format(len(self.results))
        s += "+=================================+\n"
        ret = OrderedDict()
        for childname, childptr in self.give_child_pointers().items():
            s += f"\n{childname}:\n"
            childobj = childptr.give_pointed_object()
            s2, resultdict = childobj.show_view(ct=ct, objectview=objectview)
            s += s2
            for k,v in resultdict.items():
                ret[k] = v
            ct += len(resultdict)
        return (s, ret)

    def exportjson(self):
        yield from self.results.exportjson()
    




























