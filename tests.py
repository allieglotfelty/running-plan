import unittest

from server import app
from model import db, example_data, connect_to_db

class ServerTestsNoDB(unittest.TestCase):
    """Tests for Run Holmes site."""

    def setUp(self):
        self.client = app.test_client()
        app.config['TESTING'] = True

    def test_homepage(self):
        result = self.client.get("/")
        self.assertIn("What is your running goal", result.data)
        self.assertEqual(result.status_code, 200)

    def test_homepage_after_generate_plan(self):
        result = self.client.post("/plan.json", data={"current-ability": 6, 
                                                       "goal-distance": 13.1,
                                                       "goal-date": "2017-06-03"},
                                                       follow_redirects=True)

        self.assertIn("13.1", result.data)
        self.assertIn("2017-06-03", result.data)
        self.assertEqual(result.status_code, 200)


    def test_homepage_if_click_generate_plan_without_info(self):
        result = self.client.post("/plan.json", data={"current-ability": "---",
                                                       "goal-distance": "---",
                                                       "goal-date": "2017-06-03"},
                                                       follow_redirects=True)
        self.assertNotIn("13.1", result.data)
        self.assertIn("Please complete all fields", result.data)
        self.assertEqual(result.status_code, 200)


    def test_download_good_info(self):
        with self.client as c:
            with c.session_transaction() as sess:
                sess['weekly_plan'] = {'1': {"2017-06-03": 13.1,
                                       "2017-06-02": 3,
                                       "2017-06-01": 0,
                                       "2017-05-31": 6}}

        result = self.client.get("/download", data={"current-ability": 6, 
                                                     "goal-distance": 13.1,
                                                     "goal-date": "2017-06-03"})
        self.assertEqual(result.headers['Content-Type'], 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

    
    def test_sign_up(self):
        result = self.client.get("/sign-up")
        self.assertIn("<h1>Sign-up</h1>", result.data)
        self.assertEqual(result.status_code, 200)

    def test_logout(self):
        result = self.client.get("/logout-complete", follow_redirects=True)
        self.assertIn("What is your running goal", result.data)
        self.assertIn("You have successfully logged out!", result.data)
        self.assertEqual(result.status_code, 200)


class ServerTestsWithDB(unittest.TestCase):
    """Flask tests that use the database."""

    def setUp(self):
        """What to do before each test."""

        self.client = app.test_client()
        app.config['TESTING'] = True
        connect_to_db(app, 'postgresql:///testdb')

        db.create_all()
        example_data()

    def tearDown(self):
        """Do at end of each test."""

        db.session.close()
        db.drop_all()

    def test_sign_up_complete(self):
        result = self.client.post('/sign-up-complete', data={'email': 'john@gmail.com',
                                                             "password": 'password'}, 
                                                             follow_redirects=True)
        self.assertIn('<h1>Running Dashboard</h1>', result.data)
        self.assertNotIn('<h1>Sign-up</h1>', result.data)
        self.assertEqual(result.status_code, 200)

    def test_login_good_account(self):
        with self.client as c:
            with c.session_transaction() as sess:
                sess['runner_id'] = 1

        result = self.client.post('/login-complete', data={'email': 'sally@gmail.com',
                                                           'password': 'password'},
                                                           follow_redirects=True)
        self.assertIn('<h1>Running Dashboard</h1>', result.data)
        self.assertEqual(result.status_code, 200)

    def test_login_bad_account(self):
        result = self.client.post('/login-complete', data={'email': 'joe@gmail.com',
                                                           'password': 'password'}, 
                                                           follow_redirects=True)
        self.assertIn('Email or Password is incorrect.', result.data)
        self.assertNotIn('<h1>Running Dashboard</h1>', result.data)
        self.assertEqual(result.status_code, 200)

    def test_dashboard(self):
        with self.client as c:
            with c.session_transaction() as sess:
                sess['runner_id'] = 1

        result = self.client.get("/dashboard")
        self.assertIn("Monday", result.data)
        self.assertIn("2017-04-27", result.data)
        self.assertIn('<input type="submit" value="Logout"', result.data)
        self.assertEqual(result.status_code, 200)


if __name__ == "__main__":
    unittest.main()