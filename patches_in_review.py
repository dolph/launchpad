import argparse
import json
import subprocess


def query(project, branch):
    command = ['ssh', '-p', '29418', 'review.openstack.org']
    command.extend(['gerrit', 'query', '--format=JSON'])
    command.extend(['--dependencies'])
    command.extend(
        ['project:%(project)s AND branch:%(branch)s AND status:open' % {
            'project': project,
            'branch': branch}])
    print(' '.join(command))
    output = subprocess.check_output(command)

    changes = [json.loads(change) for change in output.splitlines()[:-1]]

    return changes


def build_hierarchy(changes):
    # make it easy to index in to a flat dict by change number
    changes_by_number = dict((str(c['number']), c) for c in changes)

    # this is the hierarchy that we'll mutate and return
    hierarchy = dict(changes_by_number)

    for change in changes:
        if ('dependsOn' in change
                and change['dependsOn'][0]['number'] in changes_by_number):
            # this change depends on another, so drop it from the root
            hierarchy.pop(change['number'])

            # a change can't possibly depend on multiple other changes...
            # right?
            depends_on_change_number = str(change['dependsOn'][0]['number'])
            depends_on_change = changes_by_number[depends_on_change_number]
            depends_on_change.setdefault('dependencies', {})
            depends_on_change['dependencies'][change['number']] = change
    return hierarchy


def print_hierarchy(hierarchy, indentation=0):
    for change_number, change in hierarchy.iteritems():
        print('%s- [%s](%s) ' % (
            ' ' * indentation * 2,
            change['subject'],
            change['url']))
        print_hierarchy(change.get('dependencies', {}), indentation + 1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('project')
    parser.add_argument('--branch', default='master')
    args = parser.parse_args()
    changes = query(args.project, args.branch)
    hierarchy = build_hierarchy(changes)
    print_hierarchy(hierarchy)
