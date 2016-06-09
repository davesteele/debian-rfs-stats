#!/usr/bin/python


from BeautifulSoup import BeautifulSoup

import HTMLParser
_htmlparser = HTMLParser.HTMLParser()
unescape = _htmlparser.unescape

import hashlib
import re
import datetime
import rfsfetch
import json

def hash(text):
    return(hashlib.sha1(text.encode('ascii', errors='ignore')).hexdigest())

def get_comment_params(rfsnum, rfs, commenttext):
    params = {}

    params['num'] = rfsnum
    params['anchor'] = re.search("<a name=\"(.+?)\"", commenttext, re.MULTILINE).group(1)

    who = re.search("\"headerfield\">From:</span> (.+?)</div>", commenttext, re.MULTILINE | re.DOTALL).group(1)
    whor = who.strip()
    who = unescape(who)
    params['commenter'] = who

    datestr = re.search("\"headerfield\">Date:</span> (.+?)</div>", commenttext, re.MULTILINE).group(1)
    try:
        params['date'] = datetime.datetime.strptime( datestr[5:24], "%d %b %Y %H:%M:%S")
    except ValueError:
        params['date'] = datetime.datetime.strptime( datestr[5:21], "%d %b %Y %H:%M")

    params['response'] = rfs.submitter != params['commenter']

    return(params)


def _is_closed(rfstext):

    if re.search('<title>.+RFS:', rfstext) is None:
        print "is closed"
        return True

    return(re.search('<strong>Done:</strong>', rfstext, re.MULTILINE) is not None)

    srch = re.compile('<strong>Bug reopened</strong>|%s\-done|%s\-close'
                      % (self.num, self.num))

    matches = [x for x in rfstext if srch.search(x)]

    if matches:
        print "Reopen found in ", self.num

    if( [x for x in rfstext if '<strong>Done:</strong>' in x] ):
        return True

    if not bool(matches):
        return False

    return( '-done' in matches[-1] or '-close' in matches[-1] )

def get_rfs_params(rfsnum, rfstext):
    params = {}

    params['num'] = rfsnum
    params['sha'] = hash(rfstext)

    soup = BeautifulSoup(rfstext)

    sender = soup.find('div', attrs={'class': 'header'} ).contents[1]
    sender = sender.strip()
    sender = unescape(sender)
    params['submitter'] = sender

    rfslines = rfstext.split('\n')

    opendateln = [x for x in rfslines if 'Date:' in x][0]
    opendatestr = re.search('<p>Date: (.+)</p>', opendateln).group(1)
    params['opened'] = datetime.datetime.strptime( opendatestr[5:], "%d %b %Y %H:%M:%S UTC")

    if _is_closed(rfstext):
        dateSearch = re.compile('headerfield.+Date:</span>')
        dateLine = [x for x in rfslines if dateSearch.search(x)][-1]
        dateStr = re.search('</span> (.+)</div>', dateLine).group(1)
        params['closed'] = datetime.datetime.strptime( dateStr[5:24], "%d %b %Y %H:%M:%S")
    else:
        params['closed'] = None

    params['package'] = rfslines[2].split()[3]
    params['version'] = ''

    if '/' in params['package']:
        (params['package'], params['version']) = params['package'].split('/')[0:2]

    return params

def commentgen(rfstext):
    s = rfstext
    while True:
        match = re.search( ".+?(<hr><p class=\"msgreceived\">.+?<hr>)(.+)", s, re.MULTILINE | re.DOTALL)

        if match is None:
            return

        t = match.group(2)
        s = t

        if re.search("<span class=\"headerfield\">Date:</span>", match.group(1), re.MULTILINE | re.DOTALL):
            yield match.group(1)

BUG_URL="http://bugs.debian.org/cgi-bin/bugreport.cgi?bug="

RFS_URL="http://bugs.debian.org/cgi-bin/pkgreport.cgi?package=sponsorship-requests&archive=both"




class RFSList(object):
    def __init__(self, rfs_url=RFS_URL):

        self.raw = rfsfetch.get_cache_object( 'tmp/rfslist.cache', RFS_URL ).split('\n')

        buglines = [x for x in self.raw if re.search('bugreport.cgi.+RFS', x)]
        self.bugs = [re.search('bug=([0-9]+)', x).group(1) for x in buglines]



    def __iter__(self):
        for bug in self.bugs:
            yield(bug)

def lineiter(text):
    line = []

    for char in text:
        if char == "\n":
            yield ''.join(line)
            line = []
        else:
            line.append(char)


def pkgiter(pkgtext):
    for line in lineiter(pkgtext):
        line = line.rstrip('\n')

        if( line[0:len("Source: ")] == "Source: "):
            pkg = line[len("Source: "):]

        if( line[0:len("Package: ")] == "Package: "):
            pkg = line[len("Package: "):]

        if( line[0:len("Version: ")] == "Version: "):
            yield((pkg, line[len("Version: "):]))


