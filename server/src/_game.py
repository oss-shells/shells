"""
construct game from lobby and run until completion
"""

from _api import OPS as _api_OPS, ERR as _api_ERR
C_OP  = _api_OPS.GAME.CLIENT
C_ERR = _api_ERR.GAME.CLIENT
S_OP  = _api_OPS.GAME.SERVER

from _debug import *

class _GameContext():
    def __init__(self, lobbycontext):
        self.players = lobbycontext.players
        self.epoll   = lobbycontext.epoll

    def broadcast(self, opcode, *args):
        for player in self.players:
            player.send(opcode, *args)



"""
init game
"""
def init(engine):
    iiprint("initing game")

    # clear old engine vals and assign new context object
    engine.statecheck = None
    engine.catch      = None
    engine.ops        = []
    engine.context    = _GameContext(engine.context)

    for i, fn in enumerate((

    )):
        name = S_OP[i]
        engine.register(name, fn)

        dprint(f"registered: {name}/{fn}")

    iprint("sending game state to players")
    lobby.broadcast(C_OP.START)

    iiprint("game has started")

