import time, threading, urllib, urllib2, os, re

from xml.etree import ElementTree
from xml.etree.ElementTree import Element, SubElement

import lazylibrarian

from lazylibrarian import logger, database, formatter, providers, sabnzbd

def searchbook(books=None):

    # rename this thread
    threading.currentThread().name = "SEARCHBOOKS"
    myDB = database.DBConnection()
    searchlist = []

    if books is None:
        searchbooks = myDB.select('SELECT BookID, AuthorName, Bookname from books WHERE Status="Wanted"')
        searchmags = myDB.select('SELECT Title, Frequency, LastAcquired from magazines WHERE Status="Active"')
    else:
        searchbooks = []
        for book in books:
            searchbook = myDB.select('SELECT BookID, AuthorName, BookName from books WHERE BookID=? AND Status="Wanted"', [book['bookid']])
            for terms in searchbook:
                searchbooks.append(terms)
        searchmags = []

    for searchbook in searchbooks:
        bookid = searchbook[0]
        author = searchbook[1]
        book = searchbook[2]

        dic = {'...':'', ' & ':' ', ' = ': ' ', '?':'', '$':'s', ' + ':' ', '"':'', ',':'', '*':''}

        author = formatter.latinToAscii(formatter.replace_all(author, dic))
        book = formatter.latinToAscii(formatter.replace_all(book, dic))

        searchterm = author + ' ' + book
        searchterm = re.sub('[\.\-\/]', ' ', searchterm).encode('utf-8')
        searchlist.append({"bookid": bookid, "searchterm": searchterm})

    for searchmag in searchmags:
        bookid = searchmag[0]
        searchterm = searchmag[0]

        dic = {'...':'', ' & ':' ', ' = ': ' ', '?':'', '$':'s', ' + ':' ', '"':'', ',':'', '*':''}

        searchterm = formatter.latinToAscii(formatter.replace_all(searchterm, dic))
        searchterm = re.sub('[\.\-\/]', ' ', searchterm).encode('utf-8')
        searchlist.append({"bookid": bookid, "searchterm": searchterm})

        # if searchmag[2] is None:
        #     searchlist.append({"bookid": bookid, "searchterm": searchterm})
        # else:
        #     if searchmag[1] == "Weekly" and formatter.age(searchmag[2]) >=7:
        #         searchlist.append({"bookid": bookid, "searchterm": searchterm})
        #     if searchmag[1] == "BiWeekly" and formatter.age(searchmag[2]) >=14:
        #         searchlist.append({"bookid": bookid, "searchterm": searchterm})
        #     if searchmag[1] == "Monthly" and formatter.age(searchmag[2]) >=28:
        #         searchlist.append({"bookid": bookid, "searchterm": searchterm})
        #     if searchmag[1] == "Quarterly" and formatter.age(searchmag[2]) >=122:
        #         searchlist.append({"bookid": bookid, "searchterm": searchterm})
        #     if searchmag[1] == "SemiYearly" and formatter.age(searchmag[2]) >=182:
        #         searchlist.append({"bookid": bookid, "searchterm": searchterm})


    if not lazylibrarian.SAB_HOST and not lazylibrarian.BLACKHOLE:
        logger.info('No downloadmethod is set, use SABnzbd or blackhole')

    if not lazylibrarian.NEWZNAB:
        logger.info('No providers are set.')

    if searchlist == []:
        logger.info('There is nothing to search for.  Mark some items as wanted or active.')

    for book in searchlist:
        resultlist = []
        if lazylibrarian.NEWZNAB and not resultlist:
            logger.info('Searching NZB\'s at provider %s ...' % lazylibrarian.NEWZNAB_HOST)
            resultlist = providers.NewzNab(book)

        if lazylibrarian.NZBMATRIX and not resultlist:
            logger.info('Searching NZB at provider NZBMatrix ...')
            resultlist = providers.NZBMatrix(book)

        if not resultlist:
            logger.info("Search didn't have results. Adding book %s to queue." % book['searchterm'])

        else:
            for nzb in resultlist:
                bookid = nzb['bookid']
                nzbtitle = nzb['nzbtitle']
                nzburl = nzb['nzburl']
                nzbprov = nzb['nzbprov']
                nzbdate_temp = nzb['nzbdate']
                nzbdate = formatter.nzbdate2format(nzbdate_temp)

                controlValueDict = {"NZBurl": nzburl}
                newValueDict = {
                    "NZBprov": nzbprov,
                    "BookID": bookid,
                    "NZBdate": nzbdate,
                    "NZBtitle": nzbtitle,
                    "Status": "Skipped"
                    }
                myDB.upsert("wanted", newValueDict, controlValueDict)

                snatchedbooks = myDB.action('SELECT * from books WHERE BookID=? and Status="Snatched"', [bookid]).fetchone()
                if not snatchedbooks:
                    checkifmag = myDB.select('SELECT * from magazines WHERE Title=?', [bookid])
                    if checkifmag:
                        for results in checkifmag:
                            control_date = results['LastAcquired']
                        comp_date = formatter.datecompare(nzbdate, control_date)
                        if comp_date > 0:
                            myDB.upsert("magazines", {"LastAcquired": nzbdate}, {"Title": bookid})
                            snatch = DownloadMethod(bookid, nzbprov, nzbtitle, nzburl)
                        else:
                            logger.info('This issue of %s is old; skipping.' % bookid)
                    else:
                        snatch = DownloadMethod(bookid, nzbprov, nzbtitle, nzburl)                 
                time.sleep(1)

def DownloadMethod(bookid=None, nzbprov=None, nzbtitle=None, nzburl=None):

    myDB = database.DBConnection()

    if lazylibrarian.SAB_HOST and not lazylibrarian.BLACKHOLE:
        download = sabnzbd.SABnzbd(nzbtitle, nzburl)

    elif lazylibrarian.BLACKHOLE:

        try:
            nzbfile = urllib2.urlopen(nzburl, timeout=30).read()

        except urllib2.URLError, e:
            logger.warn('Error fetching nzb from url: ' + nzburl + ' %s' % e)

        nzbname = str.replace(nzbtitle, ' ', '_') + '.nzb'
        nzbpath = os.path.join(lazylibrarian.BLACKHOLEDIR, nzbname)

        try:
            f = open(nzbpath, 'w')
            f.write(nzbfile)
            f.close()
            logger.info('NZB file saved to: ' + nzbpath)
            download = True
        except Exception, e:
            logger.error('%s not writable, NZB not saved. Error: %s' % (nzbpath, e))
            download = False

    else:
        logger.error('No downloadmethod is enabled, check config.')
        return False

    if download:
        logger.info(u'Downloaded nzbfile @ <a href="%s">%s</a>' % (nzburl, lazylibrarian.NEWZNAB_HOST))
        myDB.action('UPDATE books SET status = "Snatched" WHERE BookID=?', [bookid])
        myDB.action('UPDATE wanted SET status = "Snatched" WHERE NZBurl=?', [nzburl])
    else:
        logger.error(u'Failed to download nzb @ <a href="%s">%s</a>' % (nzburl, lazylibrarian.NEWZNAB_HOST))
        myDB.action('UPDATE wanted SET status = "Failed" WHERE NZBurl=?', [nzburl])





