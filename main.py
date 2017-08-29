# -*- coding: utf-8 -*-

import requests
from requests.auth import HTTPBasicAuth
import json
import datetime
from dateutil.parser import parse
import itertools
from operator import itemgetter, attrgetter
import config


def url_issues_last_couple_weeks():

    today = datetime.date.today()
    start_date = today - datetime.timedelta(days=today.weekday() + 7)

    url_template = '{}/rest/api/latest/search' \
                   '?jql=worklogDate>"{:%Y/%m/%d}"&fields=key&maxResults=1000'.format(config.base_url, start_date)

    return url_template


def get_issues(url):

    result = list()

    response = requests.get(url, auth=config.auth)

    issues = json.loads(response.content)
    if 'issues' not in issues:
        return result

    for issue in issues['issues']:
        try:
            key = issue['key']
            result.append(key)
        except KeyError:
            continue

    return result


def get_issues_description(issues):

    result = dict()

    url_template = '{}/rest/api/latest/issue/{{}}?fields=summary,parent'.format(config.base_url)

    for issue_key in issues:

        response = requests.get(
            url_template.format(issue_key),
            auth=config.auth
        )

        issue = json.loads(response.content)

        description = u''
        if 'parent' in issue['fields']:
            descriptions = list()
            descriptions.append(
                u'{} {}'.format(
                    issue['fields']['parent']['key'],
                    issue['fields']['parent']['fields']['summary']
                )
            )
            descriptions.append(u'{}'.format(issue['fields']['summary']))
            description = u', '.join(descriptions)
        else:
            description = u'{} {}'.format(
                issue_key,
                issue['fields']['summary']
            )

        result[issue_key] = description

    return result


def get_work_logs(issues):

    url_template = '{}/rest/api/latest/issue/{{}}/worklog'.format(config.base_url)

    result = list()

    for issue_key in issues:

        response = requests.get(
            url_template.format(issue_key),
            auth=config.auth
        )

        work_logs = json.loads(response.content)
        if 'worklogs' not in work_logs:
            return result

        for record in work_logs['worklogs']:
            try:

                result.append(
                    {
                        'key': issue_key,
                        'seconds': int(record['timeSpentSeconds']),
                        'author': record['author']['name'],
                        'period': parse(record['started']).date()
                    }
                )
            except KeyError:
                continue

    return result


def group_by_author(logs):

    result = dict()

    for key, group in itertools.groupby(logs, itemgetter('author')):

        result[key] = group_by_period(list(group))

    return result


def group_by_period(logs):

    result = dict()

    for key, group in itertools.groupby(logs, itemgetter('period')):

        # result[key] = sum(item['seconds'] for item in list(group))
        result[key] = group_by_issue(list(group))

    return result


def group_by_issue(logs):

    result = dict()

    for key, group in itertools.groupby(logs, itemgetter('key')):

        result[key] = sum(item['seconds'] for item in list(group))

    return result


if __name__ == '__main__':

    issues = get_issues(url_issues_last_couple_weeks())

    logs = get_work_logs(issues)
    descriptions = get_issues_description(issues)

    logs = sorted(logs, key=itemgetter('author', 'period'))

    result = group_by_author(logs)

    skip = False
    if not skip:
        for author in result:
            for period in sorted(result[author]):
                for key in sorted(result[author][period]):

                    print u'{}\t{}\t{}\t{}'.format(
                        author,
                        period,
                        datetime.timedelta(seconds=result[author][period][key]),
                        descriptions[key]
                    )
