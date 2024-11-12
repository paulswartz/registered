"""
Allows easy importing of the environment as:

from registered import environ
"""

import os
from registered.friendly_environ import FriendlyEnviron

env_file_environ = {}
try:
    with open(".env", encoding="utf-8") as f:
        for line in f:
            parts = line.split("=", maxsplit=1)
            if len(parts) == 2:
                [key, value] = parts
                env_file_environ[key.strip()] = value.strip()
except FileNotFoundError:
    pass

environ = FriendlyEnviron(env_file_environ, os.environ)
