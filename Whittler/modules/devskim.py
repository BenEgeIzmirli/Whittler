from Whittler.classes.Result import Result
# from Whittler.config import Config
import json

class DevskimResult(Result):

    FRIENDLY_NAME = "devskim"
    
    # This is a list of all attributes that this Result object is expected to (and is able to) contain. Result objects
    # are basically dicts with a bunch of additional functionality, so this is like a list of allowed values for the
    # Result dict's keys.
    ATTRIBUTES = [
        "filename",
        "start_line",
        #"start_column",
        "end_line",
        #"end_column",
        "rule_id",
        "rule_name",
        "severity",
        "description",
        "match"
    ]

    @staticmethod
    def give_result_dict_list(fname):
        results = []
        with open(fname, "r") as f:
            output = json.loads(f.read())
        for result_raw in output:
            result = {}
            result["filename"] = result_raw["filename"]
            result["start_line"] = result_raw["start_line"]
            result["end_line"] = result_raw["end_line"]
            result["rule_id"] = result_raw["rule_id"]
            result["rule_name"] = result_raw["rule_name"]
            result["severity"] = result_raw["severity"]
            result["description"] = result_raw["description"]
            result["match"] = result_raw["match"]
            results.append(result)
        return results