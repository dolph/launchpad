import argparse
import datetime
import os

from launchpadlib import launchpad


NAME = 'Dolph Mathews'
LP_INSTANCE = 'production'
CACHE_DIR = os.path.expanduser('~/.launchpadlib/cache/')

NOW = datetime.datetime.utcnow()
TWO_MONTHS_AGO = (NOW - datetime.timedelta(days=65)).utctimetuple()


def target_committed_tasks_to_milestone_and_release(project, milestone):
    for task in project.searchTasks(status='Fix Committed'):
        print('Targeting: %s' % task.web_link)
        task.milestone = milestone
        task.status = 'Fix Released'
        task.lp_save()


def main():
    parser = argparse.ArgumentParser(
        description='Publish a release of an OpenStack Python client.')
    parser.add_argument('project')
    parser.add_argument('milestone')
    args = parser.parse_args()

    lp = launchpad.Launchpad.login_with(NAME, LP_INSTANCE, CACHE_DIR)
    project = lp.projects[args.project]

    milestones = [x for x in project.active_milestones
                  if x.name == args.milestone]
    if not milestones:
        quit('Unable to find milestone by name: %s' % args.milestone)
    elif len(milestones) > 1:
        quit(
            'Milestone name is ambiguous (different release series?): %s' %
            args.milestone)
    milestone = milestones[0]

    target_committed_tasks_to_milestone_and_release(project, milestone)

    date_released = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M')

    print("""

    In the repo, run:

        git tag -s %(milestone)s && git push gerrit %(milestone)s

    On Launchpad, click Create Release:

        %(milestone_url)s

    Enter the current UTC time as the Date Released:

       %(date_released)s

    """ % {
        'milestone': args.milestone,
        'milestone_url': milestone.web_link,
        'date_released': date_released})


if __name__ == '__main__':
    main()
