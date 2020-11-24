from classes.Result import Result
from config import Config
import json
import requests
# try:
#     import jsonschema
# except ImportError:
#     print("The jsonschema module is required to perform sarif parsing. Try running 'python -m pip install jsonschema'")
#     raise


class SarifResult(Result):

    Config = Config.copy({"FILE_ENCODING":"utf-8"})

    FRIENDLY_NAME = "sarif"
    
    ATTRIBUTES = []

    @staticmethod
    def collapse_recursive_json(js:dict,prefix=[]):
        ret = {}
        if not isinstance(js, dict):
            ret[".".join(prefix)] = str(js)
            return ret
        for k,v in js.items():
            if isinstance(v,list):
                prefix.append(k)
                for e in v:
                    ret = {**ret,**SarifResult.collapse_recursive_json(e)}
                prefix.pop()
            elif isinstance(v,dict):
                prefix.append(k)
                ret = {**ret,**SarifResult.collapse_recursive_json(v)}
                prefix.pop()
            else:
                ret[".".join([*prefix,k])] = v
        return ret

    @staticmethod
    def give_result_dict_list(fname):
        with open(fname,"r", encoding=SarifResult.Config.FILE_ENCODING) as f:
            sarif_json = json.loads(f.read())
        
        if sarif_json["version"] != "2.1.0":
            print(f"Warning: only SARIF v2.1.0 is currently supported, found v{sarif_json['version']} in {fname}")
            return []
        
        run = sarif_json["runs"][0]

        all_keys = set()

        # Get the rules, collapsed recursively, as a list of rule dictionaries
        rules = [SarifResult.collapse_recursive_json(rule) for rule in run["tool"]["driver"]["rules"]]

        # Sort rules into a dict indexed by rule ID
        rules = {rule["id"]:rule for rule in rules}
        for rule in rules.values():
            del rule["id"]
        
        # Add the union of all rule attributes into the all_keys set (prepending "rules.")
        for r in rules.values():
            for k in r.keys():
                all_keys.add(f"rules.{k}")
        
        # get the results, collapsed recursively, as a list of result dictionaries
        ret = [SarifResult.collapse_recursive_json(result) for result in run["results"]]

        # add the union of all result attributes into the all_keys set
        for r in ret:
            for k in r.keys():
                all_keys.add(k)
        
        # set this class' ATTRIBUTES to reflect all the keys we've collected - otherwise we'll have errors
        # when casting the returned dictionaries to SarifResult objects
        SarifResult.ATTRIBUTES = list(all_keys)

        for r in ret:
            # get the rule corresponding to this result
            rule = rules[r["ruleId"]]
            
            # add each rule attribute to this result, prepending "rules."
            for k,v in rule.items():
                r[f"rules.{k}"] = v
            
            # If a key in all_keys is not present, then add it as an empty string - every result dictionary
            # returned must have every attribute specified in this class' ATTRIBUTES variable
            for k in all_keys:
                if k not in r:
                    r[k] = ""
        return ret


