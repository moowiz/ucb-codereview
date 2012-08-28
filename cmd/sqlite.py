import sys
import sqlite3
import utils

if __name__ == "__main__":
    conn = sqlite3.connect(utils.read_db_path)
    cursor = conn.cursor()
    while True:
        query = input()
        if "quit" in query and len(query) < 6:
            sys.exit(0)
        print(cursor.execute(query).fetchall())
