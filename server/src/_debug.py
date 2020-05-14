"""
various debug shits
"""
from sys import stderr
from inspect import stack, getmodule

DEBUG = True

def _caller_info():
    frame = stack()[2]
    caller_name = frame.function
    module_name = frame.filename.rsplit('/', 1)[1][1:-3]

    return f"[{module_name}.{caller_name}]"

def dprint(*args):
    if DEBUG:
        print(f"[$]{_caller_info()}", *args)

def eprint(*args):
    print(f"[!]{_caller_info()}", *args, file=stderr)

def iprint(*args):
    print(f"[*]{_caller_info()}", *args)

def iiprint(*args):
    print(f"\n[***]{_caller_info()}", *args)

