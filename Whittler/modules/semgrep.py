from Whittler.classes.Result import Result
# from Whittler.config import Config
import json

class SemgrepResult(Result):

    FRIENDLY_NAME = "semgrep"
    
    # This is a list of all attributes that this Result object is expected to (and is able to) contain. Result objects
    # are basically dicts with a bunch of additional functionality, so this is like a list of allowed values for the
    # Result dict's keys.
    ATTRIBUTES = [
        "check_id",
        "lines",
        "message",
        "CWE",
        "severity",
        "path",
        "line_number"
    ]

    @staticmethod
    def give_result_dict_list(fname):
        results = []
        with open(fname, "r") as f:
            output = json.loads(f.read())
        for result_raw in output["results"]:
            result = {}
            result["check_id"] = result_raw["check_id"]
            result["lines"] = result_raw["extra"]["lines"]
            result["message"] = result_raw["extra"]["message"]
            try:
                result["CWE"] = result_raw["extra"]["metadata"]["CWE"]
            except:
                result["CWE"] = ""
            result["severity"] = result_raw["extra"]["severity"]
            result["path"] = result_raw["path"]
            result["line_number"] = result_raw["start"]["line"]
            results.append(result)
        return results