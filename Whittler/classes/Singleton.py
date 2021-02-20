
class SingletonMeta(type):
    _singleton_instances = {}
    def __call__(cls, *args, **kwargs):
        if cls not in cls._singleton_instances:
            cls._singleton_instances[cls] = super(SingletonMeta, cls).__call__(*args, **kwargs)
        return cls._singleton_instances[cls]

class Singleton(metaclass=SingletonMeta):
    # Normally this __new__ wouldn't be necessary, but it is required in order to make unpickled objects
    # subscribe to the singleton contract.
    def __new__(cls, *args, **kwargs):
        if cls not in cls._singleton_instances:
            cls._singleton_instances[cls] = super().__new__(cls, *args, **kwargs)
        return cls._singleton_instances[cls]