import json
import logging
from typing import List

import pydantic_core
import requests

from app.entities.processed_agent_data import ProcessedAgentData
from app.interfaces.store_gateway import StoreGateway


class StoreApiAdapter(StoreGateway):
    def __init__(self, api_base_url):
        self.api_base_url = api_base_url

    def save_data(self, processed_agent_data_batch: List[ProcessedAgentData]):
        url = f"{self.api_base_url}/processed_agent_data/"
        data = [data.model_dump(mode='json') for data in processed_agent_data_batch]
        headers = {"Content-Type": "application/json"}

        try:
            response = requests.post(url, json=data, headers=headers)
            if response.status_code == 200:
                return True
            else:
                return False
        except Exception as e:
            logging.exception(f"Error saving data: {e}")
            return False
