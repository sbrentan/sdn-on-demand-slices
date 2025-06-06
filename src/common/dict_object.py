class DictObject:
    def __init__(self, **entries):
        self.__dict__.update(entries)

    def __getattr__(self, key):
        if key in self.__dict__:
            return self.__dict__[key]
        return None
    
    def __getitem__(self, key):
        return self.__dict__.get(key, None)

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def to_dict(self):
        return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}

    @property
    def empty(self):
        return not bool([k for k in self.__dict__.keys() if not k.startswith('_')])
