import hashlib
import json
import logging
import os
import shutil
import subprocess
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from google.auth import default as google_auth_default
from google.oauth2 import service_account

LOGGER = logging.getLogger(__name__)
ROOT_DIR = Path(__file__).resolve().parents[1]
FIREBASERC_PATH = ROOT_DIR / ".firebaserc"
LOCAL_HOSTNAMES = {"localhost", "127.0.0.1"}
SECRET_NAME_ALIASES = {
    "NEWSDATA_API_KEY": ("NEWSDATA_API_KEY",),
    "FIREBASE_CREDENTIALS_JSON": ("FIREBASE_CREDENTIALS_JSON", "firebase-service-account-key"),
    "ANON_COOKIE_SECRET": ("ANON_COOKIE_SECRET",),
    "GEMINI_API_KEY": ("GEMINI_API_KEY",),
}
CLOUD_PLATFORM_SCOPE = ["https://www.googleapis.com/auth/cloud-platform"]

load_dotenv()


def is_cloud_run():
    return bool(os.getenv("K_SERVICE"))


def is_local_hostname(hostname: str | None):
    return (hostname or "").lower() in LOCAL_HOSTNAMES


@lru_cache(maxsize=1)
def get_project_id():
    for env_name in ("GCP_PROJECT", "GOOGLE_CLOUD_PROJECT", "GCLOUD_PROJECT"):
        value = os.getenv(env_name)
        if value:
            os.environ.setdefault("GCP_PROJECT", value.strip())
            return value.strip()

    if FIREBASERC_PATH.exists():
        try:
            firebaserc = json.loads(FIREBASERC_PATH.read_text(encoding="utf-8"))
            project_id = firebaserc.get("projects", {}).get("default")
            if project_id:
                os.environ.setdefault("GCP_PROJECT", project_id)
                return project_id
        except Exception as exc:
            LOGGER.warning("Failed to parse .firebaserc while resolving project id: %s", exc)

    try:
        _, detected_project = google_auth_default(scopes=CLOUD_PLATFORM_SCOPE)
        if detected_project:
            os.environ.setdefault("GCP_PROJECT", detected_project)
            return detected_project
    except Exception as exc:
        LOGGER.debug("ADC project detection failed: %s", exc)

    return None


@lru_cache(maxsize=1)
def get_service_account_info():
    raw_credentials = get_runtime_value(
        "FIREBASE_CREDENTIALS_JSON",
        allow_local_dev_default=False,
        allow_service_account_secret_client=False,
    )
    if not raw_credentials:
        return None

    try:
        return json.loads(raw_credentials)
    except json.JSONDecodeError as exc:
        LOGGER.error("FIREBASE_CREDENTIALS_JSON is not valid JSON: %s", exc)
        return None


@lru_cache(maxsize=1)
def get_google_credentials():
    service_account_info = get_service_account_info()
    if service_account_info:
        return service_account.Credentials.from_service_account_info(
            service_account_info, scopes=CLOUD_PLATFORM_SCOPE
        )

    try:
        credentials, _ = google_auth_default(scopes=CLOUD_PLATFORM_SCOPE)
        return credentials
    except Exception as exc:
        LOGGER.debug("ADC credential lookup failed: %s", exc)
        return None


def _normalize_secret_value(value: str):
    if value is None:
        return None
    return value.rstrip("\r\n")


def _load_secret_from_secret_manager(project_id: str, secret_name: str, credentials=None):
    try:
        from google.cloud import secretmanager
    except ImportError:
        return None

    try:
        client = secretmanager.SecretManagerServiceClient(credentials=credentials)
        secret_path = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
        response = client.access_secret_version(request={"name": secret_path})
        return _normalize_secret_value(response.payload.data.decode("utf-8"))
    except Exception as exc:
        LOGGER.debug("Secret Manager lookup failed for %s: %s", secret_name, exc)
        return None


def _find_gcloud_binary():
    return shutil.which("gcloud.cmd") or shutil.which("gcloud")


def _load_secret_via_gcloud(project_id: str, secret_name: str):
    gcloud_binary = _find_gcloud_binary()
    if not gcloud_binary:
        return None

    try:
        result = subprocess.run(
            [
                gcloud_binary,
                "secrets",
                "versions",
                "access",
                "latest",
                "--secret",
                secret_name,
                "--project",
                project_id,
            ],
            capture_output=True,
            text=True,
            timeout=20,
            check=True,
        )
        return _normalize_secret_value(result.stdout)
    except Exception as exc:
        LOGGER.debug("gcloud secret lookup failed for %s: %s", secret_name, exc)
        return None


def _derive_local_cookie_secret(project_id: str):
    seed_value = get_runtime_value(
        "FIREBASE_CREDENTIALS_JSON",
        allow_local_dev_default=False,
        allow_service_account_secret_client=False,
    ) or project_id or "bolgzenai"
    digest = hashlib.sha256(f"{project_id}:{seed_value}".encode("utf-8")).hexdigest()
    LOGGER.warning(
        "Using a derived local ANON_COOKIE_SECRET because no dedicated secret was found."
    )
    return digest


@lru_cache(maxsize=None)
def get_runtime_value(
    name: str,
    allow_local_dev_default: bool = True,
    allow_service_account_secret_client: bool = True,
):
    value = os.getenv(name)
    if value:
        return value

    if name == "GCP_PROJECT":
        return get_project_id()

    project_id = get_project_id()
    secret_aliases = SECRET_NAME_ALIASES.get(name, (name,))

    if project_id:
        for secret_name in secret_aliases:
            value = _load_secret_from_secret_manager(project_id, secret_name)
            if value:
                os.environ[name] = value
                return value

            if allow_service_account_secret_client and name != "FIREBASE_CREDENTIALS_JSON":
                credentials = get_google_credentials()
                if credentials:
                    value = _load_secret_from_secret_manager(
                        project_id, secret_name, credentials=credentials
                    )
                    if value:
                        os.environ[name] = value
                        return value

            value = _load_secret_via_gcloud(project_id, secret_name)
            if value:
                os.environ[name] = value
                return value

    if name == "ANON_COOKIE_SECRET" and allow_local_dev_default and not is_cloud_run():
        value = _derive_local_cookie_secret(project_id or "bolgzenai")
        os.environ[name] = value
        return value

    return None
