cd cloud_function

gcloud functions deploy update_draft_sheets `
  --runtime python310 `
  --trigger-event google.storage.object.finalize `
  --trigger-resource mtg-discord-bot-data `
  --region us-central1 `
  --env-vars-file "../env.yaml" `
  --docker-registry=artifact-registry `
  --service-account mtg-discord-bot-sa@mtg-discord-bot-2010.iam.gserviceaccount.com

cd ..