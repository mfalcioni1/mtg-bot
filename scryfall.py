import requests
import os
from gcp import gcs
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Use the variables, they are now available as environment variables
SCRYFALL_API_URL = os.getenv('SCRAPFYLL_API_URL')
GCS_BUCKET_NAME = os.getenv('GCS_BUCKET_NAME')
LAST_MODIFIED_FILE = os.getenv('LAST_MODIFIED_FILE')

def check_for_updates():
    # Fetch the last modified date from Scryfall API
    response = requests.get(SCRYFALL_API_URL)
    if response.status_code == 200:
        bulk_data = response.json()
    return bulk_data

def download_data():
    # Your code to download and preprocess the data goes here
    pass

def main():
    try:
        gcs.download_from_gcs(GCS_BUCKET_NAME, LAST_MODIFIED_FILE, LAST_MODIFIED_FILE)
    except Exception as e:
        gcs.upload_to_gcs(GCS_BUCKET_NAME, , LAST_MODIFIED_FILE)
    if last_modified_blob.exists():
        last_modified_date = last_modified_blob.download_as_text()
    else:
        last_modified_date = ''

    current_modified_date = check_for_updates()

    if current_modified_date != last_modified_date:
        download_data()
        # Update the last modified date in GCS
        last_modified_blob.upload_from_string(current_modified_date)

if __name__ == '__main__':
    main()
