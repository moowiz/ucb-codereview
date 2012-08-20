"""
Unit tests for the database API.
"""
import os
import unittest

from init_codereview import create_table
import model

class TestCodeReviewDatabase(unittest.TestCase):
    """
    Tests for CodeReviewDatabase class.
    """

    DATABASE_PATH = "codereview_test.sqlite"

    # pylint: disable=C0103
    def setUp(self):
        """
        Sets up a clean database and initializes the model class
        before each test.
        """
        create_table(self.DATABASE_PATH)
        self.model = model.CodeReviewDatabase(self.DATABASE_PATH)

    def tearDown(self):
        """
        Close any db connections, and delete test file.
        """
        self.model.close()
        os.remove(self.DATABASE_PATH)
