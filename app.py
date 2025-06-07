from __future__ import print_function
import streamlit as st
import datetime
import os
import base64
import json
from email.message import EmailMessage
from google.oauth2 import service_account
from googleapiclient.discovery import build

# ===== CONFIG =====
SCOPES = [
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/gmail.send'
]

# ===== AUTH =====
@st.cache_resource
def authenticate_google():
    service_account_info = json.loads(st.secrets["SERVICE_ACCOUNT_JSON"])
    creds = service_account.Credentials.from_service_account_info(
        service_account_info, scopes=SCOPES
    ).with_subject("zack@kingdomgp.com")
    calendar_service = build('calendar', 'v3', credentials=creds)
    gmail_service = build('gmail', 'v1', credentials=creds)
    return calendar_service, gmail_service

calendar_service, gmail_service = authenticate_google()

# ===== UI =====
st.set_page_config(page_title="Jess – Your AI Assistant", layout="centered")
st.title("👩‍💼 Jess – Your AI Personal Assistant")

with st.form("jess_form"):
    action = st.radio("What would you like me to do?", ["🗓 Book Appointment", "✅ Add Task", "📧 Send Email"])
    your_email = st.text_input("Your Email")

    if action == "🗓 Book Appointment":
        name = st.text_input("Your Name")
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
    if action == "🗓 Book Appointment":
        start_dt = datetime.datetime.combine(date, time)
        delta = {"15 minutes": 15, "30 minutes": 30, "1 hour": 60}[duration]
        end_dt = start_dt + datetime.timedelta(minutes=delta)

        # Check availability
        freebusy_query = {
            "timeMin": start_dt.isoformat() + "Z",
            "timeMax": end_dt.isoformat() + "Z",
            "items": [{"id": "primary"}]
        }
        busy_times = calendar_service.freebusy().query(body=freebusy_query).execute()

        if busy_times["calendars"]["primary"]["busy"]:
            st.warning("⛔ You're already booked during this time. Please choose another slot.")
        else:
            event = {
                'summary': title,
                'description': f"Scheduled by: {name}\n\n{description}",
                'start': {'dateTime': start_dt.isoformat(), 'timeZone': 'America/Los_Angeles'},
                'end': {'dateTime': end_dt.isoformat(), 'timeZone': 'America/Los_Angeles'},
                'attendees': [{'email': participant}],
            }

            try:
                event_result = calendar_service.events().insert(
                    calendarId='primary', body=event, sendUpdates='all'
                ).execute()
                st.success(f"🗓 Appointment created: [View Event]({event_result.get('htmlLink')})")
            except Exception as e:
                st.error(f"❌ Failed to create event. Error: {e}")

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
                'start': {'dateTime': start_dt.isoformat(), 'timeZone': 'America/Los_Angeles'},
                'end': {'dateTime': end_dt.isoformat(), 'timeZone': 'America/Los_Angeles'},
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
