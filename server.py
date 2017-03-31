"""Run Planner"""

from jinja2 import StrictUndefined
from flask import Flask, jsonify, render_template, redirect, request, flash, session, Response
from flask_debugtoolbar import DebugToolbarExtension
from model import connect_to_db, db, Runner, Plan, Run
from datetime import datetime, date, timedelta

from running_plan import build_plan_with_two_dates, create_excel_text, handle_edgecases, generate_plan

app = Flask(__name__)

# Required to use Flask sessions and the debug toolbar
app.secret_key = "ABC"

app.jinja_env.undefined = StrictUndefined


@app.route('/')
def index():
    """Homepage."""

    return render_template("homepage.html")


@app.route('/plan.json', methods=["POST"])
def generate_plan():
    """Generates and displays a runner's plan based on the information 
    they entered.
    """
   
    current_ability = float(request.form.get("current-ability"))
    goal_distance = float(request.form.get("goal-distance"))
    end_date = datetime.strptime(request.form.get("goal-date"), "%Y-%m-%d")
    today_date = datetime.today()
    weekly_plan = build_plan_with_two_dates(today_date, end_date, current_ability, goal_distance)

    session['current_ability'] = current_ability
    session['goal_distance'] = goal_distance
    session['start_date'] = today_date + timedelta(days=1)
    session['end_date'] = end_date
    session['weekly_plan'] = weekly_plan

    return jsonify(weekly_plan)

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
        return flash("This user already exists. Please try to login or create an account with a different email.")
    else:
        runner = Runner(email=runner_email, password=runner_password)
        db.session.add(runner)
        db.session.commit()

        runner_id = runner.runner_id

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

    return redirect('/%s' % runner_id, runner_id)

@app.route('/<runner_id>')
def display_runner_page(runner_id):
    """Displays the runner's dashboard with current plan and tracking information."""

    # runner = Runner.query.get(runner_id)
    return render_template("runner_dashboard.html")



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