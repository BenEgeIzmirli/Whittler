from Whittler.classes.Result import Result
import json

class TrivyResult(Result):
    FRIENDLY_NAME = "trivy-conf"
    
    # This is a list of all attributes that this Result object is expected to (and is able to) contain. Result objects
    # are basically dicts with a bunch of additional functionality, so this is like a list of allowed values for the
    # Result dict's keys.
    ATTRIBUTES = [
        #parent types
        "Target",
        "Class",

        #subkeys for misconfigs
        "Type",
        "ID",
        "Title",
        "Description",
        "Message",
        "Namespace",
        "Query",
        "Resolution",
        "Severity",
        "PrimaryURL",
        "References",
        "Status",
        "Layer"
        "IacMetadata"
    ]

    @staticmethod
    def give_result_dict_list(fname):
        results = [] #full array of results
        parent_keys = [ 
        "Target",
        "Class"
        #removing type from parent key since misconfig type is more valuable
        #"Type"
        ]

        misconfiguration_keys = [
          "Type",
          "ID",
          "Title",
          "Description",
          "Message",
          "Namespace",
          "Query",
          "Resolution",
          "Severity",
          "PrimaryURL",
          "References",
          "Status",
          "Layer"
          "IacMetadata"
        ]

        with open(fname, "r") as f:
            output = json.loads(f.read())
            for raw_result in output["Results"]:
                #one or many vulns
                if "Misconfigurations" in raw_result:
                    #handle 1-n miscs for a target
                    for misc in raw_result["Misconfigurations"]:
                        entry = {}
                        #setup the target which may be the same for N miscs
                        for key in parent_keys:
                            entry[key] = raw_result[key]

                        for key in misconfiguration_keys:
                            #if for some reason the key isn't there, just add NA
                            entry[key] = misc.get(key, "N/A")
                        results.append(entry)
            return results