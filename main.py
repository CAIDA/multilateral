#!/usr/bin/env python

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

import sys
import time
import ujson
import getopt
import logging
import datetime
from shutil import copyfile
from collections.abc import Iterable
import lgParameters
import HttpQueryHandler
from Helper import Helper
from BgpParser import BgpParser


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
                    tokens = line.split()
                    addresses[tokens[0]] = tokens[1]
    return addresses


def getRegexASNs(filename):
    """
    Gets the list of ASNs that will be passed
    as argument to the regex looking glass query
    """
    as_numbers = set()
    with open(filename, "r") as f:
        for line in f:
            if not line.startswith("#"):
                lf = line.strip().split()
                if len(lf) > 1:
                    as_numbers.add(lf[1])
    return as_numbers


def set_query_arguments(lg, query_address, command, asn):
    """
    Sets the arguments of the LG query based on the
    command, the LG type and the ASN.
    :param lg: The LG parameters
    :type lg: dict
    :param query_address: The target of the LG command
    :type query_address: string
    :param command: The LG command
    :type command: string
    :param asn: The LG ASN
    :type asn: string
    :return: The appropriate method to issue the HTTP query,
    the initial value of the query argument to reset it, and the
    LG url to which the query will be sent.
    :rtype: tuple
    """
    prevq = ""
    if lg["output"]["type"] != "alice":
        q_arg = lg["commands"][command]["lg_query_arg"]

        q = lg["commands"][command]
        if q_arg in q:
            prevq = q[q_arg]

        if type(lg["http"]["rarg"]) == dict:
            lg["http"]["rarg"] = lg["http"]["rarg"][command]
        if lg["http"]["rarg"] != 0:
            if not isinstance(q[lg["http"]["rarg"]], str):
                q[lg["http"]["rarg"]] = q[lg["http"]["rarg"]][0]

        # set the command argument
        if not command.startswith("summary"):
            q[q_arg] = q[q_arg].replace("$", query_address)

    # send the http request
    if asn != "59900":
        http_func = "send_http_request"
    else:
        http_func = "http_request_alt"

    query_url = lg["http"]["url"]
    # set the appropriate API endpoint if lg type is 'alice'
    if lg["output"]["type"] == "alice":
        endpoints = {
            "summary": "neighbours",
            "neighbor": "neighbours/" + str(query_address) + "/routes"
        }
        query_url = lg["http"]["url"] + endpoints[command]
    return (http_func, prevq, query_url)


def scrap_html_output(lg, lg_output, asn):
    """
    Extracts the command output from the LG response
    :param lg: The LG parameters
    :type lg: dict
    :param lg_output: The body of the LG HTTP response
    :param asn: The LG ASN
    :type asn: string
    :return: The command output of the LG response
    :rtype: string
    """
    if type(lg["html"]) == list:
        for html_rule in lg["html"]:
            if "commands" in html_rule:
                if command in html_rule["commands"]:
                    lg["html"] = html_rule
                    break
            else:
                raise IOError("Malformed JSON format of IXP configuration file")
    command_outout = qh.parse_html(lg_output, lg["html"], asn)
    if lg["html"]["striphtml"] is True:
        command_outout = qh.strip_tags(command_outout)
    if type(command_outout) == dict:
        command_outout = ujson.dumps(command_outout)
    return command_outout


def send_query(outputfile, asn, lg, command, query_address=False):
    if command == "traceroute" or command.startswith("neighbor") or lg["http"]["prefix"] is False:
        # if IP prefix is given strip out the prefix length
        if isinstance(query_address, Iterable):
            if '/' in query_address:
                query_address = Helper.convertPrefixToAddress(address)

    # validate the ip address
    ipIsValid = Helper.validateIPNetwork(query_address)
    if ipIsValid or command.startswith("summary") or command == "regex" or (command == "neighbor" and lg["output"]["type"] == "alice"):
        http_func, prevq, query_url = set_query_arguments(lg, query_address, command, asn)
        q = lg["commands"][command]
        query_method = getattr(qh, http_func)
        lg_response = query_method(q, str(query_url), str(lg["http"]["referer"]), lg["http"]["type"])
        
        print(type(lg_response), lg_response)

        # print the_page
        q = lg["commands"][command]
        if lg["commands"][command]["lg_query_arg"] and len(lg["commands"][command]["lg_query_arg"]) > 0:
            q[lg["commands"][command]["lg_query_arg"]] = prevq

        # scrap the output
        command_output = scrap_html_output(lg, lg_response, asn)
        # write to file
        filename = outputfile
        filename = filename.replace(":", "-")
        if not command.startswith("summary"):
            Helper.saveToFile(filename, "#> " + str(query_address) + "\n", "a+", asn)
        Helper.saveToFile(filename, str(command_output), "a+", asn)
        filepath = Helper.saveToFile(filename, "\n-----------------------------------------------------\n\n", "a+", asn)
        time.sleep(15)
        return filepath


def usage():
    print("usage:")
    print("main.py -a <asn> -c <command> -o <outputfile> [-i <inputfile>] ")
    print("\t-a: the ASN you want to query")
    print("\t-c: the looking glass command:")
    print("\t\tbgp\n\t\tsummary\n\t\tneighbor")
    print("\t-o: path to file where the command's output is logged")
    print("\t-i: path to file with the addresses to query (an address per line)\n")
    print("\t-f: path to the second file with the addresses required for the bgp and inference commands\n")


def main(argv):
    asn, inputfile, outputfile, command, inputfile2 = '', '', '', '', ''
    found_a, found_i, found_o, found_c, found_i2 = False, False, False, False, False

    try:
        opts, args = getopt.getopt(argv, "ha:c:o:i:f:", [
                                   "asn=", "command=", "outputfile=", "inputfile=", "inputfile2="])
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
        if not command.startswith("summary"):
            usage()
            sys.exit(2)
    elif not found_i2 and command.startswith("bgp"):
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
    # currentDate = now.strftime("%d-%m-%Y")
    parameters = lgpar.getLgProfile(asn)

    basename = '.'.join(outputfile.split(".")[:-1])
    extension = outputfile.split(".")[-1]
    ip_version = 4
    if command.endswith("_v6"):
        ip_version = 6
    bgp_parser = BgpParser()
    if command.startswith("summary"):
        filepath = send_query(outputfile, asn, parameters, command)
        ip_to_asn = BgpParser.parse_summary(filepath, ip_version, parameters["output"])
        ipfile = basename + "_addresses." + extension
        for ip in ip_to_asn:
            # print ip_to_asn[ip]
            # Helper.saveToFile(ipfile, ip+" "+ip_to_asn[ip]+"\n", "a+", asn)
            Helper.saveToFile(ipfile, ip + " " + str(ip_to_asn[ip]) + "\n", "a+", asn)
    elif command.startswith("neighbor"):
        # read the IP addresses/prefixes
        addresses = getIptoASN(inputfile)
        counter = 1  # just for printing progress
        if len(addresses) < 1:
            logging.warning("No addresses to query")
        else:
            # start_parsing = True
            for address in addresses:
                print(str(counter) + ". " + asn + " " + ": " + address)
                counter += 1
                filepath = send_query(outputfile, asn, parameters, command, address)
    elif command == "regex":
        as_numbers = getRegexASNs(inputfile)
        counter = 1  # just for printing progress
        if len(as_numbers) < 1:
            logging.warning("No ASNs to query")
        else:
            for member_asn in as_numbers:
                print(str(counter) + ". " + asn + " " + ": " + member_asn)
                counter += 1
                filepath = send_query(outputfile, asn, parameters, command, member_asn)

    elif command.startswith("bgp"):
        addresses = getIptoASN(inputfile2)
        neigh_file = basename + "_addresses." + extension
        if ip_version == 6:
            neigh_file = basename + "_addresses-v6." + extension
        if parameters["output"]["type"] == "alice":
            copyfile(inputfile, "lg-logs/" + asn + "/" + outputfile)
        else:
            prefixes = BgpParser.parse_neigh_info(inputfile, addresses, asn, neigh_file)
            for prefix in prefixes:
                filepath = send_query(outputfile, asn, parameters, command, prefix)
    elif command == "inference":
        addresses = getIptoASN(inputfile2)
        func_name = "parse_prefix_info_%s" % parameters["output"]["type"]
        links = getattr(bgp_parser, func_name)(inputfile, addresses, parameters["output"]["communities"])
        for link in links:
            Helper.saveToFile(outputfile, link + "\n", "a+", asn)
