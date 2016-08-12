'''
Decomposition
-------------

The core of sector decomposition. This module implements
the actual decomposition routines.

Common
~~~~~~

This module collects routines that are used by
multiple decompition modules.

.. autoclass:: pySecDec.decomposition.Sector
.. autofunction:: pySecDec.decomposition.hide
.. autofunction:: pySecDec.decomposition.unhide
.. autofunction:: pySecDec.decomposition.squash_symmetry_redundant_sectors

Iterative
~~~~~~~~~

.. automodule:: pySecDec.decomposition.iterative
    :members:

Geometric
~~~~~~~~~

.. automodule:: pySecDec.decomposition.geometric
    :members:

'''

from . import iterative, geometric
from .common import *
