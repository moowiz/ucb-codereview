"""
A file for creating the sqlite file with the appropriate schema.
Needs to be run to initialize DB before code review tool can be used.

WARNING:
    Database manipulations in this file are prone to SQL injection.
    It's fine in this case, since it does not take any user input.
    Do not use this code anywhere else without proper modification!
"""

import os
import sqlite3

from utils import read_db_path


# A dictioarny repr of the schema. Mapping is
# { table_name : { column_name: column_type } }
SCHEMA = {
        'upload': {
            'last': 'INTEGER' # unix time of last upload
            },
        'roster': {
            'partners': 'TEXT', # login, sorted lexicalgraphically if > 1
            'assignment': 'TEXT', # assignment name, eg 'proj4'
            'issue': 'INTEGER' # issue number on rietveld
            }
        }


def bkup_if_exists(path):
    """
    Checks if a db already exists. If it does, moves the current
    db to db.bkp.

    Args:
        path: path of sqlite db
    """
    try:
        # throws OSError if does not exist or is not a file
        os.rename(path, path+".bkp")
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
