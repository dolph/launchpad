import datetime
import os

from launchpadlib import launchpad


NAME = 'Dolph Mathews'
LP_INSTANCE = 'production'
CACHE_DIR = os.path.expanduser('~/.launchpadlib/cache/')

NOW = datetime.datetime.utcnow()
TWO_MONTHS_AGO = (NOW - datetime.timedelta(days=65)).utctimetuple()


def unassign_if_inactive(bug):
    if bug.assignee is not None:
        date_assigned = bug.date_assigned.utctimetuple()
        date_last_message = bug.bug.date_last_message.utctimetuple()
        date_last_updated = bug.bug.date_last_updated.utctimetuple()
        last_touched = max(date_last_message, date_last_updated)
        if date_assigned < TWO_MONTHS_AGO and last_touched < TWO_MONTHS_AGO:
            print 'Unassigning %s (%s)' % (bug.web_link, bug.status)

            bug.assignee = None
            if bug.status == 'In Progress':
                bug.status = 'Triaged'
            bug.bug.newMessage(content='Unassigning due to inactivity.')
            bug.lp_save()


def main():
    lp = launchpad.Launchpad.login_with(NAME, LP_INSTANCE, CACHE_DIR)
    project = lp.projects['keystone']
    bugs = project.searchTasks()
    for bug in bugs:
        unassign_if_inactive(bug)


if __name__ == '__main__':
    main()
