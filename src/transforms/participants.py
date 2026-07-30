from typing import List, Dict

def add_meeting_id(meeting_uuid: str, meeting_participants: List[Dict]) -> List[Dict]:
    for meeting_participant in meeting_participants:
        meeting_participant["meeting_uuid"] = meeting_uuid
    
    return meeting_participants

def flatten_participant(meeting_participants: List[List[Dict]]) -> List[Dict]:
    flattened = []

    for group in meeting_participants:
        if not isinstance(group, list):
            raise TypeError("Expected list of participant groups")
        
        for item in group:
            flattened.append(item)

    return flattened