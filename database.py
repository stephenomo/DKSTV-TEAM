# database.py
"""Database operations for contributions"""

import pandas as pd
from datetime import datetime
from sqlalchemy import create_engine, text
from config import DB_PATH, DIVISION_FACTOR

import sqlite3

def ensure_role_column():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()

    # Check if 'role' column exists
    cursor.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in cursor.fetchall()]

    if 'role' not in columns:
        conn.execute("ALTER TABLE users ADD COLUMN role TEXT;")
        print("✅ Added 'role' column.")
    else:
        print("ℹ️ 'role' column already exists — skipping.")

    conn.commit()
    conn.close()



def get_engine():
    """Create and return database engine"""
    return create_engine(f"sqlite:///{DB_PATH}", connect_args={"check_same_thread": False})


def init_db():
    """Initialize database tables"""
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text("""
        CREATE TABLE IF NOT EXISTS contributions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            member TEXT NOT NULL,
            amount REAL NOT NULL,
            month TEXT NOT NULL,
            date TEXT NOT NULL
        )
        """))


def normalize_amount(amount):
    """Normalize amount by division factor"""
    return float(amount) / DIVISION_FACTOR


def add_contribution(member, amount, month):
    """Add a new contribution to database"""
    engine = get_engine()
    now = datetime.utcnow().isoformat()
    divided_amount = normalize_amount(amount)
    member = member.strip().capitalize()
    month = month.strip().capitalize()
    
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO contributions (member, amount, month, date)
            VALUES (:m, :a, :mo, :d)
        """), {"m": member, "a": divided_amount, "mo": month, "d": now})


def get_all_contributions():
    """Retrieve all contributions as DataFrame"""
    engine = get_engine()
    return pd.read_sql("SELECT * FROM contributions ORDER BY date DESC", engine)


def delete_entry(entry_id):
    """Delete a contribution entry by ID
    
    Args:
        entry_id: The ID of the entry to delete
        
    Returns:
        bool: True if deletion was successful, False otherwise
    """
    try:
        engine = get_engine()
        with engine.begin() as conn:
            result = conn.execute(
                text("DELETE FROM contributions WHERE id = :id"), 
                {"id": int(entry_id)}
            )
            # Check if any rows were affected
            return result.rowcount > 0
    except Exception as e:
        print(f"Error deleting entry: {e}")
        return False


def import_contributions_from_excel(file):
    """
    Import contributions from Excel file
    
    Args:
        file: Uploaded Excel file object
        
    Returns:
        tuple: (success_count, error_list)
    """
    try:
        # Read Excel file
        df = pd.read_excel(file)
        
        # Required columns
        required_cols = ['member', 'amount', 'month']
        missing_cols = [col for col in required_cols if col not in df.columns]
        
        if missing_cols:
            return 0, [f"Missing required columns: {', '.join(missing_cols)}"]
        
        success_count = 0
        errors = []
        
        # Process each row
        for idx, row in df.iterrows():
            try:
                member = str(row['member']).strip()
                amount = float(row['amount'])
                month = str(row['month']).strip()
                
                if not member or not month or amount <= 0:
                    errors.append(f"Row {idx + 2}: Invalid data")
                    continue
                
                add_contribution(member, amount, month)
                success_count += 1
                
            except Exception as e:
                errors.append(f"Row {idx + 2}: {str(e)}")
        
        return success_count, errors
        
    except Exception as e:
        return 0, [f"Error reading Excel file: {str(e)}"]


def export_contributions_to_excel():
    """
    Export all contributions to Excel format
    
    Returns:
        bytes: Excel file as bytes
    """
    df = get_all_contributions()
    
    # Create Excel file in memory
    from io import BytesIO
    output = BytesIO()
    
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Contributions')
    
    return output.getvalue()