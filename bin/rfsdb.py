

import sqlalchemy as alch
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import datetime
from distutils.version import LooseVersion

import rfsparse
import rfsfetch

Base = declarative_base()

class Comment(Base):
    __tablename__ = "Comment"

    id = alch.Column(alch.Integer, nullable=False, unique=True, autoincrement=True, primary_key=True)
    num = alch.Column(alch.String, index = True)
    anchor = alch.Column(alch.String)
    commenter = alch.Column(alch.String)
    date = alch.Column(alch.DateTime)
    response = alch.Column(alch.Boolean)

    def __repr__(self):
        return(u"<Comment(num='%s', anchor='%s', response='%s', commenter='%s', date='%s')>" %
                (
                    self.num,
                    self.anchor,
                    self.response,
                    self.commenter,
                    self.date.__str__(),
                ))


class RFS(Base):
    __tablename__ = 'RFS'

    num = alch.Column(alch.String, primary_key = True, index = True)
    sha = alch.Column(alch.String)
    submitter = alch.Column(alch.String)
    opened = alch.Column(alch.DateTime)
    closed = alch.Column(alch.DateTime)
    package = alch.Column(alch.String)
    version = alch.Column(alch.String)

    def __repr__(self):
        opened_str = closed_str = "<NA>"

        adatetime = datetime.datetime(1970, 1, 1)

        if type(self.opened) is type(adatetime):
            opened_str = self.opened.__str__()
        if type(self.closed) is type(adatetime):
            closed_str = self.closed.__str__()

        return(u"<RFS(num='%s', sha='%s', submitter='%s', opened='%s', closed='%s', package='%s', version='%s')>" %
                (
                    self.num,
                    self.sha,
                    #self.submitter.decode('ascii', errors='ignore'),
                    self.submitter,
                    opened_str,
                    closed_str,
                    self.package,
                    self.version,
                ))

    def is_up_to_date(self, rfsnum, rfstext):
        textsha = rfsparse.hash(rfstext)
        return self.sha == textsha

class Dist(Base):
    __tablename__ = "Dist"

    id = alch.Column(alch.Integer, primary_key = True, unique = True, autoincrement = True)
    name = alch.Column(alch.String)
    arch = alch.Column(alch.String)
    sha = alch.Column(alch.String)

    def __repr__(self):
        return(u"Dist<id='%d',name='%s', arch='%s', sha='%s'>" % (self.id, self.name, self.arch, self.sha))

class Package(Base):
    __tablename__ = "Package"

    id = alch.Column(alch.Integer, primary_key = True, unique = True, autoincrement = True)
    distid = alch.Column(alch.Integer)
    name = alch.Column(alch.String, index = True)
    ver = alch.Column(alch.String)

    def __repr__(Base):
        return(u"Package<id='%d',distid='%d',name='%s', ver='%s'>" % (self.id, self.distid, self.name, self.ver))


def process_rfs(db, rfsnum, rfstext):

    session = db()
    newrfslist = []
    commentlist = []

    try:
        rfs = session.query(RFS).filter_by(num = rfsnum)[0]
    except IndexError:
        rfs = RFS()
        session.add(rfs)

    if not rfs.is_up_to_date(rfsnum, rfstext):

        rfs.sha = rfsparse.hash(rfstext)

        rfs_params = rfsparse.get_rfs_params(rfsnum, rfstext)
        for param in rfs_params:
            rfs.__dict__[param] = rfs_params[param]

        newrfslist.append(rfsnum)

        for commenttext in rfsparse.commentgen(rfstext):

            params = rfsparse.get_comment_params(rfsnum, rfs, commenttext)
            comment = Comment(**params)
            #comment.process_comment(rfsnum, rfs, commenttext)

            commentlist.append(comment)

    for rfsn in newrfslist:
        session.query(Comment).filter_by(num = rfsn).delete()

    session.add_all(commentlist)
    session.commit()

def update_rfs_list(db):
    for rfsnum in rfsparse.RFSList():

        print "Processing ", rfsnum

        rfstext = rfsfetch.get_rfs_text(rfsnum)

        process_rfs(db, rfsnum, rfstext)

def update_package_lists(db):
    session = db()

    for dist in session.query(Dist).all():
        pkgtext = rfsfetch.get_package_text(dist.name, dist.arch)

        textsha = rfsparse.hash(pkgtext)
        if dist.sha != textsha:
            session.query(Package).filter_by(distid = dist.id).delete()
            session.commit()

            dist.sha = textsha

            for (pkg, ver) in rfsparse.pkgiter(pkgtext):
                session.add(Package(distid=dist.id, name=pkg, ver=ver))
                session.commit()

def init_db(db_file = 'sqlite:///rfsstats.db'):

    db = alch.create_engine(db_file)
    db.echo = False

    Base.metadata.create_all(db)

    Session = sessionmaker(bind=db)

    session = Session()
    for dist in ['unstable', 'experimental']:
        for arch in ['amd64']:
            if not session.query(Dist).filter_by(name=dist, arch=arch).count():
                session.add(Dist(name=dist, arch=arch))

    session.commit()

    return(Session)

def opened_between(db, start = datetime.datetime(1970, 1, 1), end = datetime.datetime(2038, 1, 1)):
    session = db()

    matches = session.query(RFS).filter(alch.and_(RFS.opened >= start, RFS.opened < end) )

    return matches

def closed_between(db, start = datetime.datetime(1970, 1, 1), end = datetime.datetime(2038, 1, 1)):
    session = db()

    matches = session.query(RFS).filter(alch.and_(RFS.closed >= start, RFS.closed < end) )

    return matches

def open_on(db, thedate):
    session = db()

    matches = session.query(RFS).filter(alch.and_(RFS.opened < thedate),
                                                  alch.or_(RFS.closed == None, RFS.closed > thedate))

    return matches


def responses_between(db, start = datetime.datetime(1970, 1, 1), end = datetime.datetime(2038, 1, 1)):
    session = db()

    matches = session.query(Comment).filter(alch.and_(Comment.date >= start, Comment.date < end, Comment.response == True))

    return matches

def rfs_days_between(db, start = datetime.datetime(1970, 1, 1), end = datetime.datetime(2038, 1, 1)):
    session = db()

    if end > datetime.datetime.now():
        end = datetime.datetime.now()

    matches = session.query(RFS).filter(alch.and_(alch.or_(RFS.closed >= start, False), RFS.opened < end)).all()
    matches = session.query(RFS).all()

    sum = 0
    for rfs in matches:
        #rfsstart = datetime.datetime.strptime(rfs.opened,  "%Y-%m-%d %H:%M:%S")
        #rfsend = datetime.datetime.strptime(rfs.closed,  "%Y-%m-%d %H:%M:%S")

        if rfs.closed != None:
            a = min(end, rfs.closed)
        else:
            a = end
        b = max(start, rfs.opened)
        c = a - b
        if c.total_seconds() > 0:
            sum += c.total_seconds()
       # sum += min(end, rfs.closed) - max(start, rfs.opened)
    #rfs_dur = sum([min(end, x.closed) - max(start, x.opened) for x in matches])

    return(sum / 86400.0)

def rfs_state(db, rfsnum):
    session = db()

    rfs = session.query(RFS).filter(RFS.num == rfsnum).one()

    if rfs.closed == None:
        return "open"

    pkgs = session.query(Package).filter(Package.name == rfs.package)

    if not rfs.version:
        return "accepted"

    if pkgs.count() == 0:
#        print rfs.package, rfs.version, "dropped"
        return "dropped"

    if 'bpo' in rfs.version:
        return "accepted"

    if all([LooseVersion(x.ver) < LooseVersion(rfs.version) for x in pkgs]):
#        print rfs.package, rfs.version, "dropped"
        return "dropped"
    else:
        return "accepted"
