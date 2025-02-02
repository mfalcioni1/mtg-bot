# MTG Discord Bot Version 1.1.0 Features

## Core Features

### Personal Deck Viewing
- New command `/seemydeck` that shows the requesting user their submitted deck
- Response should be ephemeral (only visible to the requesting user)
- Should handle cases where user hasn't submitted a deck yet

### Banned List Management
- New command `/clearbanned` to remove all cards from the banned list
- New command `/removecard` to delete a single card from the banned list
- Both commands should require appropriate permissions
- Should provide confirmation messages for successful operations

### Game Outcome Tracking
- New command `/submitwinner` to designate winning deck(s) for a game
- Should store winning deck information for historical tracking
- Should include validation to ensure submitted deck exists
- Should handle multiple winners if needed for ties

### Score Tracking System
- New command `/trackscore` to record round winners
- Should maintain running tally of wins per player
- Should support multiple winners per round
- Should include command to display current standings
- Should persist between bot restarts

## Architectural Changes

### Cloud Storage Integration
Moving from in-memory storage to Google Cloud Storage for data persistence.

#### Storage Structure 
```
mtg-discord-bot-data/
└── v4cb/
└── {server_id}/
└── {channel_id}/
├── banned_list.json
├── scores.json
├── submitted_decks.json
└── winning_decks.json
```


#### Data Components to Migrate
1. Banned List
   - Move from Discord message to JSON file
   - Removes character limit constraint
   - Maintains history between bot restarts

2. Score Tracking
   - Store player scores in dedicated JSON file
   - Track rounds and winners
   - Maintain historical data

3. Submitted Decks
   - Store current round's deck submissions
   - Include submission timestamp and player info
   - Clear between rounds

4. Winning Decks
   - Archive of winning deck submissions
   - Include round information and date
   - Maintain historical record

### Implementation Requirements
- Implement Google Cloud Storage client integration
- Create utility functions for reading/writing JSON data
- Add error handling for storage operations
- Implement automatic file creation for new servers/channels
- Add data migration for existing games
- Include backup/recovery mechanisms

## Technical Considerations
- Must handle concurrent access to storage
- Need to implement proper error handling for storage operations
- Should include data validation when reading/writing files
- Must maintain backwards compatibility
- Should include logging for storage operations
- Need to handle storage quota and rate limits

## Security Considerations
- Ensure proper access controls for admin commands
- Validate server and channel IDs before storage operations
- Sanitize all user input before storage
- Implement proper error messages that don't expose system details
- Use appropriate Cloud Storage IAM roles

## Future Considerations
- Potential for analytics based on historical data
- Possibility of implementing game statistics
- Could add export functionality for game history
- Might want to add backup system for storage