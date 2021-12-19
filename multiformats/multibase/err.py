"""
    Errors for the `multiformats.multibase` module.
"""

import builtins

class KeyError(builtins.KeyError): # pylint: disable = redefined-builtin
    """ Class `multiformats.multibase` key errors. """
    ...

class ValueError(builtins.ValueError): # pylint: disable = redefined-builtin
    """ Class `multiformats.multibase` value errors. """
    ...
