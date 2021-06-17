from Whittler.classes.MemoryCompressor import MemoryCompressorOnlyInstance

class Config:
    # The encoding of the files that will be parsed by Whittler.
    FILE_ENCODING = 'utf-8'

    # Some tools put ANSI control characters to color their output, which is nice in the console, but pesky
    # when we're trying to do bulk operations with them.
    REMOVE_ANSI_CONTROL_CHARACTERS = False

    # Grouping is performed by combining the similarity ratings from the Damerau-Levenshtein algorithm and the
    # Ratcliff-Obershelp algorithm using a Sum-Of-Squares method, except instead of precisely squaring/sqrting,
    # the exponent is modifiable through the SIMILARITY_EXPONENT parameter below.
    SIMILARITY_THRESHOLD = 0.5

    # When the SIMILARITY_THRESHOLD is auto-modified, it is modified using the following formula:
    # SIMILARITY_THRESHOLD += (DESIRED - SIMILARITY_THRESHOLD) / SIMILARITY_THRESHOLD_MODIFICATION_FACTOR
    # where DESIRED is either 1 or 0 based on whether we want to increase or decrease the threshold.
    SIMILARITY_THRESHOLD_MODIFICATION_FACTOR = 5

    # The results from the Damerau-Levenshtein algorithm and the Ratcliff-Obershelp algorithm are combined using
    # a sum-of-squares with this exponent. That is, similarity=(dl_similarity**exp + ro_similarity**exp)**(1/exp),
    # where both dl_similarity and ro_similarity are scaled from 0 to 1, with 1 being the most similar.
    SIMILARITY_EXPONENT = 2

    # The maximum printing width of the console, when printing tables and a few other things.
    MAX_OUTPUT_WIDTH = 100

    # Decreasing verbosity will suppress some of the output.
    VERBOSITY = 3

    # Enabling transparent in-memory compression can enable working with much larger datasets in memory, at the
    # cost of some performance.
    MEMORY_COMPRESSION = False


    ##################

    MemoryCompressor = MemoryCompressorOnlyInstance

    def __getstate__(self):
        state = self.__dict__.copy()
        if "MemoryCompressor" in state:
            del state["MemoryCompressor"]
        return state
    
    def __setstate__(self, state):
        self.__dict__.update(state)

    @classmethod
    def copy(cls, overridden_values={}):
        return type(f"_{cls.__name__}",(cls,),overridden_values)

ConfigMainInstance = Config()

class ConfigurableInterface:
    Config = ConfigMainInstance