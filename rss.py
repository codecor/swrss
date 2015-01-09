#!/usr/bin/python
#routine to manage rss feeds
import getopt, sys, json, os, feedparser, smtplib, getpass
from os.path import expanduser
    
# global 
confighome = expanduser("~")+"/.swrss/"
#TODO flag+function to temporarily set the path to config

def getConfig():
    """ load and parse the json config file"""
    filepath = confighome+"config"
    with open(filepath,mode='r', encoding='utf-8') as f:
        jconfig = json.load(f)
        return jconfig # success

    return -1 # fail

def sendMsg(dest):
    """ email the feeds using user supplied exchange data """
    # need to grab these creds from config
    jconfig = getConfig()
    if jconfig == -1:
        print("::unable to parse tardigrade credentials")
        return 1
    if 'tardigrade' not in jconfig[2]:
        print("::unable to parse tardigrade credentials. Add to config using (-E) --email-creds-init")
        return 1
    username=jconfig[2]['tardigrade']['username']
    password=jconfig[2]['tardigrade']['password']
    fromaddr=username
    toaddrs=dest
    msg=listFeeds(1)
    server = smtplib.SMTP('smtp.gmail.com:587')
    server.starttls()
    server.login(username,password)
    server.sendmail(fromaddr, toaddrs, msg)
    server.quit()
    print("::msg sent")

def fileAccessible(filepath, mode):
    ''' Check if a file exists and is accessible. '''
    print ("::configfile is",filepath)
    try:
        f = open(filepath, mode)
        f.close()
    except IOError as e:
        return False

    return True

def usage():
    print("-h\thelp\n-a+\tadd feed <feed-name>\n-U\tcreate new database\n-u\tupdate database\n-f\tfeeds\n-e+\tmail <dest-addr>\n-E+\temail creds init <sender-addr>\n")

def createDB():
    """ slop for creating git init directory on a remote server """
    print("::creating db")
    filepath = confighome+"config"

    # open config to get credentials for ssh 
    with open(filepath,mode='r', encoding='utf-8') as f:
        jconfig = json.load(f)
        creds=jconfig[0]

        # ssh in make a directory, initialize it with 'git --bare' 
        cmd="ssh "+creds['db']['username']+"@"+creds['db']['host']
        cmd_sqrd=" 'if ! cd swrss_database > /dev/null 2>&1 ; then mkdir swrss_database; cd swrss_database ; fi ; git init --bare ;'"
        cmd_full=cmd+cmd_sqrd
        print("::cmd=",cmd_full)
        retval= os.system(cmd_full)
        if (retval==0):
            print("::synced successfully")

        print("::system returned ",retval)
        if retval != 0:
            print("::error encountered. Make sure you have stored your remote's info in the config")

        # locally clone the "db"
        cmd_full="git clone "+creds['db']['username']+"@"+creds['db']['host']+":swrss_database"
        print("::cmd=",cmd_full)
        retval= os.system(cmd_full)
        if (retval==0):
            print("::synced successfully")

        print("::system returned ",retval)

def updateDB():
    """ this module updates the 'db' via git commit to remote """
    print("::updating db")
    filepath = confighome+"config"
    configdb = confighome+"swrss_database/"

    with open(filepath,mode='r', encoding='utf-8') as f:
        jconfig = json.load(f)
        creds=jconfig[0]

        cmd="cp "+filepath+" "+configdb
        print("cmd=",cmd)
        retval= os.system(cmd)
        if (retval==0):
            print("::copied successfully")

        cmd="cd "+configdb+"; ls; git add -A :/ ; git commit -m \"updating...\" ; " + "git push origin master "
        print("cmd=",cmd)
        retval= os.system(cmd)
        print("retval=",retval)
        if (retval==0):
            print("::updated successfully")

def addNewFeed(feed):
    """routine to append to feed to json file"""
    # config exist?
    configfile_path = confighome+"config"
    print("::checking for config")
    if fileAccessible(configfile_path,'r'):
        print("::reading config")
        appendFeed(feed,configfile_path)
    elif fileAccessible(configfile_path,'w'):
        createNewConfig(feed,configfile_path)
    else:
        print("::unable to read")
    
def workAFeed(feed):
    """ sanitary mods to feed URLs """
    print("::working ",feed)

    # add http
    if feed.find("http") == -1:
        feed = "http://" + feed
        print ("::feed=",feed)

    return feed

def createNewConfig(feed,filepath):
    """ populate default values and add newly supplied feed """
    print("::creating new config")
    feed = workAFeed(feed)
    data = { 'db': { 'host':'192.168.1.12' , 'username':'swrss' } } , { 'feeds': [ { 'url':feed } ] } 
    print(json.dumps(data,indent=2))

    try:
        f = open(filepath,'w')
        json.dump(data,f)
        f.close()
    except IOError as e:
        return False

    return False

def appendFeed(feed,filepath):
    """ append a new feed to the existing feed config """
    print("::appending feed")
    with open(filepath,mode='r', encoding='utf-8') as f:
        jconfig = json.load(f)

    with open(filepath,mode='w', encoding='utf-8') as feedsjson:
        feed = workAFeed(feed)
        entry = {'url':feed}
        print("::feeds=",jconfig[1]['feeds'])
        jconfig[1]['feeds'].append(entry)

        print(json.dumps(jconfig,indent=2))
        json.dump(jconfig,feedsjson)

def appendJson(filepath,entry):
    """append a new value pair to json config"""
    with open(filepath,mode='r', encoding='utf-8') as f:
        jconfig = json.load(f)

    with open(filepath,mode='w', encoding='utf-8') as feedsjson:
        jconfig.append(entry)
        print(json.dumps(jconfig,indent=2))
        json.dump(jconfig,feedsjson)

def rmFeed(feed,filepath):
    """ remove a feed from the existing feed config """
    print("::removing feed")
    with open(filepath,mode='r', encoding='utf-8') as f:
        jconfig = json.load(f)

    with open(filepath,mode='w', encoding='utf-8') as feedsjson:
        entry = {'url':feed}
        print("::feeds=",jconfig[1]['feeds'])
        jconfig[1]['feeds'].append(entry)

        print(json.dumps(jconfig,indent=2))
        json.dump(jconfig,feedsjson)

def listFeeds(key):
    """ pretty print the feeds to stdout or return via object """
    # read and parse config, collect each url
    filepath = confighome+"config"
    if fileAccessible(filepath,'r'):
        with open(filepath,mode='r', encoding='utf-8') as f:
            jconfig = json.load(f)

            # for each url pull the last 5 most recent posts and print them
            str=""
            for url in jconfig[1]['feeds']:
                f = feedparser.parse (url['url'])
                if 'title' not in f.feed:
                    print ("::title not found in url:",url['url'])
                else:
                    str += f.feed.title + "\n" + url['url'] + "\n"

                    # gimi five
                    count=1
                    blockcount=1
                    for post in f.entries:
                        if count % 5 == 1:
                            str += post.title +" - " + post.link +"\n"

                        count+=1

                    str=str+"\n"

            if key==0:
                print (str)
            if key==1:
                return str
    else:
        print("::unable to read")
        sys.exit()

def initEmailCreds(sender):
    """ ask for user input password interactively, store with supplied un in config """
    print ("::initializing email creds...")
    pw = getpass.getpass()
    entry = {'tardigrade': { 'username':sender, 'password':pw } }
    filepath = confighome+"config"
    appendJson(filepath,entry)

### main
def main(argv):
    try:
        opts,args = getopt.getopt(argv,"ha:Uufe:E:",["help","addfeed=","createDB","updateDB","feeds", "emailBreif", "EmailSenderInit"])
    except getopt.GetoptError:
        usage()
        sys.exit(2)
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            usage()
            sys.exit()
        elif opt in ("-a","--addfeed"):
            newfeed=arg
            addNewFeed(newfeed)
            sys.exit()
        elif opt in ("-U","--create-db"):
            createDB()
            sys.exit()
        elif opt in ("-u","--udpate-db"):
            updateDB()
            sys.exit()
        elif opt in ("-f","--feeds"):
            listFeeds(0)
            sys.exit()
        elif opt in ("-e","--email_breif"):
            dest=arg
            sendMsg(dest)
            sys.exit()
        elif opt in ("-E","--email-creds-init"):
            sender_email_addr=arg
            initEmailCreds(sender_email_addr)
            sys.exit()

if __name__ == "__main__":
    main(sys.argv[1:])
