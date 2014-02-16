#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import unicodecsv
from itertools import groupby
from shutil import copyfileobj
from collections import namedtuple
from getpass import getpass
from subprocess import Popen, PIPE, STDOUT

# Place your own settings here
filepath = ('auth.csv.gpg',)
pubkeyid = 'Your key here'
pipecmd = ('pbcopy',)
defaultgroup = "Default"

# Commands
decryptcmd = ('gpg2', '-q', '-d')
encryptcmd = ('gpg2', '-ea', '-r', pubkeyid)

Credentials = namedtuple('Credentials',
                         ['name', 'username', 'password', 'group', 'info'])

getaction = set(['get', 'g'])
saveaction = set(['save', 's'])
listaction = set(['list', 'l'])

def main(action='get', name=''):
    if action in getaction:
        find_and_deliver_credentials(name)
    elif action in saveaction:
        save_credentials(name)
    elif action in listaction:
        list_groups(name)
    else:
        print 'Incorrect action:', action

def find_and_deliver_credentials(name):
    deliver_credentials(find_credentials(name))

def find_credentials(lookup_string):
    with credentials_readstream() as f:
        reader = unicodecsv.reader(f, encoding='utf-8')
        row = find_row_by_name(reader, lookup_string)
        if row:
            return row_to_credentials(row)
        else:
            return None

def credentials_readstream():
    fname = os.path.join(*filepath)
    p = Popen(decryptcmd, stdin=open(fname),
              stdout=PIPE, stderr=STDOUT, close_fds=True)
    p.wait()
    return p.stdout

def find_row_by_name(reader, lookup_string):
    g = (row for row in reader
         if startswith_caseinsensitive(row[0], lookup_string))
    return next_or_none(g)

def startswith_caseinsensitive(a, b):
    return a.lower().startswith(b.lower())

def next_or_none(g):
    try:
        return g.next()
    except StopIteration:
        return None

def row_to_credentials(row):
    name = row[0]
    username = row[1]
    password = row[2]
    group = row[3]
    info = get_or_else(row, 4, '')
    return Credentials(name, username, password, group, info)

def get_or_else(l, i, alt=None):
    return l[i] if i < len(l) else alt

def deliver_credentials(creds):
    if creds:
        print_multiline_info(creds)
        print "----"
        pipe_credentials(creds)
    else:
        print "No matches found"

def print_multiline_info(creds):
    print "Name  :", creds.name
    print "Group :", creds.group
    if creds.info:
        print "Info  :",creds.info

def pipe_credentials(creds):
    send_to_pipe('user name', creds.username)
    send_to_pipe('password', creds.password)

def send_to_pipe(key, value):
    if value:
        wait_for_enter(key)
        pipe(value)
    else:
        print "No %s found" % key

def wait_for_enter(key):
    print "Press enter to pipe", key
    sys.stdin.read(1)

def pipe(value):
    p = Popen(pipecmd, stdin=PIPE)
    p.communicate(value)

def save_credentials(name):
    defaultcreds = Credentials(name, '', '', defaultgroup, '')
    creds = get_creds_from_user(defaultcreds)
    readstream = credentials_readstream()
    writestream = credentials_writestream()
    copy_and_write_credentials(readstream, writestream, creds)
    readstream.close()
    writestream.close()

def get_creds_from_user(cred):
    while True:
        name = read_input('Name', cred.name)
        username = read_input('User name', cred.username)
        password = getpass('Password? ')
        group = read_input('Group', cred.group)
        info = read_input('Info', cred.info)
        if read_yes_no():
            return Credentials(name, username, password, group, info)

def read_input(prompt, defaultvalue=''):
    if defaultvalue != None:
        p = '%s [%s]? ' % (prompt, defaultvalue)
    else:
        p = "%s? " % prompt
    return raw_input(p).decode(sys.stdin.encoding) or defaultvalue

def read_yes_no():
    yes = set(['yes', 'y', 'ye'])
    no = set(['no', 'n'])
    while True:
        choice = read_input('OK', None).lower()
        if choice in yes:
            return True
        elif choice in no:
            return False

def copy_and_write_credentials(readstream, writestream, creds):
    copyfileobj(readstream, writestream)
    writer = unicodecsv.writer(writestream, encoding='utf-8')
    writer.writerow(creds_to_row(creds))

def creds_to_row(creds):
    return list(creds)

def credentials_writestream():
    fname = os.path.join(*filepath)
    p = Popen(encryptcmd, stdin=PIPE,
              stdout=open(fname, 'w'), close_fds=True)
    return p.stdin

def list_groups(name):
    groups = find_matching_groups(name)
    print_groups(groups)

def find_matching_groups(name):
    with credentials_readstream() as f:
        reader = unicodecsv.reader(f, encoding='utf-8')
        rows = rows_matching_groups(reader, name)
        credentials = (row_to_credentials(row) for row in rows)
        return groupby(credentials, lambda c: c.group)

def rows_matching_groups(reader, name):
    return [row for row in reader
            if not name or startswith_caseinsensitive(row[3], name)]

def print_groups(groups):
    for groupname, credentials in groups:
        print "\n---", groupname, "---"
        for cred in credentials:
            print_singleline_info(cred)

def print_singleline_info(cred):
    if cred.info:
        print "%s, %s" % (cred.name, cred.info)
    else:
        print cred.name

if __name__ == '__main__':
    action = get_or_else(sys.argv, 1, 'get')
    name = ' '.join(sys.argv[2:])
    main(action, name)
