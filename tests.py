import unittest
from server import app
from model import db, example_data, connect_to_db
import running_plan
import server_utilities
from datetime import datetime, date, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select, WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import time
import json

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

        self.assertEqual(result.headers['Content-Type'], 
                         'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


    def test_logout(self):
        result = self.client.get("/logout-complete", 
                                 follow_redirects=True)

        self.assertIn("Generate Plan!", result.data)
        self.assertEqual(result.status_code, 200)


    def test_sign_up_complete(self):
        """Test that the sign-up works."""

        result = self.client.post('/sign-up-complete',
                                  data={'email': 'john@gmail.com',
                                        'password': 'password'}, 
                                  follow_redirects=True)

        self.assertIn('<h1>Running Dashboard</h1>', result.data)
        self.assertNotIn('<h1>Sign-up</h1>', result.data)
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

    # def test_send_sms_with_messages_to_send(self):
    #     result = self.client.post("/send-sms-reminders", data={"run-date": "2017-04-30"},
    #                                                            follow_redirects=True)
    #     self.assertIn("Messages sent successfully!", result.data)

    # def test_send_sms_with_no_messages_to_send(self):
    #     result = self.client.post("/send-sms-reminders", data={"run-date": "2017-04-27"},
    #                                                            follow_redirects=True)
    #     self.assertIn("No messages sent.", result.data)


class ServerTestsWithDBRunnerOne(unittest.TestCase):
    """Flask tests that use the database."""

    def setUp(self):
        """What to do before each test."""

        self.client = app.test_client()
        app.config['TESTING'] = True
        connect_to_db(app, 'postgresql:///testdb')

        db.create_all()
        example_data()

        with self.client as c:
            with c.session_transaction() as sess:
                sess['runner_id'] = 1

    def tearDown(self):
        """Do at end of each test."""

        db.session.close()
        db.drop_all()

    def test_login_good_account(self):
        """Test that login works with a good account."""

        result = self.client.post('/login-complete',
                                  data={'email': 'sally@gmail.com',
                                        'password': 'password'},
                                  follow_redirects=True)

        self.assertIn('Running Dashboard', result.data)
        self.assertEqual(result.status_code, 200) 


    def test_dashboard(self):
        """Test that the dashboard will display when a user is logged in."""

        result = self.client.get("/dashboard")
        self.assertIn("Monday", result.data)
        self.assertIn("2017-04-27", result.data)
        self.assertIn('<input type="submit" value="Logout"', result.data)
        self.assertEqual(result.status_code, 200)


    def test_update_run(self):
        """Test that the user can effectively update their run from their 
        dashboard.
        """

        result = self.client.post("/update-run.json",
                                  data={'run-id': 2},
                                  follow_redirects=True)

        self.assertIn('"total_miles_completed": 11.0', result.data)
        self.assertEqual(result.status_code, 200)


    def test_update_incomplete_run(self):
        """Test that a user can unclick a run they actually didn't complete."""

        result = self.client.post("/update-run-incomplete.json",
                                  data={'run-id': 1},
                                  follow_redirects=True)

        self.assertIn('"total_miles_completed": 0', result.data)
        self.assertEqual(result.status_code, 200)

    def test_workout_chart(self):
        """Test that the workout chartjs chart renders properly."""

        result = self.client.get("/workout-info.json")

        self.assertIn("Workouts Remaining", result.data)


    def test_mileage_chart(self):
        """Test that the mileage chartjs chart renders properly."""

        result = self.client.get("/mileage-info.json")

        self.assertIn("Total Miles Remaining", result.data)


    def test_update_account_adding_email(self):
        """Test that the runner's account updates properly when they sign-up to
        receive emails on the Accountability Settings form.
        """

        result = self.client.post("/update-account",
                                  data={"opt-email": "on"},
                                  follow_redirects=True)

        self.assertIn("You are now subscribed to receive weekly emails.",
                      result.data)
        self.assertIn('<input type="checkbox" class="opt-email" name="opt-email" checked="checked">',
                      result.data)


    def test_update_account_text(self):
        """Test that the runner's account updates properly when they sign-up to
        receive text messages on the Accountability Settings form.
        """

        result = self.client.post("/update-account", 
                                  data={"opt-text": "on",
                                        "phone-number": '(603) 275-0521'},
                                  follow_redirects=True)

        self.assertIn("You are now signed-up to receive text message reminders.",
                      result.data)
        self.assertIn('<input type="checkbox" class="opt-text" name="opt-text" checked="checked">',
                      result.data)


    def test_update_account_timezone(self):
        """Test that the runner's account updates properly when they update
        their timezone on the Accountability Settings form.
        """

        result = self.client.post("/update-account",
                                  data={"time-zone": "America/Anchorage"},
                                  follow_redirects=True)

        self.assertIn('<option selected value="America/Anchorage">America/Anchorage</option>',
                      result.data)


    def test_update_account_start_time(self):
        """Test that the runner's account updates properly when they update
        their start time on the Accountability Settings form.
        """

        result = self.client.post("/update-account",
                                  data={"cal-run-start-time": "04:00:00"},
                                  follow_redirects=True)

        self.assertIn('<option selected value="04:00:00">04:00:00</option>',
                      result.data)


class ServerTestsWithDBRunnerTwo(unittest.TestCase):
    """Flask tests that use the database."""

    def setUp(self):
        """What to do before each test."""

        self.client = app.test_client()
        app.config['TESTING'] = True
        connect_to_db(app, 'postgresql:///testdb')

        db.create_all()
        example_data()

        with self.client as c:
            with c.session_transaction() as sess:
                sess['runner_id'] = 2

    def tearDown(self):
        """Do at end of each test."""

        db.session.close()
        db.drop_all()

    def test_update_account_removing_email(self):
        """Test that the runner's account updates properly when they unsign-up to
        receive emails on the Accountability Settings form.
        """

        result = self.client.post("/update-account",
                                  data={"opt-email": None},
                                  follow_redirects=True)

        self.assertIn("You are no longer subscribed to weekly emails.",
                      result.data)

        self.assertIn('<input type="checkbox" class="opt-email" name="opt-email">',
                      result.data)


    def test_update_account_removing_text(self):
        """Test that the runner's account updates properly when they unsign-up
        to receive texts on the Accountability Settings form.
        """

        result = self.client.post("/update-account", 
                                  data={"opt-text": None},
                                  follow_redirects=True)

        self.assertIn("You will no longer receive text message reminders.",
                      result.data)
        self.assertIn('<input type="checkbox" class="opt-text" name="opt-text">',
                      result.data)


    def test_update_account_removing_gcal(self):
        """Test that the runner's account updates properly when they unsign-up
        to add runs to their Google Calendar on the Accountability Settings form.
        """

        result = self.client.post("/update-account",
                                  data={"opt-gcal": None},
                                  follow_redirects=True)

        self.assertIn('<input type="checkbox" class="opt-gcal" name="opt-gcal">',
                      result.data)


class ServerTestsWithAdmin(unittest.TestCase):
    """Flask tests that use the database."""

    def setUp(self):
        """What to do before each test."""

        self.client = app.test_client()
        app.config['TESTING'] = True
        connect_to_db(app, 'postgresql:///testdb')

        db.create_all()
        example_data()

        with self.client as c:
            with c.session_transaction() as sess:
                sess['admin'] = 'admin'


    def tearDown(self):
        """Do at end of each test."""

        db.session.close()
        db.drop_all()


    def test_admin(self):
        """Test that admin page renders properly."""

        result = self.client.get("/admin")
        self.assertIn("<h1>Admin Page</h1>", result.data)
        self.assertEqual(result.status_code, 200)


class RunningPlanUnitTests(unittest.TestCase):
    """Unit tests!"""

    def test_round_quarter(self):
        """Test that the round_quarter function works."""

        assert running_plan.round_quarter(12) == 12.0
        assert running_plan.round_quarter(12.10) == 12.0
        assert running_plan.round_quarter(12.15) == 12.25
        assert running_plan.round_quarter(12.35) == 12.25
        assert running_plan.round_quarter(12.45) == 12.5
        assert running_plan.round_quarter(12.60) == 12.5
        assert running_plan.round_quarter(12.65) == 12.75
        assert running_plan.round_quarter(12.85) == 12.75
        assert running_plan.round_quarter(12.90) == 13.00

    def test_calculate_days_in_last_week(self):
        """Tests that the calculate_days_in_last_week function works."""

        end_date = datetime.strptime("2017-4-19", "%Y-%m-%d")
        assert running_plan.calculate_days_in_last_week(end_date) == 3

    def test_calculate_start_date(self):
        """Tests that the calculate_start_date function works."""

        today_date = datetime.strptime("2017-4-19", "%Y-%m-%d")
        assert running_plan.calculate_start_date(today_date) == datetime.strptime("2017-4-20", "%Y-%m-%d")


    def test_calculate_days_in_first_week(self):
        """Test that the calculate_days_in_first_week function works."""

        start_date = datetime.strptime("2017-4-19", "%Y-%m-%d")

        assert running_plan.calculate_days_in_first_week(start_date) == 4


    def test_calculate_number_of_weeks_to_goal(self):
        """Test that calculate_number_of_weeks_to_goal function works."""

        start_date = datetime.strptime("2017-4-19", "%Y-%m-%d")
        end_date = datetime.strptime("2017-6-24", "%Y-%m-%d")

        assert running_plan.calculate_number_of_weeks_to_goal(start_date, end_date) == 10


    def test_generate_first_week_of_runs(self):
        """Test that the algorithm generates the first week of the running plan 
        successfully.
        """

        start_date = datetime.strptime("2017-4-21", "%Y-%m-%d")
        start_day = start_date.weekday()

        result = json.dumps(running_plan.generate_first_week_of_runs(start_day, start_date, 6), sort_keys=True)
        # week_one = {"2017-04-17": 0.0, "2017-04-18": 0.0, "2017-04-19": 0.0, "2017-04-20": 0.0, "2017-04-21": 1.5, "2017-04-22": 0.0, "2017-04-23": 3.0}
        week_one = '{"2017-04-17 00:00:00": 0.0, "2017-04-18 00:00:00": 0.0, "2017-04-19 00:00:00": 0.0, "2017-04-20 00:00:00": 0.0, "2017-04-21 00:00:00": 1.5, "2017-04-22 00:00:00": 0.0, "2017-04-23 00:00:00": 3.0}'
        assert result == week_one


    def test_generate_middle_weeks_of_plan(self):
        """Test that the algorithm generates the middle weeks of the running
        plan successfully.
        """

        start_date = datetime.strptime("2017-4-21", "%Y-%m-%d")

        middle_weeks, start_date = running_plan.generate_middle_weeks_of_plan({}, 8, start_date, 6, 1, 2)

        result = json.dumps(middle_weeks)
        mid_weeks_test_case = '{"2": {"2017-04-27 00:00:00": 6.0, "2017-04-22 00:00:00": 0.0, "2017-04-23 00:00:00": 1.5, "2017-04-25 00:00:00": 0.0, "2017-04-21 00:00:00": 3.0, "2017-04-26 00:00:00": 1.5, "2017-04-24 00:00:00": 3.0}, "3": {"2017-04-30 00:00:00": 1.75, "2017-05-01 00:00:00": 3.5, "2017-04-29 00:00:00": 0.0, "2017-05-03 00:00:00": 1.75, "2017-05-02 00:00:00": 0.0, "2017-05-04 00:00:00": 7.0, "2017-04-28 00:00:00": 3.5}, "4": {"2017-05-08 00:00:00": 4.0, "2017-05-05 00:00:00": 4.0, "2017-05-06 00:00:00": 0.0, "2017-05-10 00:00:00": 2.0, "2017-05-11 00:00:00": 8.0, "2017-05-09 00:00:00": 0.0, "2017-05-07 00:00:00": 2.0}, "5": {"2017-05-16 00:00:00": 0.0, "2017-05-12 00:00:00": 4.5, "2017-05-15 00:00:00": 4.5, "2017-05-17 00:00:00": 2.25, "2017-05-18 00:00:00": 9.0, "2017-05-13 00:00:00": 0.0, "2017-05-14 00:00:00": 2.25}, "6": {"2017-05-23 00:00:00": 0.0, "2017-05-24 00:00:00": 2.5, "2017-05-21 00:00:00": 2.5, "2017-05-20 00:00:00": 0.0, "2017-05-22 00:00:00": 5.0, "2017-05-25 00:00:00": 10.0, "2017-05-19 00:00:00": 5.0}}'

        assert result == mid_weeks_test_case


    def test_generate_second_to_last_week_of_plan(self):
        """Test that the algorithm generates the second to last week of the
        running plan successfully.
        """

        start_date = datetime.strptime("2017-4-21", "%Y-%m-%d")

        second_to_last_week = running_plan.generate_second_to_last_week_of_plan({}, 8, 6, start_date)

        result = json.dumps(second_to_last_week)

        second_to_last_week_test_case = '{"7": {"2017-04-27 00:00:00": 6.0, "2017-04-22 00:00:00": 0.0, "2017-04-23 00:00:00": 1.5, "2017-04-25 00:00:00": 0.0, "2017-04-21 00:00:00": 3.0, "2017-04-26 00:00:00": 1.5, "2017-04-24 00:00:00": 3.0}}'

        assert result == second_to_last_week_test_case


    def test_generate_last_week_of_plan(self):
        """Test that the algorithm generates the last week of the
        running plan successfully.
        """

        end_date = datetime.strptime("2017-5-28", "%Y-%m-%d")

        last_week = running_plan.generate_last_week_of_plan({}, 8, 13.1, 6, 6, end_date)

        result = json.dumps(last_week)
        last_week_test_case = '{"8": {"2017-05-28 00:00:00": 13.1, "2017-05-23 00:00:00": 4.25, "2017-05-24 00:00:00": 0.0, "2017-05-26 00:00:00": 0.0, "2017-05-22 00:00:00": 3.25, "2017-05-25 00:00:00": 3.25, "2017-05-27 00:00:00": 3.0}}'

        assert result == last_week_test_case


    def test_build_plan_with_two_dates(self):
        """Test that the algorithm generates the last week of the
        running plan successfully.
        """

        today_date = datetime.strptime("2017-4-21", "%Y-%m-%d")
        end_date = datetime.strptime("2017-5-28", "%Y-%m-%d")

        plan = running_plan.build_plan_with_two_dates(today_date, end_date, 6, 13.1)

        result = json.dumps(plan)

        plan_test_case = '{"1": {"2017-04-20 00:00:00": 0.0, "2017-04-22 00:00:00": 1.5, "2017-04-23 00:00:00": 0.0, "2017-04-19 00:00:00": 0.0, "2017-04-17 00:00:00": 0.0, "2017-04-21 00:00:00": 0.0, "2017-04-18 00:00:00": 0.0}, "2": {"2017-04-27 00:00:00": 3.0, "2017-04-30 00:00:00": 6.0, "2017-04-29 00:00:00": 1.5, "2017-04-25 00:00:00": 0.0, "2017-04-26 00:00:00": 1.5, "2017-04-28 00:00:00": 0.0, "2017-04-24 00:00:00": 3.0}, "3": {"2017-05-05 00:00:00": 0.0, "2017-05-01 00:00:00": 4.0, "2017-05-06 00:00:00": 2.0, "2017-05-03 00:00:00": 2.0, "2017-05-02 00:00:00": 0.0, "2017-05-04 00:00:00": 4.0, "2017-05-07 00:00:00": 7.75}, "4": {"2017-05-08 00:00:00": 4.75, "2017-05-12 00:00:00": 0.0, "2017-05-10 00:00:00": 2.5, "2017-05-11 00:00:00": 4.75, "2017-05-09 00:00:00": 0.0, "2017-05-13 00:00:00": 2.5, "2017-05-14 00:00:00": 9.5}, "5": {"2017-05-16 00:00:00": 0.0, "2017-05-21 00:00:00": 6.0, "2017-05-20 00:00:00": 1.5, "2017-05-15 00:00:00": 3.0, "2017-05-17 00:00:00": 1.5, "2017-05-18 00:00:00": 3.0, "2017-05-19 00:00:00": 0.0}, "6": {"2017-05-28 00:00:00": 13.1, "2017-05-23 00:00:00": 4.25, "2017-05-24 00:00:00": 0.0, "2017-05-26 00:00:00": 0.0, "2017-05-22 00:00:00": 3.25, "2017-05-25 00:00:00": 3.25, "2017-05-27 00:00:00": 3.0}}'

        assert result == plan_test_case


class ServerUtilitiesUnitTests(unittest.TestCase):
    """Unit tests for the server_utilities file"""

    def test_calculate_date_year_from_today(self):
        """Test that the function generates the correct date a year from today.
        """

        date_to_test = datetime.strptime("2017-4-23", "%Y-%m-%d").date()

        year_from_date = date_to_test + timedelta(365)

        result = server_utilities.calculate_date_year_from_today(date)

        assert result == year_from_date


    def test_generate_date_string(self):
        """Test that the function returns a string version of the date entered.
        """

        date_string = "2017-04-23"
        date_to_test = datetime.strptime("2017-4-23", "%Y-%m-%d").date()

        result = server_utilities.generate_date_string(date_to_test)

        assert result == date_string


class SeleniumUITests(unittest.TestCase):

    def setUp(self):
        app.config['TESTING'] = True
        connect_to_db(app, 'postgresql:///testdb')
        self.driver = webdriver.PhantomJS()
        time.sleep(5)

    def tearDown(self):
        self.driver.quit()

    def test_title(self):
        self.driver.get('http://localhost:5000/')
        self.assertEqual(self.driver.title, 'Run Holmes')

    def test_homepage_user_flow(self):
        self.driver.get('http://localhost:5000/')

        # dropdown1 = self.driver.find_element_by_id('current-ability')
        dropdown1 = Select(self.driver.find_element_by_id('current-ability'))
        dropdown1.select_by_visible_text('6 miles')
        dropdown2 = Select(self.driver.find_element_by_id('goal-distance'))
        dropdown2.select_by_visible_text('Half Marathon (13.1 miles)')

        date_field = self.driver.find_element_by_id('goal-date')
        date_field.clear()
        date_field.send_keys('2017-06-30')

        generate_plan_btn = self.driver.find_element_by_id('generate-plan')
        generate_plan_btn.click()
        time.sleep(5)

        download_button = self.driver.find_element_by_id('download-to-excel')
        plan_display = self.driver.find_element_by_id('plan-calendar')
        sign_up_link = self.driver.find_element_by_id('sign-up')

        self.assertEqual(download_button.is_displayed(), True)
        self.assertEqual(plan_display.is_displayed(), True)
        self.assertEqual(sign_up_link.is_displayed(), True)

        sign_up_link.click()
        time.sleep(3)

        email_field = self.driver.find_element_by_id('email')
        password_field = self.driver.find_element_by_id('password')

        self.assertEqual(email_field.is_displayed(), True)
        self.assertEqual(password_field.is_displayed(), True)

        email_field.send_keys('judy@gmail.com')
        time.sleep(5)
        password_field.send_keys('pass')
        time.sleep(5)

        submit_btn = self.driver.find_element_by_id('sign-up-submit')
        submit_btn.click()



        # wait = WebDriverWait(self.driver, 20)
        # print self.driver.current_url
        # dashboard_header = self.driver.find_element_by_id('dashboard-header')
        # self.assertEqual(dashboard_header.is_displayed(), True)


        # wait.until(self.assertEqual(self.driver.title, 'Run Holmes'))

        # self.old_page = self.driver.find_element_by_tag_name('html')

        # try:
        #     element = WebDriverWait(self.driver, 100).until(
        #         EC.presence_of_element_located((By.ID, "update-account"))
        #     )
        # finally:
        #     self.driver.close()


        # def wait_for(condition_function):
        #     start_time = time.time()
        #     while time.time() < start_time + 3:
        #         if condition_function():
        #             return True
        #         else:
        #             time.sleep(0.1)
        #     raise Exception(
        #         'Timeout waiting for {}'.format(condition_function.__name__)
        #     )


        # def page_has_loaded(self):
        #     new_page = self.driver.find_element_by_tag_name('html')
        #     return new_page.id != self.old_page.id

        # wait_for(SeleniumUITests.page_has_loaded)

  



if __name__ == "__main__":
    unittest.main()