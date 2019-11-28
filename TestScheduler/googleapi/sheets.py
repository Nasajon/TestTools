from __future__ import print_function
import pickle
import os.path
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']


class GoogleSheets:
    def __init__(self, id, range, token, credencials):
        self.id_planilha = id
        self.range = range
        self.token = token
        self.credencials = credencials
        self.service = None

        self.__start_service()

    def __start_service(self):
        creds = None
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
                creds = flow.run_local_server(port=0)
            # Save the credentials for the next run
            with open(self.token, 'wb') as token:
                pickle.dump(creds, token)

        service = build('sheets', 'v4', credentials=creds)

        # Call the Sheets API
        self.service = service.spreadsheets()

    def get_values(self):
        result = self.service.values().get(
            spreadsheetId=self.id_planilha,
            range=self.range
        ).execute()

        self.range = result['range']

        return result.get('values', [])

    def update_values(self, rnge, num_values):
        values = []
        for i in range(num_values):
            values.append([1])

        body = {
            'range': rnge,
            'majorDimension': 'ROWS',
            'values': values
        }

        self.service.values().update(
            spreadsheetId=self.id_planilha,
            range=rnge,
            body=body,
            valueInputOption='RAW'
        ).execute()
