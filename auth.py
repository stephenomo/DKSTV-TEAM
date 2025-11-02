"""
Simple Authentication Module using SQLite Database
No roles - everyone is a viewer
"""

import streamlit as st
import streamlit_authenticator as stauth
import sqlite3
import os
import bcrypt

# Configuration
DB_FILE = "users.db"
SIGNATURE_KEY = "simple_auth_key_12345"


# ==================== DATABASE OPERATIONS ====================

def init_users_db():
    """Initialize the users database."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Create users table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            password TEXT NOT NULL,
            email TEXT,
            role TEXT,       
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()


def load_users_from_db():
    """
    Load all users from database.
    Returns:
        dict: {username: {name, password, email}}
    """
    init_users_db()
    
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("SELECT username, name, password, email, role FROM users")
    rows = cursor.fetchall()
    conn.close()
    
    users = {}
    for row in rows:
        username, name, password, email, role = row
        users[username] = {
            "name": name,
            "password": password,
            "email": email or f"{username}@example.com",
            "role": role  # ✅ Include the role!
        }
    
    return users


def save_user_to_db(username, name, password, email=None):
    """
    Save a new user to database.
    First user becomes admin, rest are viewers.
    
    Args:
        username (str): Username
        name (str): Full name
        password (str): Hashed password
        email (str): Email address
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        
        # Check if this is the first user (will be admin)
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        role = "admin" if user_count == 0 else "viewer"
        
        cursor.execute("""
            INSERT INTO users (username, name, password, email, role)
            VALUES (?, ?, ?, ?, ?)
        """, (username, name, password, email or f"{username}@example.com", role))
        
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        # Username already exists
        return False
    except Exception as e:
        st.error(f"Database error: {e}")
        return False


def user_exists(username):
    """
    Check if a username exists.
    
    Args:
        username (str): Username to check
    
    Returns:
        bool: True if exists, False otherwise
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM users WHERE username = ?", (username,))
    count = cursor.fetchone()[0]
    conn.close()
    
    return count > 0


def get_user_role(username):
    """
    Get the role of a user (case-insensitive).
    
    Args:
        username (str): Username
    
    Returns:
        str: User role (admin/viewer) or None
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Case-insensitive search using LOWER()
    cursor.execute("SELECT role FROM users WHERE LOWER(username) = LOWER(?)", (username,))
    result = cursor.fetchone()
    conn.close()
    
    return result[0] if result else None


def get_user_count():
    """
    Get total number of registered users.
    
    Returns:
        int: Number of users
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    conn.close()
    
    return count


def delete_all_users():
    """Delete all users from database."""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users")
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error deleting users: {e}")
        return False


# ==================== AUTHENTICATION ====================

def setup_authentication():
    """
    Initialize authentication system.
    
    Returns:
        tuple: (authenticator_object, users_dictionary)
    """
    # Initialize database
    init_users_db()
    
    # Load users from database
    users = load_users_from_db()
    
    # Debug: Show what we loaded
    if len(users) > 0 and st.session_state.get('show_debug', False):
        st.sidebar.write("🔍 Debug - Users loaded:", list(users.keys()))
    
    # Prepare credentials in the format expected by streamlit-authenticator
    credentials = {
        "usernames": users
    }
    
    # Create authenticator
    authenticator = stauth.Authenticate(
        credentials,
        cookie_name="simple_viewer_app",
        key=SIGNATURE_KEY,
        cookie_expiry_days=30
    )
    
    return authenticator, users


# ==================== REGISTRATION ====================

def register_user_ui():
    """Display user registration form."""
    st.sidebar.write("### 🆕 Register New User")
    
    with st.sidebar.form("register_form", clear_on_submit=True):
        new_username = st.text_input("Username*", max_chars=20)
        new_name = st.text_input("Full Name*")
        new_email = st.text_input("Email (optional)")
        new_password = st.text_input("Password*", type="password")
        confirm_password = st.text_input("Confirm Password*", type="password")
        
        submit = st.form_submit_button("✅ Register", use_container_width=True)
        
        if submit:
            # Validation
            if not all([new_username, new_name, new_password, confirm_password]):
                st.error("❌ Please fill all required fields")
                return
            
            if new_password != confirm_password:
                st.error("❌ Passwords do not match")
                return
            
            if len(new_password) < 6:
                st.error("❌ Password must be at least 6 characters")
                return
            
            # Check if username exists
            if user_exists(new_username):
                st.error(f"❌ Username '{new_username}' already exists")
                return
            
            # Hash the password directly with bcrypt
            try:
                # Use bcrypt directly to ensure compatibility
                hashed_password = bcrypt.hashpw(new_password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
                st.success("✅ Password hashed successfully")
            except Exception as e:
                st.error(f"❌ Error hashing password: {e}")
                return
            
            # Save to database
            if save_user_to_db(new_username, new_name, hashed_password, new_email):
                user_count = get_user_count()
                if user_count == 1:
                    st.success(f"✅ Admin user '{new_username}' registered successfully!")
                    st.info("🔑 You are the first user and have admin privileges!")
                else:
                    st.success(f"✅ User '{new_username}' registered successfully!")
                    st.info("🔑 Switch to 'Log In' mode and use your credentials")
                
                st.info(f"📝 Remember: Username='{new_username}'")
                st.balloons()
                
                # Force a rerun to reload users
                st.rerun()
            else:
                st.error("❌ Registration failed. Please try again.")


# ==================== UTILITY FUNCTIONS ====================

def get_all_users():
    """
    Get list of all usernames.
    
    Returns:
        list: List of usernames with their details
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("SELECT username, name, role FROM users ORDER BY created_at DESC")
    users = cursor.fetchall()
    conn.close()
    
    return users


def delete_user(username):
    """
    Delete a user from database.
    
    Args:
        username (str): Username to delete
    
    Returns:
        bool: True if successful
    """
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE username = ?", (username,))
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Error deleting user: {e}")
        return False


def debug_test_password(username, test_password):
    """
    Test if a password matches for a user (for debugging only).
    Remove this function in production!
    """
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    cursor.execute("SELECT password FROM users WHERE username = ?", (username,))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        stored_hash = result[0]
        st.write(f"🔍 Stored hash starts with: {stored_hash[:20]}...")
        
        # Test with bcrypt
        try:
            match = bcrypt.checkpw(test_password.encode('utf-8'), stored_hash.encode('utf-8'))
            st.write(f"✅ bcrypt match: {match}")
            return match
        except Exception as e:
            st.write(f"❌ bcrypt error: {e}")
            return False
    else:
        st.write(f"❌ User '{username}' not found")
        return False