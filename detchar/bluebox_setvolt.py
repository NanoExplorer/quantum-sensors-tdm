#! /usr/bin/env python
'''test_bluebox.py '''

from instruments import bluebox 
import sys 

vs = bluebox.BlueBox(port='vbox', version='mrk2')
v=float(sys.argv[1])
vs.setvolt(v)
vs.setvolt(v) # command repeated because after power cycle 1st command doesn't take
