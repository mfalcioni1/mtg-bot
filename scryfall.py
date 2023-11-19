import requests
import os
from google.cloud import storage

# Constants
SCRYFALL_API_URL = 'https://api.scryfall.com/bulk-data'
GCS_BUCKET_NAME = 'your-gcs-bucket-name'
LAST_MODIFIED_FILE = 'last_modified.txt'

def check_for_updates():
    # Fetch the last modified date from Scryfall API
    response = requests.get(SCRYFALL_API_URL)
    if response.status_code == 200:
        bulk_data = response.json()
        for data in bulk_data['data']:
            if data['type'] == 'your-desired-dataset-type':  # e.g., 'oracle_cards'
                return data['updated_at']
    return None

def download_data():
    # Your code to download and preprocess the data goes here
    pass

def main():
    storage_client = storage.Client()
    bucket = storage_client.bucket(GCS_BUCKET_NAME)

    # Check if last_modified.txt exists in GCS and read the last modified date
    last_modified_blob = bucket.blob(LAST_MODIFIED_FILE)
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
