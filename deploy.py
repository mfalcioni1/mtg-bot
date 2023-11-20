from gcp import cloud_scheduler as cs
# Example usage
cs.create_cloud_scheduler_job(
    job_name="scryfall-data-update-job",
    schedule="0 * * * *",  # every hour
    time_zone="America/Los_Angeles",
    function_url="https://your-cloud-function-url"
)