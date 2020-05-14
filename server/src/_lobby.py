from select import EPOLLIN, EPOLLERR

from _enum import Enum

from _game import init as init_game

from _api import Messenger
from _api import OPS as _api_OPS, ERR as _api_ERR
C_OP  = _api_OPS.LOBBY.CLIENT
C_ERR = _api_ERR.LOBBY.CLIENT
S_OP  = _api_OPS.LOBBY.SERVER

from _debug import *

"""
wait for requested number of players to join and become ready, then init primary game construct
"""

# construct new lobby entity
PLAYER_STATE = Enum(
    'NOT_JOINED', # connection exists but has not joined lobby
    'JOINED', # player has joined lobby
    'ACK', # player has acked game starting
)

class _LobbyPlayer():
    def __init__(self, sock):
        self.state     = PLAYER_STATE.NOT_JOINED
        self.messenger = Messenger(sock)

        self.alias     = None # set to str on JOIN

    # wrapper over messenger send()
    def send(self, *args):
        self.messenger.send(*args)

LOBBY_STATE = Enum(
    'WAITING_JOIN', # waiting for players to join
    'WAITING_ACK', # all players have joined, waiting on clients to acknowledge
)

class _LobbyContext():
    def __init__(self, n_players, password, epoll):
        self.n_players = n_players
        self.password  = password
        self.epoll     = epoll

        self.players   = []
        self.state     = LOBBY_STATE.WAITING_JOIN

    # get players who are in particular state
    def get_p_state(self, state):
        return [_p for _p in self.players if _p.state == state]

    # get player by file descriptor of the connection they own
    def get_player_by_fd(self, fd):
        for player in self.players:
            if fd == player.messenger.sock.fileno():
                return player
        raise ValueErrorf("no player owning fd {fd} exists")

    # handle inbound connections, creating unready player if there are any open slots
    def handle_inbound(self, ep, sock):
        dprint(f"{sock.getpeername()[0]} requested connect")

        # if lobby is full, tell them to piss off
        if self.state != LOBBY_STATE.WAITING_JOIN or len(self.get_p_state(PLAYER_STATE.JOINED)) >= self.n_players:
            dprint("denied: lobby full")
            Messenger(sock).send(C_OP.ERROR, C_ERR.FULL)
            sock.close()
            return

        # if it's not full, add an un-joined player and await JOIN op
        dprint("accepted")
        self.players.append(_LobbyPlayer(sock))
        ep.register(sock.fileno(), EPOLLIN|EPOLLERR)

    # broadcast message to all players
    def broadcast(self, opcode, *args):
        for player in self.players:
            player.send(opcode, *args)

    # wrapper over internal epoll struct
    def poll(self):
        return self.epoll.poll()

# TODO catch the fker and return True if we can fix it
# we should use this to deal with malformed requests, as well as socket errors from client disconnects
def _lobby_catch(*args):
    return False

# check state of lobby and transition as appropriate
def _lobby_statecheck(engine):
    # if waiting for player to join, and all players have joined, broadcast game start and await client ACKs
    lobby = engine.context

    if lobby.state == LOBBY_STATE.WAITING_JOIN:
        joined = lobby.get_p_state(PLAYER_STATE.JOINED)

        if len(joined) >= lobby.n_players:
            iprint("all players have joined, waiting for clients to ack")

            # boot any waiting connections which haven't joined
            for p in lobby.get_p_state(PLAYER_STATE.NOT_JOINED):
                p.send(C_OP.KICK, "game is starting")
                p.messenger.sock.close()

            lobby.players = joined
            lobby.state   = LOBBY_STATE.WAITING_ACK
            lobby.broadcast(C_OP.READY)

        return

    # if waiting for ack, and all players are ack, start game and send game state
    if lobby.state == LOBBY_STATE.WAITING_ACK and len(lobby.get_p_state(PLAYER_STATE.ACK)) >= lobby.n_players:
        dprint("all clients ack")
        game_init(engine)


def init(players, password, epoll, engine):
    iiprint("initing lobby")

    # init the lobby's state
    context = _LobbyContext(players, password, epoll)

    engine.context    = context
    engine.statecheck = _lobby_statecheck
    engine.catch      = _lobby_catch

    for i, fn in enumerate((
        _op_join,
        _op_ack,
    )):
        name = S_OP[i]
        engine.register(name, fn)

        dprint(f"registered: {name}/{fn}")

    iiprint("waiting for players to join...")

# join lobby
def _op_join(lobby, player, alias, password):
    dprint(f"{player.messenger.sock.getpeername()[0]} requested join game")

    # deny if they're already in
    if player.state == 1:
        dprint(f"denied: already joined as {player.alias}")
        player.send(C_OP.ERROR, C_ERR.ALREADY_JOINED)
        return

    # check their password and desired alias for validity
    if lobby.password is not None and password != lobby.password:
        dprint("denied: invalid password")
        player.send(C_OP.ERROR, C_ERR.INVALID_PASSWORD)
        return

    if len(alias) == 0:
        dprint("denied: empty alias")
        player.send(C_OP.ERROR, C_ERR.ALIAS_EMPTY)
        return

    if alias in [_p.alias for _p in lobby.get_p_state(PLAYER_STATE.JOINED)]:
        dprint("denied: alias already in use")
        player.send(C_OP.ERROR, C_ERR.ALIAS_IN_USE)
        return

    iprint(f"{player.messenger.sock.getpeername()[0]} joined as {alias}")
    lobby.broadcast(C_OP.JOINED, f"{alias}", [_p.alias for _p in lobby.get_p_state(PLAYER_STATE.JOINED)])

    player.state = PLAYER_STATE.JOINED
    player.alias = alias

# acknowledge that game is starting and client will avoid sending more ops until game has begun
def _op_ack(lobby, player):
    if player.state != PLAYER_STATE.JOINED:
        dprint(f"denied ack from {player.messenger.sock.getpeername()[0]}: state is {PLAYER_STATE[player.state]}")
        player.send(C_OP.ERROR, C_ERR.DENY)
        return

    dprint(f"accepted ack from {player.alias}")
    player.state = PLAYER_STATE.ACK

