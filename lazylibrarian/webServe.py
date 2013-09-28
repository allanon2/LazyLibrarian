import os, cherrypy, urllib

from mako.template import Template
from mako.lookup import TemplateLookup
from mako import exceptions

import threading, time

import lazylibrarian

from lazylibrarian import logger, importer, database, postprocess, formatter
from lazylibrarian.searchnzb import searchbook
from lazylibrarian.formatter import checked
from lazylibrarian.gr import GoodReads
from lazylibrarian.gb import GoogleBooks


def serve_template(templatename, **kwargs):

    interface_dir = os.path.join(str(lazylibrarian.PROG_DIR), 'data/interfaces/')
    template_dir = os.path.join(str(interface_dir), lazylibrarian.HTTP_LOOK)

    _hplookup = TemplateLookup(directories=[template_dir])

    try:
        template = _hplookup.get_template(templatename)
        return template.render(**kwargs)
    except:
        return exceptions.html_error_template().render()


class WebInterface(object):

    def index(self):
        raise cherrypy.HTTPRedirect("home")
    index.exposed=True

    def home(self):
        myDB = database.DBConnection()
        authors = myDB.select('SELECT * from authors order by AuthorName COLLATE NOCASE')
        return serve_template(templatename="index.html", title="Home", authors=authors)
    home.exposed = True

    def books(self, BookLang=None, BookID=None):
        myDB = database.DBConnection()

        languages = myDB.select('SELECT DISTINCT BookLang from books WHERE NOT STATUS="Skipped" AND NOT Status="Ignored"')

        if BookLang:
            books = myDB.select('SELECT * from books WHERE BookLang=? AND NOT Status="Skipped" AND NOT Status="Ignored"', [BookLang])
        elif BookID:
            time.sleep(2.0)
            books = myDB.select('SELECT * from books WHERE BookID=?', [BookID])
            # start searchthreads
            book_search = []
            book_search.append({"bookid": BookID})
            threading.Thread(target=searchbook, args=[book_search]).start()
        else:
            books = myDB.select('SELECT * from books WHERE NOT STATUS="Skipped" AND NOT Status="Ignored"')

        if books is None:
            raise cherrypy.HTTPRedirect("books")
        return serve_template(templatename="books.html", title='Books', books=books, languages=languages, bookid=BookID)
    books.exposed = True

    def magazines(self):
        myDB = database.DBConnection()

        magazines = myDB.select('SELECT * from magazines')

        if magazines is None:
            raise cherrypy.HTTPRedirect("magazines")
        return serve_template(templatename="magazines.html", title="Magazines", magazines=magazines)
    magazines.exposed = True

    def wanted(self):
        myDB = database.DBConnection()

        wanted = myDB.select('SELECT * from wanted')

        if wanted is None:
            raise cherrypy.HTTPRedirect("wanted")
        return serve_template(templatename="wanted.html", title="Wanted", wanted=wanted)
    wanted.exposed = True

    def config(self):
        http_look_dir = os.path.join(lazylibrarian.PROG_DIR, 'data/interfaces/')
        http_look_list = [ name for name in os.listdir(http_look_dir) if os.path.isdir(os.path.join(http_look_dir, name)) ]

        config = {
                    "http_host":        lazylibrarian.HTTP_HOST,
                    "http_user":        lazylibrarian.HTTP_USER,
                    "http_port":        lazylibrarian.HTTP_PORT,
                    "http_pass":        lazylibrarian.HTTP_PASS,
                    "http_look":        lazylibrarian.HTTP_LOOK,
                    "http_look_list":   http_look_list,
                    "launch_browser":   checked(lazylibrarian.LAUNCH_BROWSER),
                    "logdir" :          lazylibrarian.LOGDIR,
                    "use_imp_onlyisbn": checked(lazylibrarian.IMP_ONLYISBN),
                    "imp_preflang":     lazylibrarian.IMP_PREFLANG,
                    "sab_host":         lazylibrarian.SAB_HOST,
                    "sab_port":         lazylibrarian.SAB_PORT,
                    "sab_api":          lazylibrarian.SAB_API,
                    "sab_user":         lazylibrarian.SAB_USER,
                    "sab_pass":         lazylibrarian.SAB_PASS,
                    "use_destination_copy": checked(lazylibrarian.DESTINATION_COPY),
                    "destination_dir":  lazylibrarian.DESTINATION_DIR,
                    "download_dir":     lazylibrarian.DOWNLOAD_DIR,
                    "sab_cat":          lazylibrarian.SAB_CAT,
                    "usenet_retention": lazylibrarian.USENET_RETENTION,
                    "use_blackhole":    checked(lazylibrarian.BLACKHOLE),
                    "blackholedir":     lazylibrarian.BLACKHOLEDIR,
                    "use_nzbmatrix" :   checked(lazylibrarian.NZBMATRIX),
                    "nzbmatrix_user" :  lazylibrarian.NZBMATRIX_USER,
                    "nzbmatrix_api" :   lazylibrarian.NZBMATRIX_API,
                    "use_newznab" :     checked(lazylibrarian.NEWZNAB),
                    "newznab_host" :    lazylibrarian.NEWZNAB_HOST,
                    "newznab_api" :     lazylibrarian.NEWZNAB_API,
                    "use_newzbin" :     checked(lazylibrarian.NEWZBIN),
                    "newzbin_uid" :     lazylibrarian.NEWZBIN_UID,
                    "newzbin_pass" :    lazylibrarian.NEWZBIN_PASS,
                }
        return serve_template(templatename="config.html", title="Settings", config=config)    
    config.exposed = True

    def configUpdate(self, http_host='0.0.0.0', http_user=None, http_port=5299, http_pass=None, http_look=None, launch_browser=0, logdir=None, imp_onlyisbn=0, imp_preflang=None,
        sab_host=None, sab_port=None, sab_api=None, sab_user=None, sab_pass=None, destination_copy=0, destination_dir=None, download_dir=None, sab_cat=None, usenet_retention=None, blackhole=0, blackholedir=None,
        nzbmatrix=0, nzbmatrix_user=None, nzbmatrix_api=None, newznab=0, newznab_host=None, newznab_api=None, newzbin=0, newzbin_uid=None, newzbin_pass=None):

        lazylibrarian.HTTP_HOST = http_host
        lazylibrarian.HTTP_PORT = http_port
        lazylibrarian.HTTP_USER = http_user
        lazylibrarian.HTTP_PASS = http_pass
        lazylibrarian.HTTP_LOOK = http_look
        lazylibrarian.LAUNCH_BROWSER = launch_browser
        lazylibrarian.LOGDIR = logdir

        lazylibrarian.IMP_ONLYISBN = imp_onlyisbn
        lazylibrarian.IMP_PREFLANG = imp_preflang

        lazylibrarian.SAB_HOST = sab_host
        lazylibrarian.SAB_PORT = sab_port
        lazylibrarian.SAB_API = sab_api
        lazylibrarian.SAB_USER = sab_user
        lazylibrarian.SAB_PASS = sab_pass
        lazylibrarian.SAB_CAT = sab_cat

        lazylibrarian.DESTINATION_COPY = destination_copy
        lazylibrarian.DESTINATION_DIR = destination_dir
        lazylibrarian.DOWNLOAD_DIR = download_dir
        lazylibrarian.USENET_RETENTION = usenet_retention
        lazylibrarian.BLACKHOLE = blackhole
        lazylibrarian.BLACKHOLEDIR = blackholedir

        lazylibrarian.NZBMATRIX = nzbmatrix
        lazylibrarian.NZBMATRIX_USER = nzbmatrix_user
        lazylibrarian.NZBMATRIX_API = nzbmatrix_api

        lazylibrarian.NEWZNAB = newznab
        lazylibrarian.NEWZNAB_HOST = newznab_host
        lazylibrarian.NEWZNAB_API = newznab_api

        lazylibrarian.NEWZBIN = newzbin
        lazylibrarian.NEWZBIN_UID = newzbin_uid
        lazylibrarian.NEWZBIN_PASS = newzbin_pass

        lazylibrarian.config_write()

        raise cherrypy.HTTPRedirect("config")

    configUpdate.exposed = True

#SEARCH
    def search(self, name, type):
        GB = GoogleBooks(name, type)
        if len(name) == 0:
            raise cherrypy.HTTPRedirect("config")
        else:
            searchresults = GB.find_results()
        return serve_template(templatename="searchresults.html", title='Search Results for: "' + name + '"', searchresults=searchresults, type=type)
    search.exposed = True

#AUTHOR
    def authorPage(self, AuthorName, BookLang=None):
        myDB = database.DBConnection()

        languages = myDB.select('SELECT DISTINCT BookLang from books WHERE AuthorName=?', [AuthorName.replace("'","''")])

        if BookLang:
            querybooks = "SELECT * from books WHERE BookLang='%s' AND AuthorName='%s' AND NOT Status='Ignored' order by BookName ASC" % (BookLang, AuthorName.replace("'","''"))
        else:
            querybooks = "SELECT * from books WHERE AuthorName='%s' AND NOT Status='Ignored' order by BookName ASC" % AuthorName.replace("'","''")

        queryauthors = "SELECT * from authors WHERE AuthorName='%s'" % AuthorName.replace("'","''")

        author = myDB.action(queryauthors).fetchone()
        books = myDB.select(querybooks)
        if author is None:
            raise cherrypy.HTTPRedirect("home")
        return serve_template(templatename="author.html", title=author['AuthorName'], author=author, books=books, languages=languages)
    authorPage.exposed = True

    def pauseAuthor(self, AuthorID, AuthorName):
        logger.info(u"Pausing author: " + AuthorID)
        myDB = database.DBConnection()
        controlValueDict = {'AuthorID': AuthorID}
        newValueDict = {'Status': 'Paused'}
        myDB.upsert("authors", newValueDict, controlValueDict)
        raise cherrypy.HTTPRedirect("authorPage?AuthorName=%s" % AuthorName)
    pauseAuthor.exposed = True

    def resumeAuthor(self, AuthorID, AuthorName):
        logger.info(u"Resuming author: " + AuthorID)
        myDB = database.DBConnection()
        controlValueDict = {'AuthorID': AuthorID}
        newValueDict = {'Status': 'Active'}
        myDB.upsert("authors", newValueDict, controlValueDict)
        raise cherrypy.HTTPRedirect("authorPage?AuthorName=%s" % AuthorName)
    resumeAuthor.exposed = True

    def deleteAuthor(self, AuthorID):
        logger.info(u"Removing author: " + AuthorID)
        myDB = database.DBConnection()
        myDB.action('DELETE from authors WHERE AuthorID=?', [AuthorID])
        myDB.action('DELETE from books WHERE NOT Status="Have" AND NOT Status="Downloaded" AND NOT Status="Wanted" AND AuthorID=?', [AuthorID])
        raise cherrypy.HTTPRedirect("home")
    deleteAuthor.exposed = True

    def refreshAuthor(self, AuthorID, AuthorName):
        importer.addAuthorToDB(AuthorName)
        raise cherrypy.HTTPRedirect("authorPage?AuthorName=%s" % AuthorName)
    refreshAuthor.exposed=True

    def addResults(self, action=None, **args):
        for arg in args:
            if not arg == 'book_table_length':
                name = arg.split('&')
                authorname = name[0]
                bookid = name[1]

                if action == 'author':
                    threading.Thread(target=importer.addAuthorToDB, args=[authorname]).start()
                    raise cherrypy.HTTPRedirect("authorPage?AuthorName=%s" % authorname)
                elif action == 'book':
                    threading.Thread(target=importer.addBookToDB, args=[bookid, authorname]).start()
                    raise cherrypy.HTTPRedirect("books?BookID=%s" %bookid)
                else:
                    logger.info('Oops, a bug')

    addResults.exposed = True

    def addKeyword(self, type=None, title=None, frequency=None, **args):
        myDB = database.DBConnection()
        if type == 'magazine':
            if len(title) == 0:
                raise cherrypy.HTTPRedirect("config")
            else:
                controlValueDict = {"Title": title}
                newValueDict = {
                    "Frequency":   frequency,
                    "Regex":   None,
                    "Status":       "Active",
                    "MagazineAdded":    formatter.today(),
                    }
                myDB.upsert("magazines", newValueDict, controlValueDict)
                raise cherrypy.HTTPRedirect("magazines")
    addKeyword.exposed = True

#BOOKS

    def markBooks(self, AuthorName=None, action=None, **args):
        myDB = database.DBConnection()
        for bookid in args:
            # ouch dirty workaround...
            if not bookid == 'book_table_length':

                controlValueDict = {'BookID': bookid}
                newValueDict = {'Status': action}
                myDB.upsert("books", newValueDict, controlValueDict)
                logger.info('Status set to %s for BookID: %s' % (action, bookid))

                if AuthorName is not None:
                    authorname = AuthorName
                else:
                    find_author = myDB.action('SELECT AuthorName FROM books WHERE BookID="%s"' % bookid).fetchone()
                    authorname = find_author['AuthorName']
                if action == "Ignored":
                    lastbook = myDB.action("SELECT BookName, BookLink, BookDate from books WHERE AuthorName='%s' AND NOT Status='Ignored' order by BookDate DESC" % authorname.replace("'","''")).fetchone()
                    totalbooknum = myDB.action("SELECT TotalBooks, HaveBooks from authors WHERE AuthorName='%s'" % authorname.replace("'","''")).fetchone()
                    bookscount = int(totalbooknum['TotalBooks']) - 1
                    query = 'SELECT COUNT(*) FROM books WHERE AuthorName="%s" AND Status="Have"' % authorname
                    countbooks = myDB.action(query).fetchone()
                    havebooks = int(countbooks[0])    
                    controlValueDict = {"AuthorName": authorname}
                    newValueDict = {
                        "TotalBooks": bookscount,
                        "HaveBooks": havebooks,
                        "LastBook": lastbook['BookName'],
                        "LastLink": lastbook['BookLink'],
                        "LastDate": lastbook['BookDate']
                        }
                    myDB.upsert("authors", newValueDict, controlValueDict)
                else:
                    query = 'SELECT COUNT(*) FROM books WHERE AuthorName="%s" AND Status="Have"' % authorname
                    countbooks = myDB.action(query).fetchone()
                    havebooks = int(countbooks[0])
                    check_author = 'SELECT * FROM authors WHERE AuthorName="%s"' % authorname
                    dbauthor = myDB.action(check_author).fetchone()
                    controlValueDict = {"AuthorName": authorname}
                    newValueDict = {
                        "HaveBooks": havebooks,
                        }
                    if dbauthor is not None:
                        myDB.upsert("authors", newValueDict, controlValueDict)

        # start searchthreads
        books = []
        for bookid in args:
            # ouch dirty workaround...
            if not bookid == 'book_table_length':
                if action == 'Wanted':
                    books.append({"bookid": bookid})

        threading.Thread(target=searchbook, args=[books]).start()
        if AuthorName:
            raise cherrypy.HTTPRedirect("authorPage?AuthorName=%s" % AuthorName)
        else:
            raise cherrypy.HTTPRedirect("books")
    markBooks.exposed = True

    def markMagazines(self, action=None, **args):
        myDB = database.DBConnection()
        for title in args:
            # ouch dirty workaround...
            if not title == 'book_table_length':
                if action != "Delete":
                    controlValueDict = {"Title": title}
                    newValueDict = {
                        "Status":       action,
                        }
                    myDB.upsert("magazines", newValueDict, controlValueDict)
                    logger.info('Status of magazine %s changed to %s' % (title, action))
                else:
                    myDB.action('DELETE from magazines WHERE Title=?', [title])
                    logger.info('Magazine %s removed from database' % title)
                raise cherrypy.HTTPRedirect("magazines")
    markMagazines.exposed = True

    def markWanted(self, action=None, **args):
        myDB = database.DBConnection()
        #I think I need to consolidate bookid in args to unique values...
        for nzbtitle in args:
            if not nzbtitle == 'book_table_length':
                if action != "Delete":
                    controlValueDict = {"NZBtitle": nzbtitle}
                    newValueDict = {
                        "Status":       action,
                        }
                    myDB.upsert("wanted", newValueDict, controlValueDict)
                    logger.info('Status of wanted item %s changed to %s' % (nzbtitle, action))
                else:
                    myDB.action('DELETE from wanted WHERE NZBtitle=?', [nzbtitle])
                    logger.info('Item %s removed from wanted' % bookid)
                raise cherrypy.HTTPRedirect("wanted")
    markWanted.exposed = True

    def updateRegex(self, action=None, title=None):
        myDB = database.DBConnection()
        controlValueDict = {"Title": title}
        newValueDict = {
            "Regex":       action,
            }
        myDB.upsert("magazines", newValueDict, controlValueDict)
        raise cherrypy.HTTPRedirect("magazines")
    updateRegex.exposed = True

    def forceSearch(self):
        threading.Thread(target=searchbook).start()
        logger.info('Forcing NZB Search for Wanted Items')
        raise cherrypy.HTTPRedirect("books")
    forceSearch.exposed = True

    def forceProcess(self):
        threading.Thread(target=postprocess.processDir).start()
        logger.info('Forcing Post-Process of Items in Download Directory')
        raise cherrypy.HTTPRedirect("books")
    forceProcess.exposed = True

    def logs(self):
        return serve_template(templatename="logs.html", title="Log", lineList=lazylibrarian.LOGLIST)
    logs.exposed = True

    def shutdown(self):
        lazylibrarian.config_write()
        lazylibrarian.SIGNAL = 'shutdown'
        message = 'closing ...'
        return serve_template(templatename="shutdown.html", title="Close library", message=message, timer=15)
        return page
    shutdown.exposed = True

    def restart(self):
        lazylibrarian.SIGNAL = 'restart'
        message = 'reopening ...'
        return serve_template(templatename="shutdown.html", title="Reopen library", message=message, timer=30)
    restart.exposed = True
