import sqlite3

# Connect to your database
conn = sqlite3.connect("users.db")
cursor = conn.cursor()

# Get all users
cursor.execute("SELECT * FROM users")
rows = cursor.fetchall()

# Get column names (for context)
columns = [desc[0] for desc in cursor.description]

# Display results
print(f"{' | '.join(columns)}")
print("-" * 50)
for row in rows:
    print(row)

conn.close()
