from google.cloud import storage

def upload_to_gcs(bucket_name, source_file_name, destination_blob_name):
    """
    Uploads a file to the Google Cloud Storage bucket.

    :param bucket_name: str, the name of the bucket.
    :param source_file_name: str, the path to the file to upload.
    :param destination_blob_name: str, the desired object name in the bucket.
    """
    # Initialize a storage client
    storage_client = storage.Client()

    # Get the bucket
    bucket = storage_client.bucket(bucket_name)

    # Create a blob object from the filepath
    blob = bucket.blob(destination_blob_name)

    # Upload the file to a destination
    blob.upload_from_filename(source_file_name)

    print(f"File {source_file_name} uploaded to {destination_blob_name}.")
