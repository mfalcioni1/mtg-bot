from google.cloud import storage
from google.oauth2 import service_account
import json
import os
from googleapiclient.discovery import build
import functions_framework
from google.auth import default

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SPREADSHEET_ID = os.getenv('SPREADSHEET_ID')

def get_sheets_service():
    """Create and return Google Sheets service object"""
    # Use Application Default Credentials instead of service account file
    credentials, project = default()
    credentials = credentials.with_scopes(SCOPES)
    service = build('sheets', 'v4', credentials=credentials)
    return service

def read_json_from_gcs(bucket_name, file_path):
    """Read JSON file from Google Cloud Storage"""
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(file_path)
    content = blob.download_as_string()
    return json.loads(content)

def get_sheet_id(service, spreadsheet_id, sheet_name):
    """Get the sheet ID if it exists, otherwise return None"""
    try:
        spreadsheet = service.spreadsheets().get(spreadsheetId=spreadsheet_id).execute()
        for sheet in spreadsheet['sheets']:
            if sheet['properties']['title'] == sheet_name:
                return sheet['properties']['sheetId']
        return None
    except Exception:
        return None

def update_draft_sheet(service, draft_data, player_names, channel_name):
    """Update draft picks sheet with player pools"""
    sheet_name = f'Draft Picks - {channel_name}'
    
    # Check if sheet exists
    sheet_id = get_sheet_id(service, SPREADSHEET_ID, sheet_name)
    
    if sheet_id is None:
        # Create new sheet if it doesn't exist
        body = {
            'requests': [
                {
                    'addSheet': {
                        'properties': {
                            'title': sheet_name
                        }
                    }
                }
            ]
        }
        service.spreadsheets().batchUpdate(
            spreadsheetId=SPREADSHEET_ID,
            body=body
        ).execute()
    
    # Get player display names and pools
    player_pools = draft_data['player_pools']
    name_lookup = player_names['player_names']
    
    # Create headers (player names)
    headers = []
    
    # First, determine the maximum number of cards any player has
    max_cards = 0
    for pool in player_pools.values():
        max_cards = max(max_cards, len(pool))
    
    # Initialize values list with empty rows
    values = [[''] * len(player_pools) for _ in range(max_cards)]
    
    # Process human players first, then bots
    for player_idx, (player_id, pool) in enumerate(player_pools.items()):
        # Add player name to headers
        if player_id.startswith('Bot'):
            display_name = player_id
        else:
            display_name = name_lookup.get(player_id, player_id)
        headers.append(display_name)
        
        # Add each card to the appropriate row in that player's column
        for card_idx, card in enumerate(pool):
            values[card_idx][player_idx] = card['name']
    
    # Prepare data for sheet
    sheet_data = [headers] + values
    
    # Update the sheet data
    range_name = f'{sheet_name}!A1:Z{len(sheet_data)}'
    body = {
        'values': sheet_data
    }
    service.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID,
        range=range_name,
        valueInputOption='RAW',
        body=body
    ).execute()

def update_cube_sheet(service, draft_data, player_names, channel_name):
    """Update cube cards sheet with taken status"""
    sheet_name = f'Cube Cards - {channel_name}'
    
    # Check if sheet exists
    sheet_id = get_sheet_id(service, SPREADSHEET_ID, sheet_name)
    
    if sheet_id is None:
        # Create new sheet if it doesn't exist
        body = {
            'requests': [
                {
                    'addSheet': {
                        'properties': {
                            'title': sheet_name
                        }
                    }
                }
            ]
        }
        service.spreadsheets().batchUpdate(
            spreadsheetId=SPREADSHEET_ID,
            body=body
        ).execute()
    
    # Prepare headers
    headers = ['Card Name', 'Color', 'Type', 'CMC', 'Status', 'Taken By']
    values = [headers]
    
    # Get all cards and create a set of taken cards with their owners
    taken_cards = {}
    for player_id, pool in draft_data['player_pools'].items():
        for card in pool:
            taken_cards[card['name']] = player_id
    
    # Process all cards
    for card in draft_data['cards']:
        taken_by = taken_cards.get(card['name'], '')
        if taken_by.startswith('Bot'):
            owner = taken_by
        else:
            owner = player_names['player_names'].get(taken_by, taken_by) if taken_by else ''
            
        values.append([
            card['name'],
            card['color_category'],
            card['type'],
            str(card['cmc']),
            'Taken' if card['name'] in taken_cards else 'Available',
            owner
        ])
    
    # Update the sheet data
    range_name = f'{sheet_name}!A1:F{len(values)}'
    body = {
        'values': values
    }
    service.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID,
        range=range_name,
        valueInputOption='RAW',
        body=body
    ).execute()

@functions_framework.cloud_event
def update_draft_sheets(cloud_event):
    """Cloud Function triggered by a Cloud Storage event"""
    data = cloud_event.data
    
    bucket_name = data["bucket"]
    file_path = data["name"]
    
    # Only process content.json files under the draft directory
    if not file_path.startswith('draft') or not file_path.endswith('content.json'):
        return
    
    # Get the directory path for the related files
    dir_path = os.path.dirname(file_path)
    
    try:
        # Read the necessary files
        draft_data = read_json_from_gcs(bucket_name, file_path)
        player_names = read_json_from_gcs(bucket_name, f"{dir_path}/player_names.json")
        
        # Get channel name from player_names.json
        channel_name = player_names.get('channel_name', 'Unknown Channel')
        
        # Initialize Google Sheets service
        service = get_sheets_service()
        
        # Update both sheets
        update_draft_sheet(service, draft_data, player_names, channel_name)
        update_cube_sheet(service, draft_data, player_names, channel_name)
        
    except Exception as e:
        print(f"Error processing draft data: {str(e)}")
        raise


if __name__ == "__main__":
    # Test function to process specific draft files
    def test_draft_sheet_update():
        """Test function to process specific draft files"""
        # Simulate cloud event data
        test_event_data = {
            "bucket": "mtg-discord-bot-data",
            "name": "draft/710271701899804682/1320098394039128064/content.json"
        }
        
        # Create a mock cloud event
        class MockCloudEvent:
            def __init__(self, data):
                self.data = data
        
        # Run the function with our test data
        cloud_event = MockCloudEvent(test_event_data)
        update_draft_sheets(cloud_event)

    print("Starting test draft sheet update...")
    try:
        test_draft_sheet_update()
        print("Test completed successfully!")
    except Exception as e:
        print(f"Test failed with error: {str(e)}")