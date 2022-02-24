from Whittler.classes.Result import Result
import json

class GosecResult(Result):
    FRIENDLY_NAME = "gosec"
    
    ATTRIBUTES = [
        "severity",
        "confidence",
        "cwe",
        "rule_id",
        "details",
        "file",
        "code", 
        "line"
    ]

    @staticmethod
    def give_result_dict_list(fname):
        results = []
        with open(fname, "r") as f:
            output = json.loads(f.read())
        for result_raw in output["Issues"]:
            result = {}
            result["severity"] = result_raw["severity"]
            result["confidence"] = result_raw["confidence"]
            result["cwe"] = result_raw["cwe"]
            result["rule_id"] = result_raw["rule_id"]
            result["details"] = result_raw["details"]
            result["file"] = result_raw["file"]
            result["code"] = result_raw["code"]
            result["line"] = result_raw["line"]
            results.append(result)
        return results