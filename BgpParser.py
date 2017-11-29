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
from Helper import Helper
import re
import operator
from math import ceil
import sys


class Prefix:
    asnCount = 0  # how many ASNs advertise this prefix
    prefix = ""

    def __init__(self, prefix):
        self.prefix = prefix
        self.asnList = set()

    def addToAsnList(self, asn):
        self.asnList.add(asn)
        self.asnCount = len(self.asnList)


class BgpParser:
    """
    Methods to parse BGP output from looking glasses queries and extract BGP attributes
    """
    @staticmethod
    def samplePrefixes(asnToPrfxCount, prfxList, ixp, outfile):
        """
        This function selects a sample of the advertised prefixes to minimize the number
        of queries to the looking glasses (see section 4.3 of the paper "Inferring multilateral peering".
        """
        filename = ""
        prefixesToQuery = set()  # the list of prefixes to query
        asnQueryPrefixes = {}  # the set that holds the number of prefixes to be queried for each ASN
        # iterate prefixes sorted by the number of ASes that advertise each prefix
        for prefix in (sorted(prfxList.values(), key=operator.attrgetter('asnCount'), reverse=True)):
            query_this_prefix = False
            # print prefix.prefix +" "+str(prefix.asnCount)
            for asn in prefix.asnList:
                if asn not in asnQueryPrefixes:
                    asnQueryPrefixes[asn] = 0
                if asnQueryPrefixes[asn] < 3:
                    query_this_prefix = True
                    asnQueryPrefixes[asn] += 1
                if query_this_prefix:
                    prefixesToQuery.add(prefix.prefix)
                    filename = Helper.saveToFile(outfile, prefix.prefix+"\n", "a+", ixp)
        print "Use " + str(len(prefixesToQuery)) + " out of " + str(len(prfxList))
        return prefixesToQuery

    @staticmethod
    def parseNeighInfo(inputfile, ipToAsn, ixp, outfile):
        """
        Function to parse a BGP neighbor output file.
        It returns a subset of the advertised prefixes to be queried for BGP info
        """
        print "Parsing neighbor file", inputfile
        asnToPrfxCount = {}
        prfxList = {}

        with open(inputfile, 'rb') as f:
            for line in f:
                line = line.strip()

                # A line with: #> <ASN> will precede each part of the output that refers to a specific IP address or ASN
                # By detecting the #> characters I know that a new section starts and I retrieve the ASN for that section
                if line.startswith("#>"):
                    ipaddr = re.compile("^\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}$")
                    tokens = line.strip().split()
                    if ipaddr.match(tokens[1]):
                        asn = ipToAsn[tokens[1]]
                    else:
                        asn = tokens[1]
                    if asn not in asnToPrfxCount:
                        asnToPrfxCount[asn] = 0
                else:
                    # If the line contains an IP prefix and starts with '*' it means that I reached the BGP table and
                    # therefore I proceed to extract the prefixes for the corresponding ASN
                    prefix = re.findall(r'(?:[\d]{1,3})\.(?:[\d]{1,3})\.(?:[\d]{1,3})\.(?:[\d]{1,3}\/(?:[\d]{2}))',
                                        line)
                    if prefix is not None and len(prefix) > 0:
                        if line.startswith("*") or line.startswith(prefix[0]):
                            asnToPrfxCount[asn] += 1
                            if prefix[0] not in prfxList:
                                prfxObj = Prefix(prefix[0])
                                prfxList[prefix[0]] = prfxObj
                            prfxList[prefix[0]].addToAsnList(asn)
        return BgpParser.samplePrefixes(asnToPrfxCount, prfxList, ixp, outfile)


    @staticmethod
    def parse_summary(ixp, inputfile, ipversion, ixpParam):
        """
        Function to parse a  BGP summary output file.
        It prints the ASN->Neighbor IP mapping in a file
        """
        ipToAsn = {}
        addrPos, asnPos, ipcountPos, rtrType = [int(ixpParam["summary"]["ip"]), int(ixpParam["summary"]["asn"]),
                                                int(ixpParam["summary"]["ipCount"]), ixpParam["type"]]
        with open(inputfile, 'rb') as f:
            for line in f:
                # split the line to white spaces
                lineTokens = line.strip().split()
                if len(lineTokens) <= ipcountPos: continue
                interfaces = re.findall(
                    r'(?:\s|^|\(|\[)(?:[\d]{1,3})\.(?:[\d]{1,3})\.(?:[\d]{1,3})\.(?:[\d]{1,3})(?:\s|\)|$|\])', line)
                if len(lineTokens) > addrPos and len(interfaces) > 0:
                    # check if the string that is supposed to be in the position of the address is indeed a valid IP address
                    ip = lineTokens[addrPos]
                    ipType = Helper.getIPNetwork(ip)
                    if str(ipType) == str(ipversion) or (ipType > 0 and int(ipversion) == 10):
                        # check if the string in the position of the ASN is a valid number
                        asn = lineTokens[asnPos]
                        asn = asn.replace("AS", "")
                        if '.' in asn:
                            asn = Helper.convertToAsn32(asn)
                        if Helper.isPositiveInt(asn):
                            # check if the ASN is active and advertises prefixes
                            # often the number of advertised prefixes may be split in total received/best
                            # in this case we want the total which is the first of the two numbers
                            ipcount = lineTokens[ipcountPos]
                            try:
                                if rtrType == "bird":
                                    received = re.findall(r"[\w']+", ipcount)[0]
                                elif rtrType == "quagga":
                                    received = ipcount
                            except:
                                print ipcount
                            # if string represents a valid positive number add asn->ip mapping to the dictionary
                            if Helper.isPositiveInt(received):
                                if ip not in ipToAsn:
                                    ipToAsn[ip] = asn
        return ipToAsn

    @staticmethod
    def parse_prefix_info_quagga(inputfile, ip2asn, rs_community_allow, rs_community_block):
        """
        Function that parses the results of the `show ip bgp` command and combines them with the 
        route server community files and list of route server members to infer the multilateral 
        peering links established over the route server.
        """
        encountered_members = set()
        allowed = dict()
        blocked = dict()
        members = set(ip2asn.values())
        # initialize the allowed and blocked lists
        for member in members:
            allowed[member] = list()
            allowed[member].extend(members) # this is the default RS behaviour, which can be overriden by communities
        for member in members:
            blocked[member] = list()
        flag = 0
        next_hop = ""
        tmp_allowed = set()
        tmp_blocked = set()
        with open(inputfile, 'rb') as fin:
            for line in fin:
                line = line.strip()
                if line.endswith("RS-client)"):
                    line_tokens = line.split(",")
                    as_path = line_tokens[0].strip().split()
                    next_hop = as_path[0]
                    if next_hop in members:
                        encountered_members.add(next_hop)
                if line.startswith("Community"):
                    line_tokens = line.split(": ")
                    communities = line_tokens[1].strip().split()
                    
                    # Do two passes, one for "all or nothing" communities, and one for communities
                    # that allow or block specific ASes

                    # 1st pass
                    aon_community = False
                    for community in communities:
                        first_16 = community.split(":")[0]
                        last_16 = community.split(":")[1]
                        # check for no-export or no-advertise communities according to rfc1997
                        block_all = (first_16 == rs_community_allow or first_16 == "65535") and (last_16 == "65281" or last_16 == "65282")
                        if first_16 == rs_community_block and last_16 == rs_community_allow or block_all:
                            tmp_blocked |= members
                            tmp_allowed = set()
                            aon_community = True
                        elif first_16 == rs_community_allow and last_16 == rs_community_allow:
                            tmp_allowed |= members
                            tmp_blocked = set()
                            aon_community = True

                    # if no "all or nothing" (aon) community was present assume the default route server behaviour
                    # which is to advertise the received prefixes to every route server member
                    if aon_community is False:
                        tmp_allowed |= members
                        tmp_blocked = set()

                    # 2nd pass
                    for community in communities:
                        first_16 = community.split(":")[0]
                        last_16 = community.split(":")[1]
                        if first_16 == rs_community_block and last_16 != rs_community_allow:
                            if last_16 in members:
                                tmp_blocked.add(last_16)
                                if last_16 in tmp_allowed:
                                    tmp_allowed.remove(last_16)
                        elif first_16 == rs_community_allow and last_16 != rs_community_allow:
                            if last_16 in members:
                                tmp_allowed.add(last_16)
                                if last_16 in tmp_blocked: tmp_blocked.remove(last_16)
                    if len(tmp_blocked) > 0:
                        for asn in tmp_blocked:
                            if next_hop in allowed and asn in allowed[next_hop]:
                                allowed[next_hop].remove(asn)
                        for asn in tmp_allowed:
                            if next_hop in allowed:
                                allowed[next_hop].append(asn)
                if line.startswith("#>"): #reset
                    next_hop = ""
                    tmp_allowed = set()
                    tmp_blocked = set()
        links = set()
        as_to_link = dict()
        for m1 in encountered_members:
            for m2 in allowed[m1]:
                if m1 in allowed[m2] and m1 != m2:
                    link = m1 + " " + m2
                    if int(m1) > int(m2):
                        link = m2 + " " + m1
                    links.add(link)
                    if m1 not in as_to_link:
                        as_to_link[m1] = set()
                    if m2 not in as_to_link:
                        as_to_link[m2] = set()    
                    as_to_link[m1].add(m2)
                    as_to_link[m2].add(m1)
        print len(encountered_members)
        for asn in as_to_link:
            print asn," ",len(as_to_link[asn])
        return links

    @staticmethod
    def parse_prefix_info(inputfile, ip2asn, rs_communities):
        """
        Function that parses the results of the `show ip bgp` command and combines them with the
        route server community files and list of route server members to infer the multilateral
        peering links established over the route server.
        """
        encountered_members = set()
        allowed = dict()
        blocked = dict()
        members = set(ip2asn.values())
        # initialize the allowed and blocked lists
        for member in members:
            allowed[member] = list()
            allowed[member].extend(members) # this is the default RS behaviour, which can be overriden by communities
        for member in members:
            blocked[member] = list()
        flag = 0
        next_hop = ""
        tmp_allowed = set()
        tmp_blocked = set()
        with open(inputfile, 'rb') as fin:
            for line in fin:
                line = line.strip()
                if line.startswith("BGP.as_path"):
                    line_tokens = line.split(":")
                    as_path = line_tokens[1].strip().split()
                    next_hop = as_path[0]
                    if next_hop in members:
                        encountered_members.add(next_hop)
                if line.startswith("BGP.community"):
                    line_tokens = line.split(":")
                    communities = line_tokens[1].strip().split()

                    # Do two passes, one for "all or nothing" communities, and one for communities
                    # that allow or block specific ASes

                    # 1st pass
                    aon_community = False
                    for c in communities:
                        community = c[1:-1] # remove the parentheses
                        first_16 = community.split(",")[0]
                        last_16 = community.split(",")[1]
                        # check for no-export or no-advertise communities according to rfc1997
                        block_all = (first_16 == rs_community_allow or first_16 == "65535") and (last_16 == "65281" or last_16 == "65282")
                        if community in rs_communities["block_all"] or block_all:
                            tmp_blocked |= members
                            tmp_allowed = set()
                            aon_community = True
                        elif community in rs_communities["allow_all"]:
                            tmp_allowed |= members
                            tmp_blocked = set()
                            aon_community = True

                    # if no "all or nothing" (aon) community was present assume the default route server behaviour
                    # which is to advertise the received prefixes to every route server member
                    if aon_community is False:
                        tmp_allowed |= members
                        tmp_blocked = set()

                    # 2nd pass
                    for c in communities:
                        community = c[1:-1] # remove the parentheses
                        first_16 = community.split(",")[0]
                        last_16 = community.split(",")[1]
                        if first_16 == rs_community_block and last_16 != rs_community_allow:
                            if last_16 in members:
                                tmp_blocked.add(last_16)
                                if last_16 in tmp_allowed:
                                    tmp_allowed.remove(last_16)
                        elif first_16 == rs_community_allow and last_16 != rs_community_allow:
                            if last_16 in members:
                                tmp_allowed.add(last_16)
                                if last_16 in tmp_blocked: tmp_blocked.remove(last_16)
                    if len(tmp_blocked) > 0:
                        for asn in tmp_blocked:
                            if next_hop in allowed and asn in allowed[next_hop]:
                                allowed[next_hop].remove(asn)
                        for asn in tmp_allowed:
                            if next_hop in allowed:
                                allowed[next_hop].append(asn)
                if line.startswith("#>"): #reset
                    next_hop = ""
                    tmp_allowed = set()
                    tmp_blocked = set()
        links = set()
        as_to_link = dict()
        for m1 in encountered_members:
            for m2 in allowed[m1]:
                if m1 in allowed[m2] and m1 != m2:
                    link = m1 + " " + m2
                    if int(m1) > int(m2):
                        link = m2 + " " + m1
                    links.add(link)
                    if m1 not in as_to_link:
                        as_to_link[m1] = set()
                    if m2 not in as_to_link:
                        as_to_link[m2] = set()
                    as_to_link[m1].add(m2)
                    as_to_link[m2].add(m1)
        print len(encountered_members)
        for asn in as_to_link:
            print asn," ",len(as_to_link[asn])
        return links
