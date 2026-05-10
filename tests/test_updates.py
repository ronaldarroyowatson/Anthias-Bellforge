import logging
import os
from typing import Any
from unittest import mock

from django.test import TestCase

from lib.github import fetch_remote_hash, get_update_github_repo, is_up_to_date

GIT_HASH_1 = 'da39a3ee5e6b4b0d3255bfef95601890afd80709'
GIT_SHORT_HASH_1 = 'da39a3e'
GIT_HASH_2 = '6adfb183a4a2c94a2f92dab5ade762a47889a5a1'


logging.disable(logging.CRITICAL)


class UpdateTest(TestCase):
    def test_get_update_github_repo_should_default_to_bellforge_repo(
        self,
    ) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(
                get_update_github_repo(),
                'ronaldarroyowatson/Anthias-Bellforge',
            )

    def test_fetch_remote_hash_should_use_configured_github_repo(self) -> None:
        with (
                },
                self,
            ),
                test_cases = [
                    (
                        'master head matches local',
                        {
                            'latest_remote_hash': GIT_HASH_1,
                            'git_hash': GIT_HASH_1,
                            'git_short_hash': GIT_SHORT_HASH_1,
                            'is_running_latest_published_image': True,
                        },
                        True,
                    ),
                    (
                        'master ahead but published image matches',
                        {
                            'latest_remote_hash': GIT_HASH_2,
                            'git_hash': GIT_HASH_1,
                            'git_short_hash': GIT_SHORT_HASH_1,
                            'is_running_latest_published_image': True,
                        },
                        True,
                    ),
                    (
                        'master head matches local even when ghcr disagrees',
                        {
                            'latest_remote_hash': GIT_HASH_1,
                            'git_hash': GIT_HASH_1,
                            'git_short_hash': GIT_SHORT_HASH_1,
                            'is_running_latest_published_image': False,
                        },
                        True,
                    ),
                    (
                        'master ahead and published image older',
                        {
                            'latest_remote_hash': GIT_HASH_2,
                            'git_hash': GIT_HASH_1,
                            'git_short_hash': GIT_SHORT_HASH_1,
                            'is_running_latest_published_image': False,
                        },
                        False,
                    ),
                    (
                        'master ahead and ghcr lookup inconclusive',
                        {
                            'latest_remote_hash': GIT_HASH_2,
                            'git_hash': GIT_HASH_1,
                            'git_short_hash': GIT_SHORT_HASH_1,
                            'is_running_latest_published_image': None,
                        },
                        True,
                    ),
                ]

                for _, hashes, expected in test_cases:
                    with self.subTest(hashes=hashes):
                        os.environ['GIT_BRANCH'] = 'master'
                        os.environ['DEVICE_TYPE'] = 'pi4'

                        latest_remote_hash = hashes['latest_remote_hash']
                        git_hash = hashes['git_hash']
                        git_short_hash = hashes['git_short_hash']
                        published_match = hashes['is_running_latest_published_image']

                        with (
                            mock.patch(
                                'lib.github.fetch_remote_hash',
                                mock.MagicMock(
                                    return_value=(latest_remote_hash, False)
                                ),
                            ),
                            mock.patch(
                                'lib.github.get_git_hash',
                                mock.MagicMock(return_value=git_hash),
                            ),
                            mock.patch(
                                'lib.github.get_git_short_hash',
                                mock.MagicMock(return_value=git_short_hash),
                            ),
                            mock.patch(
                                'lib.github.is_running_latest_published_image',
                                mock.MagicMock(return_value=published_match),
                            ),
                        ):
                            self.assertEqual(is_up_to_date(), expected)
                    'latest_remote_hash': GIT_HASH_2,
                    'git_hash': GIT_HASH_1,
                    'git_short_hash': GIT_SHORT_HASH_1,
                    'is_running_latest_published_image': None,
                },
                True,
            ),
        ],
    )
    def test_is_up_to_date_should_return_value_depending_on_git_hashes(
        self, hashes: dict[str, Any], expected: bool
    ) -> None:
        os.environ['GIT_BRANCH'] = 'master'
        os.environ['DEVICE_TYPE'] = 'pi4'

        latest_remote_hash = hashes['latest_remote_hash']
        git_hash = hashes['git_hash']
        git_short_hash = hashes['git_short_hash']
        published_match = hashes['is_running_latest_published_image']

        with (
            mock.patch(
                'lib.github.fetch_remote_hash',
                mock.MagicMock(return_value=(latest_remote_hash, False)),
            ),
            mock.patch(
                'lib.github.get_git_hash',
                mock.MagicMock(return_value=git_hash),
            ),
            mock.patch(
                'lib.github.get_git_short_hash',
                mock.MagicMock(return_value=git_short_hash),
            ),
            mock.patch(
                'lib.github.is_running_latest_published_image',
                mock.MagicMock(return_value=published_match),
            ),
        ):
            self.assertEqual(is_up_to_date(), expected)
