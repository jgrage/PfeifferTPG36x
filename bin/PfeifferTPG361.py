#!/usr/bin/env python3
# -*- coding: utf-8 -*-

""" Tango device classes for the Pfeiffer TPG361 vacuum gauge
controller series. This module uses the ethernet interface of
the new controller family. Per default the controller listens on
port 8000 for incoming tcp connections. Support for the serial
interface is not implemented yet.
"""

__author__ = "Jonas Grage"
__copyright__ = "Copyright 2020"
__license__ = "GPLv3"
__version__ = "1.0"
__maintainer__ = "Jonas Grage"
__email__ = "grage@physik.tu-berlin.de"
__status__ = "Production"

from PfeifferTPG36x import *

if __name__ == "__main__":
    PfeifferTPG361.run_server()