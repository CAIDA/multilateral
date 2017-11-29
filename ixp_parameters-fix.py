#! /usr/bin/env python
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
import json
import sys

f = open(sys.argv[1], "r")
decoded = json.load(f)
fixed = {}
fixed["looking_glasses"] = {}

http_keys = ["url","referer","rarg", "type","prefix"]
for server in decoded["looking_glasses"].keys():
    fixed["looking_glasses"][server] = {}
    fixed["looking_glasses"][server]["http"] = {}
    arg = None
    for key in decoded["looking_glasses"][server].keys():
	value = decoded["looking_glasses"][server][key]
	if key == "arg":
	    arg = value
	elif key in http_keys:
	    fixed["looking_glasses"][server]["http"][key] = value
	else:
	    fixed["looking_glasses"][server][key] = value
    if key is None:
	sys.stderr.write("failed to find arg for "+server+"\n")

    for key in fixed["looking_glasses"][server]["commands"].keys():
	fixed["looking_glasses"][server]["commands"][key]["lg_query_arg"] = arg
    if "output" in fixed["looking_glasses"][server]:
    	fixed["looking_glasses"][server]["output"]["type"] = "bird"
    
print json.dumps(fixed,sort_keys=True, indent=4, separators=(',', ': '))
