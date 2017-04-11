"""Run Planner"""

from jinja2 import StrictUndefined
from flask import Flask, jsonify, render_template, redirect, request, flash, session, Response, url_for
from flask_debugtoolbar import DebugToolbarExtension
from model import connect_to_db, db, Runner, Plan, Run
from datetime import datetime, date, timedelta, time
from tzlocal import get_localzone
from apiclient import discovery as gcal_client
from oauth2client import client
import httplib2
from running_plan import create_excel_text, handle_edgecases, calculate_start_date, calculate_number_of_weeks_to_goal
from server_utilities import *
from twilio.twiml.messaging_response import MessagingResponse

app = Flask(__name__)

# Required to use Flask sessions and the debug toolbar
app.secret_key = "amcio9320e9wjadmclswep9q2-[ie290qfmvwnuq34op092iwopqk;dsmlcvq84yp9hrwafousdzncjlkx2[qOAPDSSGURW9EI"

app.jinja_env.undefined = StrictUndefined


@app.route('/')
def index():
    """Homepage."""

    today = datetime.today()
    year_from_today = today + timedelta(365)
    date_today = datetime.strftime(today, '%Y-%m-%d')
    date_year_from_today = datetime.strftime(year_from_today, '%Y-%m-%d')

    distances = range(2, 26)

    try:
        session['runner_id']
    except KeyError:
        return render_template("homepage.html", today=date_today, yearaway=date_year_from_today, distances=distances)
    
    return redirect("/dashboard")


@app.route('/plan.json', methods=["POST"])
def generate_plan():
    """Generates and displays a runner's plan based on the information
    they entered.
    """
 
    raw_current_ability = request.form.get("current-ability")
    raw_goal_distance = request.form.get("goal-distance")
    raw_end_date = request.form.get("goal-date")
    # today_date = datetime.today()
    weekly_plan = generate_weekly_plan(raw_current_ability, raw_goal_distance, raw_end_date)

    # start_date = calculate_start_date(today_date)
    # weeks_to_goal = calculate_number_of_weeks_to_goal(start_date, raw_end_date)
    # increment = (raw_goal_distance - raw_current_ability) / float(weeks_to_goal)

    # edgecase = handle_edgecases(increment, raw_goal_distance, raw_current_ability)

    # if not edgecase:
    return jsonify(weekly_plan)
    # else:
    #     flash(edgecase)
    #     return redirect('/')


@app.route('/download', methods=["GET"])
def download_excel():
    """Creates an excel file and downloads it to the users computer."""
    
    weekly_plan = session.get('weekly_plan')

    if not weekly_plan:
        flash("Please complete all questions before trying to download your plan!")
        return redirect('/')

    # weekly_plan = session.get('weekly_plan')
    excel_text = create_excel_text(weekly_plan)

    # Create a response object that takes in the excel_text (string of excel doc) and the mimetime (format) for the doc
    response = Response(response=excel_text, status=200, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    
    # Says the header will contain an attachement of the filename RunPlan.xlsx
    response.headers["Content-Disposition"] = "attachment; filename=RunPlan.xlsx"

    return response


# @app.route('/sign-up')
# def display_sign_up_page():
#     """Sign-up Page."""

#     weekly_plan = session.get('weekly_plan')

#     if not weekly_plan:
#         flash("Please complete all questions before trying to sign-up!")
#         return redirect('/')

#     else:
#         return render_template('registration.html')


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

    times = range(1, 25)

    runner_id = session.get('runner_id')
    runner = Runner.query.get(runner_id)

    if not runner:
        return redirect('/')

    today_date = datetime.today()

    current_plan = db.session.query(Plan).join(Runner).filter(Runner.runner_id==runner_id, 
                                                              Plan.end_date >= today_date).one()

    dates = generate_running_dates(current_plan.start_date, current_plan.end_date)

    if current_plan:
        days_left_to_goal = calculate_days_to_goal(today_date, current_plan.end_date)
        total_workouts_completed = calculate_total_workouts_completed(current_plan.runs)
        total_miles_completed = calculate_total_miles_completed(current_plan.runs)
    else:
        flash("It seems like all of your plans have expired. Feel free to click and view and old plan or make a new one!")

    weeks_in_plan = calculate_weeks_in_plan(current_plan)
    runs = {}
    for run in current_plan.runs:
        runs[run.date.date()] = {'run_id': run.run_id,
                                 'distance': run.distance, 
                                 'is_completed': run.is_completed}

    return render_template("runner_dashboard.html", plan=current_plan,
                                                    runs=runs,
                                                    weeks_in_plan=weeks_in_plan,
                                                    days_left_to_goal=days_left_to_goal,
                                                    total_workouts_completed=total_workouts_completed,
                                                    total_miles_completed=total_miles_completed,
                                                    dates=dates,
                                                    times=times)


@app.route('/update-run.json', methods=["POST"])
def update_run_and_dashboard_as_completed():
    """When a runner clicks a run checkbox, updates run is_completed as true,
    commits updated run to database, and updates the total miles and total workouts
    completed on the dashboard.
    """

    run_id = request.form.get("run-id")
    update_run(run_id, True)
    result_data = gather_info_to_update_dashboard(run_id)

    return jsonify(result_data)


@app.route('/update-run-incomplete.json', methods=["POST"])
def update_run__and_dashboard_as_incompleted():
    """When a runner unclicks a run checkbox, updates run is_completed as false,
    commits updated run to database, and updates the total miles and total workouts
    completed on the dashboard.
    """

    run_id = request.form.get("run-id")
    update_run(run_id, False)
    result_data = gather_info_to_update_dashboard(run_id)

    return jsonify(result_data)

@app.route('/add-timezone-to-session', methods=["GET"])
def add_timezone_to_session():
    """Adds the users selected timezone to the session to be
    added to their Google Calendar.
    """

    timezone = request.args.get("time-zone")
    session['timezone'] = timezone
    message = {'message': 'timezone updated'}

    return jsonify(message)


@app.route('/add-start-time-to-session', methods=["GET"])
def add_start_time_to_session():
    """Adds the users selected run start time to the session to be
    added to their Google Calendar.
    """

    entered_start_time = request.args.get("cal-run-start-time")
    formatted_start_time = datetime.strptime(entered_start_time, '%H:%M')
    session['preferred_start_time'] = formatted_start_time

    message = {'message': 'start time updated'}

    return jsonify(message)

@app.route('/add-to-google-calendar', methods=["POST", "GET"])
def add_runs_to_runners_google_calenadr_account():
    """Adds a runner's runs to their Google Calendar account."""

    # if request.method == "POST":
    #     timezone = request.form.get("time-zone")
    #     preferred_start_time = request.form.get("cal-run-start-time")
    #     session['timezone'] = timezone
    #     session['preferred_start_time'] = preferred_start_time

    timezone = session.get('timezone')
    preferred_start_time = session.get('preferred_start_time')

    # If there are no credentials in the current session, redirect to get oauth permisssions
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
        update_runner_to_is_using_gCal(runner_id)

        today_date = datetime.today()
        current_plan = db.session.query(Plan).join(Runner).filter(Runner.runner_id == runner_id,
                                                                  Plan.end_date >= today_date).one()

        if current_plan:
            if timezone and preferred_start_time:
                run_events = generate_run_events_for_google_calendar(current_plan, timezone, preferred_start_time)
                del session['timezone']
                del session['preferred_start_time']
            elif timezone and not preferred_start_time:
                run_events = generate_run_events_for_google_calendar(current_plan, timezone, current_plan.start_time)
                del session['timezone']
            elif preferred_start_time and not timezone:
                run_events = generate_run_events_for_google_calendar(current_plan, "America/Los_Angeles", preferred_start_time)
                del session['preferred_start_time']
            else:
                run_events = generate_run_events_for_google_calendar(current_plan, "America/Los_Angeles", current_plan.start_time)
            if not run_events:
                flash('There are no new runs to add to your Google Calendar.')
            else:
                for event in run_events:
                    event_to_add = calendar.events().insert(calendarId='primary', body=event).execute()
                    flash('Added event to Google Calendar: %s on %s' % (event['summary'], event['start']['dateTime']))
                    print'Event created: %s' % (event_to_add.get('htmlLink'))
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
        add_oauth_token_to_database(credentials)
        return redirect(url_for('add_runs_to_runners_google_calenadr_account'))


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


@app.route('/account-settings')
def display_account_settings_page():
    """Displays the account settings page to allow users to update their account settings."""
    pass


@app.route('/opt-into-weekly-emails')
def opt_into_weekly_emails():
    """Opts users into weekly emails and updates."""
    pass


@app.route("/", methods=['GET', 'POST'])
def hello_monkey():
    """Respond to incoming calls with a simple text message."""

    resp = MessagingResponse().message("Hello, Mobile Monkey")
    return str(resp)



# @app.route('/message')
# def sms_survey():
#     response = twiml.Response()

#     survey = Survey.query.first()
#     if survey_error(survey, response.message):
#         return str(response)

#     if 'question_id' in session:
#         response.redirect(url_for('answer',
#                                   question_id=session['question_id']))
#     else:
#         welcome_user(survey, response.message)
#         redirect_to_first_question(response, survey)
#     return str(response)


# def redirect_to_first_question(response, survey):
#     first_question = survey.questions.order_by('id').first()
#     first_question_url = url_for('question', question_id=first_question.id)
#     response.redirect(first_question_url, method='GET')


# def welcome_user(survey, send_function):
#     welcome_text = 'Welcome to the %s' % survey.title
#     send_function(welcome_text)

# @app.route('/question/<question_id>')
# def question(question_id):
#     question = Question.query.get(question_id)
#     session['question_id'] = question.id
#     if not is_sms_request():
#         return voice_twiml(question)
#     else:
#         return sms_twiml(question)



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
