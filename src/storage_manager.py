from google.cloud import storage
import json
from typing import Any, Dict, Optional, List, Tuple
import logging

class StorageManager:
    def __init__(self, game_type: str, server_id: str, channel_id: str, bucket_name: str = "mtg-discord-bot-data"):
        """Initialize the storage manager with Google Cloud Storage client."""
        self.client = storage.Client()
        self.bucket_name = bucket_name
        self.game_type = game_type
        self.server_id = str(server_id)  # Ensure string type
        self.channel_id = str(channel_id)  # Ensure string type
        self._ensure_bucket_exists()

    def _ensure_bucket_exists(self) -> None:
        """Ensure the bucket exists, create it if it doesn't."""
        try:
            self.bucket = self.client.get_bucket(self.bucket_name)
        except Exception:
            self.bucket = self.client.create_bucket(self.bucket_name)
            logging.info(f"Created new bucket: {self.bucket_name}")

    def _get_blob_path(self, filename: str) -> str:
        """Generate the full path for a blob."""
        return f"{self.game_type}/{self.server_id}/{self.channel_id}/{filename}"

    async def read_json(self, filename: str) -> Optional[Dict[str, Any]]:
        """Read JSON data from a file in storage."""
        try:
            blob_path = self._get_blob_path(filename)
            blob = self.bucket.blob(blob_path)
            
            if not blob.exists():
                return None
            
            content = blob.download_as_string()
            return json.loads(content)
        except Exception as e:
            logging.error(f"Error reading {filename}: {str(e)}")
            return None

    async def write_json(self, filename: str, data: Dict[str, Any]) -> bool:
        """Write JSON data to a file in storage."""
        try:
            blob_path = self._get_blob_path(filename)
            blob = self.bucket.blob(blob_path)
            
            json_str = json.dumps(data, indent=2)
            blob.upload_from_string(json_str, content_type='application/json')
            return True
        except Exception as e:
            logging.error(f"Error writing {filename}: {str(e)}")
            return False

    async def delete_json(self, filename: str) -> bool:
        """Delete a JSON file from storage."""
        try:
            blob_path = self._get_blob_path(filename)
            blob = self.bucket.blob(blob_path)
            
            if blob.exists():
                blob.delete()
            return True
        except Exception as e:
            logging.error(f"Error deleting {filename}: {str(e)}")
            return False

    async def list_files(self) -> list[str]:
        """List all files in the current game/server/channel directory."""
        try:
            prefix = f"{self.game_type}/{self.server_id}/{self.channel_id}/"
            blobs = self.bucket.list_blobs(prefix=prefix)
            return [blob.name.split('/')[-1] for blob in blobs]
        except Exception as e:
            logging.error(f"Error listing files: {str(e)}")
            return []

    async def ensure_directory_exists(self) -> bool:
        """
        Ensure the directory structure exists by creating an empty .keep file if needed.
        Returns True if successful, False otherwise.
        """
        try:
            blob_path = self._get_blob_path(".keep")
            blob = self.bucket.blob(blob_path)
            
            if not blob.exists():
                blob.upload_from_string("")
            return True
        except Exception as e:
            logging.error(f"Error ensuring directory exists: {str(e)}")
            return False

    async def list_active_sessions(self) -> List[Tuple[str, str]]:
        """List all active sessions in the bucket, returns list of (server_id, channel_id) tuples"""
        try:
            # List all blobs with the game_type prefix
            blobs = self.client.list_blobs(self.bucket_name, prefix=f"{self.game_type}/")
            
            # Extract unique server/channel combinations
            active_sessions = set()
            for blob in blobs:
                # Path format is: game_type/server_id/channel_id/filename
                parts = blob.name.split('/')
                if len(parts) >= 4:  # Ensure we have all parts
                    active_sessions.add((parts[1], parts[2]))
            
            return list(active_sessions)
        except Exception as e:
            logging.error(f"Error listing active sessions: {str(e)}")
            return []

    @classmethod
    async def list_all_active_sessions(cls, bucket_name: str = "mtg-discord-bot-data") -> Dict[str, List[Tuple[str, str]]]:
        """List all active sessions for all game types"""
        try:
            client = storage.Client()
            bucket = client.bucket(bucket_name)
            
            # Get all blobs
            blobs = client.list_blobs(bucket_name)
            
            # Organize by game type
            sessions = {}
            for blob in blobs:
                parts = blob.name.split('/')
                if len(parts) >= 4:  # game_type/server_id/channel_id/filename
                    game_type = parts[0]
                    if game_type not in sessions:
                        sessions[game_type] = set()
                    sessions[game_type].add((parts[1], parts[2]))
            
            # Convert sets to lists
            return {game_type: list(session_set) for game_type, session_set in sessions.items()}
        except Exception as e:
            logging.error(f"Error listing all active sessions: {str(e)}")
            return {} 