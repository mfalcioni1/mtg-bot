# Read environment variables from .env file
$envContent = Get-Content .env
$envVars = @{}
foreach ($line in $envContent) {
    if ($line -match '^\s*([^#][^=]+?)\s*=\s*(.+?)\s*$') {
        $key = $matches[1].Trim()
        $value = $matches[2].Trim("'", '"', ' ')
        $envVars[$key] = $value
    }
}

# Set variables
$PROJECT_ID = $envVars["GOOGLE_CLOUD_PROJECT"]
$ZONE = "us-east1-b"
$INSTANCE_NAME = "mtg-draft-bot"
$MACHINE_TYPE = "e2-micro"
$CREDENTIALS_PATH = "C:\Users\mfalc\Documents\Projects\auth\discord_bot_gcp_key.json"

# Create a temporary build directory
$BUILD_DIR = "temp_build"
if (Test-Path $BUILD_DIR) {
    Remove-Item -Recurse -Force $BUILD_DIR
}
New-Item -ItemType Directory -Path $BUILD_DIR

# Copy necessary files to build directory
Copy-Item -Path "src" -Destination "$BUILD_DIR/" -Recurse
Copy-Item -Path ".env" -Destination "$BUILD_DIR/"
Copy-Item -Path "Dockerfile" -Destination "$BUILD_DIR/"

# Create auth directory and copy credentials
New-Item -ItemType Directory -Path "$BUILD_DIR/auth"
Copy-Item -Path $CREDENTIALS_PATH -Destination "$BUILD_DIR/auth/credentials.json"

# Create a temporary cloudbuild.yaml file
@"
steps:
- name: 'gcr.io/cloud-builders/docker'
  args: ['build', '-t', 'gcr.io/$PROJECT_ID/$INSTANCE_NAME', '.']
images: ['gcr.io/$PROJECT_ID/$INSTANCE_NAME']
"@ | Out-File -FilePath "$BUILD_DIR/cloudbuild.yaml" -Encoding UTF8

# Build the container from the build directory
Write-Host "Building container..."
Write-Host "Using project ID: $PROJECT_ID"
Set-Location $BUILD_DIR
gcloud builds submit --config cloudbuild.yaml .

# Return to original directory
Set-Location ..

# Clean up build directory
Remove-Item -Recurse -Force $BUILD_DIR

# Check if instance exists
$instance = gcloud compute instances describe $INSTANCE_NAME --zone $ZONE --project $PROJECT_ID 2>$null
if ($LASTEXITCODE -eq 0) {
    Write-Host "Instance exists, checking status..."
    
    # Check if instance is running
    $status = (gcloud compute instances describe $INSTANCE_NAME --zone $ZONE --project $PROJECT_ID --format="get(status)")
    if ($status -eq "RUNNING") {
        Write-Host "Instance is running, updating container..."
        gcloud compute instances update-container $INSTANCE_NAME `
            --container-image "gcr.io/$PROJECT_ID/$INSTANCE_NAME" `
            --zone $ZONE `
            --project $PROJECT_ID `
            --container-env "DISCORD_BOT_TOKEN=$($envVars['DISCORD_BOT_TOKEN'])" `
            --container-env "GOOGLE_CLOUD_PROJECT=$PROJECT_ID"
    } else {
        Write-Host "Instance exists but is not running. Starting instance..."
        gcloud compute instances start $INSTANCE_NAME --zone $ZONE --project $PROJECT_ID
        Write-Host "Waiting for instance to start..."
        Start-Sleep -Seconds 30
        Write-Host "Updating container..."
        gcloud compute instances update-container $INSTANCE_NAME `
            --container-image "gcr.io/$PROJECT_ID/$INSTANCE_NAME" `
            --zone $ZONE `
            --project $PROJECT_ID `
            --container-env "DISCORD_BOT_TOKEN=$($envVars['DISCORD_BOT_TOKEN'])" `
            --container-env "GOOGLE_CLOUD_PROJECT=$PROJECT_ID"
    }
} else {
    Write-Host "Instance does not exist, creating new instance..."
    gcloud compute instances create-with-container $INSTANCE_NAME `
        --container-image "gcr.io/$PROJECT_ID/$INSTANCE_NAME" `
        --machine-type $MACHINE_TYPE `
        --zone $ZONE `
        --project $PROJECT_ID `
        --container-env "DISCORD_BOT_TOKEN=$($envVars['DISCORD_BOT_TOKEN'])" `
        --container-env "GOOGLE_CLOUD_PROJECT=$PROJECT_ID" `
        --no-address `
        --network-interface=network=default,no-address
}

Write-Host "Deployment complete!" 