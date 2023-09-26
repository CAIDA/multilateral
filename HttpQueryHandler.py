
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

import urllib
import time
import re
from bs4 import BeautifulSoup
from html.parser import HTMLParser
from pprint import pprint
import sys
import json
import httplib
import socket
from StringIO import StringIO
import pycurl
import importlib

importlib.reload(sys)
sys.setdefaultencoding("utf-8")


class MLStripper(HTMLParser):
    """
    Methods to strip html tags from string
    """

    def __init__(self):
        self.reset()
        self.fed = []

    def handle_data(self, d):
        self.fed.append(d)

    def get_data(self):
        return ' '.join(self.fed)


class HttpQueryHandler(object):
    """
    Methods to handle issue of HTTP queries and parsing of the responses
    """

    def __init__(self):
        pass

    @staticmethod
    def strip_tags(html):
        s = MLStripper()
        s.feed(str(html))
        return s.get_data()

    @staticmethod
    def remove_break_line(html_txt):
        result = ""
        tokens = re.split("<br>|<br />|<br/>", html_txt)
        for token in tokens:
            result = result + token.strip() + "\n"
        result = result.replace("&nbsp;", "")
        return result

    @staticmethod
    def send_http_request(params, url, referrer, verb):
        user_agent = 'Mozilla/5.0 (Windows NT 5.2; WOW64; rv:17.0) Gecko/20100101 Firefox/17'
        timeout = 900

        storage = StringIO()
        try:
            curl_connector = pycurl.Curl()
            curl_connector.setopt(pycurl.CONNECTTIMEOUT, timeout)
            curl_connector.setopt(pycurl.TIMEOUT, timeout)
            if verb == "post":
                headers = ['User-Agent: ' + user_agent, 'Referer: ' + referrer, 'Connection: keep-alive']
                if url == "http://noc.ucomline.net/lg1":
                    headers.append("Cookie: PHPSESSID=199d19597747f15a4d778d68b56d4ab7")
                post_fields = urllib.parse.urlencode(params)
                pprint(post_fields)
                curl_connector.setopt(pycurl.HTTPHEADER, headers)
                curl_connector.setopt(curl_connector.URL, url)
                curl_connector.setopt(curl_connector.POSTFIELDS, post_fields)
            elif verb == "get":
                headers = ['User-Agent: ' + user_agent,
                           'Referer: ' + url,
                           'Connection: keep-alive',
                           'Cache-Control: max-age=0']
                url += "?"
                counter = 1
                for key, value in params.items():
                    counter += 1
                    if key == "zeroparam":
                        url += value
                    elif key == "lg_query_arg":
                        continue
                    else:
                        url += key + "=" + value
                    if counter <= len(params):
                        url += "&"
                url = url.replace(" ", "%20")
                print(url)
                curl_connector.setopt(pycurl.HTTPHEADER, headers)
                curl_connector.setopt(curl_connector.URL, url)
            curl_connector.setopt(pycurl.SSL_VERIFYPEER, 0)
            curl_connector.setopt(pycurl.SSL_VERIFYHOST, 0)
            curl_connector.setopt(curl_connector.WRITEFUNCTION, storage.write)
            curl_connector.perform()
            curl_connector.close()
            content = storage.getvalue()
        except pycurl.error as e:
            error_code, error_text = e.args
            print('We got an error. Code: %s, Text:%s' % (error_code, error_text))
            if str(error_code) != "18":
                return -1
            else:
                content = storage.getvalue()
        return content

    @staticmethod
    def send_http_request_alt(params, url, referrer, verb):
        user_agent = 'Mozilla/5.0 (Windows NT 5.2; WOW64; rv:17.0) Gecko/20100101 Firefox/17'
        timeout = 900
        query_ok = False
        retry_counter = 0

        while query_ok is False:
            try:
                if verb == "post":
                    headers = {'User-Agent': user_agent,
                               'Referer': referrer,
                               'Content-Type': 'application/x-www-form-urlencoded',
                               'Connection': 'keep-alive'}
                    if url == "http://noc.ucomline.net/lg1":
                        headers["Cookie"] = "PHPSESSID=199d19597747f15a4d778d68b56d4ab7"

                    data = urllib.parse.urlencode(params)
                    req = urllib.request.Request(url, data, headers)
                elif verb == "get":
                    headers = {'User-Agent': user_agent,
                               'Referer': url,
                               'Cache-Control': 'max-age=0',
                               'Connection': 'keep-alive'}
                    url += "?"
                    counter = 1
                    for key, value in params.items():
                        counter += 1
                        if key == "zeroparam":
                            url += value
                        elif key == "lg_query_arg":
                            continue
                        else:
                            url += key + "=" + value
                        if counter <= len(params) - 1:
                            url += "&"
                    url = url.replace(" ", "%20")
                    print(url)
                    req = urllib.request.Request(url, None, headers)
                response = urllib.request.urlopen(req, timeout=timeout)
                try:
                    chunk = True
                    src = ""
                    while chunk:
                        chunk = response.read(1024)
                        src += chunk
                    response.close()
                    the_page = src
                except httplib.IncompleteRead as e:
                    the_page = e.partial
                query_ok = True
            except (urllib.error.URLError, httplib.HTTPException, socket.timeout, socket.error) as e:
                time.sleep(20)
                retry_counter += 1
                if retry_counter >= 2:
                    the_page = "ERROR"
                    break
        return the_page

    @classmethod
    def parse_html(cls, html_text, lg_html, asn):
        """
        Parse the HTML of the reply to extract the LG output
        """
        html_tag = lg_html["tag"]
        tag_index = int(lg_html["tagindex"])
        content_index = int(lg_html["contentindex"])
        html_class = lg_html["class"]
        html_id = lg_html["id"]
        insert_br = lg_html["insertbr"]
        contents = ""
        try:
            soup = BeautifulSoup(html_text, "html.parser")
            if html_tag == "result":
                pre = soup.findAll("div", {"class": "result"})
                pre = pre[1]
                reply = ''.join(str(pre.contents))
                contents = BeautifulSoup(reply, "html.parser")
            elif html_tag == "json":
                decoded_html = None
                decoded = json.loads(html_text)
                if 'lg' in decoded:
                    contents = decoded['lg']
                elif 'title' in decoded and "rs1.ripn.net" in decoded['title']:
                    if 'txt' in decoded:
                        if "BGP information for neighbor" in decoded['txt'][0]:
                            decoded_html = '\n'.join(decoded['txt'][14:])
                        else:
                            decoded_html = '\n'.join(decoded['txt'])
                        sanitized_html = decoded_html.replace("<t>", "\t")
                        soup = BeautifulSoup(sanitized_html, "html.parser")
                        # html_pretty = soup.prettify()
                        # soup = BeautifulSoup(html_pretty, "html.parser")
                        return soup.get_text()
                else:
                    contents = decoded
            elif html_tag == "table":
                if html_id != "":
                    table_rows = soup.find("table", {"id": html_id}).find_all('tr')
                else:
                    table_rows = soup.find_all("table")[tag_index].find_all('tr')
                for tr in table_rows:
                    if len(contents) == 0:
                        contents += tr.text.replace("\n", "\t")
                    else:
                        contents += "\n" + tr.text.replace("\n", "\t")
            elif tag_index == -1:
                contents = cls.remove_break_line(html_text)
            elif tag_index == -2:
                contents = html_text
            else:
                html_pretty = soup.prettify()
                soup = BeautifulSoup(html_pretty, "html.parser")
                try:
                    if html_class == "" and html_id == "":
                        pre = soup.findAll(html_tag)[tag_index]
                    elif html_class != "":
                        pre = soup.findAll(html_tag, html_class)[tag_index]
                    elif html_id != "":
                        pre = soup.find(id=html_id)
                except IndexError:
                    return -1
                if content_index == -1:
                    contents = ""
                    for idx in pre.contents:
                        content = str(idx)
                        if insert_br:
                            contents += "\n" + str(content.strip())
                        else:
                            contents += str(content.strip())
                    contents = BeautifulSoup(contents, "html.parser")
                    contents = cls.remove_break_line(contents.encode('utf-8').strip())
                else:
                    if asn == "59900":
                        pre = soup.find_all(html_tag)[tag_index]
                        pre = str(pre).replace("<br>", "\n")
                        pre = str(pre).replace("\r", "\n")
                        soup = BeautifulSoup(pre, 'html.parser')
                        contents = soup.text
                    elif len(pre.contents) > content_index:
                        contents = pre.contents[content_index]
                contents = cls.remove_break_line(contents.encode('utf-8').strip())
        except AttributeError:
            return -1

        # specific cases
        if html_tag == "table" and tag_index == 0:
            contents = contents.replace("<tr>", "\n")
            contents = contents.replace("</tr>", "")
        return contents
