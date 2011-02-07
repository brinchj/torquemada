from twisted.python import log

import re
from collections import defaultdict


def load_rules():
    log.msg('loading ad rules')
    groups = []
    for line in file('easylist.txt'):
        if '!' in line or '||' in line or '#' in line:
            continue
        line = line.strip()
        line = re.escape(line)
        if line[0:1] == r'\|':
            line = '^%s' % line[2:]
        if line[-2:] == '\|':
            line = '%s$' % line[:-2]
        groups.append(line)
    return (["easylist.txt"], re.compile('|'.join(groups), re.I))
    log.msg('%i rules loaded' % len(groups))

rules = load_rules()
users = defaultdict(lambda: rules)


def blocking_regex(user):
    return users[user][1]


def user_lists(user):
    return users[user][0]


def add_list(user, lst):
    users[user] = (users[user][0] + [lst],
                   re.compile('foobar'))
