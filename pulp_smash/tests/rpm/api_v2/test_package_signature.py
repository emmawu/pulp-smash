# coding=utf-8
"""Tests for how well Pulp can deal with signatures of RPMs.

This module targets `Pulp #1156`_.
Signature attribute should be stored for rpm/srpm/drpm packages
when they are imported or synchronized to rpm repos.

.. _Pulp #1156: https://pulp.plan.io/issues/1156

"""
from __future__ import unicode_literals

import unittest2

from pulp_smash import api, selectors, utils
from pulp_smash.compat import urljoin
from pulp_smash.constants import (
    DRPM_UNSIGNED_FEED_URL,
    DRPM_UNSIGNED_URL,
    RPM_FEED_URL,
    RPM_UNSIGNED_FEED_URL,
    RPM_UNSIGNED_URL,
    RPM_URL,
    REPOSITORY_PATH,
    SRPM_FEED_URL,
    SRPM_UNSIGNED_FEED_URL,
    SRPM_UNSIGNED_URL,
    SRPM_URL
)
from pulp_smash.tests.rpm.api_v2.utils import (
    gen_repo,
)

_PACKAGE_URLS = {
    'rpm': {
        'repo_url': RPM_FEED_URL,
        'pkg_url': RPM_URL
    },
    'rpm-unsigned': {
        'repo_url': RPM_UNSIGNED_FEED_URL,
        'pkg_url': RPM_UNSIGNED_URL
    },
    'srpm': {
        'repo_url': SRPM_FEED_URL,
        'pkg_url': SRPM_URL
    },
    'srpm-unsigned': {
        'repo_url': SRPM_UNSIGNED_FEED_URL,
        'pkg_url': SRPM_UNSIGNED_URL
    },
    'drpm-unsigned': {
        'repo_url': DRPM_UNSIGNED_FEED_URL,
        'pkg_url': DRPM_UNSIGNED_URL
    }
}
"""A dict of information about urls of test repos and packages."""


class UploadRPMSignatureTestCase(utils.BaseAPITestCase):
    """Test how well Pulp can deal with package signature.

    When uploading and importing packages.
    """

    @classmethod
    def setUpClass(cls):
        """Create a RPM repository."""
        super(UploadRPMSignatureTestCase, cls).setUpClass()
        if selectors.bug_is_untestable(1156, cls.cfg.version):
            raise unittest2.SkipTest('https://pulp.plan.io/issues/1156')
        cls.repos = {}

        # Create RPM repositories
        cls.client = api.Client(cls.cfg, api.json_handler)
        for package_type in ['rpm', 'rpm-unsigned', 'srpm', 'srpm-unsigned']:
            cls.repos[package_type] = \
                cls.client.post(REPOSITORY_PATH, gen_repo())
            cls.resources.add(cls.repos[package_type]['_href'])

    def setUp(self):
        """Set up common test variable."""
        super(UploadRPMSignatureTestCase, self).setUp()
        self.signature = None
        self.package_type = None

    def _import_pkg_validate_signature(self):
        """Import a package to the repo.

        Validate the signature stored for the package.
        """
        repo_url = self.repos[self.package_type]['_href']
        pkg_url = _PACKAGE_URLS[self.package_type]['pkg_url']
        if pkg_url.split('.')[-2] == 'src':
            unit_type = 'srpm'
        else:
            unit_type = pkg_url.split('.')[-1]
        unit_name = pkg_url.split('/')[-1]

        # Upload and import the package to the repo
        utils.upload_import_unit(
            self.cfg,
            utils.http_get(pkg_url),
            unit_type,
            repo_url)
        # Get the package imported
        units = self.client.post(
            urljoin(repo_url, 'search/units/'),
            {
                'criteria': {
                    'type_ids': [unit_type],
                    'filters': {
                        'unit': {
                            'filename': {'$in': [unit_name]}
                        }
                    }
                }
            }
        )
        # Validate the signature of the package imported
        self.assertEqual(len(units), 1)
        if self.signature:
            self.assertTrue('signature' in units[0]['metadata'])
            self.assertEqual(units[0]['metadata']['signature'], self.signature)
        else:
            self.assertFalse('signature' in units[0]['metadata'])

    def test_import_rpm_signed(self):
        """Assert signature is stored for signed rpm imported."""
        self.package_type = 'rpm'
        self.signature = 'f78fb195'
        self._import_pkg_validate_signature()

    def test_import_srpm_signed(self):
        """Assert signature is stored for signed srpm imported."""
        self.package_type = 'srpm'
        self.signature = '260f3a2b'
        self._import_pkg_validate_signature()

    def test_import_rpm_unsigned(self):
        """Assert no signature is stored for unsigned rpm imported."""
        self.package_type = 'rpm-unsigned'
        self._import_pkg_validate_signature()

    def test_import_srpm_unsigned(self):
        """Assert no signature is stored for unsigned srpm imported."""
        self.package_type = 'srpm-unsigned'
        self._import_pkg_validate_signature()


class SyncRPMSignatureTestCase(utils.BaseAPITestCase):
    """Test how well Pulp can deal with package sig when syncing a repo."""

    @classmethod
    def setUpClass(cls):
        """Create a RPM repository."""
        super(SyncRPMSignatureTestCase, cls).setUpClass()
        if selectors.bug_is_untestable(1156, cls.cfg.version):
            raise unittest2.SkipTest('https://pulp.plan.io/issues/1156')
        cls.repos = {}

        # Create RPM repositories with feeds for signed/unsigned RPM/SRPM/DRPM
        cls.client = api.Client(cls.cfg, api.json_handler)
        allow_types = [
            'rpm',
            'rpm-unsigned',
            'srpm',
            'srpm-unsigned',
            'drpm-unsigned'
        ]
        for package_type in allow_types:
            body = gen_repo()
            body['importer_config']['feed'] = \
                _PACKAGE_URLS[package_type]['repo_url']
            cls.repos[package_type] = cls.client.post(REPOSITORY_PATH, body)
            cls.resources.add(cls.repos[package_type]['_href'])

    def setUp(self):
        """Set up common test variable."""
        super(SyncRPMSignatureTestCase, self).setUp()
        self.signature = None
        self.package_type = None

    def _sync_repo_validate_package_sig(self):
        """Sync a repo from feed.

        Validate the signature stored for the package after sync.
        """
        repo_url = self.repos[self.package_type]['_href']
        print repo_url
        pkg_url = _PACKAGE_URLS[self.package_type]['pkg_url']
        if pkg_url.split('.')[-2] == 'src':
            unit_type = 'srpm'
        else:
            unit_type = pkg_url.split('.')[-1]
        unit_name = pkg_url.split('/')[-1]

        # Sync content into the repository
        utils.sync_repo(self.cfg, repo_url)
        # Search units from repo
        units = self.client.post(
            urljoin(repo_url, 'search/units/'),
            {
                'criteria': {
                    'type_ids': [unit_type],
                    'filters': {
                        'unit': {
                            'filename': {'$in': [unit_name]}
                        }
                    }
                }
            }
        )
        # Validate the signature of the package
        self.assertEqual(len(units), 1)
        if self.signature:
            self.assertTrue('signature' in units[0]['metadata'])
            self.assertEqual(units[0]['metadata']['signature'], self.signature)
        else:
            self.assertFalse('signature' in units[0]['metadata'])

    def test_sync_rpm_signed(self):
        """Assert signature is stored for signed rpm during sync."""
        self.package_type = 'rpm'
        self.signature = 'f78fb195'
        self._sync_repo_validate_package_sig()

    def test_sync_srpm_signed(self):
        """Assert signature is stored for signed srpm during sync."""
        self.package_type = 'srpm'
        self.signature = '260f3a2b'
        self._sync_repo_validate_package_sig()

    def test_sync_rpm_unsigned(self):
        """Assert no signature is stored for unsigned rpm during sync."""
        self.package_type = 'rpm-unsigned'
        self._sync_repo_validate_package_sig()

    def test_sync_srpm_unsigned(self):
        """Assert no signature is stored for unsigned srpm during sync."""
        self.package_type = 'srpm-unsigned'
        self._sync_repo_validate_package_sig()

    def test_sync_drpm_unsigned(self):
        """Assert no signature is stored for unsigned drpm during sync."""
        self.package_type = 'dpm-unsigned'
        self._sync_repo_validate_package_sig()
