# utils/database.py
import datetime
from google.cloud import firestore

db = firestore.Client()

def save_generation_to_history(topic: str, tone: str, metadata: dict, markdown_content: str):
    history_collection = db.collection('history')
    doc_ref = history_collection.document()
    doc_ref.set({
        'topic': topic, 'tone': tone, 'metadata': metadata,
        'generated_output': markdown_content,
        'timestamp': datetime.datetime.now(datetime.timezone.utc)
    })
    print(f"Successfully saved ANONYMOUS generation for topic '{topic}'")
    return doc_ref.id

def get_history(user_id: str, limit: int = 20):
    """Retrieves the most recent generation history FOR A SPECIFIC USER."""
    history_collection = db.collection('history')
    query = history_collection.where('userId', '==', user_id).order_by(
        'timestamp', direction=firestore.Query.DESCENDING
    ).limit(limit)
    
    results = []
    for doc in query.stream():
        data = doc.to_dict()
        data['id'] = doc.id
        data['timestamp'] = data['timestamp'].isoformat()
        results.append(data)
    
    print(f"Successfully retrieved {len(results)} history items for user {user_id}")
    return results

def get_history_item_by_id(doc_id: str):
    doc_ref = db.collection('history').document(doc_id)
    doc = doc_ref.get()
    if not doc.exists: return None
    data = doc.to_dict()
    data['id'] = doc.id
    if 'timestamp' in data and hasattr(data['timestamp'], 'isoformat'):
        data['timestamp'] = data['timestamp'].isoformat()
    return data

def save_user_generation_to_history(user_info: dict, topic: str, tone: str, metadata: dict, markdown_content: str):
    history_collection = db.collection('history')
    doc_ref = history_collection.document()
    doc_ref.set({
        'userId': user_info.get('uid'),
        'userName': user_info.get('name'),
        'userEmail': user_info.get('email'),
        'topic': topic, 'tone': tone, 'metadata': metadata,
        'generated_output': markdown_content,
        'timestamp': datetime.datetime.now(datetime.timezone.utc)
    })
    print(f"Successfully saved generation for user {user_info.get('uid')}")
    return doc_ref.id