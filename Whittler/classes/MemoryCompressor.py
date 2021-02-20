import zlib
from Whittler.classes.Singleton import Singleton

# TODO: this can all be coded in cpython! That would be a kickass library to have exist!
# https://docs.python.org/3/c-api/buffer.html#bufferobjects

# based on https://stackoverflow.com/questions/479218/how-to-compress-small-strings
class MemoryCompressor(Singleton):
    def __init__(self):
        # wbits=-15 gives a raw output stream with no header or checksum, with a 2**15 byte window.
        self.compressor = zlib.compressobj(wbits=-15)
        self.decompressor = zlib.decompressobj(wbits=-15)
        self.junk_offset = 0

        self.trainee_compression_callbacks = []
        self.training_mode = True
        self.total_train_count = 1000

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


class MaybeCompressedString(bytearray):
    
    def __new__(cls, data_string):
        if type(data_string) == MaybeCompressedString:
            return data_string
        assert type(data_string) == str
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
        ret.extend(data)
        ret.compressed = compressed
        if add_callback:
            MemoryCompressorOnlyInstance.add_compression_callback(ret)
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

    def __hash__(self):
        return hash(self.value)
    
    def __eq__(self, other):
        return hash(self) == hash(other)
    
    # _initted = False
    # def __init__(self,data_string):
    #     if not self._initted:
    #         if MemoryCompressorOnlyInstance.COMPRESSION_ENABLED:
    #             if MemoryCompressorOnlyInstance.training_mode:
    #                 _value = MemoryCompressorOnlyInstance.train(data_string, self)
    #                 self._value = _value
    #                 self._compressed = type(_value) is bytes
    #             else:
    #                 self._value = MemoryCompressorOnlyInstance.compress(data_string)
    #                 self._compressed = True
    #         else:
    #             self._value = data_string
    #             self._compressed = False
    #         self._initted = True
