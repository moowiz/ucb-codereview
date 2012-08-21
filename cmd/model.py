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

    def last_uploaded(self):
        """
        Retrieve last upload time from database.

        Returns:
            Unix time in integer if exists, else None
        """
        get_last_upload_sql = "SELECT last FROM upload LIMIT 1"
        result = self.cursor.execute(get_last_upload_sql).fetchone()
        if result:
            # if not empty, then result should be tuple with 1 elem
            return result[0]
        else:
            # this clause not really necessary
            return None

    def set_last_uploaded(self, time_int):
        """
        Update the last upload time.

        Args:
            time_int: integer repr. unix time
        """
        if self.last_uploaded():
            # if an entry exists, then we need an UPDATE command
            update_last_upload_sql = "UPDATE upload SET last = ?"
            self.cursor.execute(update_last_upload_sql, (time_int,))
            self.conn.commit()
        else:
            # we need to create a new entry
            insert_last_upload_sql = "INSERT INTO upload VALUES (?)"
            self.cursor.execute(insert_last_upload_sql, (time_int,))
            self.conn.commit()
