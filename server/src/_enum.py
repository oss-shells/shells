"""
I don't like Python's enums. Here's a version that doesn't suck for what I'm trying to use them for.
"""

"""
map a bunch of ID/name pairs to named attrs at "runtime" (read: import) so we can nicely reference IDs by name
"""
class Enum():
    def __init__(self, *keys):
        for i, k in enumerate(keys):
            if k.startswith('_'):
                raise ValueError("Enum keys may not start with '_'")

            # lets us map a bunch of shit to attrs at runtime
            setattr(self, k, i)

        self._keys = keys

    # return the key corresponding to a specific integer value
    def __getitem__(self, i):
        return self._keys[i]

    def __len__(self):
        return len(self._keys)

