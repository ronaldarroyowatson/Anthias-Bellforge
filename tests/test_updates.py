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
            mock.patch.dict(
                os.environ,
                {
                    'GIT_BRANCH': 'master',
                    'ANTHIAS_UPDATE_GITHUB_REPO': 'owner/custom-anthias',
                },
                clear=False,
            ),
            mock.patch('lib.github.r') as redis_mock,
            mock.patch(
                'lib.github.remote_branch_available',
                mock.MagicMock(return_value=True),
            ),
            mock.patch('lib.github.requests_get') as requests_get_mock,
        ):
            redis_mock.get.return_value = None
            response = mock.MagicMock()
            response.status_code = 200
            response.json.return_value = {'object': {'sha': GIT_HASH_2}}
            requests_get_mock.return_value = response

            latest_sha, cache_updated = fetch_remote_hash()

        self.assertEqual(latest_sha, GIT_HASH_2)
        self.assertEqual(cache_updated, True)
        requests_get_mock.assert_called_once_with(
            'https://api.github.com/repos/owner/custom-anthias/git/refs/heads/master',  # noqa: E501
            timeout=1,
        )

    def test_is_up_to_date_should_return_value_depending_on_git_hashes(
        self,
    ) -> None:
        test_cases: list[tuple[str, dict[str, Any], bool]] = [
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

        for case_name, hashes, expected in test_cases:
            with self.subTest(case_name=case_name):
                os.environ['GIT_BRANCH'] = 'master'
                os.environ['DEVICE_TYPE'] = 'pi4'

                with (
                    mock.patch(
                        'lib.github.fetch_remote_hash',
                        mock.MagicMock(
                            return_value=(hashes['latest_remote_hash'], False)
                        ),
                    ),
                    mock.patch(
                        'lib.github.get_git_hash',
                        mock.MagicMock(return_value=hashes['git_hash']),
                    ),
                    mock.patch(
                        'lib.github.get_git_short_hash',
                        mock.MagicMock(return_value=hashes['git_short_hash']),
                    ),
                    mock.patch(
                        'lib.github.is_running_latest_published_image',
                        mock.MagicMock(
                            return_value=hashes[
                                'is_running_latest_published_image'
                            ]
                        ),
                    ),
                ):
                    self.assertEqual(is_up_to_date(), expected)