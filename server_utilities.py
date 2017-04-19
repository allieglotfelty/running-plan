from flask import session
from model import db, Runner, Plan, Run
from datetime import datetime, timedelta, date
import hashlib
import binascii
import random
from running_plan import build_plan_with_two_dates, calculate_start_date
from dateutil.relativedelta import *
import pytz
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
import os
import sendgrid
from sendgrid.helpers.mail import *


def generate_weekly_plan(raw_current_ability, raw_goal_distance, raw_end_date):
    """Generates a runner's plan based on the information they entered."""

    current_ability = float(raw_current_ability)
    goal_distance = float(raw_goal_distance)
    end_date = datetime.strptime(raw_end_date, "%Y-%m-%d").date()
    today_date = calculate_today_date_pacific()
    weekly_plan = build_plan_with_two_dates(today_date, 
                                            end_date, 
                                            current_ability, 
                                            goal_distance)
    start_date = calculate_start_date(today_date)

    updated_vals = {
                    'current_ability': current_ability,
                    'goal_distance': goal_distance,
                    'start_date': start_date,
                    'end_date': end_date,
                    'weekly_plan': weekly_plan
                    }

    session.update(updated_vals)
    print session

    return weekly_plan


def generate_salt():
    """Generates salt for password encryption."""

    letters = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"

    return "".join(random.choice(letters) for i in range(16))


def generate_hashed_password(runner_password, salt):
    """Takes in a users password, hashes it and returns a hashed version of it"""

    binary_password = hashlib.pbkdf2_hmac('sha256', runner_password, salt, 100000)
    hex_password = binascii.hexlify(binary_password)

    return hex_password


def add_runner_to_database(email, password, salt):
    """Adds a runner to the database and returns the runner object"""

    runner = Runner(email=email, password=password, salt=salt)
    db.session.add(runner)
    db.session.commit()

    return runner


def calculate_today_date_pacific():
    """Calculates current date in Pacific time."""

    pacific = pytz.timezone('US/Pacific')
    dt = datetime.now(tz=pacific)
    today = dt.date()

    return today


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


def generate_run_events_for_google_calendar(plan, timezone, chosen_start_time):
    """Generates plans to add to user's google calendar account."""

    runs = plan.runs
    run_events = []

    for run in runs[15:20]:
        if not run.is_on_gCal:
            title = "Run %s miles" % run.distance
            date = run.date

            finish_time_datetime = chosen_start_time + timedelta(hours=1)
            start_time = chosen_start_time.time()
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


def get_runs_for_reminder_texts(run_date):
    """Query database for all users who need to receive a text reminder."""

    runs_for_date = db.session.query(Run).join(Plan).join(Runner).filter(Runner.is_subscribed_to_texts == True,
                                                                         Run.date == run_date).all()
    return runs_for_date


def send_reminder_sms_messages(run_date):
    """Send text messages to runners via Twilio."""

    ACCOUNT_SID = os.environ['TWILIO_ACCOUNT_SID']
    AUTH_TOKEN = os.environ['TWILIO_AUTH_TOKEN']

    client = Client(ACCOUNT_SID, AUTH_TOKEN)

    runs_for_date = get_runs_for_reminder_texts(run_date)

    if runs_for_date:
        for run_event in runs_for_date:
            distance = run_event.distance
            runner_phone = run_event.plan.runner.phone
            print run_event.plan.runner.runner_id, run_event.plan.runner.phone
            runner_message = "%s Don't forget your %s mile run today! Reply Y to log your run or N for words of encouragement." % (run_event.plan.runner.runner_id, distance)

            message = client.messages.create(
                                             to=runner_phone,
                                             from_="+19785484823",
                                             body=runner_message)
            return True
    else:
        print "No runs for today!"
        return False


def response_to_inbound_text(number, message_body):
    """Response to an inbound text message to update run in database, send words
    of encouragement or let the user know what to enter.
    """
    runner = Runner.query.filter_by(phone=number).first()
    today_date = runner.calculate_today_date_for_runner()

    resp = MessagingResponse()

    positive_message_responses = ['Congrats! Keep up the great work!',
                                  'Great job! You are progressing nicely.',
                                  'Just keep running. Just keep running.',
                                  'You are a running master',
                                  'Way to go!',
                                  'Good job completing your run.']

    encouraging_negative_responses = ['Bummer, see if you can fit in your run later this week.',
                                      'Hope everything is okay.',
                                      'We all have our off days. Try again tomorrow.',
                                      'Remember to make today your off day, and run tomorrow!']

    positive_reply_choice = random.choice(positive_message_responses)
    negative_reply_choice = random.choice(encouraging_negative_responses)

    if message_body.lower() in ['y', 'yes']:
        reply = positive_reply_choice + ' Your run has been logged.'
        run = db.session.query(Run).join(Plan).join(Runner).filter(Runner.phone == number,
                                                                   Runner.is_subscribed_to_texts == True,
                                                                   Run.date == today_date).first()
        update_run(run.run_id, True)

    elif message_body.lower() in ['n', 'no']:
        reply = negative_reply_choice
    else:
        reply = "Reply with one of the following: Y or N"

    return resp.message(reply)


def send_email_reminders():
    """Send email messages to runners via SendGrid."""

    sg = sendgrid.SendGridAPIClient(apikey=os.environ.get('SENDGRID_API_KEY'))

    today_date = calculate_today_date_pacific()
    next_sunday_date = today_date + timedelta(7)
    runners_for_emails = Runner.query.filter_by(is_subscribed_to_email=True).all()

    for runner in runners_for_emails:
        runner_email = runner.email
        runner_id = runner.runner_id
        runs_for_email = db.session.query(Run).join(Plan).join(Runner).filter(
                                    (Runner.runner_id == runner_id)
                                    & (Run.date > today_date)
                                    & (Run.date <= next_sunday_date)
                                    ).order_by(Run.date).all()
        runs_to_add_to_email = ""

        for run in runs_for_email:
            date = datetime.strftime(run.date, "%A, %b %d:")
            run_for_date = "<li>%s %s miles</li>" % (date, run.distance)
            runs_to_add_to_email = runs_to_add_to_email + run_for_date

        from_email = Email("runholmesplanner@gmail.com")
        subject = "Weekly Run Reminder!"
        to_email = Email(runner_email)
        content = Content("text/html", """<html>
                          <body>
                            <h2>Happy Monday!</h2>
                            <p>Here are your runs for this week:</p>
                            <ul>""" + runs_to_add_to_email + """
                            </ul>
                            <p>We look forward to hearing about your progress!</p>
                            <img src="https://media.giphy.com/media/SZ8ZhNzb86LFC/giphy.gif">
                            <p> - The Run Holmes Team</p>
                        </body>
                        </html>""")
        mail = Mail(from_email, subject, to_email, content)
        response = sg.client.mail.send.post(request_body=mail.get())
        print(response.status_code)
        print(response.body)
        print(response.headers)

    return runners_for_emails


def is_admin(password):
    """Checks if the user who logged in is an admin."""

    admin_salt = 'EdHqqrZbJPxjpKfX'
    hashed_password = generate_hashed_password(password, admin_salt)

    return hashed_password == '7652c53ed89bf85a6da936f614bb32c9274706b7dbafe2a5fe68bbeebf24d9e1'
