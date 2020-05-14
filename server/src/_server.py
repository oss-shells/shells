import socket
import sys

from select import epoll, EPOLLIN, EPOLLERR

import _lobby
from _debug import *

"""
process events recvd from clients and new connections
"""

"""
translate events from clients into serverside calls

reg opcodes to calls. then, when an opcode is recvd, look up the internal call and give it the
current context (arbitrary obj repring current state) and the other shit it needs
"""

# function wrapper which lets us pull a str describing its name for debug purposes
class _Operation():
    def __init__(self, name, handle):
        self.name   = name
        self._handle = handle

    def __call__(self, *args):
        return (self._handle)(*args)

class Engine():
    def __init__(self, lsock):
        self.context    = None
        self.statecheck = None
        self.catch      = None # bind a function here to deal with unexpected process() excepts. ret True if you fixed it.

        self.ops   = []
        self.queued = []

        self._lsock = lsock

    # bind opcode and ret the ID used to proc that operation
    def register(self, name, handle):
        self.ops.append(_Operation(name, handle))
        return len(self.ops) - 1

    # queue call to handle for op. supply op-agnostic info (anything that ALL ops receive) as
    # *global_args and op-specific as op_args
    #
    # handles will be called in FIFO at next call to process()
    def queue(self, opcode, op_args, *global_args):
        self.queued.append((opcode, op_args, global_args))

    # flush queue, calling handles for all queued operations
    def process(self):
        for opcode, op_args, global_args in self.queued:
            # if handle fails for some reason, try to recover by passing the exception off to the
            # registered handler, if one exists
            try:
                (self.ops[opcode])(self.context, *global_args, *op_args)

            except Exception as e:
                if self.catch is not None:
                    eprint(f"received {type(e).__name__}, passing to handler {self.catch}")

                    # re-raise exception if catch failed to successfully deal with it
                    try:
                        if not (self.catch)(e, self.context, *global_args, *op_args):
                            eprint("failed to fix it, FATAL time")
                            raise e

                    except Exception as e:
                        eprint(f"exception catch handler raised new {type(e).__name__}")
                        raise e

                else:
                    eprint(f"received {type(e).__name__}. no catch configured, FATAL time")
                    raise e

        self.queued = []

    # if state-based checks exist, run them
    # supply self so that state-based checks can edit context and ops
    def state_check(self):
        if self.statecheck is not None:
            (self.statecheck)(self)

    # wrapper over context poll()
    def poll(self):
        return self.context.poll()

    # wrapper over context handle_inbound()
    def handle_inbound(self, *args):
        (self.context.handle_inbound(*args))

def run(players, password, sockaddr):
    iiprint(f"starting server on {sockaddr}")

    # init engine. have lobby init its context, register its ops, etc
    lsock = socket.create_server(sockaddr, reuse_port=True)

    ep = epoll()
    ep.register(lsock.fileno(), EPOLLIN|EPOLLERR)

    engine = Engine(lsock)
    _lobby.init(players, password, ep, engine)

    while True:
        # deal with all waiting IO
        for fd, event in engine.poll():
            if   event == EPOLLIN:
                # handle inbound connections
                if fd == lsock.fileno():
                    engine.handle_inbound(ep, lsock.accept()[0])
                    continue

                # handle inbound messages
                player = engine.context.get_player_by_fd(fd)

                if None is not (message := player.messenger.recv()):
                    dprint(f"[{player.messenger.sock.getpeername()[0]}] {message[0]} {'INVALID' if message[0] >= len(engine.ops) else engine.ops[message[0]].name}: {message[1:]}")

                    engine.queue(message[0], message[1:], player)

            elif event == EPOLLERR:
                pass # TODO

        # then, process all waiting operations
        engine.process()

        # finally, run state-based checks
        engine.state_check()

