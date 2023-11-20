from google.cloud import storage

GCS = storage.Client()

def upload_to_gcs(bucket_name, 
                  source_file_name, 
                  destination_blob_name, 
                  storage_client = None):
    """
    Uploads a file to the Google Cloud Storage bucket.

    :param bucket_name: str, the name of the bucket.
    :param source_file_name: str, the path to the file to upload.
    :param destination_blob_name: str, the desired object name in the bucket.
    :param storage_client: google.cloud.storage.client.Client, the Google Cloud Storage client. 
                           If not provided, a new client will be created.

    :return: None
    """
    storage_client = GCS or storage_client

    # Get the bucket
    bucket = storage_client.bucket(bucket_name)
    # Create a blob object from the filepath
    blob = bucket.blob(destination_blob_name)
    # Upload the file to a destination
    blob.upload_from_filename(source_file_name)
    print(f"File {source_file_name} uploaded to {destination_blob_name}.")

def download_from_gcs(bucket_name, source_blob_name, destination_file_name, storage_client = None):
    """
    Downloads a blob from the Google Cloud Storage bucket to a local file.

    :param bucket_name: str, the name of the bucket.
    :param source_blob_name: str, the name of the blob to download.
    :param destination_file_name: str, the local path to store the downloaded file.
    :param storage_client: Optional, the Google Cloud Storage client. If not provided, a new client will be initialized.
    """
    # Initialize a storage client
    storage_client = GCS or storage_client

    # Get the bucket
    bucket = storage_client.bucket(bucket_name)
    # Create a blob object
    blob = bucket.blob(source_blob_name)
    # Download the file to a destination
    blob.download_to_filename(destination_file_name)
    print(f"Blob {source_blob_name} downloaded to {destination_file_name}.")

