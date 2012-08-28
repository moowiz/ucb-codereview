#! /usr/bin/env python3

import sys
import subprocess
import argparse
import os

GMAILS_FILE = "MY.GMAILS"
SECTIONS_FILE = "MY.SECTIONS"

def run_submit(assign):
    """Runs submit. Basic, slightly dumb version."""
    # print "running command {}".format(cmd)
    # print "cwd {}".format(os.getcwd())
    cmd = "submit " + assign
    proc = subprocess.call(cmd.split())

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

def write_defaults(defaults, filename):
    out = open(filename, 'w')
    out.write("\n".join(defaults))
    out.flush()
    out.close()

def get_gmails():
    """
    Prompts the user for their gmails, and stores the file in the GMAILS_FILE file
    """
    gmails = my_prompt("Enter you and your partner's gmail addresses.", "GMail", GMAILS_FILE)
    write_defaults(gmails, GMAILS_FILE)
    return gmails

def get_sections():
    sections = my_prompt("Enter you and your partner's section numbers.", "Section Number", SECTIONS_FILE)
    write_defaults(sections, SECTIONS_FILE)
    return sections

def main(assign):
    gmails = get_gmails()
    sections = get_sections()
    print("")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Submits the assignment, \
        assuming the correct files are in the given directory.")    
    parser.add_argument('assign', type=str,
                        help='the assignment to submit')
    args = parser.parse_args()
    main(args.assign)