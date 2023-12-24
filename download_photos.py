import os
import requests
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/photoslibrary.readonly']


def authenticate():
    creds = None

    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json')

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                'credentials.json', SCOPES,
                redirect_uri='urn:ietf:wg:oauth:2.0:oob')

            auth_uri, _ = flow.authorization_url()
            print(f'Please visit {auth_uri} on your local computer')

            # The user will get an authorization code. This code is used to get the
            # access token.
            code = input('Enter the authorization code:\n').split("data='")[1].strip("\\n')")
            flow.fetch_token(code=code)

            creds = flow.credentials

        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    return creds


def get_album_id(service, album_name):
    albums = service.albums().list().execute().get('albums', [])
    for album in albums:
        if album['title'] == album_name:
            return album['id']
    return None


def download_photo(photo_url, filename, folder_path):
    response = requests.get(photo_url)
    if response.status_code == 200:
        file_path = os.path.join(folder_path, filename)
        with open(file_path, 'wb') as file:
            file.write(response.content)
        print(f"Photo downloaded: {filename}")
    else:
        print(f"Failed to download photo. Status code: {response.status_code}")


def download_and_delete_photos(album_name, folder_path):
    creds = authenticate()

    # Build the service using the correct API name and version
    service = build('photoslibrary', 'v1', credentials=creds, static_discovery=False)

    # Get the album ID for the specified album name
    album_id = get_album_id(service, album_name)

    if album_id:
        page_token = None
        while True:
            # List media items from the specified album with pageSize
            results = service.mediaItems().search(
                body={"albumId": album_id,
                      "pageSize": 100,  # Adjust the pageSize as needed
                      "pageToken": page_token}
            ).execute()
            items = results.get('mediaItems', [])

            if items:
                # Get the list of files already present in the folder
                existing_files = set(os.listdir(folder_path))

                # Download only new photos to the specified folder
                for photo in items:
                    photo_url = f"{photo['baseUrl']}=d"
                    filename = photo['filename']
                    file_path = os.path.join(folder_path, filename)

                    # Check if the photo is not already in the folder
                    if filename not in existing_files:
                        download_photo(photo_url, filename, folder_path)
                    else:
                        print(f"Skipping existing photo: {filename}")

                # Check if there are more pages
                page_token = results.get('nextPageToken')
                if not page_token:
                    break
            else:
                print(f"No photos found in '{album_name}' album.")
                break

        # Get the list of files in the folder
        folder_files = set(os.listdir(folder_path))

        # Identify files in the folder that are not in the album and delete them
        files_to_delete = folder_files - {photo['filename'] for photo in items}
        for file_to_delete in files_to_delete:
            file_path_to_delete = os.path.join(folder_path, file_to_delete)
            os.remove(file_path_to_delete)
            print(f"Deleted photo from folder: {file_to_delete}")
    else:
        print(f"Album '{album_name}' not found.")


if __name__ == '__main__':
    album_name = "Family_Shared_Photo_Frame"
    download_folder_path = "Downloaded_photos_5"

    # Create the download folder if it doesn't exist
    os.makedirs(download_folder_path, exist_ok=True)

    download_and_delete_photos(album_name, download_folder_path)

