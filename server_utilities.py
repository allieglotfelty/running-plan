from model import db, Runner, Plan, Run
from datetime import datetime, date, timedelta, time
import hashlib, binascii
from random import choice
from running_plan import build_plan_with_two_dates


def generate_weekly_plan(raw_current_ability, raw_goal_distance, raw_end_date):
    """Generates a runner's plan based on the information they entered."""

    current_ability = float(raw_current_ability)
    goal_distance = float(raw_goal_distance)
    end_date = datetime.strptime(raw_end_date, "%Y-%m-%d")
    today_date = datetime.today()
    weekly_plan = build_plan_with_two_dates(today_date, end_date, current_ability, goal_distance)

    session['current_ability'] = current_ability
    session['goal_distance'] = goal_distance
    session['start_date'] = today_date + timedelta(days=1)
    session['end_date'] = end_date
    session['weekly_plan'] = weekly_plan

    return weekly_plan


def generate_salt():
    """Generates salt for password encryption."""

    letters = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"

    return "".join(choice(letters) for i in range(16))


def calculate_days_to_goal(today_date, end_date):
    """Calculates how many days remain until the runner's goal to display on dashboard."""
    
    return (end_date - today_date).days


def calculate_total_miles_completed(runs):
    """Calculates the total miles that the runner has completed so far to display on dashboard."""
    total_miles_completed = 0
    for run in runs:
        if run.is_completed == True:
            total_miles_completed += run.distance

    return total_miles_completed


def calculate_total_workouts_completed(runs):
    """Calculates the total workouts that the runner has completed so far to display on dashboard."""
    total_workouts_completed = 0
    for run in runs:
        if run.is_completed == True:
            total_workouts_completed += 1

    return total_workouts_completed


def add_plan_to_database(runner_id):
    """Adds a plan to the database and returns the plan object."""

    plan = Plan(runner_id=runner_id,
                start_date=session.get('start_date'), 
                end_date=session.get('end_date'),
                goal_distance=session.get('goal_distance'),
                current_ability=session.get('current_ability'),
                )
    db.session.add(plan)
    db.session.commit() 

    return plan


def add_runner_to_database(email, password, salt):
    """Adds a runner to the database and returns the runner object"""

    runner = Runner(email=email, password=password, salt=salt)
    db.session.add(runner)
    db.session.commit()

    return runner


def generate_hashed_password(runner_password, salt):
    """Takes in a users password, hashes it and returns a hashed version of it"""

    binary_password = hashlib.pbkdf2_hmac('sha256', runner_password, salt, 100000)
    hex_password = binascii.hexlify(binary_password)

    return hex_password


def add_runs_to_database(weekly_plan, plan_id):
    """Takes a plan and adds each run in the plan to the database."""

    for i in range(1, len(weekly_plan) + 1):
        for date in weekly_plan[str(i)]:
            distance = weekly_plan[str(i)][date]
            run = Run(plan_id=plan_id, date=date, distance=distance)
            db.session.add(run)
    db.session.commit()


def update_run(run_id, is_completed):
    """Updates run is_complete to true or false, commits updated run to database.
    """
    run = Run.query.get(run_id)
    run.is_completed = is_completed
    db.session.commit()


def gather_info_to_update_dashboard(run_id):
    """Updates the total miles and total workouts completed on a user's dashboard."""

    run = Run.query.get(run_id)
    plan_id = run.plan_id
    plan = Plan.query.get(plan_id)
    runs = plan.runs

    total_miles_completed = calculate_total_miles_completed(runs)
    total_workouts_completed = calculate_total_workouts_completed(runs)
    result_data = {'total_miles_completed': total_miles_completed,
                   'total_workouts_completed': total_workouts_completed,
                   'run_id': run_id}

    return result_data


def update_runner_to_is_using_gCal(runner_id):
    """Updates a runner in the database to is_using_gCal is True."""

    runner = Runner.query.get(runner_id)
    runner.is_using_gCal = True
    db.session.commit()


def generate_run_events_for_google_calendar(plan):
    """Generates plans to add to user's google calendar account."""

    runs = plan.runs
    run_events = []

    for run in runs[:5]:
        if run.distance > 0 and run.is_on_gCal == False:
            title = "Run %s miles" % run.distance
            date = run.date.date()
            
            start_time = plan.start_time
            finish_time = start_time + timedelta(hours=1)
            start_time = start_time.time()
            finish_time = finish_time.time()
            
            start = datetime.combine(date, start_time).isoformat()
            finish = datetime.combine(date, finish_time).isoformat()

            event = {
                'summary': title,
                'start': {
                           'dateTime': start,
                           'timeZone': 'America/Los_Angeles'
                },
                'end': {
                           'dateTime': finish,
                           'timeZone': 'America/Los_Angeles'
                },
                'reminders': {
                            'useDefault': False,
                },
            }
            run_events.append(event)
            run.is_on_gCal = True

    db.session.commit()
    
    return run_events


def add_oauth_token_to_database(credentials):
    """Adds oauth token to database"""
    runner_id = session.get('runner_id')
    runner = Runner.query.get(runner_id)
    runner.OAuth_token = credentials.to_json()
    db.session.commit()

