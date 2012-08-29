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
    def read_until_newline(stream):
        s = bs(stream.read(1))
        count = 1
        while count < 5:
            print(s)
            s = bs(stream.read(1))
            count += 1
        return s
    cmd = "submit " + assign
    temp_file = open('.temp', 'w')
    reader = open('.temp', 'r')
    proc = Popen(cmd.split(), stdin=PIPE, stdout=temp_file, stderr=temp_file)
    proc.communicate(input=bs('no\n'))
    temp_file.flush()
    print(reader.read())
    print('aaaaaa')
    print('initial out {} initial err {}'.format(out, err))
    to_write = proc.stdin
    to_write.write(bs('no\n'))
    read_until_newline(proc.stdout)    
    read_until_newline(proc.stderr)
    print(proc.stdout)
    print(proc.stderr)
    # print(proc.stdout.read())
    # print(proc.stderr.read())
    out, err = proc.communicate()
    print('initial out {} initial err {}'.format(out, err))
    count = 0
    while count < 7:
        print('out {} err {}'.format(out_sio.getvalue(), err_sio.getvalue()))
        to_send = sys.stdin.readline()
        proc.communicate(to_send)
        count += 1
    # proc = Popen(cmd.split(), stdin=PIPE, stdout=PIPE, stderr=PIPE)
    # out, err = proc.communicate(input=".")
    # print("out {} err {}".format(out, err))
        

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