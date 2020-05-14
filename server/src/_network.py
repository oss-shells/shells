from _enum import Enum
from enum import IntEnum

from _debug import *

"""
NOT networking!!!
all things concerning the physical board, aka the in-game concept known as "the network"
"""
# dimensions of cards
WIDTH  = 6
HEIGHT = 4

# obvious
class Point():
    def __init__(self, x, y):
        self.x = x
        self.y = y

    def __repr__(self):
        return f"Point({self.x}, {self.y})"

    def __str__(self):
        return self.__repr__()

    def __eq__(self, other):
        return isinstance(other, Point) and self.x == other.x and self.y == other.y

    def __add__(self, other):
        if not isinstance(other, Point):
            raise ValueError(f"can only add Point (not \"{type(other).__name__}\") to Point")

        return Point(self.x + other.x, self.y + other.y)

# "ports" used to allow the cards to connect to eachother
# hosts use a bitmask for which ports are set
class PORT(IntEnum):
    TOP    = 1 << 0
    RIGHT  = 1 << 1
    BOTTOM = 1 << 2
    LEFT   = 1 << 3

# connectivity state of a port. DISCONNECTED if both ports are off. CONNECTED if both are on. ERROR if one is off and one is on,
# which is an illegal placement
CONN = Enum(
    'DISCONNECTED',
    'CONNECTED',
    'ERROR'
)

# index w/ rotation into transform table to receive, respectively, deltas from origin for left X, right X, top Y, bottom Y
_WALL = Enum(
    'LEFT',
    'RIGHT',
    'TOP',
    'BOTTOM'
)

_HITBOX_TRANSFORM = [
    [0,            WIDTH,   0,      -1 * HEIGHT],
    [-1 * HEIGHT,  0,       0,      -1 * WIDTH],
    [-1 * WIDTH,   0,       HEIGHT,  0],
    [0,            HEIGHT,  WIDTH,   0]
]

# index w/ rotation to receive, respectively, Point deltas from origin for top left, top right, bottom left, and bottom right corners
_CORNER = Enum(
    'TOP_LEFT',
    'TOP_RIGHT',
    'BOTTOM_LEFT',
    'BOTTOM_RIGHT'
)
_CORNER_TRANSFORM = [
    [Point(0, 0),               Point(WIDTH, 0),      Point(0, -1 * HEIGHT),          Point(WIDTH, -1 * HEIGHT)],
    [Point(-1 * HEIGHT, 0),     Point(0, 0),          Point(-1 * HEIGHT, -1 * WIDTH), Point(0, -1 * WIDTH)],
    [Point(-1 * WIDTH, HEIGHT), Point(0, HEIGHT),     Point(-1 * WIDTH, 0),           Point(0, 0)],
    [Point(0, WIDTH),           Point(HEIGHT, WIDTH), Point(0, 0),                    Point(HEIGHT, 0)]
]

# index w/ rotation to receive, respectively, Point deltas from origin for top, right, bottom, and left ports
# no 0-3 enum, since PORTs are a bitmask. instead, enumerate over PORT and use i
_PORT_TRANSFORM = [
    [Point(WIDTH // 2, 0),           Point(WIDTH, -1 * HEIGHT // 2), Point(WIDTH // 2, -1 * HEIGHT),      Point(0, -1 * HEIGHT // 2)],
    [Point(-1 * HEIGHT // 2, 0),     Point(0, -1 * WIDTH // 2),      Point(-1 * HEIGHT // 2, -1 * WIDTH), Point(-1 * HEIGHT, -1 * WIDTH // 2)],
    [Point(-1 * WIDTH // 2, HEIGHT), Point(0, HEIGHT // 2),          Point(-1 * WIDTH // 2, 0),           Point(-1 * WIDTH, HEIGHT // 2)],
    [Point(HEIGHT // 2, WIDTH),      Point(HEIGHT, WIDTH // 2),      Point(HEIGHT // 2, 0),               Point(0, WIDTH // 2)]
]

# initialize a host by calling the constructor on a HostInfo, which confs the host's name, ports, etc and other properties of the card as it appears in one's hand
class Host():
    def __init__(self, name, origin_x, origin_y, ports, rotation=0):
        # (x,y) of top left point
        self.origin = Point(origin_x, origin_y)

        # which ports this card has open, see PORT above
        self.ports = ports

        # rotation from 0 to 3, 90d clockwise increments
        self.rotation = rotation

        # other hosts this host is immediately connected to
        self.connections = []

    # return card's hitbox data as [left x, right x, top y, bottom y]
    def get_hitbox(self):
        deltas = _HITBOX_TRANSFORM[self.rotation]

        return [self.origin.x + deltas[0], self.origin.x + deltas[1], self.origin.y + deltas[2], self.origin.y + deltas[3]]

    # return card's corners as [top left, top right, bottom left, bottom right]
    def get_corners(self):
        deltas = _CORNER_TRANSFORM[self.rotation]

        return [
            self.origin + deltas[_CORNER.TOP_LEFT],
            self.origin + deltas[_CORNER.TOP_RIGHT],
            self.origin + deltas[_CORNER.BOTTOM_LEFT],
            self.origin + deltas[_CORNER.BOTTOM_RIGHT]
        ]

    # return a list of (point, state) for card's ports, where point is the space occupied and state is whether that port is on
    def get_portbox(self):
        return [
            (self.origin + _PORT_TRANSFORM[self.rotation][_i], bool(self.ports & _port)) for _i, _port in enumerate((
                PORT.TOP,
                PORT.RIGHT,
                PORT.BOTTOM,
                PORT.LEFT
            ))
        ]


    # determine connectivity status w/ target, see CONN
    def check_connectivity(self, other):
        # first, we have to check for overlap. any overlap is immediately illegal
        my_hitbox    = self.get_hitbox()
        other_hitbox = other.get_hitbox()

        # if we're in the same space, we're overlapping, doy
        if my_hitbox == other_hitbox:
            return CONN.ERROR

        if (
            my_hitbox[_WALL.LEFT]   < other_hitbox[_WALL.RIGHT]  and
            my_hitbox[_WALL.RIGHT]  > other_hitbox[_WALL.LEFT]   and
            my_hitbox[_WALL.BOTTOM] < other_hitbox[_WALL.TOP]    and
            my_hitbox[_WALL.TOP]    > other_hitbox[_WALL.BOTTOM]
        ):
            return CONN.ERROR

        # next, we have to check adjacency, as direct connectivity can only occur between adjacent cards
        # (cards sharing exactly one point are not adjacent)
        # if there's an adjacency, one port overlap must occur for the placement to be legal

        if (
            other_hitbox[_WALL.BOTTOM] <= my_hitbox[_WALL.TOP]    and
            other_hitbox[_WALL.LEFT]   <= my_hitbox[_WALL.RIGHT]  and
            other_hitbox[_WALL.TOP]    >= my_hitbox[_WALL.BOTTOM] and
            other_hitbox[_WALL.RIGHT]  >= my_hitbox[_WALL.LEFT]
        ):
            # if adjacency, check that this isn't a corner adjacency. this reqs 4 extra checks
            # maybe there's an optimization here, but I don't know it
            my_corners    = self.get_corners()
            other_corners = other.get_corners()

            if (
                other_corners[_CORNER.BOTTOM_RIGHT] == my_corners[_CORNER.TOP_LEFT]     or
                other_corners[_CORNER.BOTTOM_LEFT]  == my_corners[_CORNER.TOP_RIGHT]    or
                other_corners[_CORNER.TOP_RIGHT]    == my_corners[_CORNER.BOTTOM_LEFT]  or
                other_corners[_CORNER.TOP_LEFT]     == my_corners[_CORNER.BOTTOM_RIGHT]
            ):
                return CONN.DISCONNECTED

            # if any ports occupy the same space, they must both be ON or both be OFF, otherwise this is illegal
            # if they're both ON, connectivity is est. if no conn is est, this is an error
            my_portbox    = self.get_portbox()
            other_portbox = other.get_portbox()

            for my_point, my_state in my_portbox:
                for other_point, other_state in other_portbox:
                    if my_point == other_point:
                        if my_state:
                            return CONN.CONNECTED if other_state else CONN.ERROR

            # if adjacency but no connectivity, err
            return CONN.ERROR

        # if no adjacency and no overlap, there's no connection here and no error: move on
        return CONN.DISCONNECTED

class Network():
    def __init__(self):
        self.hosts = []

"""
unit tests
"""
if __name__ == "__main__":
    print("test 1: overlap")
    assert Host('', 0, 0, 0, rotation=0).check_connectivity(Host('', 9, 5, 0, rotation=1)) == CONN.ERROR

    print("\ntest 2: corners adjacent")
    assert Host('', 0, 0, 0, rotation=0).check_connectivity(Host('', 10, 6, 0, rotation=1)) == CONN.DISCONNECTED

    print("\ntest 3: port adjacent, both ports OFF")
    assert Host('', 0, 0, 0, rotation=0).check_connectivity(Host('', 6, 0, 0, rotation=0)) == CONN.ERROR

    print("\ntest 4: port adjacent, one port ON, one port OFF")
    assert Host('', 0, 0, PORT.RIGHT, rotation=0).check_connectivity(Host('', 6, 0, 0, rotation=0)) == CONN.ERROR

    print("\ntest 5: port adjacent, both ports ON")
    assert Host('', 0, 0, PORT.RIGHT, rotation=0).check_connectivity(Host('', 6, 0, PORT.LEFT, rotation=0)) == CONN.CONNECTED

    print("\ntest 6: side adjacent, no ports touching")
    assert Host('', 0, 0, 15, rotation=0).check_connectivity(Host('', 9, 6, 15, rotation=1)) == CONN.ERROR

    print("\nall tests successful!")

