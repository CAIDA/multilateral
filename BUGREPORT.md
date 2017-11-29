"""
Current known Issues:
"""
ISSUE:
42476 was attempting to concatenate an integer to a string in main.py, line 162.
FIX: 
Modified main.py line 162 from ip_to_asn[ip] to str(ip_to_asn[ip]).

ISSUE:
2108 was realizing a keyError in which the "url" key did not exist.
FIX:
Added the field used in "referer" as the "url".

ISSUE:
513 was getting an indexOutOfBOunds error for "contentindex" = -2.
FIX:
Modified 513 to use "contentindex" = -1.

ISSUE:
19214 and 24029 is viewing the_page field as -1, since the connection to the looking glass servers in the JSON is timing out.
FIX:
Find an acceptable server URL to query and modify the JSON to reflect this.
FOUND new server for 24029.  OLD: 203.190.131.164, NEW: 180.179.222.68

ISSUE:
65000 accesses line 53 in main.py, which attempts to iterate through a boolean value set at the beginning of the function.  One of the variables that uses this function calls it on an iterable object "addresses", which may be the intent of the logic in line 53.
FIX:
sendQuery parameters need to be changed, to create an iterable field.
