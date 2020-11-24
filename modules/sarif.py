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
        if not fname.endswith(".sarif"):
            print(f"Warning: ignoring {fname} as its filename does not end with \".sarif\".")
            return []
        with open(fname,"r", encoding=SarifResult.Config.FILE_ENCODING) as f:
            sarif_json = json.loads(f.read())
        
        # I'd prefer to have this be a set(), but it needs to stay ordered for convenience.
        all_keys = []

        run = sarif_json["runs"][0]
        
        version = sarif_json["version"]

        # Get the rules, collapsed recursively, as a list of rule dictionaries (version-dependent)
        if version == "2.1.0":
            rules = [SarifResult.collapse_recursive_json(rule) for rule in run["tool"]["driver"]["rules"]]
            
        elif version == "1.0.0":
            rules = [SarifResult.collapse_recursive_json(rule) for rule in run["rules"].values()]
        else:
            print(f"Warning: Unsupported SARIF version v{version}")
            return []
        
        # Sort rules into a dict indexed by rule ID
        rules = {rule["id"]:rule for rule in rules}
        for rule in rules.values():
            del rule["id"]
        
        # Add the union of all rule attributes into the all_keys set (prepending "rules.")
        for r in rules.values():
            for k in r.keys():
                key = f"rules.{k}"
                if key not in all_keys:
                    all_keys.append(key)
        
        # get the results, collapsed recursively, as a list of result dictionaries
        ret = [SarifResult.collapse_recursive_json(result) for result in run["results"]]

        # add the union of all result attributes into the all_keys set
        for r in ret:
            for k in r.keys():
                if k not in all_keys:
                    all_keys.append(k)
        
        # set this class' ATTRIBUTES to reflect all the keys we've collected - otherwise we'll have errors
        # when casting the returned dictionaries to SarifResult objects
        for k in all_keys:
            if k not in SarifResult.ATTRIBUTES:
                SarifResult.ATTRIBUTES.append(k)

        for r in ret:
            # get the rule corresponding to this result
            rule = rules[r["ruleId"]]
            
            # add each rule attribute to this result, prepending "rules."
            for k,v in rule.items():
                r[f"rules.{k}"] = v
            
            # If a key in ATTRIBUTES is not present, then add it as an empty string - every result dictionary
            # returned must have every attribute specified in this class' ATTRIBUTES variable
            for k in SarifResult.ATTRIBUTES:
                if k not in r:
                    r[k] = ""
        return ret


