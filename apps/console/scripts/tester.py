#!/usr/bin/env python -u

"""
Simple script to output data in timed chunks
"""


import os
import sys
import time

filelist = os.listdir('/Users/mgarabedian/flyscript/dashboard/apps/console/scripts')

line = ', '.join(filelist)

print 'first line'
print line

time.sleep(1)
print 'second line'
print line

time.sleep(2)
print 'third line'
print line
