"""
    Errors for the `multiformats.multihash` module.
"""

import builtins

class KeyError(builtins.KeyError): # pylint: disable = redefined-builtin
    """ Class `multiformats.multihash` key errors. """
    ...

class ValueError(builtins.ValueError): # pylint: disable = redefined-builtin
    """ Class `multiformats.multihash` value errors. """
    ...
