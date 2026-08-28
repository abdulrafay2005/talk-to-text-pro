"""
connection.py
Handles the connection to MongoDB Atlas.

We connect once and keep the connection, so we do not
open a new connection on every request.
"""

import os

from dotenv import load_dotenv
from pymongo import MongoClient

# Load the values from the .env file.
load_dotenv()

MONGO_URI = os.getenv("MONGO_URI")
DATABASE_NAME = os.getenv("DATABASE_NAME", "talktotext")

_client = None
_database = None


def get_database():
    """
    Return the MongoDB database object.
    Connects on the first call and reuses the connection afterwards.
    """
    global _client, _database

    if _database is None:
        if not MONGO_URI:
            raise ValueError("MONGO_URI is missing. Check your .env file.")

        _client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)
        _database = _client[DATABASE_NAME]

    return _database


def get_meetings_collection():
    """
    Shortcut method that returns the "meetings" collection.
    """
    return get_database()["meetings"]


def get_users_collection():
    """
    Shortcut method that returns the "users" collection.
    Passwords are always stored as password hashes (never plain text).
    """
    return get_database()["users"]