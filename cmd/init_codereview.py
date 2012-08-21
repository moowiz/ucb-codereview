"""
A file for creating the sqlite file with the appropriate schema.
Needs to be run to initialize DB before code review tool can be used.

WARNING:
    Database manipulations in this file are prone to SQL injection.
    It's fine in this case, since it does not take any user input.
    Do not use this code anywhere else without proper modification!
"""

import sys
import os     
import os.path
import sqlite3   
from datetime import datetime

from utils import read_db_path


# A dictionary repr of the schema. Mapping is
# { table_name : { column_name: column_type } }
SCHEMA = {
        'upload': {
            'last': 'INTEGER' # unix time of last upload
            },
        'roster': {
            'partners': 'TEXT', # login, sorted lexicographically if > 1
            'assignment': 'TEXT', # assignment name, eg 'proj4'
            'issue': 'INTEGER' # issue number on rietveld
            },
        'queue': {
            'reviewer': 'TEXT',
            'assigned': 'INTEGER'
            }
        }

BACKUP_EXT = ".bkp"

def bkup_if_exists(path):
    """
    Checks if a db already exists. If it does, moves the current
    db to db.bkp.

    Args:
        path: path of sqlite db
    """
    now = datetime.now() #-2012-08-21-2-45
    date_str = now.strftime(".%Y-%m-%d-%H-%M")
    newpath = path + date_str + BACKUP_EXT
    if os.path.exists(newpath):
        raise RuntimeError("Tried to backup the database too fast!") #not sure about this error message
    print('path {}'.format(newpath))
    try:
        # throws OSError if does not exist or is not a file
        os.rename(path, newpath)
    except OSError:
        pass


def create_table(path):
    """
    Call bkup_if_exists before this function.
    Creates tables according to SCHEMA.

    Args:
        path: where the db should be.
    """
    conn = sqlite3.connect(path)
    cursor = conn.cursor()
    for table, columns in SCHEMA.items():
        # create list of "col_name col_type"
        columns = ["{0} {1}".format(col_name, col_type) \
                for col_name, col_type in columns.items()]
        # join the list with ","
        columns_str = ",".join(columns)
        # now we can form the SQL string.
        # again, this is NOT sql-injection safe, do not copy-paste
        cursor.execute("CREATE TABLE {0} ({1})".format(table, columns_str))
    conn.commit()
    conn.close()


def main():
    """
    The main function to run.
    """
    db_path = read_db_path()
    bkup_if_exists(db_path)
    create_table(db_path)


if __name__ == "__main__":
    main()
