from Whittler.classes.Result import Result
import csv

class PSSAResult(Result):

    FRIENDLY_NAME = "pssa_csv"
    
    ATTRIBUTES = []

    @staticmethod
    def give_result_dict_list(fname):
        ret = []
        with open(fname, newline='') as csvfile:
            filecache = {}
            for row in csv.DictReader(csvfile):
                if not PSSAResult.ATTRIBUTES:
                    for key in row.keys():
                        PSSAResult.ATTRIBUTES.append(key)
                    PSSAResult.ATTRIBUTES.append("FullLine")
                    PSSAResult.ATTRIBUTES.append("FullLineContext")
                if "ScriptPath" in row and "Line" in row:
                    try:
                        path = row["ScriptPath"]
                        if path not in filecache:
                            with open(row["ScriptPath"],"r") as f:
                                filecache[path] = f.read()
                        fcontent = filecache[path]
                        flines = fcontent.splitlines()
                        lineno = int(row["Line"])-1
                        row["FullLine"] = flines[lineno].strip()
                        row["FullLineContext"] = "\n".join(flines[lineno-5: lineno+5])
                    except Exception as e:
                        if isinstance(e, IndexError):
                            print(f"WARNING: line number {lineno} too high for file with {len(flines)} lines: {path}")
                        row["FullLine"] = ""
                        row["FullLineContext"] = ""
                else:
                    row["FullLine"] = ""
                    row["FullLineContext"] = ""
                        
                ret.append(row)
        return ret