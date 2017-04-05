"""Run Planner"""

from jinja2 import StrictUndefined
from flask import Flask, jsonify, render_template, redirect, request, flash, session, Response, url_for
from flask_debugtoolbar import DebugToolbarExtension
from model import connect_to_db, db, Runner, Plan, Run
from datetime import datetime, date, timedelta, time
import hashlib, binascii
from random import choice
from apiclient import discovery as gcal_client
from oauth2client import client, tools
from oauth2client.file import Storage
import httplib2
from running_plan import build_plan_with_two_dates, create_excel_text, build_plan_no_weeks, create_event_source

app = Flask(__name__)

# Required to use Flask sessions and the debug toolbar
app.secret_key = "amcio9320e9wjadmclswep9q2-[ie290qfmvwnuq34op092iwopqk;dsmlcvq84yp9hrwafousdzncjlkx2[qOAPDSSGURW9EI"

app.jinja_env.undefined = StrictUndefined


@app.route('/')
def index():
    """Homepage."""

    try:
        session['runner_id']
    except KeyError:
        return render_template("homepage.html")

    return redirect("/dashboard")


@app.route('/plan.json', methods=["POST"])
def generate_plan():
    """Generates and displays a runner's plan based on the information
    they entered.
    """
    
    raw_current_ability = request.form.get("current-ability")
    raw_goal_distance = request.form.get("goal-distance")
    raw_end_date = request.form.get("goal-date")
    today_date = datetime.today()
    weekly_plan = generate_weekly_plan(raw_current_ability, raw_goal_distance, raw_end_date)

    return jsonify(weekly_plan)


# @app.route('/run-event', methods=["GET"])
# def generate_run_event():
#     """Gets running info for a particular date"""

#     current_ability = float(request.form.get("current-ability"))
#     goal_distance = float(request.form.get("goal-distance"))
#     end_date = datetime.strptime(request.form.get("goal-date"), "%Y-%m-%d")
#     today_date = datetime.today()
#     weekly_plan = build_plan_no_weeks(today_date, end_date, current_ability, goal_distance)
#     event_source = create_event_source(weekly_plan)

#     # weekly_plan()
#     pass


@app.route('/download', methods=["GET"])
def download_excel():
    """Creates an excel file and downloads it to the users computer."""
    
    weekly_plan = session.get('weekly_plan')

    # weekly_plan = session.get('weekly_plan')
    excel_text = create_excel_text(weekly_plan)

    # Create a response object that takes in the excel_text (string of excel doc) and the mimetime (format) for the doc
    response = Response(response=excel_text, status=200, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    
    # Says the header will contain an attachement of the filename RunPlan.xlsx
    response.headers["Content-Disposition"] = "attachment; filename=RunPlan.xlsx"

    return response


@app.route('/sign-up')
def display_sign_up_page():
    """Sign-up Page."""

    return render_template('registration.html')


@app.route('/sign-up-complete', methods=["POST"])
def process_sign_up():
    """Checks if user exists. If not, creates new account."""

    raw_runner_email = request.form.get("email")
    raw_runner_password = request.form.get("password")
    email_query = Runner.query.filter_by(email=raw_runner_email).all()

    if email_query:
        flash('This user already exists. Please try to login or create an account with a different email.')
        return redirect('/')

    else:
        salt = generate_salt()
        hashed_password = generate_hashed_password(raw_runner_password, salt)

        current_runner = add_runner_to_database(raw_runner_email, hashed_password, salt)

        current_runner_id = current_runner.runner_id
        session['runner_id'] = current_runner_id

        current_plan = add_plan_to_database(current_runner_id)

        current_plan_id = current_plan.plan_id
        current_plan.name = "Running Plan %s" % current_plan_id
        db.session.commit()

        weekly_plan = session.get('weekly_plan') 
        add_runs_to_database(weekly_plan, current_plan_id)

        return redirect('/dashboard')

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


@app.route('/login-complete', methods=["POST"])
def process_login():
    """Checks if user email and password exist on same account. 
    If so, logs them into their account. If not, flashes a message.
    """

    raw_runner_email = request.form.get("email")
    raw_runner_password = request.form.get("password")

    try:
        runner_account = Runner.query.filter_by(email=raw_runner_email).one()
    except Exception, e:
        runner_account = False

    if runner_account:
        hashed_password = generate_hashed_password(raw_runner_password, runner_account.salt)

    if runner_account and runner_account.password == hashed_password:
        session["runner_id"] = runner_account.runner_id
        flash("You have successfully logged in!")
        return redirect('/dashboard')
    else:
        flash("Email or Password is incorrect. Please try again!")
        return redirect("/")

@app.route('/logout-complete')
def process_logout():
    """Logout user and clear their session."""
    
    session.clear()
    flash("You have successfully logged out!")
    return redirect("/")


@app.route('/dashboard')
def display_runner_page():
    """Displays the runner's dashboard with current plan and tracking information."""

    runner_id = session.get('runner_id')
    runner = Runner.query.get(runner_id)

    if not runner:
        return redirect('/')

    today_date = datetime.today()
    
    current_plan = db.session.query(Plan).join(Runner).filter(Runner.runner_id==runner_id, Plan.end_date > today_date).one()

    if current_plan:
        days_left_to_goal = calculate_days_to_goal(today_date, current_plan.end_date)
        total_workouts_completed = calculate_total_workouts_completed(current_plan.runs)
        total_miles_completed = calculate_total_miles_completed(current_plan.runs)
    else:
        flash("It seems like all of your plans have expired. Feel free to click and view and old plan or make a new one!")
    length_of_plan = len(current_plan.runs)
    weeks_in_plan = int(length_of_plan/7)

    return render_template("runner_dashboard.html", runner=runner, 
                                                    plan=current_plan, 
                                                    weeks_in_plan=weeks_in_plan, 
                                                    days_left_to_goal=days_left_to_goal,
                                                    total_workouts_completed=total_workouts_completed,
                                                    total_miles_completed=total_miles_completed)


@app.route('/update-run.json', methods=["POST"])
def update_run():
    """When a runner clicks a run checkbox, updates run is_completed as true."""
    run_id = request.form.get("run-id")
    run = Run.query.get(run_id)
    run.is_completed = True
    db.session.commit()
    plan_id = run.plan_id
    plan = Plan.query.get(plan_id)
    runs = plan.runs
    total_miles_completed = calculate_total_miles_completed(runs)
    total_workouts_completed = calculate_total_workouts_completed(runs)
    result_data = {'total_miles_completed': total_miles_completed,
                   'total_workouts_completed': total_workouts_completed,
                   'run_id': run_id}
    return jsonify(result_data)

@app.route('/update-run-incomplete.json', methods=["POST"])
def update_run_incomplete():
    """When a runner clicks a run checkbox, updates run is_completed as false."""
    run_id = request.form.get("run-id")
    run = Run.query.get(run_id)
    run.is_completed = False
    db.session.commit()
    plan_id = run.plan_id
    plan = Plan.query.get(plan_id)
    runs = plan.runs
    total_miles_completed = calculate_total_miles_completed(runs)
    total_workouts_completed = calculate_total_workouts_completed(runs)
    result_data = {'total_miles_completed': total_miles_completed,
                   'total_workouts_completed': total_workouts_completed,
                   'run_id': run_id}
    return jsonify(result_data)


@app.route('/account-settings')
def display_account_settings_page():
    """Displays the account settings page to allow users to update their account settings."""
    pass

@app.route('/add-to-google-calendar')
def add_runs_to_runners_google_calenadr_account():
    """Adds a runner's runs to their Google Calendar account."""

    timezone = request.args.get("time-zone")
    preferred_start_time = request.args.get("cal-run-start-time")

    if not session.get('credentials'):
        return redirect('/start_oauth')
    credentials = client.OAuth2Credentials.from_json(session['credentials'])
    if credentials.access_token_expired:
        return redirect('/start_oauth')
    else:
        http_auth = credentials.authorize(httplib2.Http())
        calendar = gcal_client.build('calendar', 'v3', http_auth)
        
        runner_id = session.get('runner_id')
        runner = Runner.query.get(runner_id)
        runner.is_using_gCal = True
        db.session.commit()

        today_date = datetime.today()
        for plan in runner.plans:
            if today_date < plan.end_date:
                current_plan = plan
        if current_plan:
            for run in current_plan.runs[5:10]:
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
                    event = calendar.events().insert(calendarId='primary', body=event).execute()
                    run.is_on_gCal = True

                    flash('Added event to Google Calendar: %s on %s' % (title, date))
                    print'Event created: %s' % (event.get('htmlLink'))
                else:
                     flash('There are no new runs to add to your Google Calendar.')
            db.session.commit()
        else:
            flash('There are no new runs to add to your Google Calendar.')

    return redirect("/dashboard")

@app.route('/start_oauth')
def start_oauth():
    flow = client.flow_from_clientsecrets(
        'client_secret.json',
        scope='https://www.googleapis.com/auth/calendar',
        redirect_uri=url_for('oauth2callback', _external=True))

    # flow = websites you step through - front door: sends user to email page & asks permission to send info to calendar
    auth_uri = flow.step1_get_authorize_url()
    return redirect(auth_uri)

@app.route('/oauth2callback')
def oauth2callback():
    flow = client.flow_from_clientsecrets(
        'client_secret.json',
        scope='https://www.googleapis.com/auth/calendar',
        redirect_uri=url_for('oauth2callback', _external=True))
    if 'code' not in request.args:
        return "", 403

    # answer from user re: using calendar, gives back oauth token to send info to calendar
    auth_code = request.args.get('code')
    credentials = flow.step2_exchange(auth_code)
    session['credentials'] = credentials.to_json()
    add_oauth_token_to_database(credentials)
    
    return redirect('/add-to-google-calendar')

def add_oauth_token_to_database(credentials):
    """Adds oauth token to database"""
    runner_id = session.get('runner_id')
    runner = Runner.query.get(runner_id)
    runner.OAuth_token = credentials.to_json()
    db.session.commit()

@app.route('/opt-into-weekly-emails')
def opt_into_weekly_emails():
    """Opts users into weekly emails and updates."""
    pass

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
