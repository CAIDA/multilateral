# Inferring Multilateral Peering

Code for inferring Multilateral Peering Agreements (MLPA) based on the algorithm presented in the paper: 

```
Giotsas, Vasileios, Shi Zhou, and Matthew Luckie. 
"Inferring Multilateral Peering." 
Proceedings of the ninth ACM conference on Emerging networking experiments and technologies (CoNEXT 2013). ACM, 2013.
http://conferences.sigcomm.org/co-next/2013/program/p247.pdf
```

Cite the above paper in publications that use the source code or the produced data.

# Dependencies
   - [BeautifulSoup](http://www.crummy.com/software/BeautifulSoup/) used to parse the HTML responses
   - [netaddr](https://pypi.python.org/pypi/netaddr) used to validate IP addresses
   - [PyCURL](http://pycurl.sourceforge.net/) used to issue HTTP requests
   
# IMPORTANT DISCLAIMER

   - **DO NOT INCREASE THE FREQUENCY OF HTTP QUERIES** 
   - **DO NOT USE THE CODE WITH LOOKING GLASSES THAT SPECIFICALLY PROHIBIT AUTOMATED QUERYING**
   
This code issues queries to web-based looking glasses that are meant for low-frequency querying. For this reason the code is designed to minize the number of queries to respect the operational requirements of the looking glass providers. **Do not alter the code to increase the querying frequency.** Overwhelming the looking glass servers with queries will be perceived as Denial of Service attack that will either lead to your address being blocked, or even worse for the community, it may result in the termination of public access to the looking glass. 

# Usage

These scripts automate the issuing of queries to IXP looking glasses and the parsing of the looking glass results. 
To infer Multilateral Peering Links you need to issue three type of queries:
1. BGP Summary query to retrieve the networks connected to the IXP route server (members)
2. BGP Neighbor Info to retrieve the prefixes advertised by the route server member
3. BGP Prefix Info to retrieve the BGP communities set on the prefixes advdertised to the route server

With the produced output you can then run the inference of the multilateral peering links.

To syntax to execute each of these commands is the following:

```
python main.py -a <asn> -c <command> -o <outputfile> [-i <inputfile>]  [-f <inputfile2>]
```


-a is the ASN of the IXP you want to query  
-o is the file where you want to log the looking glass output  
-c is the command (bgp, summary, neighbor, inference)  
-i is the first file that contains the arguments of the commands. Required for all commmands except summary
-f is the second file that contains the arguments of the commands. Required for the `bgp` command and `inference` commands.
  
### BGP Summary
The `summary` (show ip bgp summary) command doesn't take any argument so you omit the inputfile for this command. 

The `summary` command outputs two files: 
1. The raw bgp summary returned by the looking glass. The name of this file is given by the -o <outputfile> parameter.
2. the mapping of IP to ASN connected on the route server. The name of this file is the same as the -o <outputfile> parameter with "\_addresses" appended before the file extention. For example if the name of the outputfile is summary-example.txt the name of the mapping file will be summary-example\_addresses.txt

### Neighbor Info

The `neighbor` (show ip bgp neighbor) command requires a mapping of IP addresses to ASNs which you get from the `summary` command. 

The `neighbor` command outputs one file, the prefixes advertised by each route server member to the route server. The name of this file is given by the -o <outputfile> parameter.

### Prefix Info

The `bgp` (show ip bgp) command requires a list of prefixes which you get from the neighbor command, and the mapping of IP addresses to ASNs which you get from the `summary` command. 

The `bgp` command outputs a file a that contains the prefix BGP attributes (AS path, communities etc) for each queried prefix. The name of this file is given by the -o <outputfile> parameter.

### Inference

This is the only command that doesn't issue a query to a looking glass but it just parsed the output of the `bgp` command to infer the multilateral peering links. The output of this commands is the file with the inferred peering links. The name of this file is given by the -o <outputfile> parameter.

All the output files are written in the ``lg-logs/<ixp-asn>`` folder.

# Example

Here we show an example of command sequence that infers the multilateral peering links over the DE-CIX route server (AS6695).

**1. Run the summary command**

```
python main.py -a 6695 -c summary -o summary-decix-10092015.txt
```
   - Input: nothing
   - Output: 
      - lg-logs\6695\summary-decix-10092015.txt
      - lg-logs\6695\summary-decix-10092015_addresses.txt


**2. Run the neighbor command**

```
 python main.py -a 6695 -c neighbor -o neigh-decix-10092015.txt -i lg-logs/6695/summary-decix-10092015_addresses.txt
```

   - Input: 
      - lg-logs/6695/summary-decix-10092015_addresses.txt
   - Output: 
      - lg-logs/6695/neighinfo-decix-10092015.txt


**3. Run the bgp command**

```
python main.py -a 6695 -c bgp -o bgp-decix-10092015.txt -i lg-logs/6695/neighinfo-decix-10092015.txt -f lg-logs/6695/summary-decix-10092015_addresses.txt
```

   - Input: 
      - lg-logs/6695/neighinfo-decix-10092015.txt
      - lg-logs/6695/summary-decix-10092015_addresses.txt
   - Output:
      -  lg-logs/6695/bgp-decix-10092015.txt


**4. Run the inference**
```
python main.py -a 6695 -c inference -o links-decix-10092015.txt -i lg-logs/6695/bgp-decix-09092015.txt -f lg-logs/6695/summary-decix-10092015_addresses.txt
```

   - Input: 
      - lg-logs/6695/bgp-decix-09092015.txt
      - lg-logs/6695/summary-decix-10092015_addresses.txt
   - Output:
      - links-decix-10092015.txt
