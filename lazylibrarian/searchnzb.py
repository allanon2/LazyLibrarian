import time, threading, urllib, urllib2, os, re

from xml.etree import ElementTree
from xml.etree.ElementTree import Element, SubElement

import lazylibrarian

from lazylibrarian import logger, database, formatter, providers, sabnzbd
from lazylibrarian import notifiers

#new to support torrents
from StringIO import StringIO
import gzip
import datetime

def parse_date (title):

    logger.info("Trying to parse [%s]" % title)

    search_strings = [r'(?P<Day>\d+)\s+(?P<Month>January|February|March|April|May|June|July|August|September|October|November|December)\s+(?P<Year>\d{4})', \
                      r'\s(?P<Month>January|February|March|April|May|June|July|August|September|October|November|December)\s+(?P<Day>\d+)\s+(?P<Year>\d{4})', \
                      r'\s(?P<Month>January|February|March|April|May|June|July|August|September|October|November|December)\s+(?P<Year>\d{4})']

    Year = ''
    Day = ''
    Month = ''
    for regex in search_strings:
        match = re.search(regex, title)
        if match:
            Year = match.group('Year')
            Month = match.group('Month')
            try:
                Day = match.group('Day')
            except:
                Day = '01'
                
            print "MATCHED " + Day + " " + Month + " " + Year
            break


    if Year == '':
        print "NO MATCH"
        
    return (Year, Month, Day)
        


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

    if not lazylibrarian.NEWZNAB and not lazylibrarian.KAT and not lazylibrarian.BIBLIOTIK and not lazylibrarian.MYANONAMOUSE:
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

        if lazylibrarian.BIBLIOTIK and not resultlist:
            logger.info('Searching Torrents at provider Bibliotik ...')
            resultlist = providers.Bibliotik(book)

        if lazylibrarian.MYANONAMOUSE and not resultlist:
            logger.info('Searching Torrents at provider MyAnonaMouse ...')
            resultlist = providers.MyAnonaMouse(book)

        if lazylibrarian.KAT and not resultlist:
            logger.info('Searching Torrents at provider KAT ...')
            resultlist = providers.KAT(book)

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
                # al - not setting torrent date yet, so this will be blank
                try:
                    nzbdate = formatter.nzbdate2format(nzbdate_temp)
                except:
                    nzbdate = ''

                checkifmag = myDB.select('SELECT * from magazines WHERE Title=?', [bookid])
                if checkifmag:
                    for results in checkifmag:
                        control_date = results['IssueDate']
                        frequency = results['Frequency']
                        regex = results['Regex']

                    nzbtitle_formatted = nzb['nzbtitle'].replace('.',' ').replace('/',' ').replace('+',' ').replace('_',' ').replace('-',' ').replace('(',' ').replace(')',' ').replace('.',' ')
                    nzbtitle_exploded = nzbtitle_formatted.split(' ')
                    logger.info(nzbtitle_formatted)

                    (regexA_year, regexA_month_temp, regexA_day) = parse_date (nzbtitle_formatted)
                    regexA_month = formatter.month2num(regexA_month_temp)
                    
                    if frequency != "Weekly" and frequency != "BiWeekly":
                        regexA_day = '01'

                    logger.info('Year = %s, Month = %s, Day = %s' % (regexA_year, regexA_month, regexA_day))
                    newdatish_regexA = regexA_year+regexA_month+regexA_day

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
                    if keyword_check == nzbtitle_formatted:
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
                        logger.info('Compared [%s] to [%s]' % (keyword_check, nzbtitle_formatted))
                       
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
                        title_formatted = nzbtitle.replace('.',' ').replace('/',' ').replace('+',' ').replace('_',' ')
                        notifiers.notify_snatch(title_formatted+' at '+formatter.now())                 

                time.sleep(1)


def DownloadMethod(bookid=None, nzbprov=None, nzbtitle=None, nzburl=None):

    myDB = database.DBConnection()

    if lazylibrarian.SAB_HOST and not lazylibrarian.BLACKHOLE:
        download = sabnzbd.SABnzbd(nzbtitle, nzburl)

    elif lazylibrarian.BLACKHOLE:

        if nzbprov == 'KAT' or nzbprov == 'Bibliotik' or nzbprov == "MyAnonamouse":

            request = urllib2.Request(nzburl)
            request.add_header('Accept-encoding', 'gzip')
    
            if nzbprov == 'KAT':
                request.add_header('Referer', 'http://kat.ph/')
        
            response = urllib2.urlopen(request)
            if response.info().get('Content-Encoding') == 'gzip':
                buf = StringIO(response.read())
                f = gzip.GzipFile(fileobj=buf)
                torrent = f.read()
            else:
                torrent = response.read()

            nzbname = str.replace(str(nzbtitle), ' ', '_') + '.torrent'
            nzbpath = os.path.join(lazylibrarian.BLACKHOLEDIR, nzbname)

            torrent_file = open(nzbpath , 'wb')
            torrent_file.write(torrent)
            torrent_file.close()
            logger.info('Torrent file saved: %s' % nzbtitle)
            download = True
        else:
                
            
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



