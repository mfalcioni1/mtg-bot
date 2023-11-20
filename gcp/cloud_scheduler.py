import subprocess

def create_cloud_scheduler_job(job_name, schedule, time_zone, function_url):
    """
    Create a Cloud Scheduler job using the gcloud CLI command.

    Args:
    job_name (str): Name of the Cloud Scheduler job.
    schedule (str): Cron schedule for the job.
    time_zone (str): Time zone for the schedule.
    function_url (str): URL of the Cloud Function to be triggered by this job.
    """

    try:
        command = [
            "gcloud", "scheduler", "jobs", "create", "http", job_name,
            "--schedule", schedule,
            "--time-zone", time_zone,
            "--uri", function_url,
            "--description", "Job to check and update Scryfall data"
        ]
        
        subprocess.run(command, check=True)
        print(f"Cloud Scheduler job '{job_name}' created successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Failed to create Cloud Scheduler job: {e}")
