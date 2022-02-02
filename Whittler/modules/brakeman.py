from Whittler.classes.Result import Result
import json


class BrakemanResult(Result):
    FRIENDLY_NAME = "brakeman"

    ATTRIBUTES = [
        "warning_type",
        "warning_code",
        "check_name",
        "message",
        "file",
        "line",
        "link",
        "code",
        "user_input",
        "confidence"
    ]

    @staticmethod
    def give_result_dict_list(fname):
        with open(fname, "r") as f:
            results = []
            output = json.loads(f.read())
            for raw_result in output["warnings"]:
                result = {}
                for key in BrakemanResult.ATTRIBUTES:
                    result[key] = raw_result[key]
                results.append(result)
        return results
