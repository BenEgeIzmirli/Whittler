from Whittler.classes.Singleton import Singleton

WHITTLER_VERSION = "1.2.0"

class Metadata(Singleton):
    
    version = WHITTLER_VERSION

    def major_versions_match(self):
        return self.version.split(".")[0] == WHITTLER_VERSION.split(".")[0]

    def minor_versions_match(self):
        return ".".join(self.version.split(".")[:2]) == ".".join(WHITTLER_VERSION.split(".")[:2])

    def revision_versions_match(self):
        return self.version == WHITTLER_VERSION

    def to_dict(self):
        # get all instance variables that aren't dunder variables like __class__
        ret = {attrname:getattr(self,attrname) for attrname in filter(lambda name: not name.startswith("__"), dir(self))}
        
        # remove all callable functions specified in this exact class definition (like exportjson())
        return dict(filter(lambda tup: not callable(getattr(type(self),tup[0],None)), ret.items()))

    def __repr__(self):
        md = self.exportjson()
        longest_metadata_varname_length = max(len(varname) for varname in md.keys())
        fmt = f"   {{:>{longest_metadata_varname_length}}} : {{}}\n"
        s = "WHITTLER METADATA:\n"
        for k,v in self.to_dict().items():
            # convert each value to bytes and remove the "b''" to escape newlines and control chars etc
            s += fmt.format(k, repr(v.encode('utf-8'))[2:-1])
        return s

    def exportjson(self):
        # convert non-string values to their string representations for storage in JSON
        return {key:f"{value}" for key,value in self.to_dict().items()}

metadata_only_instance = Metadata()

class MetadataInterface:
    metadata = metadata_only_instance