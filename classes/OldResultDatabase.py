from .Result import Result
from .Relevance import RelevanceFilteredList
from collections import defaultdict
import math
import difflib
import hashlib
import random
import re
import json
import os


class ResultDatabase:
    
    def __init__(self, result_class=Result):
        self.result_class = result_class
        # key=Result object, value=boolean indicating whether it is a relevant result
        self.results = RelevanceFilteredList()
        for attr in result_class.ATTRIBUTES:
            setattr(self,f"results_by_{attr}",defaultdict(RelevanceFilteredList))
        self.grouped_attributes = []
    
    def add_result(self, result):
        assert isinstance(result,Result)
        if result in self.results:
            return
        result._frozen = True
        self.results.append(result)
        for attr in self.result_class.ATTRIBUTES:
            getattr(self,f"results_by_{attr}")[result[attr]].append(result)
    
    def group_by_attribute(self, attr):
        if attr not in self.result_class.ATTRIBUTES:
            raise Exception(f"can't group by this {attr}, must be one of {self.result_class.ATTRIBUTES}")
        if attr in self.grouped_attributes:
            return getattr(self,f"similar_{attr}")
        self.grouped_attributes.append(attr)
        setattr(self,f"similar_{attr}",defaultdict(RelevanceFilteredList))
        setattr(self,f"_similar_{attr}_handles",dict())
        setattr(self,f"_cached_sequencematchers_{attr}",dict())
        
        for result in list.__iter__(self.results):
            cache_hit = False
            similaritydict = getattr(self, f"similar_{attr}")
            # first, do an order-of-magnitude check for the length.
            attrlen_oom = math.log2(len(result[attr]))
            for potential_similar, resultlist in similaritydict.items():
                ps_len_oom = math.log2(len(potential_similar))
                if attrlen_oom < ps_len_oom-0.5 or attrlen_oom > ps_len_oom+0.5:
                    continue
                # We're dealing with a similar length attribute. Worth it to do similarity rating...
                # first, get the cached SequenceMatcher
                sm = getattr(self, f"_cached_sequencematchers_{attr}")[potential_similar]
                # Now, rate the similarity and compare with SIMILARITY_THRESHOLD
                sm.set_seq1(result[attr])
                if sm.ratio() > self.SIMILARITY_THRESHOLD:
                    resultlist.append(result)
                    cache_hit = True
                    break
            if not cache_hit:
                sm = difflib.SequenceMatcher()
                sm.set_seq2(result[attr])
                getattr(self, f"_cached_sequencematchers_{attr}")[result[attr]] = sm
                getattr(self, f"similar_{attr}")[result[attr]].append(result)
                getattr(self, f"_similar_{attr}_handles")[result[attr]] = hashlib.md5(bytes(result[attr],'utf-8')).hexdigest()[:6]
    
    def display_statistics(self, attribute=None, count_entries=False):
        print("{:6d} total results".format(len(self.results)))
        if attribute is None:
            to_print = {}
            for attr in self.result_class.ATTRIBUTES:
                to_print[attr] = len(getattr(self,f"results_by_{attr}"))
            for attr, resultlen in reversed(sorted(to_print.items(),key=lambda tup:tup[1])):
                print("      | {:6d} values for {}".format(resultlen,attr))
        else:
            if attribute not in self.result_class.ATTRIBUTES:
                raise Exception(f"The provided attribute must be one of {self.result_class.ATTRIBUTES}.")
            to_print = {}
            for attrval, resultlist in getattr(self,f"results_by_{attribute}").items():
                to_print[attrval] = len(resultlist)
            ct = 0
            for attrval, resultlen in reversed(sorted(to_print.items(),key=lambda tup:tup[1])):
                if count_entries:
                    print(" {:3d}  | {:6d} values for {}".format(ct, resultlen, attrval))
                    ct += 1
                else:
                    print("      | {:6d} values for {}".format(resultlen,attrval))
    
    def display_similar_groups(self, attribute=None):
        if attribute is None:
            attribute = self.grouped_attributes
        else:
            attribute = [attribute]
        for attr in attribute:
            print("~~~~~~~~~~~~~~~~~~~~~~~")
            print(attr)
            print("~~~~~~~~~~~~~~~~~~~~~~~")
            similaritydict = getattr(self, f"similar_{attr}")
            for simulacra, resultlist in reversed(sorted(similaritydict.items(), key=lambda tup: len(tup[1]))):
                if not len(resultlist):
                    continue
                print(f"----- {len(resultlist)} similar to: (id: {getattr(self, f'_similar_{attr}_handles')[simulacra]})")
                print(simulacra)
                print()
    
    def show_random_from_group(self, group_id, ignore_attrs=[]):
        for attr in self.result_class.ATTRIBUTES:
            for simulacra, handle in getattr(self,f"_similar_{attr}_handles").items():
                if handle == group_id:
                    results = [e for e in getattr(self,f"similar_{attr}")[simulacra]]
                    if not len(results):
                        return
                    results[random.randint(0,len(results)-1)].display(ignore_attrs=ignore_attrs)
                    return
    
    def show_random_from_similar_attribute_set(self, attr, attrval, ignore_attrs=[]):
        results = [e for e in getattr(self, f"results_by_{attr}")[attrval]]
        if not len(results):
            return
        results[random.randint(0,len(results)-1)].display(ignore_attrs=ignore_attrs)
        return
    
    def mark_group_irrelevant(self, group_id):
        for attr in self.grouped_attributes:
            for simulacra, handle in getattr(self,f"_similar_{attr}_handles").items():
                if handle == group_id:
                    getattr(self,f"similar_{attr}")[simulacra].declare_all_irrelevant()
                    return
    
    def mark_similar_attribute_set_irrelevant(self, attr, attrval):
        getattr(self, f"results_by_{attr}")[attrval].declare_all_irrelevant()
    
    # filterfunc should be a function that will take a TrufflehogResult object, and return True if the
    # result is relevant, and False if it is irrelevant.
    def filter_by_relevance(self, filterfunc):
        for result in self.results:
            result.relevant = filterfunc(result)
    
    def reset_relevances(self):
        self.results.reset_relevances()

    def parse_from_file(self,fname):
        with open(fname,"r", encoding=FILE_ENCODING) as f:
            output_raw = f.read()
            # For some reason, trufflehog just tacks together JSON objects without commas or an array to contain them,
            # e.g. {blah:blah} {blah:blah} . We want to turn that into [{blah:blah},{blah:blah}] .
            output_raw = re.sub(r"}\s*{","},{",output_raw)
            output_raw = f"[{output_raw}]"
            # ct = 0
            for result in json.loads(output_raw):
                # if not ct % 10:
                #     print(ct, end=' ')
                # ct += 1
                self.add_result(self.result_class(result))

    def parse_from_directory(self,dirname):
        for output_file in os.listdir(dirname):
            self.parse_from_file(dirname+"/"+output_file)
