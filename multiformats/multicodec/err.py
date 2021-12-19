"""
    Errors for the `multiformats.multicodec` module.
"""

import builtins

class KeyError(builtins.KeyError): # pylint: disable = redefined-builtin
    """ Class `multiformats.multicodec` key errors. """
    ...

class ValueError(builtins.ValueError): # pylint: disable = redefined-builtin
    """ Class `multiformats.multicodec` value errors. """
    ...
