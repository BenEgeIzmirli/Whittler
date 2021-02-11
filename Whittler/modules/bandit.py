from Whittler.classes.Result import Result
from Whittler.config import Config
import json

class BanditResult(Result):

    Config = Config.copy({"FILE_ENCODING":"utf-8"})

    FRIENDLY_NAME = "bandit"
    
    ATTRIBUTES = [
      "code",
      "filename",
      "issue_confidence",
      "issue_severity",
      "issue_text",
      "line_number",
      "line_range",
      "more_info",
      "test_id",
      "test_name",
    ]

    @staticmethod
    def give_result_dict_list(fname):
        with open(fname,"r", encoding=BanditResult.Config.FILE_ENCODING) as f:
            output = json.loads(f.read())
            return output["results"]