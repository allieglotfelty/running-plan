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


    def test_logout(self):
        result = self.client.get("/logout-complete", follow_redirects=True)
        self.assertIn("Generate Plan!", result.data)
        self.assertEqual(result.status_code, 200)

    # def test_send_sms_with_messages_to_send(self):
    #     result = self.client.post("/send-sms-reminders", data={"run-date": "2017-04-30"},
    #                                                            follow_redirects=True)
    #     self.assertIn("Messages sent successfully!", result.data)

    # def test_send_sms_with_no_messages_to_send(self):
    #     result = self.client.post("/send-sms-reminders", data={"run-date": "2017-04-27"},
    #                                                            follow_redirects=True)
    #     self.assertIn("No messages sent.", result.data)


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
        """Test that the sign-up works."""
        result = self.client.post('/sign-up-complete', data={'email': 'john@gmail.com',
                                                             "password": 'password'}, 
                                                             follow_redirects=True)
        self.assertIn('<h1>Running Dashboard</h1>', result.data)
        self.assertNotIn('<h1>Sign-up</h1>', result.data)
        self.assertEqual(result.status_code, 200)


    def test_login_good_account(self):
        """Test that login works with a good account."""
        with self.client as c:
            with c.session_transaction() as sess:
                sess['runner_id'] = 1

        result = self.client.post('/login-complete', data={'email': 'sally@gmail.com',
                                                           'password': 'password'},
                                                           follow_redirects=True)
        self.assertIn('<h1>Running Dashboard</h1>', result.data)
        self.assertEqual(result.status_code, 200)


    def test_login_bad_account(self):
        """Test that login doesn't work with a bad account."""
        result = self.client.post('/login-complete',
                                  data={'email': 'joe@gmail.com',
                                  'password': 'password'},
                                  follow_redirects=True)

        self.assertIn('Email or Password is incorrect.', result.data)
        self.assertNotIn('<h1>Running Dashboard</h1>', result.data)
        self.assertEqual(result.status_code, 200)


    def test_dashboard(self):
        """Test that the dashboard will display when a user is logged in."""
        with self.client as c:
            with c.session_transaction() as sess:
                sess['runner_id'] = 1

        result = self.client.get("/dashboard")
        self.assertIn("Monday", result.data)
        self.assertIn("2017-04-27", result.data)
        self.assertIn('<input type="submit" value="Logout"', result.data)
        self.assertEqual(result.status_code, 200)


    def test_update_run(self):
        """Test that the user can effectively update their run from their 
        dashboard.
        """
        with self.client as c:
            with c.session_transaction() as sess:
                sess['runner_id'] = 1

        result = self.client.post("/update-run.json",
                                  data={'run-id': 2},
                                  follow_redirects=True)

        self.assertIn('"total_miles_completed": 11.0', result.data)
        self.assertEqual(result.status_code, 200)


    def test_update_incomplete_run(self):
        """Test that a user can unclick a run they actually didn't complete."""

        with self.client as c:
            with c.session_transaction() as sess:
                sess['runner_id'] = 1

        result = self.client.post("/update-run-incomplete.json",
                                  data={'run-id': 1},
                                  follow_redirects=True)

        self.assertIn('"total_miles_completed": 0', result.data)
        self.assertEqual(result.status_code, 200)

    def test_workout_chart(self):
        """Test that the workout chartjs chart renders properly."""

        with self.client as c:
            with c.session_transaction() as sess:
                sess['runner_id'] = 1

        result = self.client.get("/workout-info.json")

        self.assertIn("Workouts Remaining", result.data)


    def test_mileage_chart(self):
        """Test that the mileage chartjs chart renders properly."""

        with self.client as c:
            with c.session_transaction() as sess:
                sess['runner_id'] = 1

        result = self.client.get("/mileage-info.json")

        self.assertIn("Total Miles Remaining", result.data)


    def test_update_account_adding_email(self):
        """Test that the runner's account updates properly when they sign-up to
        receive emails on the Accountability Settings form.
        """
        with self.client as c:
            with c.session_transaction() as sess:
                sess['runner_id'] = 1

        result = self.client.post("/update-account", data={"opt-email": "on"}, follow_redirects=True)

        self.assertIn("You are now subscribed to receive weekly emails.", result.data)
        self.assertIn('<input type="checkbox" class="opt-email" name="opt-email" checked="checked">', result.data)


    def test_update_account_text(self):
        """Test that the runner's account updates properly when they sign-up to
        receive text messages on the Accountability Settings form.
        """
        with self.client as c:
            with c.session_transaction() as sess:
                sess['runner_id'] = 1

        result = self.client.post("/update-account", data={"opt-text": "on",
                                                           "phone-number": '(603) 275-0521'},
                                                           follow_redirects=True)

        self.assertIn("You are now signed-up to receive text message reminders.", result.data)
        self.assertIn('<input type="checkbox" class="opt-text" name="opt-text" checked="checked">', result.data)


    def test_update_account_timezone(self):
        """Test that the runner's account updates properly when they update
        their timezone on the Accountability Settings form.
        """
        with self.client as c:
            with c.session_transaction() as sess:
                sess['runner_id'] = 1

        result = self.client.post("/update-account", data={"time-zone": "America/Anchorage"},
                                                           follow_redirects=True)

        self.assertIn('<option selected value="America/Anchorage">America/Anchorage</option>', result.data)


    def test_update_account_start_time(self):
        """Test that the runner's account updates properly when they update
        their start time on the Accountability Settings form.
        """
        with self.client as c:
            with c.session_transaction() as sess:
                sess['runner_id'] = 1

        result = self.client.post("/update-account", data={"cal-run-start-time": "04:00:00"},
                                                           follow_redirects=True)

        self.assertIn('<option selected value="04:00:00">04:00:00</option>', result.data)

    def test_update_account_removing_email(self):
        """Test that the runner's account updates properly when they unsign-up to
        receive emails on the Accountability Settings form.
        """
        with self.client as c:
            with c.session_transaction() as sess:
                sess['runner_id'] = 2

        result = self.client.post("/update-account", data={"opt-email": None}, follow_redirects=True)

        self.assertIn("You are no longer subscribed to weekly emails.", result.data)
        self.assertIn('<input type="checkbox" class="opt-email" name="opt-email">', result.data)


    def test_update_account_removing_text(self):
        """Test that the runner's account updates properly when they unsign-up to
        receive texts on the Accountability Settings form.
        """
        with self.client as c:
            with c.session_transaction() as sess:
                sess['runner_id'] = 2

        result = self.client.post("/update-account", data={"opt-text": None}, follow_redirects=True)

        self.assertIn("You will no longer receive text message reminders.", result.data)
        self.assertIn('<input type="checkbox" class="opt-text" name="opt-text">', result.data)


    def test_update_account_removing_gcal(self):
        """Test that the runner's account updates properly when they unsign-up to
        add runs to their Google Calendar on the Accountability Settings form.
        """
        with self.client as c:
            with c.session_transaction() as sess:
                sess['runner_id'] = 2

        result = self.client.post("/update-account", data={"opt-gcal": None}, follow_redirects=True)

        self.assertIn('<input type="checkbox" class="opt-gcal" name="opt-gcal">', result.data)


    def test_admin(self):
        """Test that admin page renders properly."""

        with self.client as c:
            with c.session_transaction() as sess:
                sess['admin'] = 'admin'

        result = self.client.get("/admin")
        self.assertIn("<h1>Admin Page</h1>", result.data)
        self.assertEqual(result.status_code, 200)



if __name__ == "__main__":
    unittest.main()