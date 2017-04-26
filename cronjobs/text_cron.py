from server_utilities import send_reminder_sms_messages
from datetime import date, timedelta
from server import app
from model import connect_to_db


if __name__ == '__main__':
    with app.app_context():
        print app
        connect_to_db(app)
        sms_date = date.today()+timedelta(7)
        send_reminder_sms_messages("2017-04-16")
