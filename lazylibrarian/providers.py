import time, threading, urllib, urllib2, re

from xml.etree import ElementTree

import lazylibrarian

from lazylibrarian import logger

#new libraries to support torrents
import lib.feedparser as feedparser
from bs4 import BeautifulSoup
import cookielib
import socket
import urlparse


def url_fix(s, charset='utf-8'):
    if isinstance(s, unicode):
        s = s.encode(charset, 'ignore')
    scheme, netloc, path, qs, anchor = urlparse.urlsplit(s)
    path = urllib.quote(path, '/%')
    qs = urllib.quote_plus(qs, ':&=')
    return urlparse.urlunsplit((scheme, netloc, path, qs, anchor))

def MyAnonaMouse(book=None):
    #Login and very basic parser for MyAnonamouse

    #Cookies

    socket.setdefaulttimeout(10)

    #Cookies
    cookies = cookielib.CookieJar()
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookies))
    urllib2.install_opener(opener)

    ck = cookielib.Cookie(version=0, name='userZone', value='-660', port=None, port_specified=False, domain='www.myanonamouse.net', domain_specified=False, domain_initial_dot=False, path='/', path_specified=True, secure=False, expires=2147483647, discard=False, comment=None, comment_url=None, rest={'HttpOnly': None}, rfc2109=False)

    cookies.set_cookie(ck)

    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookies))
    urllib2.install_opener(opener)

    url = "http://www.myanonamouse.net/"

    html = ''

    handle = opener.open(url)

    logger.info ("Fetching MyAnonamouse Mainpage")


    html = handle.read()

    opener.addheaders = [{
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:18.0) Gecko/20100101 Firefox/18.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Content-Type': 'application/x-www-form-urlencoded',
        'Referer': 'http://www.myanonamouse.net/login.php?',

    }]

    USERNAME = lazylibrarian.MYANONAMOUSE_USER
    PASSWORD = lazylibrarian.MYANONAMOUSE_PASS

    values = {
                                               'username': USERNAME,
                                               'password': PASSWORD,}

    data = urllib.urlencode(values)
    data = data.encode('utf-8')

    url = "http://www.myanonamouse.net/takelogin.php"

    logger.info ("Logging into MyAnonamouse")

    html = ''

    handle = opener.open(url, data)

    html = handle.read()
        
    login_headers =  {
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:18.0) Gecko/20100101 Firefox/18.0',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Content-Type': 'application/x-www-form-urlencoded',
       
    }

        
    url = "http://www.myanonamouse.net/browse.php?search=&subcat=0&cat=63&incldead=1&srch=0"

    html = ''

    req = urllib2.Request(url)

    handle = urllib.urlopen(req)

    html = handle.read()

    logger.info ("Fetching MyAnonamouse Fantasy EBooks")

    soup = BeautifulSoup(html)

    results = ''

    titles = soup.find_all('td', {'class':'row2', 'align':'left'})

    tables = soup.find_all('table', {'width':'100%', 'cellspacing':"1", 'class':"coltable"})

    upload_dates = []

    for t in tables:
        for row in t.findAll("tr"):
            for cell in row.findAll("td"):
                inner_cells = cell.findAll("td")
                try:
                    if (inner_cells[3].contents[0] is not None):
                        upload_dates.append(inner_cells[3].contents[0])
                except:
                    continue



    logging.info (upload_dates)
    k = -1

    for title in titles:
        k = k + 1
        upload_date = upload_dates[k]
        if not date_in_range (upload_date):
            continue

        items = title.findAll('a')
        item = items[0]
        print (item)

        logger.info ('Grabbing data for ' + item['title'])
        
        #logger.info (title.contents)
        #logger.info (title.contents[0])
        
        link = 'http://www.myanonamouse.net/' + item['href']
     
        logger.info ('Grabbing data for ' + item['title'])
        for i in range(100):
            try:
                resp = opener.open(link)
                test = resp.read()
                break
            except:
                logger.info ("Failed to load page. Retrying.")

        soup = BeautifulSoup(test, "html.parser" )


        #torrents = soup.find_all('a', {'class':"index"})

        #torrent = "<a href=\"http://www.myanonamouse.net/"+torrents[0]['href']+"\">Torrent</a>"

       

def Bibliotik(book=None):

    #Login and very basic parser for Bibliotik

    socket.setdefaulttimeout(10)

    #Cookies
    cookies = cookielib.CookieJar()
    opener = urllib2.build_opener(urllib2.HTTPCookieProcessor(cookies))
    urllib2.install_opener(opener)

    USERNAME = lazylibrarian.BIBLIOTIK_USER
    PASSWORD = lazylibrarian.BIBLIOTIK_PASS

    #Authenticate user
    print ("Logging into Bibliotik.org")
    url = "http://bibliotik.org/login?returnto=%2F"

    values = {"username" : USERNAME, 
              "password" : PASSWORD,
              "keeplogged" : "1" }

    data = urllib.urlencode(values)
    data = data.encode('utf-8')

    resp = opener.open(url, data)

    providerurl = url_fix("http://bibliotik.org/torrents/?search=" + book['searchterm'] + "&cat%5B%5D=5&orderby=added&order=desc")
    
    resp = opener.open(providerurl)

    data = resp.read()
    results = []
    if data:
        # to debug because of api
        logger.debug(u'Parsing results from <a href="%s">%s</a>' % (providerurl, 'Bibliotik'))

        logger.info ("Executing bs4\n")
        soup = BeautifulSoup(data)
    
        titles = soup.find_all('span', {'class':"title"})    
        torrentcount = 0
        for title in titles:
            try:
                torrentcount = torrentcount + 1
                myTitle = str(title.contents[0])
                myTitle = myTitle[47:]
                myLen =(len(myTitle))
                myTitle = myTitle[:(myLen-4)]
                logger.info (myTitle)

                results.append({
                    'bookid': book['bookid'],
                    'nzbprov': "Bibliotik",
                    'nzbtitle': myTitle,
                    'nzburl': title.contents[0]['href'],
                    'nzbdate': '',
                    'nzbsize': '',
                    })
            except:
                logger.info('No results')
                
        if torrentcount:
            logger.info('Found %s torrents for: %s' % (torrentcount, book['searchterm']))
        else:
            logger.info('Bibliotik returned 0 results for: ' + book['searchterm'])

    return results

def KAT(book=None):


    provider = "KAT"
    providerurl = url_fix("http://www.kat.ph/search/" + book['searchterm'])

    params = {   
                "categories[0]": "books",
                "field": "seeders",
                "sorder": "desc",
                "rss": "1"
              }
    searchURL = providerurl + "/?%s" % urllib.urlencode(params)

    try:
        data = urllib2.urlopen(searchURL, timeout=20)
    except urllib2.URLError, e:
        logger.warn('Error fetching data from %s: %s' % (provider, e))
        data = False
        
    results = []
    
    if data:

        logger.info(u'Parsing results from <a href="%s">KAT</a>' % searchURL)
        
        d = feedparser.parse(data)
        
        
        if not len(d.entries):
            logger.info(u"No results found from %s for %s" % (provider, book['searchterm']))
            pass
        
        else:
            for item in d.entries:
                try:
                    rightformat = True
                    title = item['title']
                    seeders = item['torrent_seeds']
                    url = item['links'][1]['href']
                    size = int(item['links'][1]['length'])
                    
                    
                    results.append({
                        'bookid': book['bookid'],
                        'nzbprov': "KAT",
                        'nzbtitle': title,
                        'nzburl': url,
                        'nzbdate': '',
                        'nzbsize': str(size),
                        })

                    logger.info('Found %s. Size: %s' % (title, size))
                
                except Exception, e:
                    logger.error(u"An unknown error occurred in the KAT parser: %s" % e)

    return results


def NewzNab(book=None):

    HOST = lazylibrarian.NEWZNAB_HOST
    results = []

    logger.info('Searching for %s.' % book['searchterm'])
    params = {
        "t": "search",
        "apikey": lazylibrarian.NEWZNAB_API,
        "cat": 7020,
        "q": book['searchterm']
        }

    if not str(HOST)[:4] == "http":
        HOST = 'http://' + HOST

    URL = HOST + '/api?' + urllib.urlencode(params)

    try:
        data = ElementTree.parse(urllib2.urlopen(URL, timeout=30))
    except (urllib2.URLError, IOError, EOFError), e:
        logger.warn('Error fetching data from %s: %s' % (lazylibrarian.NEWZNAB_HOST, e))
        data = None

    if data:
        # to debug because of api
        logger.debug(u'Parsing results from <a href="%s">%s</a>' % (URL, lazylibrarian.NEWZNAB_HOST))
        rootxml = data.getroot()
        resultxml = rootxml.getiterator('item')
        nzbcount = 0
        for nzb in resultxml:
            try:
                nzbcount = nzbcount+1
                results.append({
                    'bookid': book['bookid'],
                    'nzbprov': "NewzNab",
                    'nzbtitle': nzb[0].text,
                    'nzburl': nzb[2].text,
                    'nzbdate': nzb[4].text,
                    'nzbsize': nzb[7].attrib.get('length')
                    })
            except IndexError:
                logger.info('No results')
        if nzbcount:
            logger.info('Found %s nzb for: %s' % (nzbcount, book['searchterm']))
        else:
            logger.info('Newznab returned 0 results for: ' + book['searchterm'])
    return results

def NZBMatrix(book=None):

    results = []

    params = {
        "page": "download",
        "username": lazylibrarian.NZBMATRIX_USER,
        "apikey": lazylibrarian.NZBMATRIX_API,
        "subcat": 36,
        "age": lazylibrarian.USENET_RETENTION,
        "term": book['searchterm']
        }

    URL = "http://rss.nzbmatrix.com/rss.php?" + urllib.urlencode(params)
    # to debug because of api
    logger.debug(u'Parsing results from <a href="%s">NZBMatrix</a>' % (URL))

    try:
        data = ElementTree.parse(urllib2.urlopen(URL, timeout=30))
    except (urllib2.URLError, IOError, EOFError), e:
        logger.warn('Error fetching data from NZBMatrix: %s' % e)
        data = None

    if data:
        rootxml = data.getroot()
        resultxml = rootxml.getiterator('item')
        nzbcount = 0
        for nzb in resultxml:
            try:
                results.append({
                    'bookid': book['bookid'],
                    'nzbprov': "NZBMatrix",
                    'nzbtitle': nzb[0].text,
                    'nzburl': nzb[2].text,
                    'nzbsize': nzb[7].attrib.get('length')
                    })
                nzbcount = nzbcount+1
            except IndexError:
                logger.info('No results')

        if nzbcount:
            logger.info('Found %s nzb for: %s' % (nzbcount, book['searchterm']))
        else:
            logger.info('NZBMatrix returned 0 results for: ' + book['searchterm'])
    return results
