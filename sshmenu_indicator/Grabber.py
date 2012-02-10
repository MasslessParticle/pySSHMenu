'''
Created on Feb 10, 2012

@author: travis
'''
import os
import subprocess
import re

class GeoGrabber():
    
    @staticmethod
    def can_grab():
        return len(filter(lambda x: os.path.exists(x + '/xwininfo'), 
                          os.environ['PATH'].split(':'))) > 0
    
    @staticmethod
    def grab():
        if GeoGrabber.can_grab():
            proc = subprocess.Popen('xwininfo', stdout=subprocess.PIPE)
            output = proc.stdout.read()
            geometry = re.search('-geometry\s+([\d+x-]+)', output)
            if geometry:
                return geometry.group(1)
            else:
                return ''
        