import socket
import msgpack
import struct

from socket import MSG_PEEK

from _enum import Enum

"""
serverside abstr over app layer for sending/recving game events
"""

"""
nestable pseudo-dictionarish thing which uses attrs instead of keys,
sorta similar to how our custom _enum.Enum works only not with ints

used here to sort opcodes/errors by context and client/server
"""
class _OpEnum():
    def __init__(self, **items):
        for key, item in items.items():
            if key.startswith('_'):
                raise ValueError("_OpEnum keys may not start with '_'")

            setattr(self, key, item)
"""
def and name ALL the ops and error codes our entire API uses
"""
OPS = _OpEnum(
    LOBBY=_OpEnum(
        CLIENT=Enum(
            'ERROR',
            'KICK',
            'JOINED',
            'READY',
        ),

        SERVER=Enum(
            'JOIN',
            'ACK',
        )
    ),

    GAME=_OpEnum(
        CLIENT=Enum(
            'START',
        ),

        SERVER=Enum(

        )
    )
)

ERR = _OpEnum(
    LOBBY=_OpEnum(
        CLIENT=Enum(
            'DENY',
            'FULL',
            'ALREADY_JOINED',
            'INVALID_PASSWORD',
            'ALIAS_EMPTY',
            'ALIAS_IN_USE',
        )
    ),

    GAME=_OpEnum(
        CLIENT=Enum(

        )
    )
)

"""
socket wrapper to read and write packed "messages" in the format (opcode, *op_args)
use nearly identically to socket obj
"""
class Messenger():
    def __init__(self, sock):
        self.sock = sock
        self._expected = 0
        self._buffered = []

    def fileno(self):
        return self.sock.fileno()

    def send(self, opcode, *args):
        payload = msgpack.packb((opcode,) + args)

        # prepend length header and ship
        self.sock.send(struct.pack('!I', len(payload)) + payload)

    # receive any waiting data and return complete message if any, None otherwise
    def recv(self):
        if self._expected == 0:
            # peek for length header. if present, consume it and set expected payload size
            if len(self.sock.recv(4, MSG_PEEK)) == 4:
                self._expected = struct.unpack("!I", self.sock.recv(4))[0]
        else:
            # receive up to expected waiting data and decrement expected by amount received.
            # if expected is decremented to zero in this way, flush the internal buffer and return the unpacked message
            data = self.sock.recv(self._expected)
            self._expected -= len(data)
            self._buffered.append(data)

            if self._expected == 0:
                message = msgpack.unpackb(b''.join(self._buffered), raw=False)
                self._buffered = []

                return message

        return None

