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

