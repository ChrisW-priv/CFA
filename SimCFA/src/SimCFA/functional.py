def apply(fn):
    def inner(args):
        return fn(*args)

    return inner


def apply_kwarg(fn):
    def inner(kwargs):
        return fn(**kwargs)

    return inner


def identity(x):
    return x


def empty(*args, **kwargs):
    pass


def pipe(*unary_functions):
    def inner(value):
        for fn in unary_functions:
            value = fn(value)
        return value

    return inner
