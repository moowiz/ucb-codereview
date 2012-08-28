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
import utils

from utils import read_db_path, get_timestamp_str


# A dictionary repr of the schema. Mapping is
# { table_name : { column_name: column_type } }
SCHEMA = {
        'upload': {
            'assign': 'TEXT', #the assignment for which we're looking for the last time
            'last': 'INTEGER' # unix time of last upload
            },
        'roster': {
            'partners': 'TEXT', # login, sorted lexicographically if > 1
            'assignment': 'TEXT', # assignment name, eg 'proj4'
            'issue': 'INTEGER' # issue number on rietveld
            },
        'section_to_email': {
            'section': 'INTEGER', # section number for the staff number
            'email': 'TEXT' # staff member email
            },
        'important_file': {
            'assignment':'TEXT',
            'file': 'TEXT'
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
    newpath = path + "." + get_timestamp_str() + BACKUP_EXT
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
    The main function to run. Populates the database with basic info. 
    """
    db_path = read_db_path()
    bkup_if_exists(db_path)
    create_table(db_path)
    queries = ["INSERT INTO section_to_email (section, email) VALUES (201, 'moowiz2020@gmail.com')",
               "INSERT INTO section_to_email (section, email) VALUES (201, 'sharad.vikram@gmail.com')", 
               "INSERT INTO important_file (assignment, file) VALUES ('hw05', 'hw5.py')"]
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    for query in queries:
        cursor.execute(query)
    conn.commit()
    conn.close()
    utils.chown_staff_master(db_path)
    utils.chmod_own_grp(db_path)

if __name__ == "__main__":
    main()
