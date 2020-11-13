from classes.Result import Result
from config import Config
import re
import json


class TrufflehogResult(Result):

    FRIENDLY_NAME = "trufflehog"
    
    ATTRIBUTES = [
        "branch",
        "commit",
        "commitHash",
        "date",
        "diff",
        "path",
        "printDiff",
        "reason",
        "stringsFound"
    ]

    @staticmethod
    def give_result_dict_list(fname):
        with open(fname,"r", encoding=Config.FILE_ENCODING) as f:
            output_raw = f.read()
            # For some reason, trufflehog just tacks together JSON objects without commas or an array to contain them,
            # e.g. {blah:blah} {blah:blah} . We want to turn that into [{blah:blah},{blah:blah}] .
            output_raw = re.sub(r"}\s*{","},{",output_raw)
            output_raw = f"[{output_raw}]"
            return json.loads(output_raw)