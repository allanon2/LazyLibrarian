import shutil, os, datetime, urllib, urllib2, threading

from urllib import FancyURLopener

import lazylibrarian

from lazylibrarian import database, logger, formatter

def processDir():
    # rename this thread
    threading.currentThread().name = "POSTPROCESS"

    processpath = lazylibrarian.DOWNLOAD_DIR
    downloads = os.listdir(processpath)
    myDB = database.DBConnection()
    snatched = myDB.select('SELECT * from wanted WHERE Status="Snatched"')

    if snatched is None:
        logger.info('No books are snatched. Nothing to process.')
    elif downloads is None:
        logger.info('No downloads are found. Nothing to process.')
    else:
        ppcount=0
        for book in snatched:
            if book['NZBtitle'] in downloads:
                pp_path = os.path.join(processpath, book['NZBtitle'])
                logger.info('Found folder %s.' % pp_path)

                data = myDB.select("SELECT * from books WHERE BookID='%s'" % book['BookID'])
                if data:
                    for metadata in data:
                        authorname = metadata['AuthorName']
                        authorimg = metadata['AuthorLink']
                        bookname = metadata['BookName']
                        bookdesc = metadata['BookDesc']
                        bookisbn = metadata['BookIsbn']
                        bookrate = metadata['BookRate']
                        bookimg = metadata['BookImg']
                        bookpage = metadata['BookPages']
                        booklink = metadata['BookLink']
                        bookdate = metadata['BookDate']
                        booklang = metadata['BookLang']
                        bookpub = metadata['BookPub']

                    #Default destination path, should be allowed change per config file.
                    dest_path = lazylibrarian.EBOOK_DEST_FOLDER.replace('$Author', authorname).replace('$Title', bookname)
                    #dest_path = authorname+'/'+bookname
                    global_name = lazylibrarian.EBOOK_DEST_FILE.replace('$Author', authorname).replace('$Title', bookname)
                    #global_name = bookname + ' - ' + authorname
                else:
                    data = myDB.select("SELECT * from magazines WHERE Title='%s'" % book['BookID'])
                    for metadata in data:
                        title = metadata['Title']
                    #AuxInfo was added for magazine release date, normally housed in 'magazines' but if multiple
                    #files are downloading, there will be an error in post-processing, trying to go to the 
                    #same directory.
                    dest_path = lazylibrarian.MAG_DEST_FOLDER.replace('$IssueDate', book['AuxInfo']).replace('$Title', title)
                    #dest_path = '_Magazines/'+title+'/'+book['AuxInfo']
                    authorname = None
                    bookname = None
                    global_name = lazylibrarian.MAG_DEST_FILE.replace('$IssueDate', book['AuxInfo']).replace('$Title', title)
                    #global_name = book['AuxInfo']+' - '+title
               
                dic = {'<':'', '>':'', '=':'', '?':'', '"':'', ',':'', '*':'', ':':'', ';':''}
                dest_path = formatter.latinToAscii(formatter.replace_all(dest_path, dic))
                dest_path = os.path.join(lazylibrarian.DESTINATION_DIR, dest_path).encode(lazylibrarian.SYS_ENCODING)  

                #Remove all extra files before sending to destination (non ePub, mobi, PDF)                
                for root, dirs, files in os.walk(pp_path):
                    for filename in files:
                        source = os.path.realpath(os.path.join(root, filename))
                        destination = os.path.join(pp_path, filename)
                        if filename.endswith('.pdf'):
                            shutil.move(source,destination)
                            new_name = global_name + '.pdf'
                            new_loc = os.path.join(pp_path,new_name)
                            os.rename(destination, new_loc)
                        elif filename.endswith('.mobi'):
                            shutil.move(source,destination)
                            new_name = global_name + '.mobi'
                            new_loc = os.path.join(pp_path,new_name)
                            os.rename(destination, new_loc)
                        elif filename.endswith('.epub'):
                            shutil.move(source,destination)
                            new_name = global_name + '.epub'
                            new_loc = os.path.join(pp_path,new_name)
                            os.rename(destination, new_loc)
                        else:
                            os.remove(source)

                #now that everything is moved, let's delete empty directories
                for root, dirs, files in os.walk(pp_path, topdown=False):
                    for directory in dirs:
                        os.rmdir(os.path.join(root, directory))


                processBook = processDestination(pp_path, dest_path, authorname, bookname)

                if processBook:

                    ppcount = ppcount+1

                    #update nzbs
                    controlValueDict = {"NZBurl": book['NZBurl']}
                    newValueDict = {"Status": "Success"}
                    myDB.upsert("wanted", newValueDict, controlValueDict)

                    # try image
                    if bookname is not None:
                        processIMG(dest_path, bookimg, global_name)

                        # try metadata
                        processOPF(dest_path, authorname, bookname, bookisbn, book['BookID'], bookpub, bookdate, bookdesc, booklang, global_name)

                        #update books
                        controlValueDict = {"BookID": book['BookID']}
                        newValueDict = {"Status": "Have"}
                        myDB.upsert("books", newValueDict, controlValueDict)

                        #update authors
                        query = 'SELECT COUNT(*) FROM books WHERE AuthorName="%s" AND Status="Have"' % authorname
                        countbooks = myDB.action(query).fetchone()
                        havebooks = int(countbooks[0])
                        controlValueDict = {"AuthorName": authorname}
                        newValueDict = {"HaveBooks": havebooks}
                        author_query = 'SELECT * FROM authors WHERE AuthorName="%s"' % authorname
                        countauthor = myDB.action(author_query).fetchone()
                        if countauthor:
                            myDB.upsert("authors", newValueDict, controlValueDict)

                    logger.info('Successfully processed: %s' % global_name)
                else:
                    logger.info('Postprocessing for %s has failed.' % global_name)
        if ppcount:
            logger.info('%s items are downloaded and processed.' % ppcount)

def processDestination(pp_path=None, dest_path=None, authorname=None, bookname=None):

    if not os.path.exists(dest_path):
        logger.info('%s does not exist, so it\'s safe to create it' % dest_path)
        try:
            if lazylibrarian.DESTINATION_COPY:
                shutil.copytree(pp_path, dest_path)
                logger.info('Successfully copied %s to %s.' % (pp_path, dest_path))
            else:
                shutil.move(pp_path, dest_path)
                logger.info('Successfully moved %s to %s.' % (pp_path, dest_path))
            pp = True

        except OSError:
            logger.error('Could not create destinationfolder. Check permissions of: ' + lazylibrarian.DESTINATION_DIR)
            pp = False
    else:
        logger.error('Destination Folder %s exists.  Processing aborted.' % lazylibrarian.DESTINATION_DIR)
        pp = False
    return pp

def processIMG(dest_path=None, bookimg=None, global_name=None):
    #handle pictures
    try:
        if not bookimg == 'images/nocover.png':
            logger.info('Downloading cover from ' + bookimg)
            coverpath = os.path.join(dest_path, global_name+'.jpg')
            img = open(coverpath,'wb')
            imggoogle = imgGoogle()
            img.write(imggoogle.open(bookimg).read())
            img.close()

    except (IOError, EOFError), e:
        logger.error('Error fetching cover from url: %s, %s' % (bookimg, e))

def processOPF(dest_path=None, authorname=None, bookname=None, bookisbn=None, bookid=None, bookpub=None, bookdate=None, bookdesc=None, booklang=None, global_name=None):
    opfinfo = '<?xml version="1.0"  encoding="UTF-8"?>\n\
<package version="2.0" xmlns="http://www.idpf.org/2007/opf" >\n\
    <metadata xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:opf="http://www.idpf.org/2007/opf">\n\
        <dc:title>%s</dc:title>\n\
        <creator>%s</creator>\n\
        <dc:language>%s</dc:language>\n\
        <dc:identifier scheme="GoogleBooks">%s</dc:identifier>\n' % (bookname, authorname, booklang, bookid)

    if bookisbn:
        opfinfo += '        <dc:identifier scheme="ISBN">%s</dc:identifier>\n' % bookisbn

    if bookpub:
        opfinfo += '        <dc:publisher>%s</dc:publisher>\n' % bookpub

    if bookdate:
        opfinfo += '        <dc:date>%s</dc:date>\n' % bookdate

    if bookdesc:
        opfinfo += '        <dc:description>%s</dc:description>\n' % bookdesc

    opfinfo += '        <guide>\n\
            <reference href="cover.jpg" type="cover" title="Cover"/>\n\
        </guide>\n\
    </metadata>\n\
</package>'

    dic = {'...':'', ' & ':' ', ' = ': ' ', '$':'s', ' + ':' ', ',':'', '*':''}

    opfinfo = formatter.latinToAscii(formatter.replace_all(opfinfo, dic))

    #handle metadata
    opfpath = os.path.join(dest_path, global_name+'.opf')
    if not os.path.exists(opfpath):
        opf = open(opfpath, 'wb')
        opf.write(opfinfo)
        opf.close()
        logger.info('Saved metadata to: ' + opfpath)
    else:
        logger.info('%s allready exists. Did not create one.' % opfpath)

class imgGoogle(FancyURLopener):
    # Hack because Google wants a user agent for downloading images, which is stupid because it's so easy to circumvent.
    version = 'Mozilla/5.0 (X11; U; Linux i686) Gecko/20071127 Firefox/2.0.0.11'

