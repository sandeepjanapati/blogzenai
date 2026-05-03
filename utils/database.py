# utils/database.py
import datetime
import logging
from functools import lru_cache

from google.api_core.exceptions import AlreadyExists
from google.cloud import firestore
from utils.runtime_config import get_google_credentials, get_runtime_value

LOGGER = logging.getLogger(__name__)
HISTORY_COLLECTION = "history"
ANON_USAGE_COLLECTION = "anonymous_generation_usage"


@lru_cache(maxsize=1)
def get_db():
    return firestore.Client(
        project=get_runtime_value("GCP_PROJECT", allow_local_dev_default=False),
        credentials=get_google_credentials(),
    )


def _utcnow():
    return datetime.datetime.now(datetime.timezone.utc)


def _serialize_history_doc(doc):
    data = doc.to_dict()
    data["id"] = doc.id
    timestamp = data.get("timestamp")
    if hasattr(timestamp, "isoformat"):
        data["timestamp"] = timestamp.isoformat()
    return data


def save_generation_to_history(topic: str, tone: str, metadata: dict, markdown_content: str):
    history_collection = get_db().collection(HISTORY_COLLECTION)
    doc_ref = history_collection.document()
    doc_ref.set(
        {
            "topic": topic,
            "tone": tone,
            "metadata": metadata,
            "generated_output": markdown_content,
            "timestamp": _utcnow(),
        }
    )
    LOGGER.info("Saved anonymous generation for topic '%s'", topic)
    return doc_ref.id


def get_history(user_id: str, limit: int = 20):
    history_collection = get_db().collection(HISTORY_COLLECTION)
    query = (
        history_collection.where("userId", "==", user_id)
        .order_by("timestamp", direction=firestore.Query.DESCENDING)
        .limit(limit)
    )

    results = [_serialize_history_doc(doc) for doc in query.stream()]
    LOGGER.info("Retrieved %s history items for user %s", len(results), user_id)
    return results


def get_history_item_by_id(doc_id: str):
    doc_ref = get_db().collection(HISTORY_COLLECTION).document(doc_id)
    doc = doc_ref.get()
    if not doc.exists:
        return None
    return _serialize_history_doc(doc)


def save_user_generation_to_history(
    user_info: dict, topic: str, tone: str, metadata: dict, markdown_content: str
):
    history_collection = get_db().collection(HISTORY_COLLECTION)
    doc_ref = history_collection.document()
    doc_ref.set(
        {
            "userId": user_info.get("uid"),
            "userName": user_info.get("name"),
            "userEmail": user_info.get("email"),
            "topic": topic,
            "tone": tone,
            "metadata": metadata,
            "generated_output": markdown_content,
            "timestamp": _utcnow(),
        }
    )
    LOGGER.info("Saved generation for user %s", user_info.get("uid"))
    return doc_ref.id


def get_anonymous_generation_usage(cookie_id: str):
    doc_ref = get_db().collection(ANON_USAGE_COLLECTION).document(cookie_id)
    doc = doc_ref.get()
    if not doc.exists:
        return None

    data = doc.to_dict()
    data["id"] = doc.id
    return data


def reserve_anonymous_generation(cookie_id: str):
    doc_ref = get_db().collection(ANON_USAGE_COLLECTION).document(cookie_id)
    try:
        doc_ref.create(
            {
                "status": "reserved",
                "reservedAt": _utcnow(),
            }
        )
        LOGGER.info("Reserved anonymous generation slot for cookie %s", cookie_id)
        return True
    except AlreadyExists:
        return False


def mark_anonymous_generation_used(cookie_id: str, history_id: str):
    doc_ref = get_db().collection(ANON_USAGE_COLLECTION).document(cookie_id)
    now = _utcnow()
    doc_ref.set(
        {
            "status": "used",
            "historyId": history_id,
            "generationCount": 1,
            "usedAt": now,
            "updatedAt": now,
        },
        merge=True,
    )
    LOGGER.info("Marked anonymous generation as used for cookie %s", cookie_id)


def release_anonymous_generation_reservation(cookie_id: str):
    doc_ref = get_db().collection(ANON_USAGE_COLLECTION).document(cookie_id)
    doc = doc_ref.get()
    if doc.exists and doc.to_dict().get("status") == "reserved":
        doc_ref.delete()
        LOGGER.info("Released anonymous generation reservation for cookie %s", cookie_id)
