#! /usr/bin/env python3

import sys
from subprocess import Popen, PIPE
import argparse
import os
import sqlite3
import re

import utils
import config

GMAILS_FILE = "MY.GMAILS"
SECTIONS_FILE = "MY.SECTIONS"
LOGINS_FILE = "MY.PARTNERS"
important_files = (GMAILS_FILE, SECTIONS_FILE, LOGINS_FILE)

class SilentException(Exception):
    pass

def run_submit(assign, partners):
    print("Looking for files to turn in....")
    files = os.listdir(os.getcwd())
    imp_files = config.get_imp_files(utils.clean_assign(assign))
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
                or "Skipping directory" in line or "Skipping file " in line or "Created MY.PARTNERS" in line
    def read_line():
        char = get_char(proc.stderr)
        s = char
        while True:
            if s.startswith("Login: "):
                handle_login()
                return read_line()
            if s.endswith("/no]") or s[-1] == "\n":
                break
            s += get_char(proc.stderr)            
        return s
    def handle_login():
        if partners:
            part = partners.pop(0)
            write_out(proc.stdin, part + "\n\r")
            return read_line()
        else:
            write_out(proc.stdin, ".\n")
            read_line()
            write_out(proc.stdin, "yes\n") 
            return read_line()     
    def write_out(stream, thing):
        if type(thing) != bytes:
            thing = bytes(thing, "utf-8")
        stream.write(thing)
        try:
            stream.flush()
        except IOError as e:
            if 'Errno 32' in str(e):
                return
            else:
                raise e
    cmd = "/share/b/grading/bin/submit " + assign
    proc = Popen(cmd.split(), stdin=PIPE, stdout=PIPE, stderr=PIPE)
    sin = proc.stdin
    special = False
    while True:
        line = read_line()
        if "Copying submission of assignment" in line:
            print(line)
            break
        print_it = True
        read = not ignore_line(line)
        if special and line.startswith('Is this corr'):
            special = False
        if not special:
            for f in important_files:
                if f in line:
                    write_out(sin, "yes\n")
                    print_it = False
        else:
            if assign == "proj01":
                print("line is {}".format(line))
            line = "    " + " ".join(list(filter(lambda x: x.replace("./", "") not in important_files, line.split()))) + "\n"
            read = False
        if print_it:
            if "You must turn in " in line:
                print(line, end="")
                print(decode(proc.stderr.read()), end="")
                return
            if "perl: warning" in line:
                print("ERROR: \"{}\". Please talk to a TA.".format(line))
                proc.stderr.read()
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
        
def my_prompt(initial_message, prompt, validate, validate_msg):
    print(initial_message)
    print("Enter '.' to stop.")
    captured = []
    while True:
        output = prompt
        output += ": "
        print(output, end="")
        sys.stdout.flush()
        value = sys.stdin.readline()
        if value.strip() == '.':
            break
        if not validate(value):
            print(validate_msg.format(value))
        else:
            captured.append(value)
    return captured

def yorn(message):
    answer = input(message + "  [yes/no] ")
    def isyes(s):
        return s in ("yes", 'y')
    def isno(s):
        return s in ("no", 'n')
    if isyes(answer):
        return True
    elif isno(answer):
        return False
    else:
        print("Please answer yes or no")
        return yorn(message)

def write_defaults(defaults, filename, string_to_join="\n"):
    out = open(filename, 'w')
    string = string_to_join.join(defaults)
    if string and not string[-1] == "\n":
        string = string + "\n"
    out.write(string)
    out.flush()
    out.close()

def get_gmails():
    """
    Prompts the user for their gmails, and stores the file in the GMAILS_FILE file
    """
    def validate(s):
        regex = r'^[A-Za-z0-9._%\+]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,6}$'
        return re.match(regex,s)
    gmails = my_prompt("Enter you and your partner's gmail addresses.", "GMail", validate, "Invalid email address: {}")
    write_defaults(gmails, GMAILS_FILE)
    return gmails

def get_partners():
    """
    Prompts the user for their logins, and stores the file in the LOGINS_FILE file
    """
    def validate(s):
        regex = '^' + config.CLASS_NAME + '-[a-zA-Z0-9]{2,3}$'.format(config.CLASS_NAME)
        return re.match(regex, s)
    partners = my_prompt("Enter your partner(s) (if you have any) full logins.", "Login", validate, "Invalid " + config.CLASS_NAME + " login {}")
    partners.append(utils.getuser())
    write_defaults(partners, LOGINS_FILE, string_to_join=" ")
    return partners

def get_sections():
    def validate(s):
        if len(s) != 2:
            return False
        try:
            int(s)
            return True
        except:
            return False
    sections = my_prompt("Enter the last 2 digits of you and your partner's section numbers.", "Section Number", validate, "Invalid section number")
    write_defaults(sections, SECTIONS_FILE)
    return sections

def summarize(gmails, sections, partners):
    print("GMails:   {}".format(",".join(gmails)))
    print("Sections: {}".format(",".join(sections)))
    print("Logins:   {}".format(",".join(partners)))

def main(assign, flag=False):
    try:
        try:
            files = config.get_imp_files(utils.clean_assign(assign))
        except ConfigException as e:
            print("ERROR {}".format(e))
            return 1
        if os.path.exists(GMAILS_FILE) and not flag:
            def read_def(f):
                try:
                    fi = open(f, 'r')
                    rval =  fi.read().split()
                except IOError:
                    main(assign, True)
                    raise SilentException()
                fi.close()
                return rval
            gmails = read_def(GMAILS_FILE)
            sections = read_def(SECTIONS_FILE)
            partners = read_def(LOGINS_FILE)
            print("The following is previous information you've entered.")
            summarize(gmails, sections, partners)
            answer = yorn("Is this correct?")
            if answer:
                run_submit(assign, partners)
                return
        def get_and_sum():
            gmails = get_gmails()
            sections = get_sections()
            partners = get_partners()
            summarize(gmails, sections, partners)
            return partners
        partners = get_and_sum()
        while not yorn("Is this correct?"):
            partners = get_and_sum()
        run_submit(assign, partners)
    except SilentException:
        pass

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Submits the assignment, \
        assuming the correct files are in the given directory.")    
    parser.add_argument('assign', type=str,
                        help='the assignment to submit')
    args = parser.parse_args()
    main(args.assign)
