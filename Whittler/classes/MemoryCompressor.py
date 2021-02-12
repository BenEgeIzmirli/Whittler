import zlib

# based on https://stackoverflow.com/questions/479218/how-to-compress-small-strings

class CompressedBytes(bytes):
    pass

class SingletonMeta(type):
    _instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            cls._instances[cls] = super(SingletonMeta, cls).__call__(*args, **kwargs)
        return cls._instances[cls]

class MemoryCompressor(metaclass=SingletonMeta):
    def __init__(self):
        # wbits=-15 gives a raw output stream with no header or checksum, with a 2**15 byte window.
        self.compressor = zlib.compressobj(wbits=-15)
        self.decompressor = zlib.decompressobj(wbits=-15)
        self.junk_offset = 0

        self.trainee_compression_callbacks = set()
        self.training_mode = True
        self.total_train_count = 1000

    def train(self, training_str, training_resultobj):
        self.trainee_compression_callbacks.add(training_resultobj)

        training_bytes = training_str.encode('utf-8')
        self.junk_offset += len(training_bytes)

        # run the training line through the compressor and decompressor
        self.junk_offset -= len(self.decompressor.decompress(self.compressor.compress(training_bytes)))

        # use Z_SYNC_FLUSH. A full flush seems to detrain the compressor, and 
        # not flushing wastes space.
        self.junk_offset -= len(self.decompressor.decompress(self.compressor.flush(zlib.Z_SYNC_FLUSH)))

        if len(self.trainee_compression_callbacks) >= self.total_train_count and training_resultobj not in self.trainee_compression_callbacks:
            self.disable_training_mode()

        return training_str
    
    def disable_training_mode(self):
        self.training_mode = False
        for resultobj in self.trainee_compression_callbacks:
            frozenstate = resultobj._frozen
            resultobj._frozen = False
            # This will get the raw string value from each attribute, then invoke the memory compression through __setitem__
            for attr in resultobj.ATTRIBUTES:
                if attr in resultobj:
                    rawval = dict.__getitem__(resultobj, attr)
                    if type(rawval) != CompressedBytes:
                        resultobj[attr] = rawval
            resultobj._frozen = frozenstate

    # Takes str, returns CompressedBytes
    def compress(self,s):
        compressor = self.compressor.copy()
        return CompressedBytes(compressor.compress(s.encode('utf-8'))+compressor.flush())

    # Takes CompressedBytes, returns str
    def decompress(self,b):
        decompressor = self.decompressor.copy()
        return (decompressor.decompress(b)+decompressor.flush())[self.junk_offset:].decode('utf-8')