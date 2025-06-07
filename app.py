from __future__ import print_function
import streamlit as st
import datetime
import os
import base64
from email.message import EmailMessage
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# ===== CONFIG =====
SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/gmail.send'
]

# ===== AUTH =====
@st.cache_resource
def authenticate_google():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)

    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file('client_secret.json', SCOPES)
        creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    calendar_service = build('calendar', 'v3', credentials=creds)
    gmail_service = build('gmail', 'v1', credentials=creds)
    return calendar_service, gmail_service

calendar_service, gmail_service = authenticate_google()

# ===== UI =====
st.set_page_config(page_title="Jess – Your AI Assistant", layout="centered")
st.title("👩‍💼 Jess – Your AI Personal Assistant")

with st.form("jess_form"):
    action = st.radio("What would you like me to do?", ["📅 Book Appointment", "✅ Add Task", "📧 Send Email"])
    your_email = st.text_input("Your Email")

    if action == "📅 Book Appointment":
        title = st.text_input("Meeting Title")
        participant = st.text_input("Participant's Email")
        date = st.date_input("Meeting Date")
        time = st.time_input("Meeting Time")
        duration = st.selectbox("Duration", ["15 minutes", "30 minutes", "1 hour"])
        description = st.text_area("Meeting Description")

    elif action == "✅ Add Task":
        task_title = st.text_input("Task Title")
        task_description = st.text_area("Task Description")
        task_date = st.date_input("Due Date")
        all_day = st.checkbox("All-day task?", value=True)
        if not all_day:
            task_time = st.time_input("Task Time")

    elif action == "📧 Send Email":
        recipient = st.text_input("Recipient's Email")
        subject = st.text_input("Subject")
        message = st.text_area("Email Body")

    submitted = st.form_submit_button("Submit")

# ===== ACTION HANDLING =====
if submitted:
    if action == "📅 Book Appointment":
        start_dt = datetime.datetime.combine(date, time)
        delta = {"15 minutes": 15, "30 minutes": 30, "1 hour": 60}[duration]
        end_dt = start_dt + datetime.timedelta(minutes=delta)

        event = {
            'summary': title,
            'description': description,
            'start': {'dateTime': start_dt.isoformat(), 'timeZone': 'America/New_York'},
            'end': {'dateTime': end_dt.isoformat(), 'timeZone': 'America/New_York'},
            'attendees': [{'email': participant}],
        }

        event_result = calendar_service.events().insert(
            calendarId='primary', body=event, sendUpdates='all'
        ).execute()
        st.success(f"📅 Appointment created: [View Event]({event_result.get('htmlLink')})")

    elif action == "✅ Add Task":
        if all_day:
            task_event = {
                'summary': task_title,
                'description': task_description,
                'start': {'date': task_date.isoformat()},
                'end': {'date': (task_date + datetime.timedelta(days=1)).isoformat()},
            }
        else:
            start_dt = datetime.datetime.combine(task_date, task_time)
            end_dt = start_dt + datetime.timedelta(hours=1)
            task_event = {
                'summary': task_title,
                'description': task_description,
                'start': {'dateTime': start_dt.isoformat(), 'timeZone': 'America/New_York'},
                'end': {'dateTime': end_dt.isoformat(), 'timeZone': 'America/New_York'},
            }

        task_result = calendar_service.events().insert(calendarId='primary', body=task_event).execute()
        st.success(f"✅ Task added: [View Task]({task_result.get('htmlLink')})")

    elif action == "📧 Send Email":
        email = EmailMessage()
        email.set_content(message)
        email['To'] = recipient
        email['From'] = your_email
        email['Subject'] = subject

        encoded_msg = base64.urlsafe_b64encode(email.as_bytes()).decode()
        send_msg = {'raw': encoded_msg}
        sent = gmail_service.users().messages().send(userId="me", body=send_msg).execute()
        st.success(f"📧 Email sent! Message ID: {sent['id']}")
