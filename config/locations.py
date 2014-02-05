# -*- coding: utf-8 -*-
# Copyright (c) 2013 Riverbed Technology, Inc.
#
# This software is licensed under the terms and conditions of the 
# MIT License set forth at:
#   https://github.com/riverbed/flyscript-portal/blob/master/LICENSE ("License").  
# This software is distributed "AS IS" as set forth in the License.
from rvbd_portal.apps.geolocation.models import Location

#
# Location list to use for geo-mapping
#

# Update this list to match internal network, ensuring to keep all names unique
# since that is currently the method by which Location lookups are made.

# If a single group name covers multiple IP addresses and/or locations, pick one that
# provides the best match


Location(name="Seattle", address="10.99.11.0", mask="255.255.255.0", latitude=47.6097, longitude=-122.3331).save()
Location(name="LosAngeles", address="10.99.12.0", mask="255.255.255.0", latitude=34.0522, longitude=-118.2428).save()
Location(name="Phoenix", address="10.99.13.0", mask="255.255.255.0", latitude=33.43, longitude=-112.02).save()
Location(name="Columbus", address="10.99.14.0", mask="255.255.255.0", latitude=40.00, longitude=-82.88).save()
Location(name="SanFrancisco", address="10.99.15.0", mask="255.255.255.0", latitude=37.75, longitude=-122.68).save()
Location(name="Austin", address="10.99.16.0", mask="255.255.255.0", latitude=30.30, longitude=-97.70).save()
Location(name="Philadelphia", address="10.99.17.0", mask="255.255.255.0", latitude=39.88, longitude=-75.25).save()
Location(name="Hartford", address="10.99.18.0", mask="255.255.255.0", latitude=41.73, longitude=-72.65).save()
Location(name="DataCenter", address="10.100.0.0", mask="255.255.0.0", latitude=35.9139, longitude=-81.5392).save()
