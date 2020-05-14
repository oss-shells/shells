#!/usr/bin/env python3

import sys
import getopt
import traceback

import _server

DEFAULT_PORT     = 1337
DEFAULT_PLAYERS  = 4
DEFAULT_PASSWORD = None

LADDR = '0.0.0.0'

def eprint(*argv):
    print(*argv, file=sys.stderr)

usage = (
    "usage: server [options]\n"
    "\n"
    "    -h  --help :: this\n"
    f"    -p  --port PORT :: specify port to listen on (default {DEFAULT_PORT})\n"
    f"    -n  --players PLAYERS :: number of players in game (default {DEFAULT_PLAYERS})\n"
    f"    -P  --password PASSWORD :: lobby password (default {DEFAULT_PASSWORD})\n"
)

def main():
    lport    = DEFAULT_PORT
    players  = DEFAULT_PLAYERS
    password = DEFAULT_PASSWORD

    try:
        optarg, argv = getopt.getopt(sys.argv[1:], 'hp:n:P:', ("help", "port=", "players=", "password="))
    except getopt.GetoptError as e:
        eprint(f'{e}\n{usage}')
        return 1

    if len(argv):
        eprint(usage)
        return 1

    try:
        for opt, arg in optarg:
            if opt in ('-h', '--help'):
                print(usage)
                return 0

            elif opt in ('-p', '--port'):
                lport = int(arg)

            elif opt in ('-n', '--players'):
                playern = int(arg)

            elif opt in ('-P', '--password'):
                password = arg

    except Exception as e:
        eprint(e)
        return 1

    # start game server and run until completion
    try:
        _server.run(players, password, (LADDR, lport))
    except Exception as e:
        eprint(f"\n[!!!] Fatal unexpected {type(e).__name__}")
        traceback.print_exc(file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())

