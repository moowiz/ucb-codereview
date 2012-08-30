#! /usr/bin/env python3

import sys
from subprocess import Popen, PIPE
import argparse
import os
import io
import re
import utils
import sqlite3

GMAILS_FILE = "MY.GMAILS"
SECTIONS_FILE = "MY.SECTIONS"
LOGINS_FILE = "MY.PARTNERS"
important_files = (GMAILS_FILE, SECTIONS_FILE, LOGINS_FILE)

def get_important_files(assign):    
    conn = sqlite3.connect(utils.read_db_path())
    cursor = conn.cursor()
    sql = "SELECT file FROM important_file WHERE assignment=?"
    files = cursor.execute(sql, (assign,))
    temp = []
    for row in files.fetchall():
        temp.append(row[0])
    conn.close()
    return temp

def run_submit(assign):
    """Runs submit. Basic, slightly dumb version."""
    # print "running command {}".format(cmd)
    # print "cwd {}".format(os.getcwd())
    print("Looking for files to turn in....")
    files = os.listdir(os.getcwd())
    imp_files = get_important_files(utils.clean_assign(assign))
    for imp_f in imp_files:
        if imp_f not in files:
            print("ERROR: missing a required file {}".format(imp_f))
            sys.exit(1)
        else:
            print("Submitting {}.".format(imp_f))
    decode = lambda x: x.decode('utf-8')
    def get_char(stream):
        got = stream.read(1)
        return decode(got)
    def goto_newline(stream):
        s, c = "", ""
        while c != "\n":
            c = get_char(stream)
            s += c
        return s
    def ignore_line(line):
        return "Looking for files to turn in...." in line or "Submitting " in line \
                "Skipping directory" in line
    def read_line(stream):
        char = get_char(stream)
        s = char
        while True:
            if s.endswith("/no]") or s[-1] == "\n":
                break
            s += get_char(stream)            
        return s
    def write_out(stream, thing):
        if type(thing) != bytes:
            thing = bytes(thing, "utf-8")
        stream.write(thing)
        stream.flush()
    cmd = "/share/b/grading/bin/submit " + assign
    proc = Popen(cmd.split(), stdin=PIPE, stdout=PIPE, stderr=PIPE)
    sin = proc.stdin
    special = False
    while True:
        line = read_line(proc.stderr)
        if "Copying submission of assignment" in line:
            print(line)
            break
        print_it = True
        read = not ignore_line(line)
        if not special:
            for f in important_files:
                if f in line:
                    write_out(sin, "yes\n")
                    print_it = False
        else:
            line = "    " + " ".join(list(filter(lambda x: x.replace("./", "") not in important_files, line.split()))) + "\n"
            read = False
            special = False
        if print_it:
            if "You must turn in " in line:
                print(line, end="")
                print(decode(proc.stderr.read()), end="")
                return
            if not ignore_line(line):
                print(line, end="")
            sys.stdout.flush()
            if "The files you have submitted are" in line:
                special = True
            elif read:
                write_out(sin, sys.stdin.readline())
    proc.wait()
    print(decode(proc.stderr.read()), end="")
        
def my_prompt(initial_message, prompt, defaults_file):
    defaults = None
    if os.path.exists(defaults_file):
        defaults = open(defaults_file, 'r').read().split()
    print(initial_message)
    msg = "Enter '.' to stop."
    if defaults:
        msg += " Hit enter to use the remaining defaults."
    print(msg)
    captured = []
    while True:
        output = prompt
        if defaults:
            output += " " + str(defaults)
        output += ": "
        print(output, end="")
        sys.stdout.flush()
        value = sys.stdin.readline()
        if value == '\n':
            print("Using defaults")
            sys.stdout.flush()
            break
        if len(value) < 3 and '.' in value:
            break
        if defaults:
            defaults.pop(0)
        captured.append(value)
    if defaults:
        captured.extend(defaults)
    return captured

def write_defaults(defaults, filename, string_to_join="\n"):
    out = open(filename, 'w')
    string = string_to_join.join(defaults)
    if not string[-1] == "\n":
        string = string + "\n"
    out.write(string)
    out.flush()
    out.close()

def get_gmails():
    """
    Prompts the user for their gmails, and stores the file in the GMAILS_FILE file
    """
    gmails = my_prompt("Enter you and your partner's gmail addresses.", "GMail", GMAILS_FILE)
    write_defaults(gmails, GMAILS_FILE)
    regex = r'^[A-Za-z0-9\.\_\%\+]+@(berkeley.edu|gmail.com)$'
    for address in gmails:
        if not re.match(regex, address):
            print("{} is an invalid email address. Please enter either a gmail email\
             address or a berkeley email address that has access to bmail and/or bcal.".format(address), file=sys.stderr)
            sys.exit(1)
    return gmails

def get_partners():
    """
    Prompts the user for their logins, and stores the file in the LOGINS_FILE file
    """
    partners = my_prompt("Enter you and your partner's full logins.", "Login", LOGINS_FILE)
    write_defaults(partners, LOGINS_FILE, string_to_join=" ")
    return partners

def get_sections():
    sections = my_prompt("Enter the last 2 digits of you and your partner's section numbers.", "Section Number", SECTIONS_FILE)
    write_defaults(sections, SECTIONS_FILE)
    return sections

def main(assign):
    files = get_important_files(utils.clean_assign(assign))
    if not files:
        print("ERROR. Trying to submit for an assignment that doesn't exist!", file=sys.stderr)
        sys.exit(1)
    gmails = get_gmails()
    sections = get_sections()
    partners = get_partners()
    run_submit(assign)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Submits the assignment, \
        assuming the correct files are in the given directory.")    
    parser.add_argument('assign', type=str,
                        help='the assignment to submit')
    args = parser.parse_args()
    main(args.assign)
