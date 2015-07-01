#run.py 
import keys
import methods
#################
import requests
import os
from bs4 import BeautifulSoup, SoupStrainer


def raven():
    sess = requests.Session()
    url = 'http://www-teach.phy.cam.ac.uk'


    print 'authenticating with Raven...'
    payload = {
        'userid':keys.user_raven,
        'pwd':keys.password,
        #'override':'override',
        'date' : '20150113T201300Z',
        'ver' : '1',
        'skew' :'300',
        "desc":'Physics Teaching Information System',
        'url' : url+'/teaching/authenticate_raven_all.php',    
        'submit' : 'Login'
    }

    primary = sess.post('https://raven.cam.ac.uk/auth/authenticate2.html',
                        data=payload, allow_redirects=False)
    #print primary.headers['location']
    #print sess.cookies
    main_page = sess.get( url+'/teaching/authenticate_raven_all.php' )

    #(hack auth fail test)
    if len(sess.cookies) == 1:
        print '\n[ERR]... authentication failed'
        print '[%s  :  %s]'%(keys.user_raven, keys.user)
        print '[edit Raven details in file: "keys.py"]\n'
        return None

    print "... all authenticated!"
    print "loading database..."
    if not os.path.exists('cavendish.db'):
        methods.boot_database(sess, url)
    print "... all loaded!\n"

    print '---------------------------------------------------------------'        
    print "\nLogged in as:>> ", keys.user_raven + '  :  ', keys.user  

    return [sess,url]

def main(package):
    sess, url = package[0], package[1]

    intro =  '''
    ---------------------------------------------------------------

    You are ready to scrape TiS. Scraping can take a long time so
    it is best to leave this running in a background terminal, and
    conduct any important work on a different terminal.  If you need
    to stop scraping at any point, this program will continue down-
    loading at the point you left off, when you make the same selec-
    tion.

    This scraper does not have a waiting point between requests. 
    Therefore please scrape considerately, at times when TiS does
    not have high demand.

    Peace.

    ---------------------------xxfromELLH--------------------------
    '''

    instruct='''Instructions:
    press 'h' + Enter to scrape handouts
    press 'e' + Enter to scrape exam_papers
    press 'u' + Enter to update database
    press 'q' + Enter to quit

    at any time the programme can be exited using Ctrl+c to quit
    '''
    print intro
    print instruct



    while True:
        cmd = raw_input('>>>  ')
        if cmd == 'h':
            methods.browse_docs(sess, url, 'h')
            print instruct
        if cmd == 'e':
            methods.browse_docs(sess,url, 'e')
            print instruct
        if cmd == 'u':
            methods.update_db(sess, url)
            print instruct
        if cmd == 'q':
            break


if __name__ == '__main__':
    package = raven()
    if package:
        main(package)

    





