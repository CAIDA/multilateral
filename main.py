#!/usr/bin/python

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
# supplied “as is”, without any accompanying services from The Regents. The
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
# SOFTWARE PROVIDED HEREUNDER IS ON AN “AS IS” BASIS, AND THE UNIVERSITY OF
# CALIFORNIA HAS NO OBLIGATIONS TO PROVIDE MAINTENANCE, SUPPORT, UPDATES,
# ENHANCEMENTS, OR MODIFICATIONS.

import HttpQueryHandler
from Helper import Helper
from BgpParser import BgpParser
import lgParameters
import datetime
import time
import re
import random
import json
import sys
import getopt
import random
from pprint import pprint
"""
test
"""
from collections import Iterable


def getIptoASN(filename):
    """
    Gets the list of addresses (or prefixes) that will
    be passed as argument to the looking glass query
    """
    addresses = dict()
    with open(filename, "r") as f:
        for line in f:
            line = line.strip()
            if not line.startswith("#"):  # skip comments
                if len(line) > 0:
                    tokens = line.split(" ")
                    addresses[tokens[0]] = tokens[1]
    return addresses

def sendQuery(outputfile, asn, lg, command, queryAddress=False):
    prevq = ""
    if command == "traceroute" or command == "neighbor" or lg["http"]["prefix"] == False:
        # if IP prefix is given strip out the prefix length
	#print queryAddress
	if isinstance(queryAddress, Iterable):
        	if '/' in queryAddress:
            		queryAddress = Helper.convertPrefixToAddress(address)
    # validate the ip address
    ipIsValid = Helper.validateIPNetwork(queryAddress)
    if ipIsValid or command == "summary" or command == "regex":
        q = lg["commands"][command]
        if lg["commands"][command]["lg_query_arg"] in q:
            prevq = q[lg["commands"][command]["lg_query_arg"]]

        if lg["http"]["rarg"] != 0:
            if not isinstance(q[lg["http"]["rarg"]], basestring):
                q[lg["http"]["rarg"]] = q[lg["http"]["rarg"]][0]

        # set the command argument
        if command != "summary":
            q[lg["commands"][command]["lg_query_arg"]] = q[lg["commands"][command]["lg_query_arg"]].replace("$", queryAddress);

        # send the http request
        the_page = qh.send_http_request(q, str(lg["http"]["url"]), str(lg["http"]["referer"]), lg["http"]["type"])
        #print the_page
        
        q[lg["commands"][command]["lg_query_arg"]] = prevq
        # scrape the output
        table = qh.parse_html(the_page, lg["html"])
        if lg["html"]["striphtml"] == True:
            table = qh.strip_tags(table)
       
        filename = outputfile
        filename = filename.replace(":", "-")
        if command != "summary":
            Helper.saveToFile(filename, "#> " + str(queryAddress) + "\n", "a+", asn)
        Helper.saveToFile(filename, str(table), "a+", asn)
        filepath = Helper.saveToFile(filename, "\n-----------------------------------------------------\n\n", "a+", asn)
        time.sleep(15)
        return filepath

def usage():
    print "usage:"
    print "main.py -a <asn> -c <command> -o <outputfile> [-i <inputfile>] "
    print "\t-a: the ASN you want to query"
    print "\t-c: the looking glass command:"
    print "\t\tbgp\n\t\tsummary\n\t\tneighbor"
    print "\t-o: path to file where the command's output is logged"
    print "\t-i: path to file with the addresses to query (an address per line)\n"
    print "\t-i: path to file with the addresses to query (an address per line)\n"
    print "\t-f: path to the second file with the addresses required for the bgp and inference commands\n"

def main(argv):
    asn, inputfile, outputfile, command, inputfile2 = '', '', '', '', ''
    found_a, found_i, found_o, found_c, found_i2 = False, False, False, False, False

    try:
        opts, args = getopt.getopt(argv, "ha:c:o:i:f:", ["asn=", "command=", "outputfile=", "inputfile=", "inputfile2="])
    except getopt.GetoptError:
        usage()
        sys.exit(2)
    for opt, arg in opts:
        if opt == "-h":
            usage()
            sys.exit()
        elif opt in ("-a", "--asn"):
            asn = arg
            found_a = True
        elif opt in ("-i", "--inputfile"):
            inputfile = arg
            found_i = True
        elif opt in ("-o", "--outputfile"):
            outputfile = arg
            found_o = True
        elif opt in ("-c", "--command"):
            command = arg
            found_c = True
        elif opt in ("-f", "--inputfile2"):
            inputfile2 = arg
            found_i2 = True

    if not found_a or not found_c or not found_o:
        usage()
        sys.exit(2)
    elif not found_i:
        ''' the summary command doesn't require input addresses to query '''
        if command != "summary":
            usage()
            sys.exit(2)
    elif not found_i2 and command == "bgp":
        usage()
        sys.exit(2)

    return (asn, inputfile, outputfile, command, inputfile2)


if __name__ == '__main__':
    asn, inputfile, outputfile, command, inputfile2 = main(sys.argv[1:])
    global qh
    global lgpar
    qh = HttpQueryHandler.HttpQueryHandler()
    lgpar = lgParameters.LgParameters()
    now = datetime.datetime.now()
    #currentDate = now.strftime("%d-%m-%Y")
    parameters = lgpar.getLgProfile(asn)

    basename = '.'.join(outputfile.split(".")[:-1])
    extension = outputfile.split(".")[-1]

    if command == "summary":
        filepath = sendQuery(outputfile, asn, parameters, command)
        ip_to_asn = BgpParser.parse_summary(asn, filepath, 4, parameters["output"])
        ipfile = basename+"_addresses."+extension
        for ip in ip_to_asn:
	    #print ip_to_asn[ip]
            #Helper.saveToFile(ipfile, ip+" "+ip_to_asn[ip]+"\n", "a+", asn)
            Helper.saveToFile(ipfile, ip+" "+str(ip_to_asn[ip])+"\n", "a+", asn)
    elif command == "neighbor":
        # read the IP addresses/prefixes
        addresses = dict()
        addresses = getIptoASN(inputfile)
        counter = 1 # just for printing progress
        if len(addresses) < 1:
            print "Not enough addresses to query"
        else:
            for address in addresses:
                print str(counter) + ". " + asn + " " + ": " + address
                counter += 1
                filepath = sendQuery(outputfile, asn, parameters, command, address)
    elif command == "bgp":
        addresses = getIptoASN(inputfile2)
        neigh_file = basename+"_addresses."+extension
        prefixes = BgpParser.parseNeighInfo(inputfile, addresses, asn, neigh_file)
        for prefix in prefixes:
            filepath = sendQuery(outputfile, asn, parameters, command, prefix)
    elif command == "inference":
        addresses = getIptoASN(inputfile2)
        if parameters["output"]["type"] == "quagga":
            links = BgpParser.parse_prefix_info_quagga(inputfile, addresses, parameters["output"]["communities"][0], parameters["output"]["communities"][1])
        else:
            links = BgpParser.parse_prefix_info(inputfile, addresses, parameters["output"]["communities"][0], parameters["output"]["communities"][1])
        for link in links:
            Helper.saveToFile(outputfile, link+"\n", "a+", asn)
