import sqlite3
import sys
import os

# Usage: python print_db.py [database_file]
def print_table(cursor, table):
    print(f"\n===== {table} =====")
    try:
        cursor.execute(f"SELECT * FROM {table} ORDER BY created_at DESC LIMIT 10")
        rows = cursor.fetchall()
        if not rows:
            print("(No rows)")
        for row in rows:
            print(dict(row))
    except Exception as e:
        print(f"(Table {table} not found or error: {e})")

def main():
    db_file = sys.argv[1] if len(sys.argv) > 1 else "enhanced_glitch_bot_v2.db"
    if not os.path.exists(db_file):
        print(f"Database file '{db_file}' not found.")
        sys.exit(1)
    conn = sqlite3.connect(db_file)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    for table in ["monitored_content", "generated_threads", "mentions_responses", "priority_queue"]:
        print_table(cursor, table)
    conn.close()

if __name__ == "__main__":
    main() 