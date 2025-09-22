# utils/database.py
import datetime
from google.cloud import firestore

# Initialize the Firestore client.
# When running on Google Cloud (like Cloud Run), the library automatically
# finds the project's credentials and project ID. No config needed.
db = firestore.Client()

def save_generation_to_history(topic: str, tone: str, metadata: dict, markdown_content: str):
    """Saves a successfully generated blog post to the Firestore 'history' collection."""
    try:
        # Create a reference to the 'history' collection.
        history_collection = db.collection('history')

        # Create a new document with a unique ID.
        # We'll store all the relevant information.
        doc_ref = history_collection.document() # Firestore generates a unique ID
        data_to_save = {
            'topic': topic,
            'tone': tone,
            'generated_output': markdown_content, # Renamed for clarity
            'timestamp': datetime.datetime.now(datetime.timezone.utc)
        }
        doc_ref.set(data_to_save)
        print(f"Successfully saved generation for topic '{topic}' to Firestore with ID: {doc_ref.id}")
        return doc_ref.id
    except Exception as e:
        print(f"Error saving to Firestore: {e}")
        return None

def get_history(limit: int = 20):
    """Retrieves the most recent generation history from Firestore."""
    try:
        history_collection = db.collection('history')
        # Query the collection, order by timestamp descending, and limit the results.
        query = history_collection.order_by(
            'timestamp', direction=firestore.Query.DESCENDING
        ).limit(limit)

        results = []
        for doc in query.stream():
            data = doc.to_dict()
            # Add the document ID to the result, which can be useful.
            data['id'] = doc.id
            # Firestore timestamp needs to be converted to a string for JSON serialization.
            data['timestamp'] = data['timestamp'].isoformat()
            results.append(data)

        print(f"Successfully retrieved {len(results)} history items from Firestore.")
        return results
    except Exception as e:
        print(f"Error retrieving history from Firestore: {e}")
        return []

def get_history_item_by_id(doc_id: str):
    """Retrieves a single history document by its Firestore ID."""
    try:
        doc_ref = db.collection('history').document(doc_id)
        doc = doc_ref.get()

        if not doc.exists:
            print(f"No history item found with ID: {doc_id}")
            return None

        data = doc.to_dict()
        data['id'] = doc.id
        # Convert timestamp to a string for JSON serialization
        if 'timestamp' in data and hasattr(data['timestamp'], 'isoformat'):
             data['timestamp'] = data['timestamp'].isoformat()

        print(f"Successfully retrieved history item with ID: {doc_id}")
        return data
    except Exception as e:
        print(f"Error retrieving document {doc_id} from Firestore: {e}")
        return None
    


def save_user_generation_to_history(user_info: dict, topic: str, tone: str, markdown_content: str):
    """Saves a generation linked to a specific user."""
    try:
        # We can store user-specific generations in a different collection
        # or add user fields to the main 'history' collection.
        # For now, let's add to the main collection.
        history_collection = db.collection('history')
        doc_ref = history_collection.document()

        data_to_save = {
            'userId': user_info.get('uid'), # The unique user ID from Firebase Auth
            'userName': user_info.get('name'),
            'userEmail': user_info.get('email'),
            'topic': topic,
            'tone': tone,
            'generated_output': markdown_content,
            'timestamp': datetime.datetime.now(datetime.timezone.utc)
        }
        doc_ref.set(data_to_save)
        print(f"Successfully saved generation for user {user_info.get('uid')}")
        return doc_ref.id
    except Exception as e:
        print(f"Error saving user generation to Firestore: {e}")
        return None