class Config:
    def __init__(self, **kwargs):
        self._data = {}
        for k, v in kwargs.items():
            self._data[k.lower()] = v

    def __getattr__(self, name):
        return self._data.get(name.lower(), None)

    def __setattr__(self, name, value):
        if name == "_data":
            super().__setattr__(name, value)
        else:
            self._data[name.lower()] = value

    def __getitem__(self, key):
        return self._data.get(key.lower(), None)

    def __setitem__(self, key, value):
        self._data[key.lower()] = value

    def __contains__(self, key):
        return key.lower() in self._data
