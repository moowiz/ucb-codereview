import sys
import sqlite3

if __name__ == "__main__":
    conn = sqlite3.connect("codereview_db.sqlite")
    cursor = conn.cursor()
    while True:
        query = input()
        if "quit" in query and len(query) < 6:
            sys.exit(0)
        print(cursor.execute(query).fetchall())
        