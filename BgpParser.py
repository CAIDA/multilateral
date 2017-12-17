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

import re
import ujson
import logging
import operator
from Helper import Helper


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

    def __init__(self):

        # for each AS maps which of the other ASes colocated in the same
        # Route Server are allowed to receive its prefix advertisments
        self.allowed = {}
        # stores if an AS has set the block_all policy for a prefix
        # this is necessary for BGP records in which the communities attribute
        # spans multiple lines
        self.block_all = set()

    @staticmethod
    def samplePrefixes(asnToPrfxCount, prfxList, ixp, outfile):
        """
        This function selects a sample of the advertised prefixes to minimize the number
        of queries to the looking glasses (see section 4.3 of the paper "Inferring multilateral peering".
        """
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
                    Helper.saveToFile(outfile, prefix.prefix + "\n", "a+", ixp)
        print "Use " + str(len(prefixesToQuery)) + " out of " + str(len(prfxList))
        return prefixesToQuery

    @staticmethod
    def parse_neigh_info(inputfile, ipToAsn, ixp, outfile):
        """
        Function to parse a BGP neighbor output file.
        It returns a subset of the advertised prefixes to be queried for BGP info.

        :param inputfile: the path to the file that contains the output of the BGP neighbor command
        :type inputfile: string
        :param ipToAsn: the mapping between ASNs and next-hop IP addresses
        :type ipToAsn: dict
        :param ixp: the ASN of the IXP Route Server
        :type ixp: string
        :param outfile: the path to the output file
        :type outfile: string
        :return: a set of IP addresses to query using the `show ip bgp` command
        :rtype: set
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
                    prefix_v4 = re.findall(r'(?:[\d]{1,3})\.(?:[\d]{1,3})\.(?:[\d]{1,3})\.(?:[\d]{1,3}\/(?:[\d]{2}))',
                                           line)
                    prefix_v6 = re.search(r'((([0-9A-Fa-f]{1,4}:){7}([0-9A-Fa-f]{1,4}|:))|(([0-9A-Fa-f]{1,4}:){6}(:[0-9A-Fa-f]{1,4}|((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3})|:))|(([0-9A-Fa-f]{1,4}:){5}(((:[0-9A-Fa-f]{1,4}){1,2})|:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3})|:))|(([0-9A-Fa-f]{1,4}:){4}(((:[0-9A-Fa-f]{1,4}){1,3})|((:[0-9A-Fa-f]{1,4})?:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(([0-9A-Fa-f]{1,4}:){3}(((:[0-9A-Fa-f]{1,4}){1,4})|((:[0-9A-Fa-f]{1,4}){0,2}:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(([0-9A-Fa-f]{1,4}:){2}(((:[0-9A-Fa-f]{1,4}){1,5})|((:[0-9A-Fa-f]{1,4}){0,3}:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(([0-9A-Fa-f]{1,4}:){1}(((:[0-9A-Fa-f]{1,4}){1,6})|((:[0-9A-Fa-f]{1,4}){0,4}:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(:(((:[0-9A-Fa-f]{1,4}){1,7})|((:[0-9A-Fa-f]{1,4}){0,5}:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:)))(%.+)?', line)
                    if prefix_v6 is not None:
                        prefix_v6 = [prefix_v6.group()]
                    else:
                        prefix_v6 = []
                    prefix = prefix_v4 + prefix_v6
                    if prefix is not None and len(prefix) > 0:
                        if line.startswith("*") or line.startswith(prefix[0]):
                            asnToPrfxCount[asn] += 1
                            if prefix[0] not in prfxList:
                                prfxObj = Prefix(prefix[0])
                                prfxList[prefix[0]] = prfxObj
                            prfxList[prefix[0]].addToAsnList(asn)
        return BgpParser.samplePrefixes(asnToPrfxCount, prfxList, ixp, outfile)

    @staticmethod
    def parse_summary_alice(input_file):
        """
        Parses the summary command JSON output of the Alice LG.

        :param input_file: The path to the file with the BGP summary output.
        :type input_file: string
        :return: The next-hop IP, ASN, and ID for each route server member
        :rtype: dict
        """
        ipToAsn = {}
        with open(input_file, 'rb') as f:
            try:
                for line in f:
                    d = ujson.loads(line.strip())
                    for neighbor in d["neighbours"]:
                        if neighbor["routes_received"] > 0:
                            ipToAsn[neighbor["id"]] = str(neighbor["asn"]) + " " + neighbor["address"]
                    break
            except ValueError:
                logging.error("The JSON format doesn't conform to the Alice LG API schema.")
            except KeyError:
                logging.error("The JSON format doesn't conform to the Alice LG API schema.")

        return ipToAsn

    @staticmethod
    def parse_summary(inputfile, ipversion, ixpParam):
        """
        Function to parse a  BGP summary output file.
        It prints the ASN->Neighbor IP mapping in a file
        """
        ipToAsn = {}
        addrPos, asnPos, ipcountPos, rtrType = [int(ixpParam["summary"]["ip"]), int(ixpParam["summary"]["asn"]),
                                                int(ixpParam["summary"]["ipCount"]), ixpParam["type"]]
        if rtrType == "alice":
            ipToAsn = BgpParser.parse_summary_alice(inputfile)
        else:
            with open(inputfile, 'rb') as f:
                for line in f:
                    # split the line to white spaces
                    lineTokens = line.strip().split()
                    if len(lineTokens) <= ipcountPos:
                        continue
                    interfaces_v4 = re.findall(
                        r'(?:\s|^|\(|\[)(?:[\d]{1,3})\.(?:[\d]{1,3})\.(?:[\d]{1,3})\.(?:[\d]{1,3})(?:\s|\)|$|\])', line)
                    interfaces_v6 = re.search(r'((([0-9A-Fa-f]{1,4}:){7}([0-9A-Fa-f]{1,4}|:))|(([0-9A-Fa-f]{1,4}:){6}(:[0-9A-Fa-f]{1,4}|((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3})|:))|(([0-9A-Fa-f]{1,4}:){5}(((:[0-9A-Fa-f]{1,4}){1,2})|:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3})|:))|(([0-9A-Fa-f]{1,4}:){4}(((:[0-9A-Fa-f]{1,4}){1,3})|((:[0-9A-Fa-f]{1,4})?:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(([0-9A-Fa-f]{1,4}:){3}(((:[0-9A-Fa-f]{1,4}){1,4})|((:[0-9A-Fa-f]{1,4}){0,2}:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(([0-9A-Fa-f]{1,4}:){2}(((:[0-9A-Fa-f]{1,4}){1,5})|((:[0-9A-Fa-f]{1,4}){0,3}:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(([0-9A-Fa-f]{1,4}:){1}(((:[0-9A-Fa-f]{1,4}){1,6})|((:[0-9A-Fa-f]{1,4}){0,4}:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:))|(:(((:[0-9A-Fa-f]{1,4}){1,7})|((:[0-9A-Fa-f]{1,4}){0,5}:((25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)(\.(25[0-5]|2[0-4]\d|1\d\d|[1-9]?\d)){3}))|:)))(%.+)?', line)

                    if interfaces_v6 is not None:
                        v6_interfaces = [interfaces_v6.group()]
                    else:
                        v6_interfaces = []
                    interfaces = interfaces_v4 + v6_interfaces
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
                                except IndexError:
                                    logging.error("Could not parse the IP count for line: '%s'\n" % line.strip())
                                # if string represents a valid positive number add asn->ip mapping to the dictionary
                                if Helper.isPositiveInt(received):
                                    if ip not in ipToAsn:
                                        ipToAsn[ip] = asn
        return ipToAsn

    def parse_prefix_communities(self, prefix_communities, rs_communities, rs_members, next_hop, communities_line=1):
        """
        Parses the RS communities attached on a prefix
        """
        tmp_allowed = set()
        tmp_blocked = set()

        allow_all = True  # Default configuration of Route Servers
        for community in prefix_communities:
            if "," in community:
                # transform community forma from (x,y) to x:y
                community = community[1:-1].replace(",", ":")
            first_16 = community.split(":")[0]
            bottom_16 = community.split(":")[1]
            if community in rs_communities["block_all"]:
                allow_all = False
                self.block_all.add(next_hop)
                tmp_blocked = set(rs_members)
            elif community == rs_communities["allow_one"].replace("$AS", first_16):
                tmp_allowed.add(first_16)
            elif community == rs_communities["allow_one"].replace("$AS", bottom_16):
                tmp_allowed.add(bottom_16)
            elif community == rs_communities["block_one"].replace("$AS", first_16):
                tmp_blocked.add(first_16)
            elif community == rs_communities["block_one"].replace("$AS", bottom_16):
                tmp_blocked.add(bottom_16)

        # B-IX uses the same community for allow_one and block_one, the community semantics
        # depend on whether the block_all community is present or not:
        # http://www.b-ix.net/technical/requirements/
        if allow_all is True and "59900:0" in rs_communities["block_all"]:
            tmp_blocked |= tmp_allowed
            tmp_allowed = set()

        # if no "block all" community was present assume the default route server behaviour
        # which is to advertise the received prefixes to every route server member
        if allow_all and next_hop not in self.block_all:
            if communities_line > 1:
                tmp_allowed |= set(self.allowed.get(next_hop, rs_members)) - tmp_blocked
            else:
                tmp_allowed |= rs_members - tmp_blocked
        try:
            self.allowed[next_hop].extend(tmp_allowed)
        except KeyError:
            self.allowed[next_hop] = list(tmp_allowed)

    def calculate_mlp_links(self, encountered_members):
        """
        Calculates the multilateral peering links over the Route Server
        based on the policies (allowed/blocked) defined by the path
        redistribution communities of each Route Server member
        """
        links = set()
        as_to_link = dict()
        for m1 in encountered_members:
            # If no community was set for the AS RS member m1,
            # we assume the "Allow all" default RS policy
            if m1 not in self.allowed:
                self.allowed[m1] = encountered_members
            for m2 in self.allowed[m1]:
                if m2 in encountered_members:
                    # If no community was set for the AS RS member m2,
                    # we assume the "Allow all" default RS policy
                    if m2 not in self.allowed:
                        self.allowed[m2] = encountered_members
                    if m1 in self.allowed[m2] and m1 != m2:
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
            print asn, " ", len(as_to_link[asn])
        return links

    def parse_prefix_info_quagga(self, inputfile, ip2asn, rs_communities):
        """
        Function that parses the results of the `show ip bgp` command and combines them with the
        route server community files and list of route server members to infer the multilateral
        peering links established over the route server.
        """
        encountered_members = set()
        members = set(ip2asn.values())
        next_hop = ""
        previous_line = ""
        community_pattern = r"(?<![:\d])\d+:\d+(?![:\d])"
        with open(inputfile, 'rb') as fin:
            for line in fin:
                line = line.strip()
                if line.endswith("RS-client)") or line.endswith("(received & used)"):
                    line_tokens = line.split(",")
                    as_path = line_tokens[0].strip().split()
                    next_hop = as_path[0]
                    if next_hop in members:
                        encountered_members.add(next_hop)
                elif line.startswith("Nexthop") and "RS-client" not in previous_line:
                    as_path = previous_line.strip().split()
                    next_hop = as_path[0]
                    if next_hop in members:
                        encountered_members.add(next_hop)
                elif line.startswith("Communit"):
                    communities = re.findall(community_pattern, line)
                    self.parse_prefix_communities(communities, rs_communities, members, next_hop)
                elif line.startswith("#>"):  # reset
                    next_hop = ""
                previous_line = line

        return self.calculate_mlp_links(encountered_members)

    def parse_prefix_info_bird(self, inputfile, ip2asn, rs_communities):
        """
        Function that parses the results of the `show ip bgp` command and combines them with the
        route server community files and list of route server members to infer the multilateral
        peering links established over the route server.
        """
        encountered_members = set()
        members = set(ip2asn.values())

        next_hop = ""
        communities_line = 0
        community_pattern = r"\(\d+,\d+\)"
        with open(inputfile, 'rb') as fin:
            for line in fin:
                line = line.strip()
                communities = re.findall(community_pattern, line)
                if len(communities) > 0:
                    communities_line += 1
                    self.parse_prefix_communities(communities, rs_communities, members, next_hop, communities_line)
                elif line.startswith("BGP.as_path"):
                    # clear the block_all set for each new prefix
                    self.block_all.clear()
                    communities_line = 0
                    line_tokens = line.split(":")
                    asn_path = line_tokens[1].strip().split()
                    next_hop = asn_path[0]
                    if next_hop in members:
                        encountered_members.add(next_hop)
                elif line.startswith("#>"):  # reset
                    next_hop = ""

        return self.calculate_mlp_links(encountered_members)

    def parse_prefix_info_alice(self, input_file, ip2asn, rs_communities):
        """
        Parses the prefix information in the output of the neighbor/$id/routes
        endpoint of the Alice LG, to infer the multilateral peering links established
        over the route server.

        :param input_file: the path to the file that contains the output of the neighbor/$id/routes endpoint
        :type input_file: string
        :param ip2asn: the mapping between neighbor IDs and ASNs
        :type ip2asn: dict
        :param rs_communities: the route redistribution communities used by the route server
        :param: dict
        :return: the inferred multilateral peering links
        :rtype: set
        """
        encountered_members = set()
        members = set(ip2asn.values())
        with open(input_file) as fin:
            for line in fin:
                try:
                    neighbor_prefixes = ujson.loads(line.strip())
                    for prefix_data in neighbor_prefixes["imported"]:
                        next_hop = str(prefix_data["bgp"]["as_path"][0])
                        if next_hop in members:
                            encountered_members.add(next_hop)
                        else:
                            print next_hop
                        communities = list()
                        for c in prefix_data["bgp"]["communities"]:
                            communities.append("%s:%s" % (c[0], c[1]))
                        self.parse_prefix_communities(communities, rs_communities, members, next_hop, 1)
                except ValueError:
                    continue
                except KeyError:
                    continue
        return self.calculate_mlp_links(encountered_members)
