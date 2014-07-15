import argparse
import datetime
import os

from launchpadlib import launchpad


NAME = 'Dolph Mathews'
LP_INSTANCE = 'production'
CACHE_DIR = os.path.expanduser('~/.launchpadlib/cache/')
DRY_RUN = False

NOW = datetime.datetime.utcnow()


def unassign_if_inactive(task, date_threshold):
    if task.assignee is not None:
        date_assigned = task.date_assigned.utctimetuple()
        date_last_message = task.bug.date_last_message.utctimetuple()
        date_last_updated = task.bug.date_last_updated.utctimetuple()
        last_touched = max(date_last_message, date_last_updated)
        if date_assigned < date_threshold and last_touched < date_threshold:
            print 'Unassigning %s (%s)' % (task.web_link, task.status)

            task.assignee = None
            if task.status == 'In Progress':
                task.status = 'Triaged'
            task.bug.newMessage(
                content='Automatically unassigning due to inactivity.')

            if not DRY_RUN:
                task.lp_save()


def main(date_threshold):
    lp = launchpad.Launchpad.login_with(NAME, LP_INSTANCE, CACHE_DIR)

    for project in args.projects:
        tasks = lp.projects[project].searchTasks()
        for task in tasks:
            unassign_if_inactive(task, date_threshold)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Unassign inactive launchpad bugs.')
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--days-inactive', type=int, default=90)
    parser.add_argument('projects', metavar='projects', nargs='+')
    args = parser.parse_args()

    DRY_RUN = args.dry_run

    date_threshold = NOW - datetime.timedelta(days=args.days_inactive)
    date_threshold = date_threshold.utctimetuple()

    main(date_threshold)
