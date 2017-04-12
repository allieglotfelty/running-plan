from flask import session
from model import db, Runner, Plan, Run
from datetime import datetime, timedelta, date
import hashlib
import binascii
from random import choice
from running_plan import build_plan_with_two_dates, calculate_start_date
from dateutil.relativedelta import *
import math
import pytz
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse



def generate_weekly_plan(raw_current_ability, raw_goal_distance, raw_end_date):
    """Generates a runner's plan based on the information they entered."""

    current_ability = float(raw_current_ability)
    goal_distance = float(raw_goal_distance)
    end_date = datetime.strptime(raw_end_date, "%Y-%m-%d").date()
    today_date = calculate_today_date()
    weekly_plan = build_plan_with_two_dates(today_date, end_date, current_ability, goal_distance)

    session['current_ability'] = current_ability
    session['goal_distance'] = goal_distance
    session['start_date'] = calculate_start_date(today_date)
    session['end_date'] = end_date
    session['weekly_plan'] = weekly_plan

    # updated_vals = {
    # "val1": 1,
    # }

    # session.update(updated_vals)

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
        if run.is_completed:
            total_miles_completed += run.distance

    return total_miles_completed


def calculate_total_workouts_completed(runs):
    """Calculates the total workouts that the runner has completed so far to display on dashboard."""
    total_workouts_completed = 0
    for run in runs:
        if run.is_completed:
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
        for run_date in weekly_plan[str(i)]:
            distance = weekly_plan[str(i)][run_date]
            if distance > 0:
                run = Run(plan_id=plan_id, date=run_date, distance=distance)
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


def generate_run_events_for_google_calendar(plan, timezone, chosen_start_time):
    """Generates plans to add to user's google calendar account."""

    # start_time_datetime = datetime.strptime(chosen_start_time, '%H:%M')
    runs = plan.runs
    run_events = []

    for run in runs[15:20]:
        if run.distance > 0 and not run.is_on_gCal:
            title = "Run %s miles" % run.distance
            date = run.date

            finish_time_datetime = chosen_start_time + timedelta(hours=1)
            start_time = chosen_start_time.time()
            # finish_time_datetime = start_time_datetime + timedelta(hours=1)
            # start_time = start_time_datetime.time()
            finish_time = finish_time_datetime.time()

            start = datetime.combine(date, start_time).isoformat()
            finish = datetime.combine(date, finish_time).isoformat()

            event = {
                'summary': title,
                'start': {
                           'dateTime': start,
                           'timeZone': timezone
                },
                'end': {
                           'dateTime': finish,
                           'timeZone': timezone
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


def generate_running_dates(start_date, end_date):
    """Generates a list of dates for the duration of the users running plan"""

    first_monday = start_date - timedelta(days=start_date.weekday())
    days_to_goal = (end_date - first_monday).days + 1
    dates = []

    for i in range(days_to_goal):
        run_date = first_monday+timedelta(days=+i)
        dates.append(run_date)

    return dates


def calculate_weeks_in_plan(plan):
    """Given a plan, calculate the number of weeks in that plan."""

    days_to_goal = calculate_days_to_goal(plan.start_date, plan.end_date)
    weeks_in_plan = int(math.ceil(days_to_goal / 7.0))

    return weeks_in_plan


def get_runs_for_reminder_texts(run_date):
    """Query database for all users who need to receive a text reminder."""

    runs_for_date = db.session.query(Run).join(Plan).join(Runner).filter(Runner.is_subscribed_to_texts == True,
                                                                          Run.date == run_date).all()
    return runs_for_date


def calculate_today_date():
    """Calculates current date in Pacific time."""

    pacific = pytz.timezone('US/Pacific')
    dt = datetime.now(tz=pacific)
    today = dt.date()

    return today


def update_runner_text_subscription(runner_id, is_subscribed):
    """Updates the runner's subscription to receive text reminders in the database."""
    
    runner = Runner.query.get(runner_id)
    runner.is_subscribed_to_texts = is_subscribed
    db.session.commit()


def update_runner_phone(runner_id, raw_phone):

    formatted_phone = "+1%s" % raw_phone
    runner = Runner.query.get(runner_id)
    runner.phone = formatted_phone
    db.session.commit()

def send_reminder_sms_messages(run_date):
    """Send text messages to runners via Twilio."""

    # Your Account SID from twilio.com/console
    account_sid = "ACa40c55b8472df2c9edc5db30907ef86e"
    # Your Auth Token from twilio.com/console
    auth_token  = "af131fa75a3b51ec3cb7f751191d0f2c"

    client = Client(account_sid, auth_token)

    runs_for_date = get_runs_for_reminder_texts(run_date)
    import pdb; pdb.set_trace()

    for run_event in runs_for_date:
        distance = run_event.distance
        runner_phone = run_event.plan.runner.phone
        runner_message = "%s Did you complete your %s mile run today? (Reply Y/N)" % (run_event.plan.runner.runner_id, distance)
        message = client.messages.create(
                                         to=runner_phone,
                                         from_="+19785484823",
                                         body=runner_message)






