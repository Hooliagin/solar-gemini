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
        Dynamically handles the 'title' property name with DEBUG logging.
        """
        if not database_id:
            logger.error("No Notion Database ID provided for task creation.")
            return False

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
            "Notion-Version": "2022-06-28"
        }
        
        prop_name = "Name" # Default guess
        
        async with httpx.AsyncClient() as client:
            def build_payload(p_name):
                return {
                    "parent": {"database_id": database_id},
                    "properties": {
                        p_name: {
                            "title": [{"text": {"content": task_name}}]
                        }
                    }
                }

            # 1. Try with default "Name"
            try:
                response = await client.post(
                    f"{NOTION_API_BASE}/pages", 
                    json=build_payload(prop_name), 
                    headers=headers
                )
            except Exception as e:
                logger.error(f"Initial Notion POST failed: {e}")
                return False
            
            # 2. If it fails due to property name, find the real one
            if response.status_code == 400 and "property that exists" in response.text:
                logger.warning(f"Default property '{prop_name}' failed. Fetching correct title property for DB {database_id}...")
                
                try:
                    # Fetch DB details
                    db_resp = await client.get(f"{NOTION_API_BASE}/databases/{database_id}", headers=headers)
                    logger.info(f"DB Fetch Status: {db_resp.status_code}")
                    
                    if db_resp.status_code == 200:
                        props = db_resp.json().get("properties", {})
                        logger.info(f"DB Properties Found: {list(props.keys())}")
                        
                        found_title_prop = None
                        for key, val in props.items():
                            if val.get("type") == "title":
                                found_title_prop = key
                                break
                        
                        if found_title_prop:
                            logger.info(f"Identified Title Property: '{found_title_prop}'")
                            prop_name = found_title_prop
                            # Retry with correct name
                            response = await client.post(
                                f"{NOTION_API_BASE}/pages", 
                                json=build_payload(prop_name), 
                                headers=headers
                            )
                            logger.info(f"Retry POST Status: {response.status_code}")
                        else:
                            logger.error("Could not determine 'title' property from DB schema.")
                    else:
                        logger.error(f"Failed to fetch DB schema (Status {db_resp.status_code}): {db_resp.text}")
                except Exception as e:
                    logger.error(f"Exception during Notion retry logic: {e}")

            if response.status_code != 200:
                logger.error(f"Failed to create Notion Task: {response.text}")
                return False
            
            logger.info(f"Successfully created Notion task: {task_name} (Property: {prop_name})")
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
