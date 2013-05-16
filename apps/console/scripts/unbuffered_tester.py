#!/usr/bin/env python

"""
Simple script to output data in timed chunks
"""


import os
import time

filelist = os.listdir(os.getcwd())

line = ', '.join(filelist)

print 'first line'
print line

time.sleep(1)
print 'second line'
print line

time.sleep(2)
print 'third line'
print line
