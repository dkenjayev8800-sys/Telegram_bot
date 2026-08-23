import json
import os
from datetime import time
from typing import List, Dict, Any

DB_FILE = "bot_data.json"

def load_database() -> Dict[str, Any]:
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "publish_times": ["09:00", "15:00"],  # Default vaqtlar
        "topics": [],
        "queue": [],
        "settings": {}
    }

def save_database(data: Dict[str, Any]):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def add_publish_time(time_str: str) -> bool:
    data = load_database()
    if time_str not in data["publish_times"]:
        data["publish_times"].append(time_str)
        data["publish_times"].sort()
        save_database(data)
        return True
    return False

def remove_publish_time(time_str: str) -> bool:
    data = load_database()
    if time_str in data["publish_times"]:
        data["publish_times"].remove(time_str)
        save_database(data)
        return True
    return False

def get_publish_times() -> List[str]:
    data = load_database()
    return data.get("publish_times", [])

def add_topic(topic: str) -> bool:
    data = load_database()
    topic_obj = {
        "id": len(data["topics"]) + 1,
        "text": topic,
        "status": "pending"
    }
    data["topics"].append(topic_obj)
    save_database(data)
    return True

def get_topics() -> List[Dict]:
    data = load_database()
    return data.get("topics", [])

def add_to_queue(post_data: Dict) -> bool:
    data = load_database()
    post_data["id"] = len(data["queue"]) + 1
    data["queue"].append(post_data)
    save_database(data)
    return True

def get_queue() -> List[Dict]:
    data = load_database()
    return data.get("queue", [])

def remove_from_queue(post_id: int) -> bool:
    data = load_database()
    data["queue"] = [p for p in data["queue"] if p["id"] != post_id]
    save_database(data)
    return True
