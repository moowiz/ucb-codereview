import argparse
import model

def main(login, assign, issue):
    db = model.CodeReviewDatabase()
    if issue:
        res = db.query_issue(issue)
    elif login:
        if assign:
            res = db.get_issue_number(login, assign)
        else:
            res = db.query_student(login)
    for row in res.fetchall():
        print(row)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Find the issue numbers for a student")

    group = parser.add_mutually_exclusive_group()
    group.add_argument('-l', '--login', type=str, help='The student\'s login')
    group.add_argument('-i', '--issue', type=int, default=0, help="The issue number.")

    parser.add_argument('-a', '--assign', default=None, type=str, help="The assignment to look at")

    args = parser.parse_args()
    main(args.login, args.assign, args.issue)
