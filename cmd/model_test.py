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

    # pylint: disable=C0103
    def tearDown(self):
        """
        Close any db connections, and delete test file.
        """
        self.model.close()
        os.remove(self.DATABASE_PATH)

    def test_upload_time(self):
        """
        Test that we can correctly manipulate the last upload time.
        """
        time_val = 1345427105 # just a realistic time val, ~ 8/19/12 6:45pm
        self.assertIsNone(self.model.last_uploaded(),
                "Did not return None even though upload entry doesn't exist")
        self.model.set_last_uploaded(time_val)
        self.assertEquals(time_val, self.model.last_uploaded(),
                "Created initial val, but appears incorect")
        self.model.set_last_uploaded(time_val + 10)
        self.assertEquals(time_val + 10, self.model.last_uploaded(),
                "Updated value, but appears incorrect")

    def test_roster(self):
        """
        Test that we can manipulate the issues table as expected.
        """
        self.assertIsNone(self.model.get_issue_number(("test",), "test"),
                "Did not return None even though roster entry doesn't exist")

        test_tuples = ( (("cs61a-ab",), "proj1", 1000),
                        (("cs61a-ab",), "proj2", 1001),
                        (("cs61a-bc", "cs61a-cd"), "proj1", 2000),
                        (("cs61a-bc", "cs61a-cd"), "proj2", 2001) )

        # pylint: disable=W0142
        for test_tuple in test_tuples:
            self.model.set_issue_number(*test_tuple)

        for students, assign, issue_num in test_tuples:
            self.assertEquals(issue_num,
                    self.model.get_issue_number(students, assign),
                    "Got wrong issue number")



if __name__ == "__main__":
    unittest.main()
