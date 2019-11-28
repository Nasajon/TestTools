import os
import pickle
import datetime
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

SCOPES = ['https://www.googleapis.com/auth/calendar']


class GoogleCalendar:

    def __init__(self, id, token, credencials):
        self.token = token
        self.credencials = credencials
        self.id = id
        self.service = None

        self.__start_service()

    def __start_service(self):
        creds = None
        service = None
        # The file token.pickle stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if os.path.exists(self.token):
            with open(self.token, 'rb') as token:
                creds = pickle.load(token)
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credencials, SCOPES
                )
                creds = flow.run_console()
            # Save the credentials for the next run
            with open(self.token, 'wb') as token:
                pickle.dump(creds, token)

        service = build('calendar', 'v3', credentials=creds)
        self.service = service

    def atualiza_evento(self, evento):
        self.service.events().update(
            calendarId=self.id,
            eventId=evento['id'],
            body=evento['description'],
            sendUpdates='all'
        )

    def list_eventos_do_dia(self):
        now = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
        hoje = datetime.date.today().isoformat() + 'T23:59:59.000000Z'
        events = self.service.events().list(
            calendarId=self.id,
            timeMin=now,
            maxResults=5,
            singleEvents=True,
            orderBy='startTime',
            timeMax=hoje
        ).execute()
        return events.get('items', [])

    def list_eventos(self, data_min, data_max):
        min = data_min.isoformat() + 'Z'  # 'Z' indicates UTC time
        max = data_max.isoformat() + 'T23:59:59.000000Z'
        events = self.service.events().list(
            calendarId=self.id,
            timeMin=min,
            maxResults=100,
            singleEvents=True,
            orderBy='startTime',
            timeMax=max
        ).execute()
        return events.get('items', [])

    def cria_evento(self, evento):
        self.service.events().insert(
            calendarId=self.id,
            body=evento
        ).execute()
