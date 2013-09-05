import argparse
import datetime
import os

from launchpadlib import launchpad


NAME = 'Dolph Mathews'
LP_INSTANCE = 'production'
CACHE_DIR = os.path.expanduser('~/.launchpadlib/cache/')

NOW = datetime.datetime.utcnow()
TWO_MONTHS_AGO = (NOW - datetime.timedelta(days=65)).utctimetuple()


def unassign_if_inactive(task):
    if task.assignee is not None:
        date_assigned = task.date_assigned.utctimetuple()
        date_last_message = task.bug.date_last_message.utctimetuple()
        date_last_updated = task.bug.date_last_updated.utctimetuple()
        last_touched = max(date_last_message, date_last_updated)
        if date_assigned < TWO_MONTHS_AGO and last_touched < TWO_MONTHS_AGO:
            print 'Unassigning %s (%s)' % (task.web_link, task.status)

            task.assignee = None
            if task.status == 'In Progress':
                task.status = 'Triaged'
            task.bug.newMessage(content='Unassigning due to inactivity.')
            task.lp_save()


def main():
    parser = argparse.ArgumentParser(
        description='Unassign inactive launchpad bugs.')
    parser.add_argument('projects', metavar='projects', nargs='+')
    args = parser.parse_args()

    lp = launchpad.Launchpad.login_with(NAME, LP_INSTANCE, CACHE_DIR)

    for project in args.projects:
        tasks = lp.projects[project].searchTasks()
        for task in tasks:
            unassign_if_inactive(task)


if __name__ == '__main__':
    main()
