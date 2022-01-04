from Whittler.classes.Result import Result
import json

class TrivyResult(Result):
    FRIENDLY_NAME = "trivy-vulns"

    ATTRIBUTES = [
        #parent types
        "Target",
        "Class",
        "Type",

        #subkeys for vulns
        "VulnerabilityID",
        "PkgName",
        "InstalledVersion",
        "FixedVersion",
        "Layer",
        "SeveritySource",
        "PrimaryURL",
        "Title",
        "Description",
        "Severity",
        "CweIDs",
        "CVSS",
        "References",
        "PublishedDate",
        "LastModifiedDate"
    ]

    @staticmethod
    def give_result_dict_list(fname):
        results = [] #full array of results
        parent_keys = [ 
        "Target",
        "Class",
        "Type"
        ]
        vuln_keys = [
        "VulnerabilityID",
        "PkgName",
        "InstalledVersion",
        "FixedVersion",
        "Layer",
        "SeveritySource",
        "PrimaryURL",
        "Title",
        "Description",
        "Severity",
        "CweIDs",
        "CVSS",
        "References",
        "PublishedDate",
        "LastModifiedDate"
        ]

        with open(fname, "r") as f:
            output = json.loads(f.read())
            for raw_result in output["Results"]:
                #one or many vulns
                if "Vulnerabilities" in raw_result:
                    #handle 1-n vulns for a target
                    for vuln in raw_result["Vulnerabilities"]:
                        entry = {}
                        #setup the target which may be the same for N vulns
                        for key in parent_keys:
                            entry[key] = raw_result[key]

                        for key in vuln_keys:
                            #if for some reason the key isn't there, just add NA
                            entry[key] = vuln.get(key, "N/A")
                        results.append(entry)
            return results