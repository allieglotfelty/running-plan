"""Run Planner"""

from jinja2 import StrictUndefined
from flask import Flask, jsonify, render_template, redirect, request, flash, session, Response
from flask_debugtoolbar import DebugToolbarExtension
from model import connect_to_db, db, Runner, Plan, Run
from datetime import datetime, date, timedelta
import hashlib, binascii
from random import choice

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

    runner_email = request.form.get("email")
    runner_password = request.form.get("password")
    email_query = Runner.query.filter_by(email=runner_email).all()
    if email_query:
        flash("This user already exists. Please try to login or create an account with a different email.")

    else:
        salt = generate_salt()
        binary_password = hashlib.pbkdf2_hmac('sha256', runner_password, salt, 100000)
        hex_password = binascii.hexlify(binary_password)

        runner = Runner(email=runner_email, password=hex_password, salt=salt)
        db.session.add(runner)
        db.session.commit()

        runner_id = runner.runner_id
        session['runner_id'] = runner_id

        plan = Plan(runner_id=runner_id, 
                    name="Running Plan %s" % runner_id,
                    start_date=session.get('start_date'), 
                    end_date=session.get('end_date'),
                    goal_distance=session.get('goal_distance'),
                    current_ability=session.get('current_ability'),
                    )
        weekly_plan = session.get('weekly_plan') 

        db.session.add(plan)
        db.session.commit() 
        plan_id = plan.plan_id

        for i in range(1, len(weekly_plan) + 1):
            for date in weekly_plan[str(i)]:
                distance = weekly_plan[str(i)][date]
                run = Run(plan_id=plan_id, date=date, distance=distance)
                db.session.add(run)

        db.session.commit()

    return redirect('/dashboard')

@app.route('/login-complete', methods=["POST"])
def process_login():
    """Checks if user email and password exist on same account. 
    If so, logs them into their account. If not, flashes a message.
    """

    runner_email = request.form.get("email")
    runner_password = request.form.get("password")

    try:
        runner_account = Runner.query.filter_by(email=runner_email).one()
    except Exception, e:
        runner_account = False

    if runner_account:
        binary_password = hashlib.pbkdf2_hmac('sha256', runner_password, runner_account.salt, 100000)
        hex_password = binascii.hexlify(binary_password)

    if runner_account and runner_account.password == hex_password:
        session["runner_id"] = runner_account.runner_id
        print session
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
    for plan in runner.plans:
        if datetime.today() < plan.end_date:
            current_plan = plan
    length_of_plan = len(current_plan.runs)
    weeks_in_plan = int(length_of_plan/7)
    return render_template("runner_dashboard.html", runner=runner, plan=current_plan, weeks_in_plan=weeks_in_plan)

def generate_salt():
    """Generates salt for password encryption."""

    letters = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"

    return "".join(choice(letters) for i in range(16))


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