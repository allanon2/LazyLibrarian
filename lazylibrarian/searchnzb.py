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
        searchmags = myDB.select('SELECT Title, Frequency, LastAcquired, IssueDate from magazines WHERE Status="Active"')
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
        frequency = searchmag[1]
        last_acquired = searchmag[2]
        issue_date = searchmag[3]

        dic = {'...':'', ' & ':' ', ' = ': ' ', '?':'', '$':'s', ' + ':' ', '"':'', ',':'', '*':''}

        searchterm = formatter.latinToAscii(formatter.replace_all(searchterm, dic))
        searchterm = re.sub('[\.\-\/]', ' ', searchterm).encode('utf-8')
        searchlist.append({"bookid": bookid, "searchterm": searchterm})

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
                nzbsize_temp = nzb['nzbsize']
                nzbsize = str(round(float(nzbsize_temp) / 1048576,2))+' MB'
                nzbdate = formatter.nzbdate2format(nzbdate_temp)

                checkifmag = myDB.select('SELECT * from magazines WHERE Title=?', [bookid])
                if checkifmag:
                    for results in checkifmag:
                        control_date = results['IssueDate']
                        frequency = results['Frequency']
                        regex = results['Regex']

                    nzbtitle_formatted = nzb['nzbtitle'].replace('.',' ')
                    nzbtitle_exploded = nzbtitle_formatted.split(' ')
                    #IF ANYTHING GOES WRONG IT HAS TO DO WITH NZB TITLE LENGTHS
                    #if len(nzbtitle_exploded) > 1:
                    #regexA = DD MonthName YYYY
                    regexA_year = nzbtitle_exploded[len(nzbtitle_exploded)-1]
                    regexA_month_temp = nzbtitle_exploded[len(nzbtitle_exploded)-2]
                    regexA_month = formatter.month2num(regexA_month_temp)
                    #regexB = YYYY-MM
                    #regexB_last = nzbtitle_exploded[len(nzbtitle_exploded)-1]
                    #regexB_exploded = regexB_last.split('-')
                    #regexB_year = regexB_exploded[0]
                    #regexB_month = regexB_exploded[1].zfill(2)
                    #regexC = MonthName DD YYYY
                    #regexC_year = nzbtitle_exploded[len(nzbtitle_exploded)-1]
                    #regexC_month_temp = nzbtitle_exploded[len(nzbtitle_exploded)-3]
                    #regexC_month = formatter.month2num(regexA_month_temp)

                    if frequency == "Weekly" or frequency == "BiWeekly":
                        regexA_day = nzbtitle_exploded[len(nzbtitle_exploded)-3].zfill(2)
                        #regexC_day = nzbtitle_exploded[len(nzbtitle_exploded)-2].zfill(2)
                    else:
                        regexA_day = '01'
                        #regexB_day = '01'

                    newdatish_regexA = regexA_year+regexA_month+regexA_day
                    #newdatish_regexB = regexB_year+regexB_month+regexB_day
                    #newdatish_regexC = regexC_year+regexC_month+regexC_day

                    try:
                        int(newdatish_regexA)
                    except:
                        logger.info('NZB %s not in proper date format.' % nzbtitle_formatted)
                        continue

                    #Need to make sure that substrings of magazine titles don't get found (e.g. Maxim USA will find Maximum PC USA)
                    keyword_check = nzbtitle_formatted.replace(bookid,'')
                    #Don't want to overwrite status = Skipped for NZBs that have been previously found
                    wanted_status = myDB.select('SELECT * from wanted WHERE NZBtitle=?', [nzbtitle])
                    if wanted_status:
                        for results in wanted_status:
                            status = results['Status']
                    else:
                        status = "Skipped"
                    if keyword_check != nzbtitle_formatted:
                        newdatish = regexA_year+'-'+regexA_month+'-'+regexA_day
                        controlValueDict = {"NZBurl": nzburl}
                        newValueDict = {
                            "NZBprov": nzbprov,
                            "BookID": bookid,
                            "NZBdate": nzbdate,
                            "NZBtitle": nzbtitle,
                            "AuxInfo": newdatish,
                            "Status": status,
                            "NZBsize": nzbsize
                            }
                        myDB.upsert("wanted", newValueDict, controlValueDict)
                        print nzbtitle_formatted
                        print newdatish

                        if control_date is None:
                            myDB.upsert("magazines", {"LastAcquired": nzbdate, "IssueDate": newdatish}, {"Title": bookid})
                            snatch = DownloadMethod(bookid, nzbprov, nzbtitle, nzburl)
                        else:                          
                            comp_date = formatter.datecompare(newdatish, control_date)
                            if comp_date > 0:
                                myDB.upsert("magazines", {"LastAcquired": nzbdate, "IssueDate": newdatish}, {"Title": bookid})
                                snatch = DownloadMethod(bookid, nzbprov, nzbtitle, nzburl)
                            else:
                                logger.info('This issue of %s is old; skipping.' % nzbtitle_formatted)
                    else:
                        logger.info('NZB %s does not completely match search term %s.' % (nzbtitle, bookid))
                       
                else:
                    snatchedbooks = myDB.action('SELECT * from books WHERE BookID=? and Status="Snatched"', [bookid]).fetchone()
                    if not snatchedbooks:
                        controlValueDict = {"NZBurl": nzburl}
                        newValueDict = {
                            "NZBprov": nzbprov,
                            "BookID": bookid,
                            "NZBdate": nzbdate,
                            "NZBtitle": nzbtitle,
                            "NZBsize": nzbsize,
                            "Status": "Skipped"
                            }
                        myDB.upsert("wanted", newValueDict, controlValueDict)
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





