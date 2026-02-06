import os
import httpx
import logging
from config import settings
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

NOTION_OAUTH_URL = "https://api.notion.com/v1/oauth/token"
NOTION_API_BASE = "https://api.notion.com/v1"

class NotionService:
    def __init__(self):
        self.client_id = os.getenv("NOTION_CLIENT_ID")
        self.client_secret = os.getenv("NOTION_CLIENT_SECRET")
        self.redirect_uri = os.getenv("NOTION_REDIRECT_URI")
        
        if not all([self.client_id, self.client_secret, self.redirect_uri]):
            logger.warning("Notion credentials not fully configured in environment.")

    async def exchange_code_for_token(self, code: str) -> Dict[str, Any]:
        """
        Exchanges the temporary Auth Code for an Access Token.
        Returns the full JSON response from Notion (access_token, bot_id, etc.)
        """
        auth_string = f"{self.client_id}:{self.client_secret}"
        import base64
        encoded_auth = base64.b64encode(auth_string.encode()).decode()

        headers = {
            "Authorization": f"Basic {encoded_auth}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }
        
        payload = {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": self.redirect_uri
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(NOTION_OAUTH_URL, json=payload, headers=headers)
            
            if response.status_code != 200:
                logger.error(f"Notion Token Exchange Failed: {response.text}")
                return None
            
            return response.json()

    async def create_todo(self, access_token: str, database_id: str, task_name: str) -> bool:
        """
        Creates a new page (Task) in the specified Notion Database.
        """
        if not database_id:
            # If no DB ID is stored, we might need to search for one or fail
            logger.error("No Notion Database ID provided for task creation.")
            return False

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }
        
        # Simple page creation payload
        payload = {
            "parent": {"database_id": database_id},
            "properties": {
                "Name": { # Adjust "Name" if user's title property is named differently
                    "title": [
                        {
                            "text": {
                                "content": task_name
                            }
                        }
                    ]
                }
            }
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(f"{NOTION_API_BASE}/pages", json=payload, headers=headers)
            
            if response.status_code != 200:
                logger.error(f"Failed to create Notion Task: {response.text}")
                return False
            
            logger.info(f"Successfully created Notion task: {task_name}")
            return True

    async def search_for_database(self, access_token: str) -> Optional[str]:
        """
        Searches for the first available database the bot has access to.
        Useful for auto-discovery after connecting.
        """
        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }
        
        payload = {
            "filter": {
                "value": "database",
                "property": "object"
            }
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{NOTION_API_BASE}/search", json=payload, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                results = data.get("results", [])
                if results:
                    return results[0]["id"]
            
            return None

notion_service = NotionService()
