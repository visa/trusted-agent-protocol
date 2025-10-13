#!/usr/bin/env python3
# © 2025 Visa.
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

"""
Script to update the database schema with new columns for the orders table
"""

import sqlite3
import os
from pathlib import Path

# Database file path
DB_PATH = Path(__file__).parent / "merchant.db"

def update_database():
    """Add new columns to the orders table"""
    
    if not DB_PATH.exists():
        print("Database file not found. Please run the backend server first to create the database.")
        return
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    try:
        # Check if the new columns already exist
        cursor.execute("PRAGMA table_info(orders)")
        columns = [column[1] for column in cursor.fetchall()]
        
        new_columns = [
            ('billing_address', 'TEXT'),
            ('payment_method', 'VARCHAR(50)'),
            ('billing_different', 'BOOLEAN DEFAULT 0'),
            ('card_last_four', 'VARCHAR(4)'),
            ('card_brand', 'VARCHAR(20)'),
            ('payment_status', 'VARCHAR(20) DEFAULT "pending"')
        ]
        
        for column_name, column_type in new_columns:
            if column_name not in columns:
                print(f"Adding column: {column_name}")
                cursor.execute(f"ALTER TABLE orders ADD COLUMN {column_name} {column_type}")
            else:
                print(f"Column {column_name} already exists")
        
        conn.commit()
        print("Database schema updated successfully!")
        
    except sqlite3.Error as e:
        print(f"Error updating database: {e}")
        conn.rollback()
    
    finally:
        conn.close()

if __name__ == "__main__":
    update_database()
