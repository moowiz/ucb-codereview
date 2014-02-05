import base
parser = argparse.ArgumentParser(description="Finds all issues where there are duplicate sections in it. I don't think this should happen anymore...")
args = base.init(parser)

from codereview.models import Issue, Account

def find_all(assign):
    with open('out', 'w') as f:
        issues = Issue.all().filter(u'subject =', assign).fetch(100)
        for iss in issues:
            #print iss.reviewers
            acc = [Account.get_account_for_email(stu) for stu in iss.reviewers]
            #print accs
            acc = [a for a in acc if len(str(a)) > 4]
            #print [a.email for a in acc]
            sections = [a.sections for a in acc]
            if sections:
                all_sections = set(reduce(lambda a, b: a + b, sections))
                #print all_sections
                if len(set(all_sections)) > 1:
                    val = iss.key().id()
                    print val, iss.sections
                    f.write("{} {}\n".format(val, iss.sections))
            else:
                print 'uhoh'
                print iss.sections


def main(assign):
    find_all(assign)

if __name__ == "__main__":
    main(args.assign)

