"""Run Planner"""

from jinja2 import StrictUndefined
from flask import Flask, jsonify, render_template, redirect, request, flash, session, Response, url_for
from flask_debugtoolbar import DebugToolbarExtension
from model import connect_to_db, db, Runner, Plan, Run
from datetime import datetime, date, timedelta, time
# import pytz
# from tzlocal import get_localzone
from apiclient import discovery as gcal_client
from oauth2client import client
import httplib2
from running_plan import create_excel_text
import server_utilities
# from twilio import twiml
# import sendgrid
# import os
from sendgrid.helpers.mail import *

app = Flask(__name__)

# Required to use Flask sessions and the debug toolbar
app.secret_key = "amcio9320e9wjadmclswep9q2-[ie290qfmvwnuq34op092iwopqk;dsmlcvq84yp9hrwafousdzncjlkx2[qOAPDSSGURW9EI"

app.jinja_env.undefined = StrictUndefined

@app.route('/')
def index():
    """Homepage."""

    today = server_utilities.calculate_today_date_pacific()
    year_from_today = server_utilities.calculate_date_year_from_today(today)
    date_today = server_utilities.generate_date_string(today)
    date_year_from_today = server_utilities.generate_date_string(year_from_today)

    distances = range(2, 26)

    if session.get('admin'):
        redirect('/admin')
    try:
        session['runner_id']
    except KeyError:
        return render_template("homepage.html",
                                today=date_today,
                                yearaway=date_year_from_today,
                                distances=distances)

    return redirect("/dashboard")


@app.route('/plan.json', methods=["GET"])
def generate_plan():
    """Generates and displays a runner's plan based on the information
    they entered.
    """

    raw_current_ability = request.args.get("current-ability")
    raw_goal_distance = request.args.get("goal-distance")
    raw_end_date = request.args.get("goal-date")

    try:
        weekly_plan = server_utilities.generate_weekly_plan(raw_current_ability,
                                                            raw_goal_distance,
                                                            raw_end_date)
    except ValueError:
        weekly_plan = {'response': 'show response'}

    results = jsonify(weekly_plan)

    return results


@app.route('/download', methods=["GET"])
def download_excel():
    """Creates an excel file and downloads it to the users computer."""

    weekly_plan = session.get('weekly_plan')

    # weekly_plan = session.get('weekly_plan')
    excel_text = create_excel_text(weekly_plan)

    # Create a response object that takes in the excel_text
    # (string of excel doc) and the mimetype (format) for the doc
    response = Response(response=excel_text,
                        status=200,
                        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

    # Says the header will contain an attachement of the filename RunPlan.xlsx
    response.headers["Content-Disposition"] = "attachment; filename=RunPlan.xlsx"

    return response


@app.route('/sign-up-complete', methods=["POST"])
def process_sign_up():
    """Checks if user exists. If not, creates new account."""

    raw_runner_email = request.form.get("email")
    raw_runner_password = request.form.get("password")
    email_query = Runner.query.filter_by(email=raw_runner_email).first()

    if email_query:
        flash('This user already exists. Please try to login or create an account with a different email.')
        return redirect('/')

    else:
        salt = server_utilities.generate_salt()
        hashed_password = server_utilities.generate_hashed_password(raw_runner_password,
                                                                    salt)

        current_runner = server_utilities.add_runner_to_database(raw_runner_email,
                                                                 hashed_password,
                                                                 salt)

        current_runner_id = current_runner.runner_id
        session['runner_id'] = current_runner_id

        current_plan = server_utilities.add_plan_to_database(current_runner_id)

        current_plan_id = current_plan.plan_id
        current_plan.name = "Running Plan %s" % current_plan_id
        db.session.commit()

        weekly_plan = session.get('weekly_plan')
        current_plan.add_runs_to_database(weekly_plan)

        return redirect('/dashboard')


@app.route('/login-complete', methods=["POST"])
def process_login():
    """Checks if user email and password exist on same account.
    If so, logs them into their account. If not, flashes a message.
    """

    raw_runner_email = request.form.get("email")
    raw_runner_password = request.form.get("password")
    check_is_admin = server_utilities.is_admin(raw_runner_password)

    if raw_runner_email == 'admin@admin.com' and check_is_admin:
        session['admin'] = 'admin'
        return redirect('/admin')

    runner_account = Runner.query.filter_by(email=raw_runner_email).first()

    if runner_account:
        hashed_password = server_utilities.generate_hashed_password(raw_runner_password,
                                                                    runner_account.salt)

    if runner_account and runner_account.password == hashed_password:
        session["runner_id"] = runner_account.runner_id
        return redirect('/dashboard')
    else:
        flash("Email or Password is incorrect. Please try again!")
        return redirect("/")


@app.route('/logout-complete')
def process_logout():
    """Logout user and clear their session."""

    session.clear()
    return redirect("/")


@app.route('/dashboard')
def display_runner_page():
    """Displays the runner's dashboard with current plan and tracking information."""

    times = range(1, 25)

    runner_id = session.get('runner_id')
    runner = Runner.query.get(runner_id)

    if not runner:
        return redirect('/')

    today_date = runner.calculate_today_date_for_runner()

    current_plan = db.session.query(Plan).join(Runner).filter(Runner.runner_id==runner_id,
                                                              Plan.end_date>=today_date).first()

    dates = current_plan.generate_running_dates()

    if current_plan:
        days_left_to_goal = current_plan.calculate_days_to_goal()
        total_workouts_completed = current_plan.calculate_total_workouts_completed()
        total_miles_completed = current_plan.calculate_total_miles_completed()
    else:
        flash("It seems like all of your plans have expired. Feel free to click and view an old plan or make a new one!")

    weeks_in_plan = current_plan.calculate_weeks_in_plan()
    runs = {}
    for run in current_plan.runs:
        future = today_date < run.date
        runs[run.date] = {'run_id': run.run_id,
                          'distance': run.distance,
                          'is_completed': run.is_completed,
                          'is_in_future': future}

    return render_template("runner_dashboard.html", runner=runner,
                                                    plan=current_plan,
                                                    runs=runs,
                                                    weeks_in_plan=weeks_in_plan,
                                                    days_left_to_goal=days_left_to_goal,
                                                    total_workouts_completed=total_workouts_completed,
                                                    total_miles_completed=total_miles_completed,
                                                    dates=dates,
                                                    times=times,
                                                    today_date=today_date)


@app.route('/update-run.json', methods=["POST"])
def update_run_and_dashboard_as_completed():
    """When a runner clicks a run checkbox, updates run is_completed as true,
    commits updated run to database, and updates the total miles and total workouts
    completed on the dashboard.
    """

    run_id = request.form.get("run-id")
    run = Run.query.get(run_id)
    run.update_run(True)
    plan = run.plan
    result_data = plan.gather_info_to_update_dashboard()

    return jsonify(result_data)


@app.route('/update-run-incomplete.json', methods=["POST"])
def update_run__and_dashboard_as_incompleted():
    """When a runner unclicks a run checkbox, updates run is_completed as false,
    commits updated run to database, and updates the total miles and total workouts
    completed on the dashboard.
    """

    run_id = request.form.get("run-id")
    run = Run.query.get(run_id)
    run.update_run(False)
    result_data = run.plan.gather_info_to_update_dashboard()

    return jsonify(result_data)


@app.route('/workout-info.json', methods=["GET"])
def return_workout_info_for_doughnut_chart():
    """Get info for workout doughnut chart."""

    runner_id = session.get('runner_id')
    runner = Runner.query.get(runner_id)
    today_date = runner.calculate_today_date_for_runner()

    count_total_plan_runs = db.session.query(Run).join(Plan).join(Runner).filter(Runner.runner_id==runner_id, 
                                                                                 Plan.end_date>=today_date).count()
    count_plan_runs_completed = db.session.query(Run).join(Plan).join(Runner).filter(Runner.runner_id==runner_id, 
                                                                                     Plan.end_date>=today_date, 
                                                                                  Run.is_completed==True).count()
    workouts_remaining = count_total_plan_runs - count_plan_runs_completed
    
    data_dict = {
                 "labels": [
                            "Total Workouts Completed",
                            "Workouts Remaining"
                           ],
                 "datasets": [
                        {
                         "data": [count_plan_runs_completed, workouts_remaining],
                         "backgroundColor": [
                                             "#FFED82",
                                             "#B0E85F"
                                            ],
                         "hoverBackgroundColor": [
                                                  "#37E8E4",
                                                  "0E60FF"
                                                 ]
                        }
                 ]
                }

    return jsonify(data_dict)


@app.route('/mileage-info.json', methods=["GET"])
def return_total_miles_info_for_doughnut_chart():
    """Get info for mileage doughnut chart."""

    runner_id = session.get('runner_id')
    runner = Runner.query.get(runner_id)
    today_date = runner.calculate_today_date_for_runner()

    current_plan = db.session.query(Plan).join(Runner).filter(Runner.runner_id==runner_id, 
                                                              Plan.end_date>=today_date).first()

    total_mileage = current_plan.calculate_total_mileage()
    total_miles_completed = current_plan.calculate_total_miles_completed()
    miles_remaining = total_mileage - total_miles_completed

    data_dict = {
                 "labels": [
                            "Total Miles Completed",
                            "Total Miles Remaining"
                           ],
                 "datasets": [
                        {
                         "data": [total_miles_completed, miles_remaining],
                         "backgroundColor": [
                                             "#37E8E4",
                                             "#B0E85F"
                                            ],
                         "hoverBackgroundColor": [
                                                  "#FFED82",
                                                  "0E60FF"
                                                 ]
                        }
                 ]
                }

    return jsonify(data_dict)


@app.route('/add-to-google-calendar', methods=["POST"])
def add_runs_to_runners_google_calendar_account():
    """Adds a runner's run events to their Google Calendar account.
    Route works if want users to add events to Google Calendar directly from
    their dashboards. The problem with this is that the user must wait for the
    events to be created and added to their calendars. Instead, I created a
    cronjob to run every 10 minutes and add any run events that have not been
    added already.
    """

    # If there are no credentials in the current session, 
    # redirect to get oauth permisssions
    if not session.get('credentials'):
        return redirect(url_for('oauth2callback'))

    # Otherwise get the credentials
    credentials = client.OAuth2Credentials.from_json(session['credentials'])

    # If the credentials have expired, redirect to get oauth permissions
    if credentials.access_token_expired:
        return redirect(url_for('oauth2callback'))

    else:
        # Get the autorization to the user's google calendar
        http_auth = credentials.authorize(httplib2.Http())

        # Gather the user's google calendar using the authorization to add events
        calendar = gcal_client.build('calendar', 'v3', http_auth)

        runner_id = session.get('runner_id')
        runner = Runner.query.get(runner_id)
        runner.update_is_using_gCal(True)

        today_date = runner.calculate_today_date_for_runner()
        current_plan = db.session.query(Plan).join(Runner).filter(Runner.runner_id == runner_id,
                                                                  Plan.end_date >= today_date).first()
        timezone = runner.timezone

        if current_plan:
            preferred_start_time = current_plan.start_time
            run_events = server_utilities.generate_run_events_for_google_calendar(current_plan,
                                                                                  timezone,
                                                                                  preferred_start_time)
            if not run_events:
                flash('There are no new runs to add to your Google Calendar.')
            else:
                for event in run_events:
                    event_to_add = calendar.events().insert(calendarId='primary', body=event).execute()
                    print'Event created: %s' % (event_to_add.get('htmlLink'))
                flash('All running events have been added to your Google Calendar.')
        else:
            flash('There are no new runs to add to your Google Calendar.')

    return redirect("/dashboard")


@app.route('/oauth2callback')
def oauth2callback():
    """Flow stores application secrets and site access we are requesting.
    Then, redirects the user to the authorization uri - site for them to login
    and/or provide permissions for the application to access their protected
    resources.
    """

    flow = client.flow_from_clientsecrets(
        'client_secret.json',
        scope='https://www.googleapis.com/auth/calendar',
        redirect_uri=url_for('oauth2callback', _external=True))
    if 'code' not in request.args:
        # Send user to email page & asks permission to send info to calendar
        auth_uri = flow.step1_get_authorize_url()
        return redirect(auth_uri)
    else:
        # answer from user re: using calendar, gives back oauth token to send info to calendar
        auth_code = request.args.get('code')
        credentials = flow.step2_exchange(auth_code)
        session['credentials'] = credentials.to_json()

        runner_id = session.get('runner_id')
        runner = Runner.query.get(runner_id)
        runner.add_oauth_token_to_database(credentials)
        flash("Your runs will be added to your Google Calender in the next 10 minutes.")
        # For using Google Calendar cronjob to add events:
        return redirect(url_for('display_runner_page'))

        # For added events directly to Google Calendar:
        # return redirect(url_for('add_runs_to_runners_google_calendar_account'))


@app.route('/update-plan-name.json', methods=["POST"])
def update_plan_name():
    """Update plan name in the database"""

    new_name = request.form.get("newName")
    plan_id = request.form.get("planId")
    plan = Plan.query.get(plan_id)
    plan.name = new_name
    db.session.commit()

    results = {'newName': new_name}

    return jsonify(results)


@app.route('/update-account', methods=["POST"])
def update_account_settings():
    """Update user account settings based on preferences specified."""

    runner_id = session.get('runner_id')
    runner = Runner.query.get(runner_id)
    today_date = runner.calculate_today_date_for_runner()
    current_plan = db.session.query(Plan).join(Runner).filter(Runner.runner_id == runner_id,
                                                              Plan.end_date >= today_date).first()
    opt_email = request.form.get("opt-email")
    opt_text = request.form.get("opt-text")
    phone = request.form.get("phone-number")
    opt_gcal = request.form.get("opt-gcal")
    timezone = request.form.get("time-zone")
    start_time = request.form.get("cal-run-start-time")

    if phone:
        runner.update_phone(phone)
        flash("Your phone number has been updated.")

    if timezone:
        if timezone is not runner.timezone:
            runner.update_timezone(timezone)

    if start_time:
        start_time_formatted = datetime.strptime(str(start_time), '%H:%M:%S')
        if start_time_formatted.time() is not current_plan.start_time.time():
            current_plan.update_start_time(start_time_formatted)

    if not runner.is_subscribed_to_texts and opt_text == 'on':
        runner.update_text_subscription(True)
        runner.update_phone(phone)
        flash("You are now signed-up to receive text message reminders.")

    if runner.is_subscribed_to_texts and not opt_text:
        runner.update_text_subscription(False)
        flash("You will no longer receive text message reminders.")

    if not runner.is_subscribed_to_email and opt_email == 'on':
        runner.update_email_subscription(True)
        flash("You are now subscribed to receive weekly emails.")

    if runner.is_subscribed_to_email and not opt_email:
        runner.update_email_subscription(False)
        flash("You are no longer subscribed to weekly emails.")

    if not runner.is_using_gCal and opt_gcal == 'on':
        runner.update_is_using_gCal(True)

        # For using google calendar cronjob to add events:
        return redirect('/oauth2callback')

        # For adding runs directly to calendar:
        # return redirect('/add-to-google-calendar')

    if runner.is_using_gCal and not opt_gcal:
        runner.update_is_using_gCal(False)

    return redirect("/dashboard")


@app.route('/send-sms-reminders', methods=["POST"])
def send_sms_reminders():
    """Gets a list of runs for the day and sends an sms reminder to the runners."""

    run_date = request.form.get("run-date")
    if server_utilities.send_reminder_sms_messages(run_date):
        flash("Messages sent successfully!")
    else:
        flash("No messages sent.")

    return redirect('/admin')


@app.route('/admin')
def render_admin_page():
    """Displays the admin page."""

    if session.get('admin'):
        return render_template('admin.html')
    else:
        redirect('/')


@app.route('/inbound-text', methods=["POST"])
def receive_and_respond_to_inbound_text():
    """Receive and inbound text, update database and respond to the runner."""

    number = request.form.get('From')
    message_body = request.form.get('Body')
    resp = server_utilities.response_to_inbound_text(number, message_body)

    return str(resp)


@app.route('/send-emails', methods=["POST"])
def send_weekly_emails():
    """Gets list of users who have opted into weekly email sand then sends a
    weekly reminder email to them."""

    runners = server_utilities.send_email_reminders()
    if runners:
        flash("Emails sent successfully!")
    else:
        flash("No emails to send.")

    return redirect('/admin')


if __name__ == "__main__":
    # We have to set debug=True here, since it has to be True at the
    # point that we invoke the DebugToolbarExtension
    app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False
    app.debug = True
    app.jinja_env.auto_reload = app.debug  # make sure templates, etc. are not cached in debug mode

    connect_to_db(app)

    # Use the DebugToolbar
    DebugToolbarExtension(app)

    app.run(port=5000, host='0.0.0.0')
