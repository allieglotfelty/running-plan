"""Run Planner"""

from jinja2 import StrictUndefined
from flask import Flask, jsonify, render_template, redirect, request, flash, session, Response
from flask_debugtoolbar import DebugToolbarExtension
from model import connect_to_db, db, Runner, Plan, Run
from datetime import datetime, date

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
    form_current_ability = request.form.get("current-ability")
    form_goal_distance = request.form.get("goal-distance")
    form_goal_date = request.form.get("goal-date")
    weekly_plan = weekly_plan_from_request(form_current_ability, form_goal_distance, form_goal_date)

    return jsonify(weekly_plan)

@app.route('/download', methods=["GET"])
def download_excel():
    """Creates an excel file and downloads it to the users computer"""

    args_current_ability = request.args.get("current-ability")
    args_goal_distance = request.args.get("goal-distance")
    args_goal_date = request.args.get("goal-date")
    
    weekly_plan = weekly_plan_from_request(args_current_ability, args_goal_distance, args_goal_date)
    excel_text = create_excel_text(weekly_plan)

    # Create a response object that takes in the excel_text (string of excel doc) and the mimetime (format) for the doc
    response = Response(response=excel_text, status=200, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    # Says the header will contain an attachement of the filename RunPlan.xlsx
    response.headers["Content-Disposition"] = "attachment; filename=RunPlan.xlsx"

    return response


def weekly_plan_from_request(raw_current_ability, raw_goal_distance, raw_end_date):
    current_ability = float(raw_current_ability)
    goal_distance = float(raw_goal_distance)
    end_date = datetime.strptime(raw_end_date, "%Y-%m-%d")
    today_date = datetime.today()
    return build_plan_with_two_dates(today_date, end_date, current_ability, goal_distance)


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