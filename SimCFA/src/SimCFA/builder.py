from copy import deepcopy


class GenericBuilder:
    def __init__(self, cls, copy_strategy=deepcopy):
        self._cls = cls
        self.copy_strategy = copy_strategy
        self._params = {}

    def set(self, key, value):
        obj = self.copy_strategy(self)
        obj._params[key] = value
        return obj

    def build(self):
        return self._cls(**self._params)

    def __or__(self, other):
        obj = self.copy_strategy(self)
        obj._params.update(other._params)
        return obj
