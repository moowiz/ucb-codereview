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

SECTION_TO_STAFF = {
    "01" : "Varun Pai",
    "02" : "Stephen Martinis",
    "03" : "Allen Nguyen", "03" : "Sharad Vikram",
    "04" : "Albert Wu",
    "11" : "Julia Oh",
    "12" : "Hamilton Nguyen",
    "13" : "Keegan Mann",
    "14" : "Andrew Nguyen",
    "15" : "Varun Pai",
    "16" : "Albert Wu",
    "17" : "Julia Oh",
    "18" : "Hamilton Nguyen",
    "19" : "Stephen Martinis",
    "20" : "Shu Zhong",
    "21" : "Steven Tang",
    "22" : "Andrew Nguyen",
    "23" : "Joy Jeng",
    "24" : "Phillip Carpenter",
    "25" : "Joy Jeng",
    "26" : "Shu Zhong",
    "27" : "Phillip Carpenter",
    "28" : "Allen Nguyen",
    "28" : "Sharad Vikram"
}

STAFF_TO_EMAIL = {
        "Andrew Nguyen" : "andrew.thienlan.nguyen@gmail.com",
        "Joy Jeng" : "joyyjeng@gmail.com",
        "Albert Wu" : "albert12132@gmail.com",
        "Phillip Carpenter" : "pcarpenter1010@gmail.com",
        "Julia Oh" : "juliahhh.oh@gmail.com",
        "Hamilton Nguyen" : "hamilton09nguyen@gmail.com",
        "Varun Pai" : "varunpai12@gmail.com",
        "Steven Tang" : "steventang24@gmail.com",
        "Akihiro Matsukawa" : "akihiro.matsukawa@gmail.com",
        "Allen Nguyen" : "nguyenallen42@gmail.com",
        "Shu Zhong" : "kramerfatman@gmail.com",
        "Keegan Mann" : "keeganmann@gmail.com",
        "Stephen Martinis" : "moowiz2020@gmail.com",
        "Sharad Vikram" : "sharad.vikram@gmail.com"
}

IMPORTANT_FILES = {
    "hw01" : "hw1.py",
    "hw02" : "hw2.py",
    "hw05" : "hw5.py"
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
    query = "INSERT INTO section_to_email (section, email) VALUES (?, ?)"
    db_path = read_db_path()
    bkup_if_exists(db_path)
    create_table(db_path)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    for k,v in SECTION_TO_STAFF.items():
        cursor.execute(query, (k,STAFF_TO_EMAIL[v]))
    query = "INSERT INTO important_file (assignment, file) VALUES (?, ?)"
    for k, v in IMPORTANT_FILES.items():
        cursor.execute(query, (k, v))
    conn.commit()
    conn.close()
    utils.chown_staff_master(db_path)
    utils.chmod_own_grp(db_path)

if __name__ == "__main__":
    main()
