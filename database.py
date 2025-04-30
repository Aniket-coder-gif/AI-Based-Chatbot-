from pymongo import MongoClient
from datetime import datetime
import logging
import os
import json
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FileStorage:
    """Fallback storage when MongoDB is not available"""

    def __init__(self, data_dir="chat_data"):
        self.data_dir = data_dir
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
        self.sessions_file = os.path.join(data_dir, "sessions.json")
        self.messages_dir = os.path.join(data_dir, "messages")
        if not os.path.exists(self.messages_dir):
            os.makedirs(self.messages_dir)

        # Load or create sessions file
        if os.path.exists(self.sessions_file):
            with open(self.sessions_file, 'r') as f:
                try:
                    self.sessions = json.load(f)
                except json.JSONDecodeError:
                    self.sessions = {}
        else:
            self.sessions = {}
            with open(self.sessions_file, 'w') as f:
                json.dump(self.sessions, f)

        logger.info(f"Using file-based storage in {data_dir}")

    def save_message(self, session_id, content, role, timestamp=None):
        """Save a message to file storage"""
        if timestamp is None:
            timestamp = datetime.now().isoformat()
        else:
            timestamp = timestamp.isoformat()

        message_data = {
            "session_id": session_id,
            "content": content,
            "role": role,
            "timestamp": timestamp
        }

        session_file = os.path.join(self.messages_dir, f"{session_id}.json")

        # Load existing messages or create new file
        if os.path.exists(session_file):
            with open(session_file, 'r') as f:
                try:
                    messages = json.load(f)
                except json.JSONDecodeError:
                    messages = []
        else:
            messages = []

        # Append new message
        message_id = str(uuid.uuid4())
        message_data["_id"] = message_id
        messages.append(message_data)

        # Save messages
        with open(session_file, 'w') as f:
            json.dump(messages, f, indent=2)

        logger.info(f"Message saved with ID: {message_id}")
        return message_id

    def get_session_messages(self, session_id, limit=100):
        """Get messages for a specific session from file storage"""
        session_file = os.path.join(self.messages_dir, f"{session_id}.json")

        if not os.path.exists(session_file):
            return []

        with open(session_file, 'r') as f:
            try:
                messages = json.load(f)
                # Sort by timestamp (convert back to datetime for consistent interface)
                for msg in messages:
                    if isinstance(msg["timestamp"], str):
                        msg["timestamp"] = datetime.fromisoformat(
                            msg["timestamp"])
                messages.sort(key=lambda x: x["timestamp"])
                return messages[:limit]
            except json.JSONDecodeError:
                logger.error(f"Error parsing session file: {session_file}")
                return []

    def create_session(self):
        """Create a new session and return the session ID"""
        session_id = str(uuid.uuid4())

        self.sessions[session_id] = {
            "created_at": datetime.now().isoformat(),
            "last_activity": datetime.now().isoformat()
        }

        # Save sessions
        with open(self.sessions_file, 'w') as f:
            json.dump(self.sessions, f, indent=2)

        logger.info(f"Session created with ID: {session_id}")
        return session_id

    def update_session_activity(self, session_id):
        """Update the last activity timestamp for a session"""
        if session_id in self.sessions:
            self.sessions[session_id]["last_activity"] = datetime.now(
            ).isoformat()

            # Save sessions
            with open(self.sessions_file, 'w') as f:
                json.dump(self.sessions, f, indent=2)

    def close(self):
        """Close the storage (nothing to do for file storage)"""
        pass


class Database:
    def __init__(self, connection_string="mongodb://localhost:27017/", db_name="Mychatbot"):
        self.using_fallback = False

        try:
            # Try to connect to MongoDB
            self.client = MongoClient(
                connection_string, serverSelectionTimeoutMS=5000)

            # Test the connection
            self.client.admin.command('ping')

            self.db = self.client[db_name]
            self.messages = self.db.messages
            logger.info(f"Connected to MongoDB: {db_name}")

            # Create index for user sessions
            self.messages.create_index("session_id")

        except Exception as e:
            logger.error(f"Error connecting to MongoDB: {e}")
            logger.info("Falling back to file-based storage")
            self.file_storage = FileStorage()
            self.using_fallback = True

    def save_message(self, session_id, content, role, timestamp=None):
        """Save a message to the database"""
        try:
            if timestamp is None:
                timestamp = datetime.now()

            message_data = {
                "session_id": session_id,
                "content": content,
                "role": role,  # "user" or "assistant"
                "timestamp": timestamp
            }

            if self.using_fallback:
                return self.file_storage.save_message(session_id, content, role, timestamp)

            result = self.messages.insert_one(message_data)
            logger.info(f"Message saved with ID: {result.inserted_id}")
            return result.inserted_id

        except Exception as e:
            logger.error(f"Error saving message: {e}")

            # If MongoDB fails, try fallback
            if not self.using_fallback:
                logger.info("Falling back to file storage for this operation")
                self.file_storage = FileStorage()
                self.using_fallback = True
                return self.file_storage.save_message(session_id, content, role, timestamp)
            return None

    def get_session_messages(self, session_id, limit=100):
        """Get messages for a specific session"""
        try:
            if self.using_fallback:
                return self.file_storage.get_session_messages(session_id, limit)

            cursor = self.messages.find(
                {"session_id": session_id}
            ).sort("timestamp", 1).limit(limit)

            return list(cursor)

        except Exception as e:
            logger.error(f"Error retrieving messages: {e}")

            # If MongoDB fails, try fallback
            if not self.using_fallback:
                logger.info("Falling back to file storage for this operation")
                self.file_storage = FileStorage()
                self.using_fallback = True
                return self.file_storage.get_session_messages(session_id, limit)
            return []

    def create_session(self):
        """Create a new session and return the session ID"""
        try:
            if self.using_fallback:
                return self.file_storage.create_session()

            session_data = {
                "created_at": datetime.now(),
                "last_activity": datetime.now()
            }

            result = self.db.sessions.insert_one(session_data)
            logger.info(f"Session created with ID: {result.inserted_id}")
            return str(result.inserted_id)

        except Exception as e:
            logger.error(f"Error creating session: {e}")

            # If MongoDB fails, try fallback
            if not self.using_fallback:
                logger.info("Falling back to file storage for this operation")
                self.file_storage = FileStorage()
                self.using_fallback = True
                return self.file_storage.create_session()
            else:
                # Last resort: just return a UUID
                session_id = str(uuid.uuid4())
                logger.info(f"Using UUID as session ID: {session_id}")
                return session_id

    def update_session_activity(self, session_id):
        """Update the last activity timestamp for a session"""
        try:
            if self.using_fallback:
                return self.file_storage.update_session_activity(session_id)

            self.db.sessions.update_one(
                {"_id": session_id},
                {"$set": {"last_activity": datetime.now()}}
            )
        except Exception as e:
            logger.error(f"Error updating session activity: {e}")

            # If MongoDB fails, try fallback
            if not self.using_fallback:
                logger.info("Falling back to file storage for this operation")
                self.file_storage = FileStorage()
                self.using_fallback = True
                self.file_storage.update_session_activity(session_id)

    def close(self):
        """Close the database connection"""
        if self.using_fallback:
            self.file_storage.close()
        elif hasattr(self, 'client'):
            self.client.close()


# Create a singleton instance
db = Database()

# Export the database instance


def get_db():
    return db
