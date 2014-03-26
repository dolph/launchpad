import argparse
import datetime
import os

from launchpadlib import launchpad
from lazr.restfulclient import errors

NAME = 'Dolph Mathews'
LP_INSTANCE = 'production'
CACHE_DIR = os.path.expanduser('~/.launchpadlib/cache/')

NOW = datetime.datetime.utcnow()
TWO_MONTHS_AGO = (NOW - datetime.timedelta(days=65)).utctimetuple()

# certain bugs are basically impossible to update due to LP timeouts
IGNORED_BUGS = [1229324]


def save_task(task, retries=10):
    try:
        task.lp_save()
    except errors.ServerError:
        if retries:
            return save_task(task, retries - 1)
        return False
    return True


def target_committed_tasks_to_milestone_and_release(project, milestone):
    for task in project.searchTasks(status='Fix Committed'):
        if task.bug.id in IGNORED_BUGS:
            continue

        print(task.web_link)
        mutated = False

        if task.milestone != milestone:
            task.milestone = milestone
            print('\tSetting milestone to %s...' % milestone)
            mutated = True

        if task.status != 'Fix Released':
            task.status = 'Fix Released'
            print('\tSetting status to Fix Released...')
            mutated = True

        if mutated:
            if save_task(task):
                print('\tSaved.')
            else:
                print('\tERROR saving task. Skipping.')
        else:
            print('\tNo changes.')


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
