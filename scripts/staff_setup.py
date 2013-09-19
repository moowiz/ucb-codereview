import base
import argparse
import os

import account_setup as setup

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Creates the email->section mappings for accounts")
    parser.add_argument('mapping', type=str,
                        help='the path to the csv file containing email to section mappings')
    args = base.init(parser)

    setup.main(os.path.expanduser(args.mapping), staff=True)
