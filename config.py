# config.py
"""Configuration settings for the application"""

import os

# Database and file paths
DB_PATH = "data/contributions.db"
EXCEL_PATH = "data/contributions.xlsx"
USERS_FILE = "data/users.json"

# Business logic
DIVISION_FACTOR = 120
EXPECTED_PER_MEMBER = 1000.0 / DIVISION_FACTOR

# Authentication
COOKIE_NAME = "contribution_tracker_cookie"
COOKIE_KEY = "supersecretkey_change_this"  # Change for production
COOKIE_EXPIRY_DAYS = 1

# First user to register becomes admin automatically
# Set to False if you want to manually assign admins later
FIRST_USER_IS_ADMIN = True

# Ensure data directory exists
os.makedirs("data", exist_ok=True)