from Whittler.classes.Result import Result
import chardet

def detect_encoding(fname):
    rawdata = open(fname, "rb").read()
    result = chardet.detect(rawdata)
    return result['encoding']

class AdtFuzzResult(Result):

    FRIENDLY_NAME = "adt_fuzzing"
    
    ATTRIBUTES = ["output","input","output_length","input_length"]

    @staticmethod
    def give_result_dict_list(fname):
        result = {}
        result["output"] = Result.force_read_file_to_string(fname)
        result["output_length"] = str(len(result["output"]))
        result["input"] = Result.force_read_file_to_string(fname.replace("_outputs","_unpack"))
        result["input_length"] = str(len(result["input"]))
        return [result]
