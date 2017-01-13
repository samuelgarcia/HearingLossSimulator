"""
.. autoclass :: InvCGC
    :members:

.. autofunction:: compute_numpy

.. autofunction:: compute_wave_file

.. autofunction:: make_cgc_filter


"""

from .version import version as __version__
from .tools import *
from .filterfactory import *
from .cgcfilter import *
from .soundgenerator import *
from .invcgc import *
from .invcomp import *
from .offlinehelper import *

try:
    from .pyacqnodes import *
except :
    pass
