#!/usr/bin/python

import urllib
import re
import os
import time
import datetime
import calendar
import pytz
import email.utils
import json
import sys

RFS_URL="http://bugs.debian.org/cgi-bin/pkgreport.cgi?package=sponsorship-requests&archive=both"

BUG_URL="http://bugs.debian.org/cgi-bin/bugreport.cgi?bug="


def get_cache_object( filename, url ):
    if not os.access(filename, os.R_OK):
        fname, hdrs = urllib.urlretrieve(url, filename)
    return( open(filename, 'r').read() )

class RFSList(object):
    def __init__(self, rfs_url=RFS_URL):

        self.raw = get_cache_object( 'tmp/rfslist.cache', RFS_URL ).split('\n')

        buglines = [x for x in self.raw if re.search('bugreport.cgi.+RFS', x)]
        bugs = [re.search('bug=([0-9]+)', x).group(1) for x in buglines]

        self.bugs = sorted(list(set(bugs)))

    def __iter__(self):
        for bug in self.bugs:
            yield(bug)

class RFS(object):
    def __init__(self, bugnum, bug_url=BUG_URL):
        self.bugnum = bugnum

        self.raw = get_cache_object('tmp/rfs%s.cache' % bugnum, bug_url).split('\n')

    def isDropped(self):
        srch = re.compile('Package .+ has been removed from mentors.')
        return(bool([x for x in self.raw if srch.search(x)]))

    def isAccepted(self):
        #srch = re.compile('Package .+ version .+ is in .+ now.')
        #return(bool([x for x in self.raw if srch.search(x)]))

        # In practice, not isDropped() is more reliable than the
        # previous isAccepted()
        return(self.isClosed() and not self.isDropped())

    def isClosed(self):
        srch = re.compile('<strong>Bug reopened</strong>|%s\-done|%s\-close'
                          % (self.bugnum, self.bugnum))

        matches = [x for x in self.raw if srch.search(x)]

        #print matches

        if( [x for x in self.raw if '<strong>Done:</strong>' in x] ):
            return True

        if not bool(matches):
            return False

        return( '-done' in matches[-1] or '-close' in matches[-1] )
        #return(bool([x for x in self.raw if srch.search(x)]))

    def isOpen(self):
        return(not self.isClosed())

    def state(self):
        if self.isOpen():
            return('open')
        elif self.isDropped():
            return('dropped')
        elif self.isAccepted():
            return('accepted')

        raise

    def numComments(self):
        return(len([x for x in self.raw if re.search('>From:<', x)]))

    def dateOpened(self):
        dateline = [x for x in self.raw if 'Date:' in x][0]
        dateStr = re.search('<p>Date: (.+)</p>', dateline).group(1)
        unixTime = time.mktime(email.utils.parsedate(dateStr))
        return (dateStr, unixTime)

    def dateClosed(self):
        pass
        if self.isOpen():
            return( "", 0 )

        dateSearch = re.compile('headerfield.+Date:</span>')
        dateLine = [x for x in self.raw if dateSearch.search(x)][-1]
        dateStr = re.search('</span> (.+)</div>', dateLine).group(1)
        unixTime = time.mktime(email.utils.parsedate(dateStr))
        return (dateStr, unixTime)

    def pkgName(self):
        pkgLine = self.raw[2]
        pkgName = pkgLine.split()[3]

        return( pkgName )


csvfl = open('data/rfsdata.csv', 'w')
csvfl.write( "number, name, openStr, openUnix, closedStr, closedUnix, age, state, comments\n" )


rfslist = []
for rfsnum in RFSList():

    print "Processing ", rfsnum

    rfs = RFS(rfsnum)

    entry = {
              'number':     rfsnum,
              'name':       rfs.pkgName(),
              'openStr':    rfs.dateOpened()[0],
              'openUnix':   rfs.dateOpened()[1],
              'closedStr':  rfs.dateClosed()[0],
              'closedUnix': rfs.dateClosed()[1],
              'age':        time.time() - rfs.dateOpened()[1],
              'state':      rfs.state(),
              'comments':   rfs.numComments(),
            }

    rfslist.append(entry)

    csvline = "\"" + \
            "\", \"".join( [
              rfsnum,
              rfs.pkgName(),
              rfs.dateOpened()[0],
              str(rfs.dateOpened()[1]),
              rfs.dateClosed()[0],
              str(rfs.dateClosed()[1]),
              str(time.time() - rfs.dateOpened()[1]),
              rfs.state(),
              str(rfs.numComments()),

              ] ) \
            + "\""

    csvfl.write( csvline )
    csvfl.write('\n')


csvfl.close()

output = open( 'data/rfsdata.json', 'w')

output.write(json.dumps( rfslist ))

output.close()


def addmonth(dtu):
    dt = datetime.datetime.utcfromtimestamp(dtu)

    if dt.month == 12:
        #ndt = datetime.datetime( dt.year+1, 1, dt.day )
        ndt = dt.replace( dt.year+1, 1 )
    else:
        #ndt = datetime.datetime( dt.year, dt.month+1, dt.day)
        ndt = dt.replace( dt.year, dt.month+1)

    return( calendar.timegm(ndt.timetuple()))

class monthIter(object):
    def __init__(self, firstu, lastu):
        print firstu, lastu
        firstdt = datetime.datetime.utcfromtimestamp(firstu)
        startdt = datetime.datetime( firstdt.year, firstdt.month, 1, 0,0,0,0, pytz.utc )
        self.startu = calendar.timegm(startdt.timetuple())

        self.lastu = lastu

    def __iter__(self):
        dtu = self.startu

        while dtu < self.lastu:
            print dtu
            yield dtu
            dtu = addmonth(dtu)


def getRFSSlice(rfslist, startu, endu, state):

    slice = None

    if state in ['new']:
        slice = [x for x in rfslist if x['openUnix']>startu and x['openUnix']<endu]
    elif state in ['accepted', 'dropped']:
        slice = [x for x in rfslist if x['closedUnix']>startu and x['closedUnix']<endu
                                       and x['state']==state]
    elif state in ['open']:
        slice = [x for x in rfslist if x['openUnix']<endu
                                    and (x['closedUnix']==0 or x['closedUnix']>endu)]
    else:
        raise

    return slice


firstu = min([x['openUnix'] for x in rfslist])
lastu = time.time()

datestatscsv = open( 'data/datestats.csv', 'w' )
datestatscsv.write( 'date, year, month, unixstart, unixend, new, accepted, dropped, open\n' )

entryList = []

for dtu in monthIter(firstu, lastu):
    #print dtu, addmonth(dtu)

    numnew =      len(getRFSSlice(rfslist, dtu, addmonth(dtu), 'new'))
    numaccepted = len(getRFSSlice(rfslist, dtu, addmonth(dtu), 'accepted'))
    numdropped =  len(getRFSSlice(rfslist, dtu, addmonth(dtu), 'dropped'))
    numopen =     len(getRFSSlice(rfslist, dtu, addmonth(dtu), 'open'))


    dt = datetime.datetime.utcfromtimestamp(dtu)

    datestatscsv.write( ", ".join( [
                      dt.strftime('%m/%Y'),
                      str(dt.year),
                      str(dt.month),
                      str(dtu),
                      str(addmonth(dtu)),
                      str(numnew),
                      str(numaccepted),
                      str(numdropped),
                      str(numopen),
                   ] ) )
    datestatscsv.write("\n")

    entry = {
              'dateStr':  dt.strftime('%m/%Y'),
              'year':     dt.year,
              'month':    dt.month,
              'startu':   dtu,
              'endu':     addmonth(dtu),
              'new':      numnew,
              'accepted': numaccepted,
              'dropped':  numdropped,
              'open':     numopen,

        }

    entryList.append(entry)


output = open( 'data/datestats.json', 'w')
output.write(json.dumps( entryList ))
output.close()


datestatscsv.close()
