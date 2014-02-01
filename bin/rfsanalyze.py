#!/usr/bin/python

import datetime
import calendar
import rfsdb
import sqlalchemy as alch

def addmonth(dt):

    if dt.month == 12:
        ndt = dt.replace( dt.year+1, 1 )
    else:
        ndt = dt.replace( dt.year, dt.month+1)

    return(ndt)

def monthIter(start = datetime.datetime(2012, 1, 1), end = datetime.datetime.now()):
    current = start

    while current < end:
        next = addmonth(current)

        yield( (current, next) )

        current = next


def monthly_stats(db):

    returnval = []
    for (start, end) in monthIter():
        stats = {}
        returnval.append(stats)

        stats['year'] = start.year
        stats['month'] = start.month
        stats['startu'] = calendar.timegm(start.utctimetuple())
        stats['endu'] = calendar.timegm(end.utctimetuple())
        stats['dateStr'] = "%d/%d" % (start.month, start.year)
        stats['open'] = rfsdb.open_on(db, end).count()
        stats['new'] = rfsdb.opened_between(db, start, end).count()

        closed = rfsdb.closed_between(db, start, end)

        stats['accepted'] = len([x for x in closed if rfsdb.rfs_state(db, x.num) == 'accepted'])
        stats['dropped']  = len([x for x in closed if rfsdb.rfs_state(db, x.num) == 'dropped'])

        stats['mdbr'] = (1.0*rfsdb.rfs_days_between(db, start, end))/rfsdb.responses_between(db, start, end).count()

    return(returnval)

def rfs_stats(db):
    returnval = []

    session = db()

    rfslist = session.query(rfsdb.RFS).order_by(rfsdb.RFS.num)

    for rfs in rfslist:
        stats = {}
        returnval.append(stats)

        comment_query = session.query(rfsdb.Comment).filter(rfsdb.Comment.num == rfs.num)
        response_query = session.query(rfsdb.Comment).filter(alch.and_(rfsdb.Comment.num == rfs.num, rfsdb.Comment.response == True))

        stats['name'] = rfs.package + "/" + rfs.version
        if rfs.closed == None:
            stats['closedUnix'] = 0
        else:
            stats['closedUnix'] = calendar.timegm(rfs.closed.utctimetuple())
        stats['openUnix'] = calendar.timegm(rfs.opened.utctimetuple())
        stats['comments'] = comment_query.count()
        stats['responses'] = response_query.count()
        last_comment_date = comment_query.order_by("date desc").first().date
        stats['lastUnix'] = calendar.timegm(last_comment_date.utctimetuple())

        stats['number'] = rfs.num
        stats['state'] = rfsdb.rfs_state(db, rfs.num)

    return returnval
