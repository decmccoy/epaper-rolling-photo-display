import os
import random
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/photoslibrary.readonly']

def authenticate():
    creds = None

    # The file token.json stores the user's access and refresh tokens and is created automatically when the authorization flow completes for the first time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json')

    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                '"C:\Users\darcy\Downloads\client_secret_1031959511778-ei3gmht9316ojisfelu9v9svtu52n8p4.apps.googleusercontent.com.json"', SCOPES)
            creds = flow.run_local_server(port=0)

        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    return creds

def get_random_photo():
    creds = authenticate()
    service = build('photoslibrary', 'v1', credentials=creds)

    # Call the Google Photos API to get a list of media items
    results = service.mediaItems().list(
        pageSize=100).execute()
    items = results.get('mediaItems', [])

    # Choose a random photo from the list
    if items:
        random_photo = random.choice(items)
        print(f"Random Photo: {random_photo['filename']} - {random_photo['baseUrl']}")
    else:
        print('No photos found.')

if __name__ == '__main__':
    get_random_photo()
