# from Whittler.config import ConfigurableInterface
from Whittler.classes.Singleton import Singleton
import zlib

# TODO: this can all be coded in cpython! That would be a kickass library to have exist!
# https://docs.python.org/3/c-api/buffer.html#bufferobjects

# based on https://stackoverflow.com/questions/479218/how-to-compress-small-strings
class MemoryCompressor(Singleton):#, ConfigurableInterface):
    def __init__(self):
        # wbits=-15 gives a raw output stream with no header or checksum, with a 2**15 byte window.
        self.compressor = zlib.compressobj(wbits=-15)
        self.decompressor = zlib.decompressobj(wbits=-15)
        self.junk_offset = 0

        self.trainee_compression_callbacks = []
        self.training_mode = True
        self.total_train_count = 100000

        self.COMPRESSION_ENABLED = False

    def train(self, training_str):
        assert self.training_mode
        training_bytes = training_str.encode('utf-8')
        self.junk_offset += len(training_bytes)

        # run the training line through the compressor and decompressor
        self.junk_offset -= len(self.decompressor.decompress(self.compressor.compress(training_bytes)))

        # use Z_SYNC_FLUSH. A full flush seems to detrain the compressor, and 
        # not flushing wastes space.
        self.junk_offset -= len(self.decompressor.decompress(self.compressor.flush(zlib.Z_SYNC_FLUSH)))

        # If we have trained on at least self.total_train_count result objects, then disable training_mode.
        # The second half of the if statement is necessary because we call train() on each call to Result.__setitem__,
        # not on each creation of a Result object.
        if len(self.trainee_compression_callbacks) >= self.total_train_count:
            print("\nMEMORY COMPRESSION TRAINING DONE.")
            self.disable_training_mode()
            return self.compress(training_str.encode('utf-8'))
        
        return training_str
    
    def add_compression_callback(self, mcd):
        self.trainee_compression_callbacks.append(mcd)
    
    def disable_training_mode(self):
        self.training_mode = False
        for mcd in self.trainee_compression_callbacks:
            assert not mcd.compressed
            compressed = self.compress(mcd)
            del mcd[:]
            mcd.extend(compressed)
            mcd.compressed = True

    # Takes bytearray or bytes, returns bytes
    def compress(self,b):
        compressor = self.compressor.copy()
        ret = compressor.compress(b)+compressor.flush()
        return ret

    # Takes bytearray or bytes, returns bytes
    def decompress(self,b):
        decompressor = self.decompressor.copy()
        return (decompressor.decompress(b)+decompressor.flush())[self.junk_offset:]

MemoryCompressorOnlyInstance = MemoryCompressor()

_MCS_cache = {}

class MaybeCompressedString(bytearray):
    
    def __new__(cls, data_string):
        if type(data_string) == MaybeCompressedString:
            return data_string
        assert type(data_string) == str
        data_string_hash = hash(data_string)
        if data_string_hash in _MCS_cache:
            return _MCS_cache[data_string_hash]
        data_bytes = data_string.encode('utf-8')
        add_callback = False
        if MemoryCompressorOnlyInstance.COMPRESSION_ENABLED:
            if MemoryCompressorOnlyInstance.training_mode:
                add_callback = True
                data = MemoryCompressorOnlyInstance.train(data_string)
                if type(data) is bytes:
                    compressed = True
                else:
                    data = data_bytes
                    compressed = False
            else:
                data = MemoryCompressorOnlyInstance.compress(data_bytes)
                compressed = True
        else:
            data = data_bytes
            compressed = False
        ret = bytearray.__new__(cls)
        ret._cached_hash = data_string_hash
        ret.extend(data)
        ret.compressed = compressed
        if add_callback:
            MemoryCompressorOnlyInstance.add_compression_callback(ret)
        _MCS_cache[data_string_hash] = ret
        return ret
    
    def __init__(self, d):
        pass

    def __reduce__(self):
        cls = self.__class__
        args = (self.value,)
        return (cls,args)
    
    @property
    def value(self):
        if self.compressed:
            return MemoryCompressorOnlyInstance.decompress(self).decode('utf-8')
        return self.decode('utf-8')
    
    def __repr__(self):
        value = self.value
        valuerepr = f"{value[:97]}..." if len(self.value) > 100 else value
        return f"{self.__class__.__name__}({valuerepr})"
    
    __str__ = __repr__

    def __hash__(self):
        cached_hash = self._cached_hash
        if cached_hash:
            return cached_hash
        return hash(self.value)
    
    def __eq__(self, other):
        return hash(self) == hash(other)
    
    def __len__(self):
        return len(self.value)
    
