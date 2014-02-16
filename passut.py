#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import csv
from shutil import copyfileobj
from collections import namedtuple
from getpass import getpass
from subprocess import Popen, PIPE, STDOUT

# Place your own settings here
filepath = ('auth.csv.gpg',)
pubkeyid = 'Your key here'
pipecmd = ('pbcopy',)

# Commands
decryptcmd = ('gpg2', '-q', '-d')
encryptcmd = ('gpg2', '-ea', '-r', pubkeyid)

Credentials = namedtuple('Credentials',
                         ['name', 'username', 'password', 'info'])

def main(action='get', name=''):
    if action == 'get':
        creds = find_credentials(name)
        deliver_credentials(creds)
    elif action == 'save':
        save_password_with_wizard(name)
    else:
        print 'Incorrect action:', action

def find_credentials(lookup_string):
    with credentials_readstream() as f:
        reader = csv.reader(f)
        row = find_row_by_name(reader, lookup_string)
        if row:
            return row_to_dict(row)
        else:
            return None

def credentials_readstream():
    fname = os.path.join(*filepath)
    p = Popen(decryptcmd, stdin=open(fname),
              stdout=PIPE, stderr=STDOUT, close_fds=True)
    p.wait()
    return p.stdout

def find_row_by_name(reader, lookup_string):
    for row in reader:
        name = row[0]
        if startswith_caseinsensitive(name, lookup_string):
            return row
    return None

def startswith_caseinsensitive(a, b):
    return a.lower().startswith(b.lower())

def row_to_dict(row):
    name = row[0]
    username = row[1]
    password = row[2]
    info = get_or_else(row, 3)
    return Credentials(name, username, password, info)

def get_or_else(l, i, alt=None):
    return l[i] if i < len(l) else alt

def deliver_credentials(creds):
    if creds:
        show_information(creds)
        pipe_credentials(creds)
    else:
        print "No matches found"

def show_information(creds):
    print "Found:", creds.name
    if creds.info:
        print creds.info
    print "----"

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

def save_password_with_wizard(name=''):
    creds = get_creds_from_user(name)
    readstream = credentials_readstream()
    writestream = credentials_writestream()
    save_creds(readstream, writestream, creds)

def get_creds_from_user(name=''):
    while True:
        if not name:
            name = read_input('Name?')
        username = read_input('User name?')
        password = getpass('Password? ')
        info = read_input('Info?')
        if read_yes_no():
            return Credentials(name, username, password, info)

def read_input(prompt='>'):
    return raw_input(prompt + ' ').decode(sys.stdin.encoding)

def read_yes_no():
    yes = set(['yes', 'y', 'ye'])
    no = set(['no', 'n'])
    while True:
        choice = read_input('OK?').lower()
        if choice in yes:
            return True
        elif choice in no:
            return False

def save_creds(readstream, writestream, creds):
    with writestream as ws:
        copyfileobj(readstream, ws)
        writer = csv.writer(ws)
        writer.writerow(list(creds))
        writestream.close()

def credentials_writestream():
    fname = os.path.join(*filepath)
    p = Popen(encryptcmd, stdin=PIPE,
              stdout=open(fname, 'w'), close_fds=True)
    return p.stdin

if __name__ == '__main__':
    action = get_or_else(sys.argv, 1, 'get')
    name = ' '.join(sys.argv[2:])
    main(action, name)
