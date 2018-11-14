# -*- coding: utf-8 -*-
#
# Copyright (C) 2008-20011, 2015 Uninett AS
#
# This file is part of Network Administration Visualized (NAV).
#
# NAV is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License version 2 as published by
# the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for
# more details.  You should have received a copy of the GNU General Public
# License along with NAV. If not, see <http://www.gnu.org/licenses/>.
#
"""
A class that tries to retrieve all sensors from Geist-branded WeatherGoose
products.

Uses the vendor-specific GEIST-V4-MIB (derived from the IT-WATCHDOGS-V4-MIB)
to detect and collect sensor-information.

"""
from nav.oids import OID
from .itw_mibv4 import ItWatchDogsMibV4


class GeistMibV4(ItWatchDogsMibV4):
    """
    A MibRetriever for retrieving information from Geist branded
    WeatherGoose products.

    Based on the GEIST-V4-MIB, which is more or less derived from the
    IT-WATCHDOGS-V4-MIB. Objects names in the derived MIB seems to be the
    same.

    """
    from nav.smidumps.geist_mibv4 import MIB as mib

    oid_name_map = {OID(attrs['oid']): name
                    for name, attrs in mib['nodes'].items()}

    lowercase_nodes = {key.lower(): key for key in mib['nodes']}
