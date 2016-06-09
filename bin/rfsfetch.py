#!/usr/bin/python


import urllib
import os
import gzip


PKG_URL="http://http.us.debian.org/debian/dists/%s/main/binary-%s/Packages.xz"

BUG_URL="http://bugs.debian.org/cgi-bin/bugreport.cgi?bug="

def get_cache_object( filename, url, uni=True ):

    if not os.access(filename, os.R_OK):
        fname, hdrs = urllib.urlretrieve(url, filename)

    f = open(filename, 'r')
    text= f.read()

    if uni:
        return(text.decode('utf-8'))
    else:
        return text

def get_rfs_text(rfsnum):
    return(get_cache_object('tmp/rfs%s.cache' % rfsnum, BUG_URL+rfsnum))

def get_package_text(distname, arch):
    url = PKG_URL % (distname, arch)

    cache_file = "tmp/Packages-%s-%s.xz" % (distname, arch)
    get_cache_object(cache_file, url, False)

    os.system("unxz %s" % cache_file)
    f = open(cache_file[:-3])
    text = f.read()
    f.close()

    return text.decode('utf-8')


