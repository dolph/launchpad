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

# github markdown rendering breaks when you give it more than 10 nested bullet
# points, so we carry a max value to avoid the broken rendering.
MAX_INDENTATION = 10


def query(project, branch, filters):
    command = ['ssh', '-p', '29418', 'review.openstack.org']
    command.extend(['gerrit', 'query', '--format=JSON'])
    command.extend(['--dependencies'])
    command.extend(['--current-patch-set'])
    command.extend(
        ['project:%(project)s AND branch:%(branch)s AND status:open' % {
            'project': project,
            'branch': branch}])
    if filters:
        command.extend(['AND %s' % ' AND '.join(filters)])

    # output command for debugging
    # print(' '.join(command))
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
    if indentation >= MAX_INDENTATION:
        # bail early if we're being asked to produce markdown that github can't
        # render.
        return

    # iterate through the hierarchy in order by change number (oldest to
    # newest). there must be a simpler way to do this? whatever it is, it's
    # escaping me right now.
    change_numbers = map(unicode, sorted(map(int, hierarchy.keys())))
    for change_number in change_numbers:
        change = hierarchy[change_number]
        authors = set([
            change['owner']['username'],
            change['currentPatchSet']['uploader']['username']])

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

        reviewers = []
        passing_tests = None
        work_in_progress = False
        blocked_by = []
        needs_revision_by = []
        plus_ones_by = []
        plus_twos_by = []
        approved_by = []
        for approval in change['currentPatchSet'].get('approvals', []):
            if approval['type'] == 'Workflow' and approval['value'] == '-1':
                work_in_progress = True
            if approval['type'] == 'Verified' and approval['value'] == '-2':
                passing_tests = False
            if approval['type'] == 'Verified' and approval['value'] == '-1':
                passing_tests = False
            if approval['type'] == 'Verified' and approval['value'] == '1':
                passing_tests = True
            if approval['type'] == 'Code-Review' and approval['value'] == '-2':
                blocked_by.append(approval['by']['username'])
            if approval['type'] == 'Code-Review' and approval['value'] == '-1':
                needs_revision_by.append(approval['by']['username'])
            if approval['type'] == 'Code-Review' and approval['value'] == '1':
                plus_ones_by.append(approval['by']['username'])
            if approval['type'] == 'Code-Review' and approval['value'] == '2':
                plus_twos_by.append(approval['by']['username'])
            if approval['type'] == 'Workflow' and approval['value'] == '1':
                approved_by.append(approval['by']['username'])

            if approval['type'] == 'Code-Review':
                reviewers.append(approval['by']['username'])

        if blocked_by:
            status = ' (**blocked** by %s)' % ', '.join(sorted(blocked_by))
        elif approved_by and passing_tests is False:
            status = ' (approved but **failing**)'
        elif approved_by and passing_tests is None:
            status = ' (gating)'
        elif passing_tests is False:
            status = ' (failing)'
        elif passing_tests is None:
            status = ' (pending tests)'
        elif approved_by:
            # this is shown when an approved patch depends on one that is not
            # approved
            status = ' (approved)'
        elif work_in_progress:
            status = ' (WIP)'
        elif needs_revision_by:
            status = (' (**needs revision** according to %s)' %
                      ', '.join(sorted(needs_revision_by)))
            reviewers = set(reviewers).difference(needs_revision_by)
        elif plus_twos_by:
            status = (' (**+2** by %s)' %
                      ', '.join(sorted(plus_twos_by)))
            reviewers = set(reviewers).difference(plus_twos_by)
        elif plus_ones_by:
            status = (' (**+1** by %s)' %
                      ', '.join(sorted(plus_ones_by)))
            reviewers = set(reviewers).difference(plus_ones_by)
        else:
            status = ''

        # remove authors from the reviewers list
        reviewers = set(reviewers).difference(authors)

        print('%s- %s[%s](%s)%s' % (
            ' ' * indentation * 2,
            reference,
            change['subject'],
            change['url'],
            status))
        extra_reviewers = (
            '; also reviewed by ' + ', '.join(sorted(reviewers))
            if reviewers else '')
        print('%sAuthored by %s%s.' % (
            ' ' * (indentation + 1) * 2,
            ', '.join(authors),
            extra_reviewers))
        print_hierarchy(change.get('dependencies', {}), indentation + 1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('project')
    parser.add_argument('--branch', default='master')
    parser.add_argument('filters', nargs='*')
    args = parser.parse_args()
    changes = query(args.project, args.branch, args.filters)
    hierarchy = build_hierarchy(changes)
    if hierarchy:
        print_hierarchy(hierarchy)
    else:
        print('(this list is empty!)')
