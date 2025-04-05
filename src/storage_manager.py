from google.cloud import storage
import json
from typing import Any, Dict, Optional, List, Tuple
import logging

class StorageManager:
    def __init__(self, bucket_name: str = "mtg-discord-bot-data"):
        """Initialize the storage manager with Google Cloud Storage client."""
        self.client = storage.Client()
        self.bucket_name = bucket_name
        self.bucket = self.client.bucket(self.bucket_name)
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self) -> None:
        """Ensure the bucket exists, create it if it doesn't."""
        try:
            self.bucket = self.client.get_bucket(self.bucket_name)
        except Exception:
            self.bucket = self.client.create_bucket(self.bucket_name)
            logging.info(f"Created new bucket: {self.bucket_name}")

    def _get_blob_path(self, game_type: str, server_id: str, channel_id: str, filename: str) -> str:
        """Generate the full path for a blob."""
        return f"{game_type}/{server_id}/{channel_id}/{filename}"

    async def read_json(self, game_type: str, server_id: str, channel_id: str, filename: str) -> Optional[Dict[str, Any]]:
        """Read JSON data from a file in storage."""
        try:
            blob_path = self._get_blob_path(game_type, server_id, channel_id, filename)
            blob = self.bucket.blob(blob_path)
            
            if not blob.exists():
                return None
            
            content = blob.download_as_string()
            return json.loads(content)
        except Exception as e:
            logging.error(f"Error reading {filename}: {str(e)}")
            return None

    async def write_json(self, game_type: str, server_id: str, channel_id: str, filename: str, data: Dict[str, Any]) -> bool:
        """Write JSON data to a file in storage."""
        try:
            blob_path = self._get_blob_path(game_type, server_id, channel_id, filename)
            blob = self.bucket.blob(blob_path)
            
            json_str = json.dumps(data, indent=2)
            blob.upload_from_string(json_str, content_type='application/json')
            return True
        except Exception as e:
            logging.error(f"Error writing {filename}: {str(e)}")
            return False

    async def delete_json(self, game_type: str, server_id: str, channel_id: str, filename: str) -> bool:
        """Delete a JSON file from storage."""
        try:
            blob_path = self._get_blob_path(game_type, server_id, channel_id, filename)
            blob = self.bucket.blob(blob_path)
            
            if blob.exists():
                blob.delete()
            return True
        except Exception as e:
            logging.error(f"Error deleting {filename}: {str(e)}")
            return False

    async def list_files(self, game_type: str, server_id: str, channel_id: str) -> list[str]:
        """List all files in a server/channel directory."""
        try:
            prefix = f"{game_type}/{server_id}/{channel_id}/"
            blobs = self.bucket.list_blobs(prefix=prefix)
            return [blob.name.split('/')[-1] for blob in blobs]
        except Exception as e:
            logging.error(f"Error listing files: {str(e)}")
            return []

    async def ensure_directory_exists(self, game_type: str, server_id: str, channel_id: str) -> bool:
        """
        Ensure the directory structure exists by creating an empty .keep file if needed.
        Returns True if successful, False otherwise.
        """
        try:
            blob_path = self._get_blob_path(game_type, server_id, channel_id, ".keep")
            blob = self.bucket.blob(blob_path)
            
            if not blob.exists():
                blob.upload_from_string("")
            return True
        except Exception as e:
            logging.error(f"Error ensuring directory exists: {str(e)}")
            return False

    async def list_game_states(self, game_type: str) -> List[Tuple[int, int]]:
        """List all saved game states for a given game type.
        
        Args:
            game_type: The type of game (e.g., "rochester", "v4cb")
            
        Returns:
            List of tuples containing (guild_id, channel_id) for each saved state
        """
        try:
            # List all blobs in the game_type directory
            blobs = self.bucket.list_blobs(prefix=f"{game_type}/")
            
            # Extract guild_id and channel_id from blob names
            states = []
            for blob in blobs:
                # Path format: game_type/guild_id/channel_id/state.json
                parts = blob.name.split('/')
                if len(parts) >= 4 and parts[-1] == 'state.json':
                    try:
                        guild_id = int(parts[1])
                        channel_id = int(parts[2])
                        states.append((guild_id, channel_id))
                    except ValueError:
                        continue
            
            return states
            
        except Exception as e:
            print(f"Error listing game states: {e}")
            return []

    async def save_game_state(self, game_type: str, guild_id: int, channel_id: int, state: Dict[str, Any]) -> bool:
        """Save game state to storage.
        
        Args:
            game_type: The type of game (e.g., "rochester", "v4cb")
            guild_id: The Discord guild ID
            channel_id: The Discord channel ID
            state: The game state to save
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Ensure the directory exists
            await self.ensure_directory_exists(game_type, str(guild_id), str(channel_id))
            
            # Save the state
            return await self.write_json(game_type, str(guild_id), str(channel_id), "state.json", state)
            
        except Exception as e:
            print(f"Error saving game state: {e}")
            return False

    async def load_game_state(self, game_type: str, guild_id: int, channel_id: int) -> Optional[Dict[str, Any]]:
        """Load game state from storage.
        
        Args:
            game_type: The type of game (e.g., "rochester", "v4cb")
            guild_id: The Discord guild ID
            channel_id: The Discord channel ID
            
        Returns:
            Optional[Dict[str, Any]]: The loaded state if successful, None otherwise
        """
        try:
            # Load the state
            return await self.read_json(game_type, str(guild_id), str(channel_id), "state.json")
            
        except Exception as e:
            print(f"Error loading game state: {e}")
            return None

    async def delete_game_state(self, game_type: str, guild_id: int, channel_id: int) -> bool:
        """Delete game state from storage.
        
        Args:
            game_type: The type of game (e.g., "rochester", "v4cb")
            guild_id: The Discord guild ID
            channel_id: The Discord channel ID
            
        Returns:
            bool: True if successful, False otherwise
        """
        try:
            # Delete the state file
            blob = self.bucket.blob(f"{game_type}/{guild_id}/{channel_id}/state.json")
            blob.delete()
            return True
            
        except Exception as e:
            print(f"Error deleting game state: {e}")
            return False

    async def game_state_exists(self, game_type: str, guild_id: int, channel_id: int) -> bool:
        """Check if a game state exists in storage.
        
        Args:
            game_type: The type of game (e.g., "rochester", "v4cb")
            guild_id: The Discord guild ID
            channel_id: The Discord channel ID
            
        Returns:
            bool: True if the state exists, False otherwise
        """
        try:
            # Check if the state file exists
            blob = self.bucket.blob(f"{game_type}/{guild_id}/{channel_id}/state.json")
            return blob.exists()
            
        except Exception as e:
            print(f"Error checking game state existence: {e}")
            return False 