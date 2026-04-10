import re
import logging
import firebase_admin
from firebase_admin import credentials, db

logger = logging.getLogger(__name__)

# Constants
SERVICE_ACCOUNT_FILE = 'teamdl-firebase-adminsdk-fbsvc-e94b44d7c0.json'
DATABASE_URL = 'https://teamdl-default-rtdb.firebaseio.com/'

_is_initialized = False

def init_firebase():
    global _is_initialized
    if _is_initialized:
        return
    
    try:
        cred = credentials.Certificate(SERVICE_ACCOUNT_FILE)
        firebase_admin.initialize_app(cred, {
            'databaseURL': DATABASE_URL
        })
        _is_initialized = True
        logger.info("Firebase Admin SDK initialized successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize Firebase: {e}")
        # We don't raise error here, but functions will fail if not fixed
        # Alternatively, we could raise if we want the bot to stop on config error
        pass

def normalize_title(title):
    """
    Normalisasi judul:
    1. Lowercase
    2. Hapus spasi berlebih
    3. Hapus karakter ilegal: . # $ [ ]
    """
    if not title:
        return ""
    # Lowercase
    title = title.lower()
    # Remove illegal characters for Firebase keys: . # $ [ ]
    title = re.sub(r'[.#$\[\]]', '', title)
    # Remove extra spaces (split then join handles multiple spaces)
    title = " ".join(title.split())
    return title

def is_title_uploaded(title):
    """Check if title exists in Firebase."""
    if not _is_initialized:
        init_firebase()
    
    if not _is_initialized:
        return False # Fallback if firebase init failed
        
    normalized = normalize_title(title)
    if not normalized:
        return False
        
    try:
        ref = db.reference(f'uploaded_titles/{normalized}')
        result = ref.get()
        return result is not None
    except Exception as e:
        logger.error(f"Error checking Firebase for {normalized}: {e}")
        return False

def mark_title_as_uploaded(title):
    """Save title to Firebase as uploaded."""
    if not _is_initialized:
        init_firebase()
    
    if not _is_initialized:
        return False
        
    normalized = normalize_title(title)
    if not normalized:
        return False
        
    try:
        ref = db.reference(f'uploaded_titles/{normalized}')
        ref.set(True)
        logger.info(f"Title '{normalized}' marked as uploaded in Firebase.")
        return True
    except Exception as e:
        logger.error(f"Error saving to Firebase for {normalized}: {e}")
        return False
