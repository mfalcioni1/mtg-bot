import aiohttp
from typing import List, Optional, Dict
import re
import csv
from io import StringIO

class CardData:
    def __init__(self, row: Dict[str, str]):
        self.name = row['name']
        self.cmc = float(row['CMC']) if row['CMC'] else 0
        self.type = row['Type']
        self.color = row['Color']
        self.set = row['Set']
        self.collector_number = row['Collector Number']
        self.rarity = row['Rarity']
        self.color_category = row['Color Category']
        self.status = row['status']
        self.tags = row['tags'].split(',') if row['tags'] else []
        self.mtgo_id = row['MTGO ID']

    def to_dict(self) -> Dict:
        return {
            "name": self.name,
            "cmc": self.cmc,
            "type": self.type,
            "color": self.color,
            "set": self.set,
            "collector_number": self.collector_number,
            "rarity": self.rarity,
            "color_category": self.color_category,
            "status": self.status,
            "tags": self.tags,
            "mtgo_id": self.mtgo_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'CardData':
        # Create a row-like dictionary that matches the expected format
        row = {
            "name": data["name"],
            "CMC": str(data["cmc"]),
            "Type": data["type"],
            "Color": data["color"],
            "Set": data["set"],
            "Collector Number": data["collector_number"],
            "Rarity": data["rarity"],
            "Color Category": data["color_category"],
            "status": data["status"],
            "tags": ",".join(data["tags"]),
            "MTGO ID": data["mtgo_id"]
        }
        return cls(row)

class CubeCobraParser:
    def __init__(self):
        self.base_url = "https://cubecobra.com"
        self.download_url_template = "https://cubecobra.com/cube/download/csv/{cube_id}"
    
    def _extract_cube_id(self, url: str) -> Optional[str]:
        """Extract cube ID from either a list URL or direct ID."""
        # Try to match the cube ID from a full URL
        url_match = re.search(r'cubecobra\.com/cube/(?:list|overview)/([a-zA-Z0-9-]+)', url)
        if url_match:
            return url_match.group(1)
        
        # If no URL match, check if the input is just a cube ID
        if re.match(r'^[a-zA-Z0-9-]+$', url):
            return url
        
        return None

    async def validate_url(self, url: str) -> bool:
        """Validate if the input is either a valid Cube Cobra URL or cube ID."""
        return self._extract_cube_id(url) is not None
    
    async def fetch_cube_data(self, url: str) -> Optional[List[CardData]]:
        """Fetch and parse cube data from Cube Cobra."""
        try:
            cube_id = self._extract_cube_id(url)
            if not cube_id:
                print(f"Invalid cube URL or ID: {url}")
                return None
            
            download_url = self.download_url_template.format(cube_id=cube_id)
            print(f"Attempting to fetch cube data from: {download_url}")
            
            # Add headers to mimic a browser request
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/csv,application/csv,text/plain,*/*',
                'Accept-Language': 'en-US,en;q=0.9',
                'Referer': 'https://cubecobra.com/',
            }
            
            # Create connector that skips SSL verification
            connector = aiohttp.TCPConnector(ssl=False)
            
            async with aiohttp.ClientSession(connector=connector, headers=headers) as session:
                print(f"Sending GET request to {download_url}")
                async with session.get(download_url, allow_redirects=True) as response:
                    print(f"Received response with status: {response.status}")
                    if response.status != 200:
                        print(f"Failed to fetch cube list. Status: {response.status}")
                        response_text = await response.text()
                        print(f"Response body: {response_text[:200]}...")
                        return None
                    
                    text = await response.text()
                    print(f"Received data length: {len(text)} characters")
                    print(f"First few lines of data:\n{text[:500]}...")
                    
                    # Parse CSV data
                    csv_file = StringIO(text)
                    reader = csv.DictReader(csv_file)
                    
                    cards = []
                    for row in reader:
                        try:
                            card = CardData(row)
                            cards.append(card)
                        except Exception as e:
                            print(f"Error parsing card row: {row}")
                            print(f"Error details: {e}")
                            continue
                    
                    print(f"Successfully parsed {len(cards)} cards from cube")
                    if not cards:
                        print("No cards found in cube list")
                        return None
                    
                    return cards
                    
        except Exception as e:
            print(f"Error fetching cube data: {e}")
            print(f"Error type: {type(e)}")
            import traceback
            print(f"Traceback:\n{traceback.format_exc()}")
            return None 