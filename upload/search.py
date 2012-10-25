import sys
import sqlite3
import utils
import argparse

def main(login, assign, issue):
    conn = sqlite3.connect(utils.read_db_path())
    cursor = conn.cursor()

    query = "SELECT * FROM roster"
    if issue:
        query += " WHERE issue=?"
        res = cursor.execute(query, (issue,))
    else:
        query += " WHERE partners=?"
        if assign:
            query += " AND assignment=?"
            res = cursor.execute(query, (login, assign))
        else:
            res = cursor.execute(query, (login,))
    for row in res.fetchall():
        print(row)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Find the issue numbers for a student")
    parser.add_argument('-l', '--login', type=str, help='The student\'s login')
    parser.add_argument('-a', '--assign', type=str, help="The assignment to look at")
    parser.add_argument('-i', '--issue', type=int, default=0, help="The issue number.")
    args = parser.parse_args()
    main(args.login, args.assign, args.issue)
