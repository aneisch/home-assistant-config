#!/usr/bin/env python

# Provide code as arg: ./whatever.py "0000 ... ..." 

import binascii
import struct

def pronto2lirc(pronto):
    codes = [long(binascii.hexlify(pronto[i:i+2]), 16) for i in xrange(0, len(pronto), 2)]

    if codes[0]:
        raise ValueError('Pronto code should start with 0000')
    if len(codes) != 4 + 2 * (codes[2] + codes[3]):
        raise ValueError('Number of pulse widths does not match the preamble')

    frequency = 1 / (codes[1] * 0.241246)
    return [int(round(code / frequency)) for code in codes[4:]]


if __name__ == '__main__': 
    import sys

    for code in sys.argv[1:]:
        pronto = bytearray.fromhex(code)
        pulses = pronto2lirc(pronto)
        output = ""
        count = 0
        for pulse in pulses:
            if count%2 != 0:
                output += "{},".format(pulse*-1)
            else:
                output += "{},".format(pulse)
            count += 1
        print "["+output[:-1]+"]"
