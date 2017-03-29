"""Run Planner"""

from jinja2 import StrictUndefined
from flask import Flask, jsonify, render_template, redirect, request, flash, session
from flask_debugtoolbar import DebugToolbarExtension
from model import connect_to_db, db, Runner, Plan, Run
from datetime import datetime, date

from running_plan import calculate_mileage_increment_per_week, round_quarter
from running_plan import build_plan_with_two_dates, create_excel_doc, handle_edgecases, generate_plan

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

    return jsonify(weekly_plan)


if __name__ == "__main__":
    # We have to set debug=True here, since it has to be True at the
    # point that we invoke the DebugToolbarExtension
    app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False
    app.debug = True
    app.jinja_env.auto_reload = app.debug  # make sure templates, etc. are not cached in debug mode

    connect_to_db(app)

    # Use the DebugToolbar
    DebugToolbarExtension(app)


    
    app.run(port=5050, host='0.0.0.0')