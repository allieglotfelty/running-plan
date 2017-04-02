import unittest

from server import app
from model import db, example_data, connect_to_db

class ServerTests(unittest.TestCase):
    """Tests for Run Holmes site."""

    def setUp(self):
        self.client = app.test_client()
        app.config['TESTING'] = True

    def test_homepage(self):
        result = self.client.get("/")
        self.assertIn("What is your running goal", result.data)

    def test_homepage_after_generate_plan(self):
        result = self.client.post("/plan.json", data= {"current-ability": 6, 
                                                       "goal-distance": 13.1,
                                                       "goal-date": "2017-06-03"},
                                                       follow_redirects=True)
        
        self.assertIn("13.1", result.data)
        self.assertIn("2017-06-03", result.data)

    # def test_download(self):
    #     result = self.client.get("/download", data= {"current-ability": 6, 
    #                                             "goal-distance": 13.1,
    #                                             "goal-date": "2017-06-03"})
    #     self.assertIn('["Content-Disposition"] = "attachment; filename=RunPlan.xlsx"', result.data)
    
    def test_sign_up(self):
        result = self.client.get("/sign-up")
        self.assertIn("<h1>Sign-up</h1>", result.data)

    def test_logout(self):
        result = self.client.get("/logout-complete", follow_redirects=True)
        self.assertIn("What is your running goal", result.data)
        self.assertIn("You have successfully logged out!", result.data)


class DatabaseTests(unittest.TestCase):
    """Flask tests that use the database."""

    def setUp(self):
        """What to do before each test."""

        self.client = app.test_client()
        app.config['TESTING'] = True
        connect_to_db(app)

        with self.client as c:
            with c.session_transaction() as sess:
                sess['runner_id'] = 1

        db.create_all()
        example_data()

    def tearDown(self):
        """Do at end of each test."""

        db.session.close()
        db.drop_all()

    def test_dashboard(self):
        result = self.client.get("/dashboard", data={"session['user_id']": 1})
        self.assertIn("Monday", result.data)
        self.assertIn("2017-04-27", result.data)
        self.assertIn('<input type="submit" value="Logout"', result.data)


    def test_sign_up_complete(self):
        result = self.client.post("/sign-up-complete", data={"email": 'sally@gmail.com',
                                                             "password": 'password'}, 
                                                             follow_redirects=True)
        self.assertIn("<h1>Running Dashboard</h1>", result.data)
        self.assertNotIn("<h1>Sign-up</h1>", result.data)



if __name__ == "__main__":
    unittest.main()