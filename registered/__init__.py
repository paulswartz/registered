"""
Allows easy importing of the environment as:

from registered import environ
"""

import os
from registered.friendly_environ import FriendlyEnviron

environ = FriendlyEnviron(os.environ)
