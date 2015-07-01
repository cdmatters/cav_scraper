#methods.py
from bs4 import BeautifulSoup, SoupStrainer
import requests
import sqlite3
import os
import time
import re


##############   BROWSE METHODS   ##################
def browse_docs(session, url, selection='q'):       
    intro = '''>>>

%s
press 'y' + Enter to download from a calender year
press 'c' + Enter to download from specific course
press 'q' + Enter to return back'''
    
    if selection == 'h':
        docs = 'Handouts'
        print intro%('Handouts:')
    elif selection == 'e':
        docs = 'Exams'
        print intro%('Exams:') 

    while True:
        cmd = raw_input('>>>')
        if cmd == 'y' or cmd == 'c':
            if cmd == 'y':
                search_by = 'Year'
            elif cmd == 'c':
                search_by = 'Course'
            
            try: 
                query = user_query_choices(docs,search_by)
            except:
                print CustErr.selection
                return None
            urlpackage = get_urlpack_from_database_query(query)
            download_resources(urlpackage, session, url, query)
            return None
        if cmd == 'q':
            print CustErr.bar
            return None

def user_query_choices(doc, sort):
    with sqlite3.connect('cavendish.db') as connection:
        cur = connection.cursor()
        cur.execute('SELECT DISTINCT %s FROM %s ORDER BY %s ASC' %(sort,doc,sort))
        tuplist = cur.fetchall()
        
        i = 1
        choices_dict = {}
        print '\n  option no : <%s>' %sort.lower()
        for option in tuplist:
            print '  ',i ,' : ', option[0]
            choices_dict.update({i : option[0]})
            i+=1

        print '''
  Enter in your download selections separeted by
  a comma to start download... [eg >>>3,12,50 + Enter]'''
              
        userchoice = raw_input('  >>>').split(',')
        userchoice = map(int, userchoice)
        
        db_query = {'doc':doc, 'sort':sort, 'query':[] }
        
        print '\n'
        for key in userchoice:
            try:
                db_query['query'].append(choices_dict[key])
            except:
                print "[ERR:] Option %s invalid" %key

        print "\nDownloading ALL:..."
        for q in db_query['query']:
            print '\t',q
    
    connection.close()
    return db_query
    

def get_urlpack_from_database_query(querydict):
    url_package = []
    with sqlite3.connect('cavendish.db') as connection:
        cur= connection.cursor()

        for query in querydict['query']:
            cur.execute('SELECT * FROM %s WHERE %s = %s' 
                        %(querydict['doc'], querydict['sort'], "'"+query+"'") )
            result = cur.fetchall()
            url_package.append(result)
    connection.close
    return url_package
    
def download_resources(urlpackage, session, url, query):  
    total_files = 0
    for pack in urlpackage:
        total_files += len(pack)
    print "Downloading...%s files: " %total_files
    err_count = []
    i = 1

    for pack in urlpackage:    
        for p in pack:

            if query['sort'] == 'Course':
                url_tuple = (query['doc'], query['sort'],p[1],p[3],p[4])
            elif query['sort'] == 'Year':
                url_tuple = (query['doc'], query['sort'],p[3],p[1],p[4])
            filename = 'resources/%s/requests_by_%s/%s/%s/%s'%url_tuple+'/%s'%(p[0].replace('/','-')) 
            
            if not os.path.exists('resources/%s/requests_by_%s/%s/%s/%s' % url_tuple):
                os.makedirs('resources/%s/requests_by_%s/%s/%s/%s' % url_tuple)                    
            
            if p[7] == 0:  # or not os.path.exists(filename):                                

                download = session.get(url+p[6])
                header_content = download.headers['content-disposition']
                extension = re.findall("\.[0-9a-z]*$", header_content)
                
                if len(extension)==0:
                    extension = ''
                else:
                    extension = extension[0]
                
                

                try:
                    with open(filename+extension,  'w+' ) as savefile:
                        savefile.write(download.content)
                    with sqlite3.connect('cavendish.db') as connection:
                        cur = connection.cursor()
                        cur.execute('UPDATE %s SET Downloaded = 1 WHERE Link = %s'%(query['doc'],"'"+p[6]+"'"))
                        connection.commit()
                        print '\r',i,' : ',p[0]              
                except Exception,e:
                    err_count.append([p[0],str(e)])
                    print '[ERR]: ',i,' : ',p[0], '\n', e

            elif p[7] == 1 :
                print '[FOUND]:',i,' :',p[0]
            
            i+=1
    
    print 'DONE: Downloaded %s/%s documents successfully' %(i-1, total_files)
    if err_count:
        print '(Errors in downloading:)'
        for e in err_count:
            print '\t', e[0], '\t', e[1]
    print  CustErr.bar


################    BOOT METHODS    ################
def boot_database(session, url):
    print '\t<no database found>'
    print '\t...retrieving contents from TiS'   
    hcontents = fetch_hcontents_list(session, url)
    econtents = fetch_econtents_list(session, url)

    insert = {'handouts':hcontents, 'exams':econtents}    
    populate_database(insert)

def fetch_hcontents_list(session, url):
    hcontents_list = []
    payload = {
        'parent':'5',
        'type' :'handouts',
        'originator':'dms/dmsSearch.php',
        'Action':'search',
        'control[1]':'0',  #All Years
        'control[7]':'0',  #All Tripos Groups
        'control[3]':'0',  #All Courses
        'control[6]':'0',  #All Handout Types
        }

    load_cookie = session.get(url+'/dms/dmsSearch.php?type=handouts') #loads a cookie
    h_out = session.get(url+'/dms/dmsSearch.php?type=handouts', 
                        stream=True, params=payload, allow_redirects=False)

    strainer = SoupStrainer('tbody')
    bigSoup = BeautifulSoup(h_out.content, parse_only=strainer)
    col_search = bigSoup.find_all('a')
    print "\t...%s resources found." % len(col_search)
    for col in col_search:
        parent = col.find_parent()

        record = {
            'name' :  unicode(col.text),
            'link' :  unicode(col['href']),   
            }
        key = {
            0:'year',
            1:'tripos',
            2:'course',
            3:'doctype',
            4:'time',
            }

        i=0
        while i<5:
            parent = parent.next_sibling
            record.update({key[i]: unicode(parent.text)})
            i+=1

        hcontents_list.append(record)
    return hcontents_list

def fetch_econtents_list(session, url):
    econtents_list = []
    payload = {
        'parent': '2',
        'originator':'/dms/dmsSearch.php',
        'type': 'examPapers',
        'Action':'search',
        'control[1]': '0'  ,
        'control[2]': '0'  ,
    }

    load_cookie = session.get(url+'/dms/dmsSearch.php?type=examPapers')
    e_out = session.get(url+'/dms/dmsSearch.php?type=examPapers',
                        stream=True, params=payload, allow_redirects=False)

    strainer = SoupStrainer('tbody')
    bigSoup = BeautifulSoup(e_out.content, parse_only=strainer)
    col_search = bigSoup.find_all('a')
    print "\t...%s resources found." % len(col_search)
    for col in col_search:
        parent = col.find_parent()
        
        record = {
            'course' : unicode(col.text),
            'link' : unicode(col['href']),
        }
        key = {
            0: 'year' ,
            1: 'tripos',
            2: 'time',
        }

        i=0 
        while i<3:
            parent = parent.next_sibling
            record.update({key[i]: unicode(parent.text)})
            i+=1

        record['name'] = record['year']+' || '+record['course']
        
        #[Improve UX]: exam papers are very poorly labelled. Group by IA, IB, III Major, etc.. 
        if not 'Part III' in record['tripos']:
            record['course'] = record['tripos'] 
        elif 'Minor' in record['course']:
            record['course'] = 'Pt III Minor Topics [collected]'
        elif 'Major' in record['course']:
            record['course'] = 'Pt III Major Topics [collected]'
        elif ('IDP' in record['course']) or ('Interdisc' in record['course']):
            record['course'] = 'Pt III Interdisciplinary Topics [collected]'
        elif 'General' in record['course']:
            record['course'] = 'Pt III General [collected]'
        else:
            record['course'] = 'Pt III Sundry (Reports, QFT, AQFT, badly labelled papers...)'

        
        econtents_list.append(record)
    return econtents_list 

def populate_database(inputdict):
    handouts_list = inputdict['handouts']
    exam_list = inputdict['exams']

    with sqlite3.connect('cavendish.db') as connection:
        cur = connection.cursor()
        cur.execute("CREATE TABLE Handouts (\
            Name Text, Course Text, Tripos Text, Year Text, Doctype Text,\
            Time Text, Link Text, Downloaded Number) ")
        cur.execute("CREATE TABLE Exams (\
            Name Text, Course Text, Tripos Text, Year Text, Doctype Text,\
            Time Text, Link Text, Downloaded Number) ")

        connection.commit()

        for handout in handouts_list:
            record = [handout['name'], handout['course'], handout['tripos'], 
                handout['year'], handout['doctype'], handout['time']]
            #filter pesky strings [motivating factor]
            record = map(lambda x: x.replace("'",''), record)     # [SQL]
            record = map(lambda x: x.replace('/', '\\'), record)  # [directories]
            
            record.append(handout['link'])
            record = tuple(record)

            cur.execute("INSERT INTO Handouts VALUES(?,?,?,?,?,?,?,0)", record)        
        connection.commit()

        for exam in exam_list:
            if 'comment' in exam['name'].lower():
                doctype = 'Report'
            elif 'examiner' in exam['name'].lower():
                doctype = 'Report'
            else:
                doctype = 'Exam'

            record = (exam['name'], exam['course'], exam['tripos'], 
                exam['year'], doctype, exam['time'], exam['link'])
            cur.execute("INSERT INTO Exams VALUES(?,?,?,?,?,?,?,0)", record)
        connection.commit()
            
    connection.close()
    pass



################# UPDATE METHODS ##################
def update_db(session, url):
    os.remove('cavendish.db')
    print '\n...old database deleted\nreinitiating boot...'
    boot_database(session, url)

    print 'updating inventory database...'
    with sqlite3.connect('cavendish.db') as connection:
        cur = connection.cursor()
        walkies =  os.walk('resources/')

        for w in walkies:
            if not w[1]:
                for name in w[2]:
                    
                    r_list = w[0].split('/',)
                    name = name.rstrip('.pdf')

                    if r_list[2] == 'requests_by_Year':
                        commitlist = [r_list[3], r_list[4], r_list[5], name]
                    elif r_list[2] == 'requests_by_Course':
                        commitlist = [r_list[4], r_list[3], r_list[5], name]
                    formatlist = map(lambda x: "'"+x+"'", commitlist)
                    formatlist.insert(0,r_list[1])
                    formattuple = tuple(formatlist)
                    cur.execute('UPDATE %s SET Downloaded=1 \
                            WHERE Year=%s AND Course=%s AND Doctype=%s AND Name=%s' %formattuple)
        connection.commit()
    connection.close()
    print '...inventory database updated'    
    print CustErr.bar
    pass


################  FORMAT CLASSES ##################
class CustErr(object):
    def __init__(self):
        pass

    bar = '---------------------xxfromELLH-----------------------\n'

    selection = '''\n[Err] Selection Invalid
---------------------xxfromELLH-----------------------\n'''
    
##########################################################


    


