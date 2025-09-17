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
        doc_ref.set({
            'topic': topic,
            'tone': tone,
            'timestamp': datetime.datetime.now(datetime.timezone.utc), # Use timezone-aware UTC time
            'metadata': metadata, # This will be stored as a map
            'markdown_content': markdown_content
        })
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