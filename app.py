from flask import Flask, request, render_template, send_file
from twilio.twiml.messaging_response import MessagingResponse
from datetime import datetime, timedelta
from sqlalchemy import create_engine, Column, Integer, String, DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import csv
import phonenumbers

app = Flask(__name__)

# Configure SQLite database
engine = create_engine('sqlite:///twilio_sms.db', echo=True)
Base = declarative_base()

class SmsCallback(Base):
    __tablename__ = 'sms_callbacks'

    id = Column(Integer, primary_key=True)
    message_sid = Column(String)
    status = Column(String)
    recipient_number = Column(String)
    timestamp = Column(DateTime)
    country = Column(String)
    api_version = Column(String)
    sender = Column(String)
    account = Column(String)


Base.metadata.create_all(engine)

# Create a session to interact with the database
Session = sessionmaker(bind=engine)

@app.route('/sms', methods=['POST'])
def sms():
    """Endpoint to handle Twilio SMS status callbacks"""
    message_sid = request.form.get('MessageSid')
    status = request.form.get('MessageStatus')
    recipient_number_str = request.form.get('To')
    api_version = request.form.get('ApiVersion')
    sender = request.form.get('From')
    account = request.form.get('AccountSid')


    timestamp = datetime.now()

    # Parse the recipient number to identify the country
    recipient_number = phonenumbers.parse(recipient_number_str, None)
    country = None
    if recipient_number.country_code:
        country = phonenumbers.region_code_for_country_code(recipient_number.country_code)

    # Save the callback to the database
    session = Session()
    callback = SmsCallback(message_sid=message_sid, status=status, recipient_number=recipient_number_str,
                        timestamp=timestamp, country=country, api_version=api_version, sender=sender, account=account)
    session.add(callback)
    session.commit()
    session.close()

    # Respond to Twilio
    resp = MessagingResponse()
    return str(resp)



@app.route('/')
def index():
    """Render the index page"""
    return render_template('index.html')

@app.route('/download_today_csv')
def download_today_csv():
    """Download CSV file for status callbacks of the current day"""
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    session = Session()
    callbacks = session.query(SmsCallback).filter(SmsCallback.timestamp >= today).all()
    session.close()

    # Prepare CSV data
    csv_data = [['Message SID', 'Status', 'Timestamp', 'RecipientNumber', 'Country', 'ApiVersion', 'Sender', 'Account']]
    for callback in callbacks:
        csv_data.append([callback.message_sid, callback.status, callback.timestamp, callback.recipient_number,  callback.country, callback.api_version, callback.sender, callback.account])

    # Create CSV file
    file_name = f'twilio_sms_callbacks_{today.strftime("%Y-%m-%d")}.csv'
    with open(file_name, 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerows(csv_data)

    # Send the CSV file to the user
    return send_file(file_name, as_attachment=True)

@app.route('/download_csv')
def download_csv():
    """Download CSV file for status callbacks of the previous day"""
    yesterday = datetime.now() - timedelta(days=1)
    session = Session()
    callbacks = session.query(SmsCallback).filter(SmsCallback.timestamp >= yesterday).all()
    session.close()

    # Prepare CSV data
    csv_data = [['Message SID', 'Status', 'Recipient Number',  'Timestamp']]
    for callback in callbacks:
        csv_data.append([callback.message_sid, callback.status, callback.recipient_number,
                      callback.timestamp])


    # Create CSV file
    with open('twilio_sms_callbacks.csv', 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerows(csv_data)

    # Send the CSV file to the user
    return send_file('twilio_sms_callbacks.csv', as_attachment=True)


if __name__ == '__main__':
    app.run(debug=True, port=8080)
