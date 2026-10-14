"""@file test_workflow_policy.py
@brief Regressions for mixed CodeQL versions that caused a real PR failure.
@details Function and variable locations are indexed in docs/generated/symbol-index.md.
"""

import unittest

from check_repository import consistent_codeql_versions


class WorkflowPolicyTests(unittest.TestCase):
    """Exercise paired, absent, mutable and mixed CodeQL references independently."""

    def test_paired_immutable_versions(self):
        """Matching init and analyze commits satisfy the guard."""
        source = "uses: github/codeql-action/init@" + "a" * 40
        source += "\nuses: github/codeql-action/analyze@" + "a" * 40
        self.assertTrue(consistent_codeql_versions(source))

    def test_mixed_versions(self):
        """The actual failure pattern is rejected before native analysis."""
        source = "uses: github/codeql-action/init@" + "a" * 40
        source += "\nuses: github/codeql-action/analyze@" + "b" * 40
        self.assertFalse(consistent_codeql_versions(source))

    def test_mutable_tag(self):
        """Mutable tags are not treated as reproducible references."""
        self.assertFalse(consistent_codeql_versions("uses: github/codeql-action/init@v4"))

    def test_without_codeql(self):
        """An unrelated workflow does not need a CodeQL pair."""
        self.assertTrue(consistent_codeql_versions("uses: actions/checkout@" + "a" * 40))

    def test_autobuild_must_match(self):
        """An optional autobuild step shares the same action version."""
        source = "uses: github/codeql-action/init@" + "a" * 40
        source += "\nuses: github/codeql-action/autobuild@" + "b" * 40
        self.assertFalse(consistent_codeql_versions(source))


if __name__ == "__main__":
    unittest.main()
