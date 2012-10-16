import model
import config
import utils
import os
import argparse

db = model.CodeReviewDatabase(utils.read_db_path())

def main(assign, path):
    if "~" in path:
        path = os.path.expanduser(path)
    grades = dict()
    with open(path) as f:
        for line in f:
            if ":" not in line:
                continue
            issue_num, score = list(map(lambda x: x.strip(), line.split(":")))
            if "N" in score:
                continue
            score = int(score)
            issue_num = int(issue_num)
            logins = db.find_logins(issue_num)
            for login in logins:
                grades[login] = score
    for k, v in grades.items():
        print("{}\n{}".format(k, v))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Grades the style for a given assignment")    
    parser.add_argument('assign', type=str,
                        help='the assignment to grade')
    parser.add_argument('path', type=str,
                        help='the path to the file containing the grades')
    args = parser.parse_args()
    main(args.assign, args.path)
