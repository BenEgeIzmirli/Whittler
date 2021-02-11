from Whittler.classes.Result import Result


class PlainTextResult(Result):

    FRIENDLY_NAME = "plaintext"
    
    ATTRIBUTES = [
       "line",
       "line length"
    ]

    @staticmethod
    def give_result_dict_list(fname):
        with open(fname,"r", encoding=PlainTextResult.Config.FILE_ENCODING) as f:
            return [{"line":line,"line length":len(line)} for line in f.readlines()]