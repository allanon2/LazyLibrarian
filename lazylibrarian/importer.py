import time, os, threading

import lazylibrarian
from lazylibrarian import logger, formatter, database
from lazylibrarian.gr import GoodReads
from lazylibrarian.gb import GoogleBooks


def addBookToDB(bookid, authorname):
    threading.currentThread().name = "DBIMPORT"
    type = 'book'
    myDB = database.DBConnection()
    #GR = GoodReads(authorname, type)
    GB = GoogleBooks(bookid, type)

# process book
    #dbbook = myDB.action('SELECT * from books WHERE BookID=?', [bookid]).fetchone()
    #controlValueDict = {"BookID": bookid}

    #if dbbook is None:
    #    newValueDict = {
    #        "BookID":   "BookID: %s" % (bookid),
    #        "Status":       "Loading"
    #        }
    #else:
    #    newValueDict = {"Status": "Loading"}
    #myDB.upsert("books", newValueDict, controlValueDict)

    book = GB.find_book(bookid)

    if not book:
        logger.warn("Error fetching bookinfo for BookID: " + bookid)

    else:
        controlValueDict = {"BookID": book[0]['bookid']}
        newValueDict = {
            "AuthorName":   book[0]['authorname'],
            "BookName":     book[0]['bookname'],
            "BookDesc":     book[0]['bookdesc'],
            "BookIsbn":     book[0]['bookisbn'],
            "BookImg":      book[0]['bookimg'],
            "BookLink":     book[0]['booklink'],
            "BookRate":     book[0]['bookrate'],
            "BookPages":    book[0]['bookpages'],
            "BookDate":     book[0]['bookdate'],
            "BookLang":     book[0]['booklang'],
            "Status":       "Wanted",
            "BookAdded":    formatter.today()
            }

        myDB.upsert("books", newValueDict, controlValueDict)

# process author
    # dbauthor = myDB.action('SELECT * from authors WHERE AuthorName=?', book[0]['authorname']).fetchone()
    # controlValueDict = {"AuthorName": authorname}

    # if dbauthor is None:
    #     newValueDict = {
    #         "AuthorName":   "Authorname: %s" % (authorname),
    #         "Status":       "Loading"
    #         }
    # else:
    #     newValueDict = {"Status": "Loading"}

    # author = GR.find_author_id()

    # if not author:
    #     logger.warn("Error fetching authorinfo with name: " + authorname)

    # else:
    #     controlValueDict = {"AuthorName": authorname}
    #     newValueDict = {
    #         "AuthorID":     author['authorid'],
    #         "AuthorLink":   author['authorlink'],
    #         "AuthorImg":    author['authorimg'],
    #         "AuthorBorn":   author['authorborn'],
    #         "AuthorDeath":  author['authordeath'],
    #         "DateAdded":    formatter.today(),
    #         "Status":       "Loading"
    #         }
    #     myDB.upsert("authors", newValueDict, controlValueDict)

def addAuthorToDB(authorname=None):
    threading.currentThread().name = "DBIMPORT"
    type = 'author'
    myDB = database.DBConnection()

    GR = GoodReads(authorname, type)
    GB = GoogleBooks(authorname, type)
    

    query = "SELECT * from authors WHERE AuthorName='%s'" % authorname.replace("'","''")
    dbauthor = myDB.action(query).fetchone()
    controlValueDict = {"AuthorName": authorname}

    if dbauthor is None:
        newValueDict = {
            "AuthorID":   "0: %s" % (authorname),
            "Status":       "Loading"
            }
    else:
        newValueDict = {"Status": "Loading"}
    myDB.upsert("authors", newValueDict, controlValueDict)

    author = GR.find_author_id()
    if author:
        authorid = author['authorid']
        authorlink = author['authorlink']
        authorimg = author['authorimg']
        controlValueDict = {"AuthorName": authorname}
        newValueDict = {
            "AuthorID":     authorid,
            "AuthorLink":   authorlink,
            "AuthorImg":    authorimg,
            "AuthorBorn":   author['authorborn'],
            "AuthorDeath":  author['authordeath'],
            "DateAdded":    formatter.today(),
            "Status":       "Loading"
            }
        myDB.upsert("authors", newValueDict, controlValueDict)
    else:
        logger.error("Nothing found")

# process books
    bookscount = 0
    havebooks = 0
    books = GB.find_results()
    for book in books:

        # this is for rare cases where google returns multiple authors who share nameparts
        if book['authorname'] == authorname:

            #check to see if this book was added to the database before adding the author
            statuscheck = myDB.action("SELECT * FROM books WHERE BookID='%s'" % book['bookid']).fetchone()
            if statuscheck:
                statusini = statuscheck['Status']
                if statusini == "Have":
                    havebooks = havebooks+1
            else:
                statusini = "Skipped"
            if statusini != "Ignored":
                bookscount = bookscount+1 
            controlValueDict = {"BookID": book['bookid']}
            newValueDict = {
                "AuthorName":   book['authorname'],
                "AuthorID":     authorid,
                "AuthorLink":   authorimg,
                "BookName":     book['bookname'],
                "BookSub":      book['booksub'],
                "BookDesc":     book['bookdesc'],
                "BookIsbn":     book['bookisbn'],
                "BookPub":      book['bookpub'],
                "BookGenre":    book['bookgenre'],
                "BookImg":      book['bookimg'],
                "BookLink":     book['booklink'],
                "BookRate":     book['bookrate'],
                "BookPages":    book['bookpages'],
                "BookDate":     book['bookdate'],
                "BookLang":     book['booklang'],
                "Status":       statusini,
                "BookAdded":    formatter.today()
                }

            myDB.upsert("books", newValueDict, controlValueDict)

    lastbook = myDB.action("SELECT BookName, BookLink, BookDate from books WHERE AuthorName='%s' AND NOT Status='Ignored' order by BookDate DESC" % authorname.replace("'","''")).fetchone()
    controlValueDict = {"AuthorName": authorname}
    newValueDict = {
        "Status": "Active",
        "TotalBooks": bookscount,
        "LastBook": lastbook['BookName'],
        "LastLink": lastbook['BookLink'],
        "LastDate": lastbook['BookDate'],
        "HaveBooks": havebooks
        }

    myDB.upsert("authors", newValueDict, controlValueDict)
    logger.info("Processing complete: Added %s books to the database" % bookscount)

