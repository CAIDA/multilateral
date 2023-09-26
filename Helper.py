__author__ = "Vasilis Giotsas"
__email__ = "<giotsas@gmail.com>"

# This software is Copyright (C) 2015 The Regents of the University of
# California. All Rights Reserved. Permission to copy, modify, and
# distribute this software and its documentation for educational, research
# and non-profit purposes, without fee, and without a written agreement is
# hereby granted, provided that the above copyright notice, this paragraph
# and the following three paragraphs appear in all copies. Permission to
# make commercial use of this software may be obtained by contacting:
#
# Office of Innovation and Commercialization
#
# 9500 Gilman Drive, Mail Code 0910
#
# University of California
#
# La Jolla, CA 92093-0910
#
# (858) 534-5815
#
# invent@ucsd.edu
#
# This software program and documentation are copyrighted by The Regents of
# the University of California. The software program and documentation are
# supplied "as is", without any accompanying services from The Regents. The
# Regents does not warrant that the operation of the program will be
# uninterrupted or error-free. The end-user understands that the program
# was developed for research purposes and is advised not to rely
# exclusively on the program for any reason.
#
# IN NO EVENT SHALL THE UNIVERSITY OF CALIFORNIA BE LIABLE TO ANY PARTY FOR
# DIRECT, INDIRECT, SPECIAL, INCIDENTAL, OR CONSEQUENTIAL DAMAGES,
# INCLUDING LOST PR OFITS, ARISING OUT OF THE USE OF THIS SOFTWARE AND ITS
# DOCUMENTATION, EVEN IF THE UNIVERSITY OF CALIFORNIA HAS BEEN ADVISED OF
# THE POSSIBILITY OF SUCH DAMAGE. THE UNIVERSITY OF CALIFORNIA SPECIFICALLY
# DISCLAIMS ANY WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE. THE
# SOFTWARE PROVIDED HEREUNDER IS ON AN "AS IS" BASIS, AND THE UNIVERSITY OF
# CALIFORNIA HAS NO OBLIGATIONS TO PROVIDE MAINTENANCE, SUPPORT, UPDATES,
# ENHANCEMENTS, OR MODIFICATIONS.

import os
from netaddr import *


class Helper:
    """
    Collection of helper classes used throughout the program
    """

    @staticmethod
    def getIPNetwork(ipnet):
        """
        Used to check if a string represents an IP prefix or address.
        Returns the ip version if a valid prefix/address, otherwise zero.
        """
        if len(ipnet) < 7:
            return 0

        try:
            ip = IPNetwork(str(ipnet))
            return ip.version
        except AddrFormatError:
            return 0

    @staticmethod
    def validateIPNetwork(ipnet):
        """
        Checks if a string is a valid IP address or not
        """
        try:
            IPNetwork(str(ipnet))
            return True
        except AddrFormatError:
            return False

    @staticmethod
    def convertToAsn32(asn):
        """
        Converts the ASN 32-bit dot notation to integer representation
        """
        asnTokens = asn.split(".")
        upper = int(asnTokens[0])
        lower = int(asnTokens[1])
        upperShifted = upper << 16
        asn = upperShifted | lower
        return asn

    @staticmethod
    def convertPrefixToAddress(address):
        """
        Some looking glasses will only accept addresses
        as parameters, not prefixes. This functions just
        removes the prefix lenght.
        """
        if '/' in address:
            tokens = address.split("/")
            ipTokens = tokens[0].split(".")
            if ipTokens[len(ipTokens) - 1] == '0':
                ipTokens[len(ipTokens) - 1] = '1'
            return '.'.join(ipTokens)

    @staticmethod
    def saveToFile(filename, output, mode, asn):
        """
        Saves the string <output> to the file <filename>
        """
        directory = "lg-logs/" + asn + "/"
        if not os.path.exists(directory):
            os.makedirs(directory)
        filepath = directory + filename
        f = open(filepath, mode)
        f.write(output)
        f.flush()
        f.close()
        return filepath

    @staticmethod
    def isPositiveInt(s):
        """
        Checks if a string represents a positive integer
        """
        try:
            if int(s) > 0:
                return True
            else:
                return False
        except ValueError:
            return False
