from server_utilities import send_email_reminders
from server import app
from model import connect_to_db
from datetime import datetime


if __name__ == '__main__':
    with app.app_context():
        now = datetime.now()
        print "Cronjob ran at %s" % now
        connect_to_db(app)
        send_email_reminders()
