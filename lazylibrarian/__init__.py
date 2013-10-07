from __future__ import with_statement

import os, sys, subprocess, threading, cherrypy, webbrowser, sqlite3

import datetime

from lib.configobj import ConfigObj
from lib.apscheduler.scheduler import Scheduler

import threading

from lazylibrarian import logger, postprocess, searchnzb

FULL_PATH = None
PROG_DIR = None

ARGS = None
SIGNAL = None

LOGLEVEL = 1
DAEMON = False
PIDFILE = None

SYS_ENCODING = None

SCHED = Scheduler()

INIT_LOCK = threading.Lock()
__INITIALIZED__ = False
started = False

DATADIR = None
DBFILE=None
CONFIGFILE = None
CFG = None

LOGDIR = None
LOGLIST = []

HTTP_HOST = None
HTTP_PORT = None
HTTP_USER = None
HTTP_PASS = None
HTTP_ROOT = None
HTTP_LOOK = None
LAUNCH_BROWSER = False

SAB_HOST = None
SAB_PORT = None
SAB_USER = None
SAB_PASS = None
SAB_API = None
SAB_CAT = None

DESTINATION_COPY = False
DESTINATION_DIR = None
DOWNLOAD_DIR = None
BLACKHOLE = False
BLACKHOLEDIR = None
USENET_RETENTION = None

IMP_PREFLANG = 'en'
IMP_ONLYISBN = False

GR_API = 'ckvsiSDsuqh7omh74ZZ6Q'

NZBMATRIX = False
NZBMATRIX_USER = None
NZBMATRIX_API = None

NEWZNAB = False
NEWZNAB_HOST = None
NEWZNAB_API = None

NEWZBIN = False
NEWZBIN_UID = None
NEWZBIN_PASSWORD = None

KAT = False

BIBLIOTIK = False
BIBLIOTIK_USER = None
BIBLIOTIK_PASS = None

MYANONAMOUSE = False
MYANONAMOUSE_USER = None
MYANONAMOUSE_PASS = None

SEARCH_INTERVAL = 360
SCAN_INTERVAL = 10

EBOOK_DEST_FOLDER = '$Author/$Title'
EBOOK_DEST_FILE = '$Title - $Author'
MAG_DEST_FOLDER = '_Magazines/$Title/$IssueDate'
MAG_DEST_FILE = '$IssueDate - $Title'

USE_TWITTER = False
TWITTER_NOTIFY_ONSNATCH = False
TWITTER_NOTIFY_ONDOWNLOAD = False
TWITTER_USERNAME = None
TWITTER_PASSWORD = None
TWITTER_PREFIX = 'LazyLibrarian'

def CheckSection(sec):
    """ Check if INI section exists, if not create it """
    try:
        CFG[sec]
        return True
    except:
        CFG[sec] = {}
        return False

#################################################################################
## Check_setting_int                                                            #
#################################################################################
#def minimax(val, low, high):
#    """ Return value forced within range """
#    try:
#        val = int(val)
#    except:
#        val = 0
#    if val < low:
#        return low
#    if val > high:
#        return high
#    return val

################################################################################
# Check_setting_int                                                            #
################################################################################
def check_setting_int(config, cfg_name, item_name, def_val):
    try:
        my_val = int(config[cfg_name][item_name])
    except:
        my_val = def_val
        try:
            config[cfg_name][item_name] = my_val
        except:
            config[cfg_name] = {}
            config[cfg_name][item_name] = my_val
    logger.debug(item_name + " -> " + str(my_val))
    return my_val

#################################################################################
## Check_setting_float                                                          #
#################################################################################
##def check_setting_float(config, cfg_name, item_name, def_val):
##    try:
##        my_val = float(config[cfg_name][item_name])
##    except:
##        my_val = def_val
##        try:
##            config[cfg_name][item_name] = my_val
##        except:
##            config[cfg_name] = {}
##            config[cfg_name][item_name] = my_val

##    return my_val

################################################################################
# Check_setting_str                                                            #
################################################################################
def check_setting_str(config, cfg_name, item_name, def_val, log=True):
    try:
        my_val = config[cfg_name][item_name]
    except:
        my_val = def_val
        try:
            config[cfg_name][item_name] = my_val
        except:
            config[cfg_name] = {}
            config[cfg_name][item_name] = my_val

    if log:
        logger.debug(item_name + " -> " + my_val)
    else:
        logger.debug(item_name + " -> ******")

    return my_val

def initialize():

    with INIT_LOCK:

        global __INITIALIZED__, FULL_PATH, PROG_DIR, LOGLEVEL, DAEMON, DATADIR, CONFIGFILE, CFG, LOGDIR, HTTP_HOST, HTTP_PORT, HTTP_USER, HTTP_PASS, HTTP_ROOT, HTTP_LOOK, LAUNCH_BROWSER, LOGDIR, CACHEDIR, \
            IMP_ONLYISBN, IMP_PREFLANG, SAB_HOST, SAB_PORT, SAB_API, SAB_USER, SAB_PASS, DESTINATION_DIR, DESTINATION_COPY, DOWNLOAD_DIR, SAB_CAT, USENET_RETENTION, BLACKHOLE, BLACKHOLEDIR, GR_API, \
            NZBMATRIX, NZBMATRIX_USER, NZBMATRIX_API, NEWZNAB, NEWZNAB_HOST, NEWZNAB_API, NEWZBIN, NEWZBIN_UID, NEWZBIN_PASS, SEARCH_INTERVAL, SCAN_INTERVAL, EBOOK_DEST_FOLDER, EBOOK_DEST_FILE, \
            MAG_DEST_FOLDER, MAG_DEST_FILE, USE_TWITTER, TWITTER_NOTIFY_ONSNATCH, TWITTER_NOTIFY_ONDOWNLOAD, TWITTER_USERNAME, TWITTER_PASSWORD, TWITTER_PREFIX, KAT, BIBLIOTIK, BIBLIOTIK_USER, BIBLIOTIK_PASS, \
            MYANONAMOUSE, MYANONAMOUSE_USER, MYANONAMOUSE_PASS

        if __INITIALIZED__:
            return False

        CheckSection('General')
        CheckSection('SABnzbd')

        try:
            HTTP_PORT = check_setting_int(CFG, 'General', 'http_port', 5299)
        except:
            HTTP_PORT = 5299

        if HTTP_PORT < 21 or HTTP_PORT > 65535:
            HTTP_PORT = 5299

        HTTP_HOST = check_setting_str(CFG, 'General', 'http_host', '0.0.0.0')
        HTTP_USER = check_setting_str(CFG, 'General', 'http_user', '')
        HTTP_PASS = check_setting_str(CFG, 'General', 'http_pass', '')
        HTTP_ROOT = check_setting_str(CFG, 'General', 'http_root', '')
        HTTP_LOOK = check_setting_str(CFG, 'General', 'http_look', 'default')

        LAUNCH_BROWSER = bool(check_setting_int(CFG, 'General', 'launch_browser', 1))
        LOGDIR = check_setting_str(CFG, 'General', 'logdir', '')

        IMP_PREFLANG = check_setting_str(CFG, 'General', 'imp_preflang', IMP_PREFLANG)
        IMP_ONLYISBN = bool(check_setting_int(CFG, 'General', 'imp_onlyisbn', 0))

        SAB_HOST = check_setting_str(CFG, 'SABnzbd', 'sab_host', '')
        SAB_PORT = check_setting_str(CFG, 'SABnzbd', 'sab_port', '')
        SAB_USER = check_setting_str(CFG, 'SABnzbd', 'sab_user', '')
        SAB_PASS = check_setting_str(CFG, 'SABnzbd', 'sab_pass', '')
        SAB_API = check_setting_str(CFG, 'SABnzbd', 'sab_api', '')
        SAB_CAT = check_setting_str(CFG, 'SABnzbd', 'sab_cat', '')


        DESTINATION_COPY = bool(check_setting_int(CFG, 'General', 'destination_copy', 0))
        DESTINATION_DIR = check_setting_str(CFG, 'General','destination_dir', '')
        DOWNLOAD_DIR = check_setting_str(CFG, 'General', 'download_dir', '')
        BLACKHOLE = bool(check_setting_int(CFG, 'General', 'blackhole', 0))
        BLACKHOLEDIR = check_setting_str(CFG, 'General', 'blackholedir', '')
        USENET_RETENTION = check_setting_str(CFG, 'General', 'usenet_retention', '')

        NZBMATRIX = bool(check_setting_int(CFG, 'NZBMatrix', 'nzbmatrix', 0))
        NZBMATRIX_USER = check_setting_str(CFG, 'NZBMatrix', 'nzbmatrix_user', '')
        NZBMATRIX_API = check_setting_str(CFG, 'NZBMatrix', 'nzbmatrix_api', '')
        
        NEWZNAB = bool(check_setting_int(CFG, 'Newznab', 'newznab', 0))
        NEWZNAB_HOST = check_setting_str(CFG, 'Newznab', 'newznab_host', '')
        NEWZNAB_API = check_setting_str(CFG, 'Newznab', 'newznab_api', '')

        NEWZBIN = bool(check_setting_int(CFG, 'Newzbin', 'newzbin', 0))
        NEWZBIN_UID = check_setting_str(CFG, 'Newzbin', 'newzbin_uid', '')
        NEWZBIN_PASS = check_setting_str(CFG, 'Newzbin', 'newzbin_pass', '')

        KAT = bool(check_setting_int(CFG, 'KAT', 'kat', 0))

        BIBLIOTIK = bool(check_setting_int(CFG, 'Bibliotik', 'bibliotik', 0))
        BIBLIOTIK_USER = check_setting_str(CFG, 'Bibliotik', 'bibliotik_user', '')
        BIBLIOTIK_PASS = check_setting_str(CFG, 'Bibliotik', 'bibliotik_pass', '')

        MYANONAMOUSE = bool(check_setting_int(CFG, 'MyAnonamouse', 'myanonamouse', 0))
        MYANONAMOUSE_USER = check_setting_str(CFG, 'MyAnonamouse', 'myanonamouse_user', '')
        MYANONAMOUSE_PASS = check_setting_str(CFG, 'MyAnonamouse', 'myanonamouse_pass', '')

        SEARCH_INTERVAL = int(check_setting_str(CFG, 'SearchScan', 'search_interval', '360'))
        SCAN_INTERVAL = int(check_setting_str(CFG, 'SearchScan', 'scan_interval', '10'))

        EBOOK_DEST_FOLDER = check_setting_str(CFG, 'PostProcess', 'ebook_dest_folder', '$Author/$Title')
        EBOOK_DEST_FILE = check_setting_str(CFG, 'PostProcess', 'ebook_dest_file', '$Title - $Author')
        MAG_DEST_FOLDER = check_setting_str(CFG, 'PostProcess', 'mag_dest_folder', '_Magazines/$Title/$IssueDate')
        MAG_DEST_FILE = check_setting_str(CFG, 'PostProcess', 'mag_dest_file', '$IssueDate - $Title')

        USE_TWITTER = bool(check_setting_int(CFG, 'Twitter', 'use_twitter', 0))
        TWITTER_NOTIFY_ONSNATCH = bool(check_setting_int(CFG, 'Twitter', 'twitter_notify_onsnatch', 0))
        TWITTER_NOTIFY_ONDOWNLOAD = bool(check_setting_int(CFG, 'Twitter', 'twitter_notify_ondownload', 0))
        TWITTER_USERNAME = check_setting_str(CFG, 'Twitter', 'twitter_username', '')
        TWITTER_PASSWORD = check_setting_str(CFG, 'Twitter', 'twitter_password', '')
        TWITTER_PREFIX = check_setting_str(CFG, 'Twitter', 'twitter_prefix', 'LazyLibrarian')


        if not LOGDIR:
            LOGDIR = os.path.join(DATADIR, 'Logs')

        # Put the cache dir in the data dir for now
        CACHEDIR = os.path.join(DATADIR, 'cache')
        if not os.path.exists(CACHEDIR):
            try:
                os.makedirs(CACHEDIR)
            except OSError:
                logger.error('Could not create cachedir. Check permissions of: ' + DATADIR)

        # Create logdir
        if not os.path.exists(LOGDIR):
            try:
                os.makedirs(LOGDIR)
            except OSError:
                if LOGLEVEL:
                    print LOGDIR + ":"
                    print ' Unable to create folder for logs. Only logging to console.'

        # Start the logger, silence console logging if we need to
        logger.lazylibrarian_log.initLogger(loglevel=LOGLEVEL)

        # Initialize the database
        try:
            dbcheck()
        except Exception, e:
            logger.error("Can't connect to the database: %s" % e)

        __INITIALIZED__ = True
        return True

def daemonize():
    """
    Fork off as a daemon
    """

    # Make a non-session-leader child process
    try:
        pid = os.fork() #@UndefinedVariable - only available in UNIX
        if pid != 0:
            sys.exit(0)
    except OSError, e:
        raise RuntimeError("1st fork failed: %s [%d]" %
                   (e.strerror, e.errno))

    os.setsid() #@UndefinedVariable - only available in UNIX

    # Make sure I can read my own files and shut out others
    prev = os.umask(0)
    os.umask(prev and int('077', 8))

    # Make the child a session-leader by detaching from the terminal
    try:
        pid = os.fork() #@UndefinedVariable - only available in UNIX
        if pid != 0:
            sys.exit(0)
    except OSError, e:
        raise RuntimeError("2st fork failed: %s [%d]" %
                   (e.strerror, e.errno))

    dev_null = file('/dev/null', 'r')
    os.dup2(dev_null.fileno(), sys.stdin.fileno())

    if PIDFILE:
        pid = str(os.getpid())
        logger.debug(u"Writing PID " + pid + " to " + str(PIDFILE))
        file(PIDFILE, 'w').write("%s\n" % pid)

def launch_browser(host, port, root):
    if host == '0.0.0.0':
        host = 'localhost'

    try:
        webbrowser.open('http://%s:%i%s' % (host, port, root))
    except Exception, e:
        logger.error('Could not launch browser: %s' % e)

def config_write():
    new_config = ConfigObj()
    new_config.filename = CONFIGFILE

    new_config['General'] = {}
    new_config['General']['http_port'] = HTTP_PORT
    new_config['General']['http_host'] = HTTP_HOST
    new_config['General']['http_user'] = HTTP_USER
    new_config['General']['http_pass'] = HTTP_PASS
    new_config['General']['http_root'] = HTTP_ROOT
    new_config['General']['http_look'] = HTTP_LOOK
    new_config['General']['launch_browser'] = int(LAUNCH_BROWSER)
    new_config['General']['logdir'] = LOGDIR

    new_config['General']['imp_onlyisbn'] = int(IMP_ONLYISBN)
    new_config['General']['imp_preflang'] = IMP_PREFLANG

    new_config['SABnzbd'] = {}
    new_config['SABnzbd']['sab_host'] = SAB_HOST
    new_config['SABnzbd']['sab_port'] = SAB_PORT
    new_config['SABnzbd']['sab_user'] = SAB_USER
    new_config['SABnzbd']['sab_pass'] = SAB_PASS
    new_config['SABnzbd']['sab_api'] = SAB_API
    new_config['SABnzbd']['sab_cat'] = SAB_CAT

    new_config['General']['destination_dir'] = DESTINATION_DIR
    new_config['General']['destination_copy'] = int(DESTINATION_COPY)
    new_config['General']['download_dir'] = DOWNLOAD_DIR
    new_config['General']['blackhole'] = int(BLACKHOLE)
    new_config['General']['blackholedir'] = BLACKHOLEDIR
    new_config['General']['usenet_retention'] = USENET_RETENTION

    new_config['NZBMatrix'] = {}
    new_config['NZBMatrix']['nzbmatrix'] = int(NZBMATRIX)
    new_config['NZBMatrix']['nzbmatrix_user'] = NZBMATRIX_USER
    new_config['NZBMatrix']['nzbmatrix_api'] = NZBMATRIX_API

    new_config['Newznab'] = {}
    new_config['Newznab']['newznab'] = int(NEWZNAB)
    new_config['Newznab']['newznab_host'] = NEWZNAB_HOST
    new_config['Newznab']['newznab_api'] = NEWZNAB_API

    new_config['Newzbin'] = {}
    new_config['Newzbin']['newzbin'] = int(NEWZBIN)
    new_config['Newzbin']['newzbin_uid'] = NEWZBIN_UID
    new_config['Newzbin']['newzbin_pass'] = NEWZBIN_PASS

    new_config['KAT'] = {}
    new_config['KAT']['kat'] = int(KAT)

    new_config['Bibliotik'] = {}
    new_config['Bibliotik']['bibliotik'] = int(BIBLIOTIK)
    new_config['Bibliotik']['bibliotik_user'] = BIBLIOTIK_USER
    new_config['Bibliotik']['bibliotik_pass'] = BIBLIOTIK_PASS

    new_config['MyAnonamouse'] = {}
    new_config['MyAnonamouse']['myanonamouse'] = int(MYANONAMOUSE)
    new_config['MyAnonamouse']['myanonamouse_user'] = MYANONAMOUSE_USER
    new_config['MyAnonamouse']['myanonamouse_pass'] = MYANONAMOUSE_PASS

    new_config['SearchScan'] = {}
    new_config['SearchScan']['search_interval'] = SEARCH_INTERVAL
    new_config['SearchScan']['scan_interval'] = SCAN_INTERVAL

    new_config['PostProcess'] = {}
    new_config['PostProcess']['ebook_dest_folder'] = EBOOK_DEST_FOLDER
    new_config['PostProcess']['ebook_dest_file'] = EBOOK_DEST_FILE
    new_config['PostProcess']['mag_dest_folder'] = MAG_DEST_FOLDER
    new_config['PostProcess']['mag_dest_file'] = MAG_DEST_FILE

    new_config['Twitter'] = {}
    new_config['Twitter']['use_twitter'] = int(USE_TWITTER)
    new_config['Twitter']['twitter_notify_onsnatch'] = int(TWITTER_NOTIFY_ONSNATCH)
    new_config['Twitter']['twitter_notify_ondownload'] = int(TWITTER_NOTIFY_ONDOWNLOAD)
    new_config['Twitter']['twitter_username'] = TWITTER_USERNAME
    new_config['Twitter']['twitter_password'] = TWITTER_PASSWORD
    new_config['Twitter']['twitter_prefix'] = TWITTER_PREFIX

    new_config.write()

def dbcheck():

    conn=sqlite3.connect(DBFILE)
    c=conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS authors (AuthorID TEXT, AuthorName TEXT UNIQUE, AuthorImg TEXT, AuthorLink TEXT, DateAdded TEXT, Status TEXT, LastBook TEXT, LastLink Text, LastDate TEXT, HaveBooks INTEGER, TotalBooks INTEGER, AuthorBorn TEXT, AuthorDeath TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS books (AuthorID TEXT, AuthorName TEXT, AuthorLink TEXT, BookName TEXT, BookSub TEXT, BookDesc TEXT, BookGenre TEXT, BookIsbn TEXT, BookPub TEXT, BookRate INTEGER, BookImg TEXT, BookPages INTEGER, BookLink TEXT, BookID TEXT UNIQUE, BookDate TEXT, BookLang TEXT, BookAdded TEXT, Status TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS wanted (BookID TEXT, NZBurl TEXT, NZBtitle TEXT, NZBdate TEXT, NZBprov TEXT, Status TEXT, NZBsize TEXT, AuxInfo TEXT)')
    c.execute('CREATE TABLE IF NOT EXISTS magazines (Title TEXT, Frequency TEXT, Regex TEXT, Status TEXT, MagazineAdded TEXT, LastAcquired TEXT, IssueDate TEXT)')

    try:
        logger.info('Checking database')
        c.execute('SELECT BookSub from books')
    except sqlite3.OperationalError:
        logger.info('Updating database to hold book subtitles.')
        c.execute('ALTER TABLE books ADD COLUMN BookSub TEXT')

    try:
        c.execute('SELECT BookPub from books')
    except sqlite3.OperationalError:
        logger.info('Updating database to hold book publisher')
        c.execute('ALTER TABLE books ADD COLUMN BookPub TEXT')

    try:
        c.execute('SELECT BookGenre from books')
    except sqlite3.OperationalError:
        logger.info('Updating database to hold bookgenre')
        c.execute('ALTER TABLE books ADD COLUMN BookGenre TEXT')

    try:
        c.execute('SELECT IssueDate from magazines')
    except sqlite3.OperationalError:
        logger.info('Updating database to hold issuedate')
        c.execute('ALTER TABLE magazines ADD COLUMN IssueDate TEXT')

    try:
        c.execute('SELECT AuxInfo from wanted')
    except sqlite3.OperationalError:
        logger.info('Updating database to hold AuxInfo')
        c.execute('ALTER TABLE wanted ADD COLUMN AuxInfo TEXT')

    try:
        c.execute('SELECT NZBsize from wanted')
    except sqlite3.OperationalError:
        logger.info('Updating database to hold NZBside')
        c.execute('ALTER TABLE wanted ADD COLUMN NZBsize TEXT')

    conn.commit()
    c.close()

def start():
    global __INITIALIZED__, started

    if __INITIALIZED__:

        # Crons and scheduled jobs go here
        starttime = datetime.datetime.now()
        #SCHED.add_interval_job(postprocess.processDir, minutes=SCAN_INTERVAL, start_date=starttime+datetime.timedelta(minutes=1))
        #SCHED.add_interval_job(searchnzb.searchbook, minutes=SEARCH_INTERVAL, start_date=starttime+datetime.timedelta(minutes=2))
        SCHED.add_interval_job(postprocess.processDir, minutes=SCAN_INTERVAL)
        SCHED.add_interval_job(searchnzb.searchbook, minutes=SEARCH_INTERVAL)

        SCHED.start()
#        for job in SCHED.get_jobs():
#            print job
        started = True

def shutdown(restart=False):
    config_write()
    logger.info('LazyLibrarian is shutting down ...')
    cherrypy.engine.exit()

    SCHED.shutdown(wait=True)

    if PIDFILE :
        logger.info('Removing pidfile %s' % PIDFILE)
        os.remove(PIDFILE)

    if restart:
        logger.info('LazyLibrarian is restarting ...')
        popen_list = [sys.executable, FULL_PATH]
        popen_list += ARGS
        if '--nolaunch' not in popen_list:
            popen_list += ['--nolaunch']
            logger.info('Restarting LazyLibrarian with ' + str(popen_list))
        subprocess.Popen(popen_list, cwd=os.getcwd())

    os._exit(0)
