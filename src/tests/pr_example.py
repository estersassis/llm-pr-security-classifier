input_data = {
    "_id": "MDExOlB1bGxSZXF1ZXN0MjA0NjQ2NTU=",
    "id": "MDExOlB1bGxSZXF1ZXN0MjA0NjQ2NTU=",
    "__typename": "PullRequest",
    "repository": "MDEwOlJlcG9zaXRvcnk0MTY0NDgy",
    "author": "MDQ6VXNlcjEyOTYzODc=",
    "author_association": "CONTRIBUTOR",
    "body": "See https://code.djangoproject.com/ticket/23381#ticket\n",
    "created_at": {
        "$date": "2014-08-28T20:29:52.000Z"
    },
    "created_via_email": False,
    "includes_created_edit": False,
    "published_at": {
        "$date": "2014-08-28T20:29:52.000Z"
    },
    "updated_at": {
        "$date": "2014-09-12T07:48:09.000Z"
    },
    "reactions_count": 0,
    "closed": True,
    "closed_at": {
        "$date": "2014-08-28T23:24:15.000Z"
    },
    "comments_count": 4,
    "database_id": 20464655,
    "full_database_id": 20464655,
    "locked": False,
    "number": 3135,
    "participants_count": 3,
    "state": "CLOSED",
    "timeline_items_count": 13,
    "title": "Fix override decorator",
    "additions": 23,
    "base_ref_name": "master",
    "base_ref_oid": "569e0a299ddf484a694d26b283214d1e55f7283e",
    "base_repository": "django/django",
    "can_be_rebased": False,
    "changed_files": 3,
    "deletions": 3,
    "files_count": 3,
    "head_ref_name": "fix_override_decorator",
    "head_ref_oid": "4d2e7fda9ebafa80bf7c4725ca636e0827b09dd7",
    "head_repository": "tchaumeny/django",
    "head_repository_owner": "tchaumeny",
    "is_cross_repository": True,
    "is_draft": False,
    "maintainer_can_modify": False,
    "merge_state_status": "DIRTY",
    "mergeable": "CONFLICTING",
    "merged": False,
    "reviews_count": 0,
    "total_comments_count": 7,
    "timeline_items": [
        {
            "_id": "MDEyOklzc3VlQ29tbWVudDUzNzk1ODQ4",
            "id": "MDEyOklzc3VlQ29tbWVudDUzNzk1ODQ4",
            "__typename": "IssueComment",
            "author": "MDQ6VXNlcjc4ODkxMA==",
            "author_association": "MEMBER",
            "body": "I would find it useful to write two tests targeted specifically at this issue, one for each decorator, in tests/utils_tests/test_timezone.py and tests/i18n/tests.py respectively.\n",
            "created_at": {
                "$date": "2014-08-28T20:48:15.000Z"
            },
            "created_via_email": False,
            "includes_created_edit": False,
            "published_at": {
                "$date": "2014-08-28T20:48:15.000Z"
            },
            "updated_at": {
                "$date": "2014-08-28T20:48:15.000Z"
            },
            "reactions_count": 0,
            "is_minimized": False,
            "database_id": 53795848,
            "full_database_id": 53795848
        },
        {
            "_id": "MDEyOklzc3VlQ29tbWVudDUzODAwMjM3",
            "id": "MDEyOklzc3VlQ29tbWVudDUzODAwMjM3",
            "__typename": "IssueComment",
            "author": "MDQ6VXNlcjc4ODkxMA==",
            "author_association": "MEMBER",
            "body": "buildbot, test this please.\n",
            "created_at": {
                "$date": "2014-08-28T21:14:54.000Z"
            },
            "created_via_email": False,
            "includes_created_edit": False,
            "published_at": {
                "$date": "2014-08-28T21:14:54.000Z"
            },
            "updated_at": {
                "$date": "2014-08-28T21:14:54.000Z"
            },
            "reactions_count": 0,
            "is_minimized": False,
            "database_id": 53800237,
            "full_database_id": 53800237
        },
        {
            "_id": "MDIzOlB1bGxSZXF1ZXN0UmV2aWV3VGhyZWFkMTUzODU0ODg6djI=",
            "id": "MDIzOlB1bGxSZXF1ZXN0UmV2aWV3VGhyZWFkMTUzODU0ODg6djI=",
            "__typename": "PullRequestReviewThread",
            "comments_count": 2,
            "diff_side": "RIGHT",
            "is_collapsed": False,
            "is_outdated": False,
            "is_resolved": False,
            "path": "django/utils/timezone.py",
            "subject_type": "LINE",
            "comments": [
                {
                    "id": "MDI0OlB1bGxSZXF1ZXN0UmV2aWV3Q29tbWVudDE2ODY2NTY4",
                    "__typename": "PullRequestReviewComment",
                    "author": "MDQ6VXNlcjc4ODkxMA==",
                    "author_association": "MEMBER",
                    "body": "Why not remove that line entirely?\n",
                    "created_at": {
                        "$date": "2014-08-28T20:43:52.000Z"
                    },
                    "created_via_email": False,
                    "includes_created_edit": False,
                    "published_at": {
                        "$date": "2014-08-28T20:43:52.000Z"
                    },
                    "updated_at": {
                        "$date": "2014-08-28T21:08:50.000Z"
                    },
                    "is_minimized": False,
                    "reactions_count": 0,
                    "commit": "MDY6Q29tbWl0NDE2NDQ4Mjo0ZDJlN2ZkYTllYmFmYTgwYmY3YzQ3MjVjYTYzNmUwODI3YjA5ZGQ3",
                    "diff_hunk": "@@ -262,9 +262,10 @@ class override(object):\n     \"\"\"\n     def __init__(self, timezone):\n         self.timezone = timezone\n-        self.old_timezone = getattr(_active, 'value', None)\n+        self.old_timezone = None",
                    "drafted_at": {
                        "$date": "2014-08-28T20:43:52.000Z"
                    },
                    "full_database_id": 16866568,
                    "outdated": False,
                    "path": "django/utils/timezone.py",
                    "state": "SUBMITTED",
                    "subject_type": "LINE"
                },
                {
                    "id": "MDI0OlB1bGxSZXF1ZXN0UmV2aWV3Q29tbWVudDE2ODY2Nzgy",
                    "__typename": "PullRequestReviewComment",
                    "author": "MDQ6VXNlcjEyOTYzODc=",
                    "author_association": "CONTRIBUTOR",
                    "body": "Well, \"some people\" consider that attributes should be defined at initialization, which is arguable. If this is not a rule within django codebase, I have no objection to remove those lines.\n",
                    "created_at": {
                        "$date": "2014-08-28T20:47:36.000Z"
                    },
                    "created_via_email": False,
                    "includes_created_edit": False,
                    "published_at": {
                        "$date": "2014-08-28T20:47:36.000Z"
                    },
                    "updated_at": {
                        "$date": "2014-08-28T21:08:50.000Z"
                    },
                    "is_minimized": False,
                    "reactions_count": 0,
                    "commit": "MDY6Q29tbWl0NDE2NDQ4Mjo0ZDJlN2ZkYTllYmFmYTgwYmY3YzQ3MjVjYTYzNmUwODI3YjA5ZGQ3",
                    "diff_hunk": "@@ -262,9 +262,10 @@ class override(object):\n     \"\"\"\n     def __init__(self, timezone):\n         self.timezone = timezone\n-        self.old_timezone = getattr(_active, 'value', None)\n+        self.old_timezone = None",
                    "drafted_at": {
                        "$date": "2014-08-28T20:47:36.000Z"
                    },
                    "full_database_id": 16866782,
                    "outdated": False,
                    "path": "django/utils/timezone.py",
                    "state": "SUBMITTED",
                    "subject_type": "LINE"
                }
            ]
        },
        {
            "_id": "MDIzOkhlYWRSZWZGb3JjZVB1c2hlZEV2ZW50MTU4Njg1NjE3",
            "id": "MDIzOkhlYWRSZWZGb3JjZVB1c2hlZEV2ZW50MTU4Njg1NjE3",
            "__typename": "HeadRefForcePushedEvent",
            "actor": "MDQ6VXNlcjEyOTYzODc=",
            "after_commit": "MDY6Q29tbWl0NDE2NDQ4Mjo0ZDJlN2ZkYTllYmFmYTgwYmY3YzQ3MjVjYTYzNmUwODI3YjA5ZGQ3",
            "created_at": {
                "$date": "2014-08-28T21:08:50.000Z"
            }
        },
        {
            "_id": "MDE1OlN1YnNjcmliZWRFdmVudDE1ODY4NjY0Nw==",
            "id": "MDE1OlN1YnNjcmliZWRFdmVudDE1ODY4NjY0Nw==",
            "__typename": "SubscribedEvent",
            "actor": "MDQ6VXNlcjc4ODkxMA==",
            "created_at": {
                "$date": "2014-08-28T21:10:57.000Z"
            }
        },
        {
            "_id": "MDExOkNsb3NlZEV2ZW50MTU4NzQyODk3",
            "id": "MDExOkNsb3NlZEV2ZW50MTU4NzQyODk3",
            "__typename": "ClosedEvent",
            "actor": "MDQ6VXNlcjkyOTM=",
            "created_at": {
                "$date": "2014-08-28T23:24:15.000Z"
            },
            "state_reason": "COMPLETED"
        },
        {
            "_id": "MDEyOklzc3VlQ29tbWVudDUzNzk5NzMw",
            "id": "MDEyOklzc3VlQ29tbWVudDUzNzk5NzMw",
            "__typename": "IssueComment",
            "author": "MDQ6VXNlcjEyOTYzODc=",
            "author_association": "CONTRIBUTOR",
            "body": "@aaugustin I updated my PR following your comments. Regarding `timezone.override`, it is not a decorator yet (I was working on a PR for that when I run into this bug... but I will add some tests for that case in my PR)\n",
            "created_at": {
                "$date": "2014-08-28T21:10:57.000Z"
            },
            "created_via_email": False,
            "includes_created_edit": False,
            "published_at": {
                "$date": "2014-08-28T21:10:57.000Z"
            },
            "updated_at": {
                "$date": "2014-08-28T21:10:57.000Z"
            },
            "reactions_count": 0,
            "is_minimized": False,
            "database_id": 53799730,
            "full_database_id": 53799730
        },
        {
            "_id": "MDE3OlB1bGxSZXF1ZXN0Q29tbWl0MjA0NjQ2NTU6NGQyZTdmZGE5ZWJhZmE4MGJmN2M0NzI1Y2E2MzZlMDgyN2IwOWRkNw==",
            "id": "MDE3OlB1bGxSZXF1ZXN0Q29tbWl0MjA0NjQ2NTU6NGQyZTdmZGE5ZWJhZmE4MGJmN2M0NzI1Y2E2MzZlMDgyN2IwOWRkNw==",
            "__typename": "PullRequestCommit",
            "commit": "MDY6Q29tbWl0NDE2NDQ4Mjo0ZDJlN2ZkYTllYmFmYTgwYmY3YzQ3MjVjYTYzNmUwODI3YjA5ZGQ3"
        },
        {
            "_id": "MDEyOklzc3VlQ29tbWVudDUzODIwMTA2",
            "id": "MDEyOklzc3VlQ29tbWVudDUzODIwMTA2",
            "__typename": "IssueComment",
            "author": "MDQ6VXNlcjkyOTM=",
            "author_association": "MEMBER",
            "body": "Merged manually in efcbf3e095dce3491eb52774978afe3f7bbdf217 with minor edits, merci.\n",
            "created_at": {
                "$date": "2014-08-28T23:24:15.000Z"
            },
            "created_via_email": False,
            "includes_created_edit": False,
            "published_at": {
                "$date": "2014-08-28T23:24:15.000Z"
            },
            "updated_at": {
                "$date": "2014-08-28T23:24:15.000Z"
            },
            "reactions_count": 0,
            "is_minimized": False,
            "database_id": 53820106,
            "full_database_id": 53820106
        },
        {
            "_id": "MDE0Ok1lbnRpb25lZEV2ZW50MTU4Njg2NjQ2",
            "id": "MDE0Ok1lbnRpb25lZEV2ZW50MTU4Njg2NjQ2",
            "__typename": "MentionedEvent",
            "actor": "MDQ6VXNlcjc4ODkxMA==",
            "created_at": {
                "$date": "2014-08-28T21:10:57.000Z"
            },
            "database_id": 158686646
        },
        {
            "_id": "MDE5OkhlYWRSZWZEZWxldGVkRXZlbnQxNjQ2MjY4NTg=",
            "id": "MDE5OkhlYWRSZWZEZWxldGVkRXZlbnQxNjQ2MjY4NTg=",
            "__typename": "HeadRefDeletedEvent",
            "actor": "MDQ6VXNlcjEyOTYzODc=",
            "created_at": {
                "$date": "2014-09-12T07:48:09.000Z"
            },
            "head_ref_name": "fix_override_decorator"
        },
        {
            "_id": "MDIzOkhlYWRSZWZGb3JjZVB1c2hlZEV2ZW50MTU4NjYyOTcx",
            "id": "MDIzOkhlYWRSZWZGb3JjZVB1c2hlZEV2ZW50MTU4NjYyOTcx",
            "__typename": "HeadRefForcePushedEvent",
            "actor": "MDQ6VXNlcjEyOTYzODc=",
            "created_at": {
                "$date": "2014-08-28T20:31:28.000Z"
            }
        },
        {
            "_id": "MDIzOlB1bGxSZXF1ZXN0UmV2aWV3VGhyZWFkMTUzODU0OTE6djI=",
            "id": "MDIzOlB1bGxSZXF1ZXN0UmV2aWV3VGhyZWFkMTUzODU0OTE6djI=",
            "__typename": "PullRequestReviewThread",
            "comments_count": 1,
            "diff_side": "RIGHT",
            "is_collapsed": False,
            "is_outdated": False,
            "is_resolved": False,
            "path": "django/utils/translation/__init__.py",
            "subject_type": "LINE",
            "comments": [
                {
                    "id": "MDI0OlB1bGxSZXF1ZXN0UmV2aWV3Q29tbWVudDE2ODY2NTg1",
                    "__typename": "PullRequestReviewComment",
                    "author": "MDQ6VXNlcjc4ODkxMA==",
                    "author_association": "MEMBER",
                    "body": "Same question as above.\n",
                    "created_at": {
                        "$date": "2014-08-28T20:44:04.000Z"
                    },
                    "created_via_email": False,
                    "includes_created_edit": False,
                    "published_at": {
                        "$date": "2014-08-28T20:44:04.000Z"
                    },
                    "updated_at": {
                        "$date": "2014-08-28T21:08:50.000Z"
                    },
                    "is_minimized": False,
                    "reactions_count": 0,
                    "commit": "MDY6Q29tbWl0NDE2NDQ4Mjo0ZDJlN2ZkYTllYmFmYTgwYmY3YzQ3MjVjYTYzNmUwODI3YjA5ZGQ3",
                    "diff_hunk": "@@ -154,9 +154,10 @@ class override(ContextDecorator):\n     def __init__(self, language, deactivate=False):\n         self.language = language\n         self.deactivate = deactivate\n-        self.old_language = get_language()\n+        self.old_language = None",
                    "drafted_at": {
                        "$date": "2014-08-28T20:44:04.000Z"
                    },
                    "full_database_id": 16866585,
                    "outdated": False,
                    "path": "django/utils/translation/__init__.py",
                    "state": "SUBMITTED",
                    "subject_type": "LINE"
                }
            ]
        }
    ]
}

output_data = {
  "pr": {
    "title": "Fix override decorator",
    "description": "See https://code.djangoproject.com/ticket/23381#ticket\n"
  },
  "threads": [
    {
      "scope": "PR",
      "discussion": [
        "I would find it useful to write two tests targeted specifically at this issue, one for each decorator, in tests/utils_tests/test_timezone.py and tests/i18n/tests.py respectively.",
        "buildbot, test this please.",
        "@aaugustin I updated my PR following your comments. Regarding `timezone.override`, it is not a decorator yet (I was working on a PR for that when I run into this bug... but I will add some tests for that case in my PR)",
        "Merged manually in efcbf3e095dce3491eb52774978afe3f7bbdf217 with minor edits, merci."
      ]
    },
    {
      "scope": "FILE:django/utils/timezone.py",
      "discussion": [
        "Why not remove that line entirely?",
        "Well, \"some people\" consider that attributes should be defined at initialization, which is arguable. If this is not a rule within django codebase, I have no objection to remove those lines."
      ]
    },
    {
      "scope": "FILE:django/utils/translation/__init__.py",
      "discussion": [
        "Same question as above."
      ]
    }
  ]
}