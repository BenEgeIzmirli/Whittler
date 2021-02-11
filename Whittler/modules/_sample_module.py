from Whittler.classes.Result import Result
# from Whittler.config import Config

class SampleResult(Result):

    # # This is totally optional, but you can override configuration settings as follows. See config.py for
    # # more information on the configuration settings.
    # Config = Config.copy({"FILE_ENCODING":"utf-8"})

    # This specifies the name that the user can specify when initializing Whittler, e.g. python Whittler.py --config samplemod
    FRIENDLY_NAME = "samplemod"
    
    # This is a list of all attributes that this Result object is expected to (and is able to) contain. Result objects
    # are basically dicts with a bunch of additional functionality, so this is like a list of allowed values for the
    # Result dict's keys.
    ATTRIBUTES = [
        "full name",
        "address",
        "phone number"
    ]

    # This method (which must be declared as a staticmethod as below) is expected to take a filename, and return a list
    # of dicts, each of which will be casted to an object of this class' type (in this case, SampleResult). These dicts
    # MUST have a string as both a key and as a value - I hope to allow recursively nested structures in the future, but
    # for now only string key/value pairs are supported. An example of a valid return value would be:
    # [
    #     {
    #         "full name" : "Chuntley Bortler",
    #         "address" : "1 Failure Ave, Falterton WY 01324",
    #         "phone number": "666-420-6969"
    #     },
    #     {
    #         "full name" : "Flubbles Troughslogger",
    #         "address" : "42 Nihilism St, Derridaville KS 80085",
    #         "phone number": "555-867-5309"
    #     }
    # ]
    @staticmethod
    def give_result_dict_list(fname):
        with open(fname, "r") as f:
            # Do whatever you need to do here to convert the content of the file in fname to the expected format.
            # This import should be at the top, but I didn't want to complicate the imports in the example module.
            import json
            output = json.loads(f.read())
            return output["people"]