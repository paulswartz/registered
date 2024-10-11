"""
Module loaded when running the validate tool.

See `registered.validate` for the main content.
"""

import sys
from registered.validate import PARSER, main

sys.exit(main(PARSER.parse_args()))
