from model import connect_to_db, db, Runner, Plan, Run
from apiclient import discovery as gcal_client
from oauth2client import client
import httplib2
from datetime import datetime, timedelta
from server import app
from server_utilities import generate_run_events_for_google_calendar

def add_runs_to_google_calendar():
    """Gets runs for users using google calendar and adds them to their accounts."""

    runners = db.session.query(Runner).join(Plan).join(Run).filter(Runner.runner_id==19,
                                                                   Runner.is_using_gCal==True,
                                                                   Run.is_on_gCal==False).all()

    for runner in runners:
        credentials = client.OAuth2Credentials.from_json(runner.OAuth_token)
        if credentials.access_token_expired:
            print "credentials expired"
            continue
        http_auth = credentials.authorize(httplib2.Http())
        calendar = gcal_client.build('calendar', 'v3', http_auth)

        today_date = runner.calculate_today_date_for_runner()

        current_plan = db.session.query(Plan).join(Runner).filter(Runner.runner_id == 19,
                                                                  Plan.end_date >= today_date).first()
        timezone = runner.timezone

        if current_plan:
            preferred_start_time = current_plan.start_time
            run_events = generate_run_events_for_google_calendar(current_plan,
                                                                 timezone,
                                                                 preferred_start_time)

            if run_events:
                for event in run_events:
                    event_to_add = calendar.events().insert(calendarId='primary', body=event).execute()
                    print'Event created: %s' % (event_to_add.get('htmlLink'))
            else:
                print 'There are no new runs to add to the Google Calendar for runner_id: %s.' % runner.runner_id
        else:
            flash('There are no new runs to add to your Google Calendar.')


if __name__ == '__main__':
    with app.app_context():
        now = datetime.now()
        print "\n\nCronjob ran at %s" % now
        connect_to_db(app)
        add_runs_to_google_calendar()
