
class FilterBankInterface:
    
    filtered_categories = []
    
    def __init__(self, thresultdb, _initial_call=True):
        if _initial_call:
            thresultdb.reset_relevances()
        filters = [getattr(self,funcname) for funcname,func in filter(lambda kv: not kv[0].startswith("__"), self.__class__.__dict__.items()) if callable(func)]
        for filterfunc in filters:
            thresultdb.filter_by_relevance(filterfunc)
        if _initial_call:
            for parentcls in self.__class__.__mro__:
                if issubclass(parentcls, FilterBankInterface):
                    parentcls(thresultdb, _initial_call=False)
        for handle in self.filtered_categories:
            thresultdb.mark_group_irrelevant(handle)


