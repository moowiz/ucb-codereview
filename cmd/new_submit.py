#! /usr/bin/env python3

import sys
from subprocess import Popen, PIPE
import argparse
import os
import io

GMAILS_FILE = "MY.GMAILS"
SECTIONS_FILE = "MY.SECTIONS"
LOGINS_FILE = "MY.PARTNERS"
important_files = (GMAILS_FILE, SECTIONS_FILE, LOGINS_FILE)

def run_submit(assign):
    """Runs submit. Basic, slightly dumb version."""
    # print "running command {}".format(cmd)
    # print "cwd {}".format(os.getcwd())
    bs = lambda x: bytes(x, "utf-8")
    dec = lambda x: x.decode('utf-8')
    def get_char(stream):
        got = stream.read(1)
        # print('got {}'.format(got))
        return dec(got)
    def goto_newline(stream):
        s = ""
        c = ""
        while c != "\n":
            c = get_char(stream)
            s += c
        return s
    def ignore_line(line):
        return "Looking for files to turn in...." in line or "Submitting " in line
    def read_line(stream):
        char = get_char(stream)
        s = char
        while True:
            if s.endswith("[yes/no] ") or s[-1] == "\n":
                break
            s += get_char(stream)            
        return s
    def write_out(stream, thing):
        if type(thing) != bytes:
            thing = bs(thing)
        print("writing {} to {}".format(stream, thing))
        stream.write(thing)
        stream.flush()
    cmd = "submit " + assign
    proc = Popen(cmd.split(), stdin=PIPE, stdout=PIPE, stderr=PIPE)
    sin = proc.stdin
    special_line = False
    while True:
        line = read_line(proc.stderr)
        print('read {}'.format(line))        
        if "Submission complete." in line:
            print(line)
            break
        flag = True
        if not special:
            for f in important_files:
                if f in line:
                    write_out(sin, "yes\n")
                    flag = False
        else:
            line = " ".join(list(filter(lambda x: x.replace("./", "") not in important_files, line.split())))
        if flag:
            print(line)
            if "The files you have submitted are" in line:
                special = True
            elif not ignore_line(line):
                write_out(sin, sys.stdin.readline())
        

def my_prompt(initial_message, prompt, defaults_file):
    defaults = None
    if os.path.exists(defaults_file):
        defaults = open(defaults_file, 'r').read().split()
    print(initial_message)
    print("Enter '.' to stop. Hit enter to use the remaining defaults.")
    captured = []
    while True:
        output = prompt
        if defaults:
            output += " " + str(defaults)
        output += ":"
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
    return gmails

def get_partners():
    """
    Prompts the user for their gmails, and stores the file in the GMAILS_FILE file
    """
    partners = my_prompt("Enter you and your partner's logins.", "Login", LOGINS_FILE)
    write_defaults(partners, LOGINS_FILE, string_to_join=" ")
    return partners

def get_sections():
    sections = my_prompt("Enter you and your partner's section numbers.", "Section Number", SECTIONS_FILE)
    write_defaults(sections, SECTIONS_FILE)
    return sections

def main(assign):
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