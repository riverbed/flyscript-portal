#!/usr/bin/env python -u

import os
import sys
import subprocess



def execute():
    #path = '/Users/mgarabedian/flyscript/dashboard/apps/console/scripts/tester.py'
    path = '/Users/mgarabedian/flyscript/dashboard/apps/console/scripts/alerter.py'
    p = subprocess.Popen([path, '--help'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    line = p.stdout.readline()
    while line:
        print line
        line = p.stdout.readline()
    
    #for line in iter(p.stdout.readline, ''):
    #    yield line
    #    #p.stdout.flush()
    p.stdout.close()
    #for line in p.stderr.readline():
    #    yield line
    #    p.stderr.flush()
    #p.stderr.close()

execute()
#print '\n'.join([x for x in execute()])
