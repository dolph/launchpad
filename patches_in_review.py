import argparse
import json
import re
import subprocess


BUG_RE = r'''(?x)                # verbose regexp
             \b([Bb]ug|[Ll][Pp]) # bug or lp
             [ \t\f\v]*          # don't want to match newline
             [:]?                # separator if needed
             [ \t\f\v]*          # don't want to match newline
             [#]?                # if needed
             [ \t\f\v]*          # don't want to match newline
             (\d+)               # bug number'''

BP_RE = r'''(?x)                         # verbose regexp
            \b([Bb]lue[Pp]rint|[Bb][Pp]) # a blueprint or bp
            [ \t\f\v]*                   # don't want to match newline
            [#:]?                        # separator if needed
            [ \t\f\v]*                   # don't want to match newline
            ([0-9a-zA-Z-_]+)             # any identifier or number'''


def query(project, branch):
    command = ['ssh', '-p', '29418', 'review.openstack.org']
    command.extend(['gerrit', 'query', '--format=JSON'])
    command.extend(['--dependencies'])
    command.extend(['--current-patch-set'])
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
        bug_match = re.search(BUG_RE, change['commitMessage'])
        bug_number = bug_match.group(2) if bug_match is not None else None

        bp_match = re.search(BP_RE, change['commitMessage'])
        bp_slug = bp_match.group(2) if bp_match is not None else None

        if bp_slug:
            reference = '**Blueprint [%s](%s)**: ' % (
                bp_slug,
                'https://blueprints.launchpad.net/openstack/?searchtext=%s' % (
                    bp_slug))
        elif bug_number:
            reference = '**Bug [%s](%s)**: ' % (
                bug_number,
                'https://bugs.launchpad.net/bugs/%s' % bug_number)
        else:
            reference = ''

        blocked = False
        approved = False
        work_in_progress = False
        for approval in change['currentPatchSet'].get('approvals', []):
            if approval['type'] == 'Workflow' and approval['value'] == '1':
                approved = True
            if approval['type'] == 'Workflow' and approval['value'] == '-1':
                work_in_progress = True
            if approval['type'] == 'Code-Review' and approval['value'] == '-2':
                blocked = True

        if blocked:
            status = ' (blocked)'
        elif approved:
            status = ' (approved)'
        elif work_in_progress:
            status = ' (WIP)'
        else:
            status = ''

        print('%s- %s[%s](%s)%s' % (
            ' ' * indentation * 2,
            reference,
            change['subject'],
            change['url'],
            status))
        print_hierarchy(change.get('dependencies', {}), indentation + 1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('project')
    parser.add_argument('--branch', default='master')
    args = parser.parse_args()
    changes = query(args.project, args.branch)
    hierarchy = build_hierarchy(changes)
    print_hierarchy(hierarchy)
