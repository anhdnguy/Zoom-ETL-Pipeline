from typing import List, Dict

def split_users(user_ids: List[str], chunk_size: int) -> List[List[str]]:
    return [user_ids[i:i + chunk_size] for i in range(0, len(user_ids), chunk_size)]

def extract_user_ids(user_data: List[Dict]) -> List[str]:
    return [user.get("email") for user in user_data]