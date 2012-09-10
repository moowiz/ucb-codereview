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
IMPORTANT_FILES = (GMAILS_FILE, SECTIONS_FILE, LOGINS_FILE)

def ignore_line(line):
    return "Looking for files to turn in...." in line or "Submitting " in line \
            or "Skipping directory" in line or "Skipping file " in line or "Created MY.PARTNERS" in line

class IOHandler:
    def __init__(self, read_stream, out, partners):
        self.read_stream = read_stream
        self.out = out
        self.partners = partners
    def get_char(self):
        return decode(self.read_stream.read(1))
    def read_line(self):
        char = self.get_char()
        s = char
        while True:
            if s.startswith("Login: "):
                self.handle_login()
                return self.read_line()
            if s.endswith("/no]") or s[-1] == "\n":
                break
            s += self.get_char()            
        return s
    def handle_login(self):
        if self.partners:
            part = self.partners.pop(0)
            self.write_out(part + "\n\r")
            return self.read_line()
        else:
            self.write_out(".\n")
            self.read_line()
            self.write_out("yes\n") 
            return self.read_line()     
    def write_out(self, thing):
        if type(thing) != bytes:
            thing = bytes(thing, "utf-8")
        self.out.write(thing)
        try:
            self.out.flush()
        except IOError as e:
            if 'Errno 32' in str(e):
                return
            else:
                raise e
    def read_all(self):
        return self.read_stream.read()

def decode(x):
    return x.decode('utf-8')

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

    cmd = "/share/b/grading/bin/submit " + assign
    proc = Popen(cmd.split(), stdin=PIPE, stdout=PIPE, stderr=PIPE)
    sin = proc.stdin
    handler = IOHandler(proc.stderr, sin, partners)
    special = False
    while True:
        line = handler.read_line()
        if "Would you like to submit additional" in line:
            handler.write_out("no\n")
            continue
        if "Copying submission of assignment" in line:
            print(line)
            break
        print_it = True
        read = not ignore_line(line)
        if not special:
            for f in IMPORTANT_FILES:
                if f in line:
                    handler.write_out("yes\n")
                    print_it = False
        else:
            def my_filter(l):
                l = list(map(lambda x: x.replace('./', ''), l.split()))
                return list(filter(lambda x: x not in IMPORTANT_FILES, l))
            files = []
            while not line.startswith("Is this correct"):
                files.extend(my_filter(line))
                line = handler.read_line()
            arr = [[]]
            tostr = lambda x: ", ".join(x)
            WIDTH_OF_OUTPUT = 50
            while(files):
                if len(tostr(arr[-1])) > WIDTH_OF_OUTPUT:
                    arr.append([])
                arr[-1].append(files.pop(0))
            arr = list(map(lambda x: "  " + tostr(x), arr))
            print()
            print('\n'.join(arr))
            special = False
        if print_it:
            if "You must turn in " in line:
                print("\n\nPlease email Stephen Martinis if you see this message with a log of what you inputted into the submit program\n\n")
                handler.read_all()
                return
            if "Submission FAILS by request" in line:
                print(line)
                handler.read_all()
                return
            if "perl: warning" in line:
                print("ERROR: \"{}\". Please talk to a TA.".format(line))
                handler.read_all()
                return
            if not ignore_line(line):
                print(line.strip(), end=" ")
            sys.stdout.flush()
            if "The files you have submitted are" in line:
                special = True
            elif read:
                handler.write_out(sys.stdin.readline())
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
        value = value.strip()
        if value == '.':
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
        regex = '^' + config.CLASS_NAME + '-[a-zA-Z0-9]{2,3}$'
        return re.match(regex, s)
    partners = my_prompt("Enter your partner(s) (if you have any) full logins.", "Login", validate, "Invalid " + config.CLASS_NAME + " login {}")
    partners.append(utils.getuser())
    partners = list(set(partners))
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
    join_str = ", "
    print("GMails:   {}".format(join_str.join(gmails)))
    print("Sections: {}".format(join_str.join(sections)))
    print("Logins:   {}".format(join_str.join(partners)))

def main(assign, flag=False):
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
                return
            fi.close()
            return rval
        gmails = read_def(GMAILS_FILE)
        sections = read_def(SECTIONS_FILE)
        partners = read_def(LOGINS_FILE)
        if not all((gmails, sections, partners)):
            main(assign, True)
            return
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

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Submits the assignment, \
        assuming the correct files are in the current directory.")    
    parser.add_argument('assign', type=str,
                        help='the assignment to submit')
    args = parser.parse_args()
    main(args.assign)
