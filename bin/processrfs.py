#!/usr/bin/python


import rfsdb
import rfsanalyze
import datetime
import math
import json

# todo - this shouldn't be here
import email.utils
import time

db = rfsdb.init_db()
rfsdb.update_package_lists(db)
rfsdb.update_rfs_list(db)

#for obj in rfsdb.opened_between(db):
#    print obj.__repr__().encode('utf-8')

#for obj in rfsdb.closed_between(db):
#    print obj.__repr__().encode('utf-8')
#    print rfsdb.rfs_state(db, obj.num)

#for obj in rfsdb.open_on(db, datetime.datetime.now()):
#    print obj.__repr__().encode('utf-8')

#for obj in rfsdb.responses_between(db):
#    print obj.__repr__().encode('utf-8')

#print rfsdb.rfs_days_between(db)

#print rfsdb.rfs_days_between(db)/rfsdb.responses_between(db).count()


datestats = rfsanalyze.monthly_stats(db)

f = open( "data/datestats.json", 'w')
f.write(json.dumps(datestats, sort_keys=True, indent=2))
f.close()

#print datestats

with open("data/datestats.json", 'wb') as f:
    f.write(json.dumps(datestats, sort_keys=True, indent=2))

pkgstats = rfsanalyze.rfs_stats(db)
#print json.dumps(pkgstats, sort_keys=True, indent=2)

rfsdata = {
              'rfslist': pkgstats,
              'runDate': email.utils.formatdate(time.mktime(datetime.datetime.now().timetuple())),
              'runUnix' : time.time(),

          }
with open("data/rfsdata.json", 'wb') as f:
    f.write(json.dumps(rfsdata, sort_keys=True, indent=2))

