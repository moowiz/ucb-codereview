import sys
import sqlite3
import utils
import argparse

def main(login, assign):
    conn = sqlite3.connect(utils.read_db_path())
    cursor = conn.cursor()

    query = "SELECT FROM roster WHERE partners=?"
    if assign:
        query += " AND assign=?"
        res = cursor.execute(query, (login, assign))
    else:
        res = cursor.execute(query, (login,))
    for row in res.fetchall():
        print(row)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Find the issue numbers for a student")
    parser.add_argument('login', type=str, help='The student\'s login')
    parser.add_argument('--assign', '-a', type=str, help="The assignment to look at")
    args = parser.parse_args()
    main(args.login, args.assign)
