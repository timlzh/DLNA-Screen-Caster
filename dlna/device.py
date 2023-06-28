import json
from typing import Any

class Device():
    location: str
    host: str
    friendly_name: str
    action_url: str
    manufacturer: str
    manufacturer_url: str
    st: str
    help: str
    info: dict
    def __init__(self, info: dict) -> None:
        self.parse(info)
    
    def __str__(self) -> str:
        return json.dumps(self.info, ensure_ascii=False, indent=4)
    
    def __getitem__(self, key: str) -> Any:
        return self.info[key]
    
    def parse(self, info: dict):
        self.info = info
        self.location = info["location"]
        self.host = info["host"]
        self.friendly_name = info["friendly_name"]
        self.action_url = info["action_url"]
        self.manufacturer = info["manufacturer"]
        self.manufacturer_url = info["manufacturer_url"]
        self.st = info["st"]
        self.help = info["help"]