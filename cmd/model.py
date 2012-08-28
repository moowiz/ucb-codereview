"""
Data model API for the database.
"""

import sqlite3

class CodeReviewDatabase(object):
    """
    An object API to interact with the sqlite3 database. Initialize it with
    the db path. Be sure to close connections for best performance.
    """

    def __init__(self, db_path):
        """
        Args:
            db_path: the path to find sqlite db at. see utils.read_db_path.
        """
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()

    def close(self):
        """
        Close all open connections
        """
        self.cursor.close()
        self.conn.close()

    def last_uploaded(self, assign):
        """
        Retrieve last upload time from database.

        Returns:
            Unix time in integer if exists, else None
        """
        get_last_upload_sql = "SELECT last FROM upload WHERE assign = ? LIMIT 1"
        result = self.cursor.execute(get_last_upload_sql, (assign,)).fetchone()
        if result:
            # if not empty, then result should be tuple with 1 elem
            return result[0]
        else:
            # this clause not really necessary
            return None

    def set_last_uploaded(self, time_int, assign):
        """
        Update the last upload time.

        Args:
            time_int: integer repr. unix time
        """
        if self.last_uploaded():
            # if an entry exists, then we need an UPDATE command
            update_last_upload_sql = "UPDATE upload WHERE assign = ? SET last = ?"
            self.cursor.execute(update_last_upload_sql, (assign, time_int))
            self.conn.commit()
        else:
            # we need to create a new entry
            insert_last_upload_sql = "INSERT INTO upload VALUES (?, ?)"
            self.cursor.execute(insert_last_upload_sql, (assign, time_int))
            self.conn.commit()
            
    def get_reviewers(self, section):
        sql = "SELEcT email FROM section_to_email WHERE section=?"
        reviewers = self.cursor.execute(sql, (section,))
        temp = []
        for row in reviewers.fetchall():
          temp.append(row[0])
        return temp #maybe add some asserts?

    def get_important_file(self, assignment):
        sql = "SELEcT file FROM important_file WHERE assignment=?"
        files = self.cursor.execute(sql, (assignment,))
        temp = []
        for row in files.fetchall():
          temp.append(row[0])
        return temp #maybe add some asserts?

    @staticmethod    
    def combine_students(students):
        return "".join(sorted(students))

    def get_issue_number(self, students, assign):
        """
        Gets the issue number for the particular student & assignment

        Args:
            students: a tuple of student logins,
                eg. ("cs61a-ab",) or ("cs61a-ab", "cs61a-bc")
            assign: assignment name, eg. "proj1"
        """
        partners = CodeReviewDatabase.combine_students(students)
        get_issue_sql = "SELECT issue FROM roster " + \
                "WHERE partners=? AND assignment=? LIMIT 1"
        res_cur = self.cursor.execute(get_issue_sql, (partners, assign))
        result = res_cur.fetchone()
        if result:
            # if not empty, then result should be tuple with 1 elem
            return result[0]
        else:
            # this clause not really necessary
            return None

    def set_issue_number(self, students, assign, issue_num):
        """
        Records the new issue number for the particular student & assignment
        in the database. Note that this method does not perform checks to
        see if an entry already exists.

        Args:
            students: a tuple of student logins,
                eg. ("cs61a-ab",) or ("cs61a-ab", "cs61a-bc")
            assign: assignment name, eg. "proj1"
            issue_num: the issue number, this comes from upload.py
        """
        partners = CodeReviewDatabase.combine_students(students)
        set_issue_sql = "INSERT INTO roster (partners, assignment, issue)" + \
                "VALUES (?, ?, ?)"
        self.cursor.execute(set_issue_sql, (partners, assign, issue_num))
        self.conn.commit()
