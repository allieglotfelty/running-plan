"""Models and database functions for Run Plan project."""

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

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
    password = db.Column(db.String(64), nullable=True)
    salt = db.Column(db.String(16), nullable=False)
    is_using_gCal = db.Column(db.Boolean, default=False, nullable=True)
    is_subscribed = db.Column(db.Boolean, default=False, nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=True)
    timezone = db.Column(db.String(20), default='Pacific', nullable=True)
    OAuth_token = db.Column(db.String(100), nullable=True)
    photo = db.Column(db.String(200), nullable=True)


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
    start_date = db.Column(db.DateTime, nullable=False)
    end_date = db.Column(db.DateTime, nullable=False)
    goal_distance = db.Column(db.Float, nullable=False)
    current_ability = db.Column(db.Integer, nullable=False)
    start_time = db.Column(db.DateTime, default=start_time_default, nullable=True)

    runner = db.relationship("Runner", backref=db.backref("plans"))

    def __repr__(self):
        """Provide helpful representation when printed."""

        return "<Plan plan_id=%s runner_id=%s name=%s>" % (self.plan_id, self.runner_id, self.name)

class Run(db.Model):
    """Runs for user plans."""

    __tablename__ = "runs"

    run_id = db.Column(db.Integer, autoincrement=True, primary_key=True)
    plan_id = db.Column(db.Integer, db.ForeignKey('plans.plan_id'), nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    distance = db.Column(db.Float, nullable=False)
    is_completed = db.Column(db.Boolean, default=False, nullable=False)
    
    plan = db.relationship("Plan", backref=db.backref("runs", order_by=date))

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
    plan = Plan(plan_id=1, runner_id=1, start_date="2017-03-29", end_date="2017-05-27", goal_distance=13.1, current_ability=6)
    run1 = Run(run_id=1, plan_id=1, date="2017-04-27", distance=7, is_completed=True)
    run2 = Run(run_id=2, plan_id=1, date="2017-04-28", distance=4, is_completed=False)
    run3 = Run(run_id=3, plan_id=1, date="2017-04-29", distance=2, is_completed=False)

    db.session.add_all([sally, plan, run1, run2, run3])
    db.session.commit()

##############################################################################
# Helper functions

def connect_to_db(app):
    """Connect the database to our Flask app."""

    # Configure to use our PstgreSQL database
    app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql:///testdb'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.app = app
    db.init_app(app)


if __name__ == "__main__":
    # As a convenience, if we run this module interactively, it will leave
    # you in a state of being able to work with the database directly.

    from server import app
    connect_to_db(app)
    print "Connected to DB."