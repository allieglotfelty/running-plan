"""Models and database functions for Run Plan project."""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, date, timedelta
import pytz
import math

# This is the connection to the PostgreSQL database; we're getting this through
# the Flask-SQLAlchemy helper library. On this, we can find the `session`
# object, where we do most of our interactions (like committing, etc.)

db = SQLAlchemy()


##############################################################################
# Model definitions

class Runner(db.Model):
    """Runner on website."""

    __tablename__ = "runners"

    runner_id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    email = db.Column(db.String(64), nullable=False)
    password = db.Column(db.String(64), nullable=False)
    salt = db.Column(db.String(16), nullable=False)
    is_using_gCal = db.Column(db.Boolean, default=False, nullable=True)
    is_subscribed_to_email = db.Column(db.Boolean, default=False, nullable=True)
    is_subscribed_to_texts = db.Column(db.Boolean, default=False, nullable=True)
    phone = db.Column(db.String(12), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=True)
    timezone = db.Column(db.String(20), default='US/Pacific', nullable=True)
    OAuth_token = db.Column(db.String, nullable=True)
    photo = db.Column(db.String(200), nullable=True)

    @staticmethod
    def format_phone(phone):
        """Formats the runner's phone number to work for Twilio messaging."""

        new_phone = "+1"
        for char in phone:
            if char.isdigit():
                new_phone += char

        return new_phone


    def calculate_today_date_for_runner(self):
        """Calculates current date in Pacific time."""

        runner_timezone = pytz.timezone(self.timezone)
        dt = datetime.now(tz=runner_timezone)
        today = dt.date()

        return today


    def update_is_using_gCal(self, Bool):
        """Updates a runner in the database to is_using_gCal is True."""

        self.is_using_gCal = Bool
        db.session.commit()


    def add_oauth_token_to_database(self, credentials):
        """Adds oauth token to database"""
        self.OAuth_token = credentials.to_json()
        db.session.commit()


    def update_text_subscription(self, is_subscribed):
        """Updates the runner's subscription to receive text reminders
        in the database.
        """

        self.is_subscribed_to_texts = is_subscribed
        db.session.commit()


    def update_email_subscription(self, is_subscribed):
        """Updates the runner's subscription to receive email reminders in the
        database.
        """

        self.is_subscribed_to_email = is_subscribed
        db.session.commit()


    def update_phone(self, raw_phone):
        """Updates the runner's phone number in the database"""

        formatted_phone = Runner.format_phone(raw_phone)

        self.phone = formatted_phone
        db.session.commit()


    def update_timezone(self, new_timezone):
        """Updates the runner's timezone to the database."""

        self.timezone = new_timezone
        db.session.commit()


    def __repr__(self):
        """Provide helpful representation when printed."""

        return "<Runner runner_id=%s email=%s>" % (self.runner_id,
                                                   self.email)


class Plan(db.Model):
    """Plans made up of runs for runners."""

    __tablename__ = "plans"

    start_time_default = datetime.strptime('07:00', '%H:%M')

    plan_id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    runner_id = db.Column(db.Integer, db.ForeignKey('runners.runner_id'), nullable=False)
    name = db.Column(db.String(100), nullable=True)
    start_date = db.Column(db.Date, nullable=False)
    end_date = db.Column(db.Date, nullable=False)
    goal_distance = db.Column(db.Float, nullable=False)
    current_ability = db.Column(db.Integer, nullable=False)
    start_time = db.Column(db.DateTime, default=start_time_default, nullable=True)

    runner = db.relationship("Runner", backref=db.backref("plans"))


    def calculate_total_miles_completed(self):
        """Calculates the total miles that the runner has completed so far to
        display on dashboard.
        """

        total_miles_completed = 0
        for run in self.runs:
            if run.is_completed:
                total_miles_completed += run.distance

        return total_miles_completed


    def calculate_total_workouts_completed(self):
        """Calculates the total workouts that the runner has completed so far
        to display on dashboard.
        """

        total_workouts_completed = 0
        for run in self.runs:
            if run.is_completed:
                total_workouts_completed += 1

        return total_workouts_completed


    def calculate_days_to_goal(self):
        """Calculates how many days remain until the runner's goal to
        display on dashboard.
        """

        today_date = self.runner.calculate_today_date_for_runner()

        return (self.end_date - today_date).days


    def calculate_weeks_in_plan(self):
        """Given a plan, calculate the number of weeks in that plan."""

        days_to_goal = self.calculate_days_to_goal()
        weeks_in_plan = int(math.ceil(days_to_goal / 7.0))

        return weeks_in_plan


    def calculate_total_mileage(self):
        """Calculate the total miles in the plan."""

        total_mileage = 0

        for run in self.runs:
            total_mileage = total_mileage + run.distance

        return total_mileage


    def add_runs_to_database(self, weekly_plan):
        """Takes a plan and adds each run in the plan to the database."""

        for i in range(1, len(weekly_plan) + 1):
            for run_date in weekly_plan[str(i)]:
                distance = weekly_plan[str(i)][run_date]
                if distance > 0:
                    run = Run(plan_id=self.plan_id,
                              date=run_date,
                              distance=distance)
                    db.session.add(run)
        db.session.commit()


    def gather_info_to_update_dashboard(self):
        """Updates the total miles and total workouts completed on a user's
        dashboard.
        """

        total_miles_completed = self.calculate_total_miles_completed()
        total_workouts_completed = self.calculate_total_workouts_completed()
        result_data = {'total_miles_completed': total_miles_completed,
                       'total_workouts_completed': total_workouts_completed}

        return result_data

    def generate_running_dates(self):
        """Generates a list of dates for the duration of the users running
        plan
        """

        first_monday = self.start_date - timedelta(days=self.start_date.weekday())
        days_to_goal = (self.end_date - first_monday).days + 1
        dates = []

        for i in range(days_to_goal):
            run_date = first_monday + timedelta(days=+i)
            dates.append(run_date)

        return dates


    def update_start_time(self, start_time):
        """Updates the plan's start time to the database."""

        self.start_time = start_time
        db.session.commit()


    def __repr__(self):
        """Provide helpful representation when printed."""

        return "<Plan plan_id=%s runner_id=%s name=%s>" % (self.plan_id, 
                                                           self.runner_id,
                                                           self.name)


class Run(db.Model):
    """Runs for user plans."""

    __tablename__ = "runs"

    run_id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    plan_id = db.Column(db.Integer, db.ForeignKey('plans.plan_id'), nullable=False)
    date = db.Column(db.Date, nullable=False)
    distance = db.Column(db.Float, nullable=False)
    is_completed = db.Column(db.Boolean, default=False, nullable=False)
    is_on_gCal = db.Column(db.Boolean, default=False, nullable=False)

    plan = db.relationship("Plan", backref=db.backref("runs", order_by=date))


    def update_run(self, is_completed):
        """Updates run is_complete to true or false, commits updated run to
        database.
        """

        self.is_completed = is_completed
        db.session.commit()


    def __repr__(self):
        """Provide helpful representation when printed."""

        return "<Run run_id=%s plan_id=%s date=%s distance=%s>" % (self.run_id,
                                                                   self.plan_id,
                                                                   self.date,
                                                                   self.distance)
def example_data():
    """Creates some sample data for testing."""
    start_date = datetime.today()

    sally = Runner(runner_id=1, email='sally@gmail.com', password='password', salt='sldeifwlopcSDUEo')
    fred = Runner(runner_id=2, email='fred@gmail.com', password='password', salt='dhelsidehwddiaoe', is_subscribed_to_email=True, is_using_gCal=True, is_subscribed_to_texts=True)
    plan1 = Plan(plan_id=1, runner_id=1, start_date="2017-03-29", end_date="2017-05-27", goal_distance=13.1, current_ability=6)
    plan2 = Plan(plan_id=2, runner_id=2, start_date="2017-04-29", end_date="2017-05-27", goal_distance=10, current_ability=1)
    run1 = Run(run_id=1, plan_id=1, date="2017-04-27", distance=7, is_completed=True, is_on_gCal=False)
    run2 = Run(run_id=2, plan_id=1, date="2017-04-28", distance=4, is_completed=False, is_on_gCal=False)
    run3 = Run(run_id=3, plan_id=1, date="2017-04-29", distance=2, is_completed=False, is_on_gCal=False)
    run4 = Run(run_id=4, plan_id=2, date="2017-04-30", distance=7, is_completed=True, is_on_gCal=False)
    run5 = Run(run_id=5, plan_id=2, date="2017-05-01", distance=4, is_completed=False, is_on_gCal=False)
    run6 = Run(run_id=6, plan_id=2, date="2017-05-02", distance=2, is_completed=False, is_on_gCal=False)

    db.session.add_all([sally, fred, plan1, plan2, run1, run2, run3, run4, run5, run6])
    db.session.commit()

##############################################################################
# Helper functions

def connect_to_db(app, db_uri = 'postgresql:///running'):
    """Connect the database to our Flask app."""

    # Configure to use our PstgreSQL database
    app.config['SQLALCHEMY_DATABASE_URI'] = db_uri
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.app = app
    db.init_app(app)


if __name__ == "__main__":
    # As a convenience, if we run this module interactively, it will leave
    # you in a state of being able to work with the database directly.

    from server import app
    connect_to_db(app)
    print "Connected to DB."