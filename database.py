import json
import os
import csv
from datetime import time, datetime, timedelta
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
    # Agar post_data'da id bo'lmasa, yangi id berish
    if "id" not in post_data:
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

def create_test(title: str, questions: List[Dict]) -> int:
    data = load_database()
    if "tests" not in data:
        data["tests"] = []

    test_id = len(data["tests"]) + 1
    test_obj = {
        "id": test_id,
        "title": title,
        "questions": questions,
        "responses": [],
        "created_at": str(datetime.now())
    }
    data["tests"].append(test_obj)
    save_database(data)
    return test_id

def get_tests() -> List[Dict]:
    data = load_database()
    return data.get("tests", [])

def get_test(test_id: int) -> Dict:
    data = load_database()
    for test in data.get("tests", []):
        if test["id"] == test_id:
            return test
    return None

def add_test_response(test_id: int, user_id: int, question_index: int, answer: str) -> bool:
    data = load_database()
    for test in data.get("tests", []):
        if test["id"] == test_id:
            response = {
                "user_id": user_id,
                "question_index": question_index,
                "answer": answer,
                "timestamp": str(__import__('datetime').datetime.now())
            }
            test["responses"].append(response)
            save_database(data)
            return True
    return False

def get_test_responses(test_id: int) -> List[Dict]:
    test = get_test(test_id)
    return test.get("responses", []) if test else []

def delete_test(test_id: int) -> bool:
    data = load_database()
    data["tests"] = [t for t in data.get("tests", []) if t["id"] != test_id]
    save_database(data)
    return True

# ==========================================
# GURUH STATISTIKASI UCHUN YANGI FUNKSIYALAR
# ==========================================

def log_user_addition(inviter_id: int, inviter_name: str, new_user_id: int) -> bool:
    """Yangi odam qo'shilganda bazaga yozib qo'yish"""
    data = load_database()
    if "group_additions" not in data:
        data["group_additions"] = []
    
    data["group_additions"].append({
        "inviter_id": inviter_id,
        "inviter_name": inviter_name,
        "new_user_id": new_user_id,
        "date": str(datetime.now())
    })
    save_database(data)
    return True

def get_addition_stats(days: int = 30) -> Dict[int, Dict[str, Any]]:
    """Belgilangan kunlar ichida kim qancha odam qo'shganini hisoblash"""
    data = load_database()
    additions = data.get("group_additions", [])
    
    stats = {}
    cutoff_date = datetime.now() - timedelta(days=days)
    
    for entry in additions:
        try:
            # Datetime formatini o'qish (mikrosoniyalar bilan yoki ularsiz)
            date_str = entry["date"]
            if "." in date_str:
                entry_date = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S.%f")
            else:
                entry_date = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
                
            if entry_date >= cutoff_date:
                inviter = entry["inviter_id"]
                if inviter not in stats:
                    stats[inviter] = {
                        "name": entry.get("inviter_name", f"ID: {inviter}"),
                        "count": 0
                    }
                stats[inviter]["count"] += 1
        except Exception:
            continue # Xato sanalar bo'lsa o'tkazib yuboramiz
            
    # Natijani eng ko'p odam qo'shgandan boshlab saralash
    sorted_stats = dict(sorted(stats.items(), key=lambda item: item[1]['count'], reverse=True))
    return sorted_stats

def export_stats_to_excel(days: int = 30, filename: str = "statistika.csv") -> str:
    """Ma'lumotlarni Excel (CSV) formatida saqlash"""
    stats = get_addition_stats(days)
    
    with open(filename, mode="w", encoding="utf-8-sig", newline="") as file:
        writer = csv.writer(file)
        # Excel ustunlari nomlari
        writer.writerow(["Foydalanuvchi ID", "Ismi", f"Qo'shgan odamlari soni ({days} kunlik)"])
        
        for inviter_id, info in stats.items():
            writer.writerow([inviter_id, info['name'], info['count']])
            
    return filename
