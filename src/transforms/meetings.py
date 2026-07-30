from typing import List, Dict

def split_meetings_to_chunk(meeting_infos: List[Dict], chunk_size: int) -> List[List[Dict]]:
    return [meeting_infos[i:i + chunk_size] for i in range(0, len(meeting_infos), chunk_size)]

def extract_meeting_ids(meeting_data: List[Dict]) -> List[str]:
    return [meeting.get("uuid") for meeting in meeting_data]