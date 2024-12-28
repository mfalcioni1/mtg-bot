#!/bin/bash

# Read environment variables from .env file
if [ -f .env ]; then
    export $(cat .env | grep -v '^#' | xargs)
else
    echo ".env file not found"
    exit 1
fi

# Set variables
PROJECT_ID="$GOOGLE_CLOUD_PROJECT"
ZONE="us-east1-b"
INSTANCE_NAME="mtg-draft-bot"
MACHINE_TYPE="e2-micro"

# Build the container
echo "Building container..."
echo "Using project ID: $PROJECT_ID"
gcloud builds submit --tag "gcr.io/$PROJECT_ID/$INSTANCE_NAME"

# Create instance
echo "Creating GCE instance..."
gcloud compute instances create-with-container $INSTANCE_NAME \
    --container-image "gcr.io/$PROJECT_ID/$INSTANCE_NAME" \
    --machine-type $MACHINE_TYPE \
    --zone $ZONE \
    --project $PROJECT_ID \
    --container-env "DISCORD_BOT_TOKEN=$DISCORD_BOT_TOKEN" \
    --container-env "GOOGLE_CLOUD_PROJECT=$PROJECT_ID" \
    --no-address \
    --network-interface=network=default,no-address 