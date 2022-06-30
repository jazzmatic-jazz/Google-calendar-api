from rest_framework.response import Response
from rest_framework.decorators import api_view

from django.shortcuts import redirect
import os.path
import json
from datetime import datetime

import google_auth_oauthlib.flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

file = os.path.join(os.path.dirname(__file__), 'credentials.json')
print("File",file)
CLIENT_SECRETS_FILE = file
SCOPES = ['https://www.googleapis.com/auth/calendar']

@api_view(['GET'])
def GoogleCalendarInitView(request):

    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
      CLIENT_SECRETS_FILE, scopes=SCOPES)

    # Indicate where the API server will redirect the user after the user completes
    # the authorization flow.
    flow.redirect_uri = 'http://localhost:8000/rest/v1/calendar/redirect'

    # # Generate URL for request to Google's OAuth 2.0 server.
    authorization_url, state = flow.authorization_url(
    access_type='offline',
    include_granted_scopes='true')

    # Store the state in the session so that the callback can verify that
    # the authorization server response.
    request.session['state'] = state

    return redirect(authorization_url)

@api_view(['GET'])
def GoogleCalendarRedirectView(request):

    # Specify the state when creating the flow in the callback so that it can
    # verify the authorization server response.
    state = request.session.get('state')
    
    flow = google_auth_oauthlib.flow.Flow.from_client_secrets_file(
      CLIENT_SECRETS_FILE, scopes=SCOPES, state=state)
    flow.redirect_uri = 'http://localhost:8000/rest/v1/calendar/redirect'

    # Use the authorization server's response to fetch the OAuth 2.0 tokens.
    authorization_response = request.get_full_path()
    flow.fetch_token(authorization_response=authorization_response)

    credentials = flow.credentials

    try:
        service = build('calendar', 'v3', credentials=credentials)

        now = datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
        # Call the Calendar API
        events_result = service.events().list(calendarId='primary', timeMin=now,
                                                singleEvents=True,
                                                orderBy='startTime').execute()
        events = events_result.get('items', [])

        if not events:
            return Response({'Message': 'No upcoming events found.'})
        else:
            events_list = []
            for event in events:
                event_dict = {
                    'event_id': event['id'],
                    'name': event['summary'],
                    'start_time': event['start'],
                    'end_time': event['end']
                }
                events_list.append(event_dict)

            return Response(events_list)

    except HttpError as error:
        return Response({'Message': 'An error occurred: %s' % error})

    