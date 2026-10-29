
import sqlite3

DATABASE_NAME = "smartlab.db"


def initialize_database():
    connection = sqlite3.connect(DATABASE_NAME)

    try:
        cursor = connection.cursor()

        # Table 1: Laboratory equipment
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS equipment (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            available INTEGER NOT NULL
        )
        """)

        # Table 2: Equipment booking requests
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_name TEXT NOT NULL,
            roll_number TEXT NOT NULL,
            equipment_name TEXT NOT NULL,
            booking_date TEXT NOT NULL,
            time_slot TEXT NOT NULL,
            purpose TEXT,
            status TEXT DEFAULT 'Pending',
            owner_username TEXT
        )
        """)

        # Table 3: Maintenance reports
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS maintenance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_name TEXT NOT NULL,
            equipment_name TEXT NOT NULL,
            issue_type TEXT NOT NULL,
            description TEXT NOT NULL,
            status TEXT DEFAULT 'Pending',
            roll_number TEXT,
            owner_username TEXT
        )
        """)

        # Add missing columns to existing databases.
        # This preserves existing records.
        booking_columns = {
            row[1]
            for row in cursor.execute(
                "PRAGMA table_info(bookings)"
            ).fetchall()
        }

        if "roll_number" not in booking_columns:
            cursor.execute(
                "ALTER TABLE bookings ADD COLUMN roll_number TEXT"
            )

        if "owner_username" not in booking_columns:
            cursor.execute(
                "ALTER TABLE bookings ADD COLUMN owner_username TEXT"
            )

        maintenance_columns = {
            row[1]
            for row in cursor.execute(
                "PRAGMA table_info(maintenance)"
            ).fetchall()
        }

        if "roll_number" not in maintenance_columns:
            cursor.execute(
                "ALTER TABLE maintenance ADD COLUMN roll_number TEXT"
            )

        if "owner_username" not in maintenance_columns:
            cursor.execute(
                "ALTER TABLE maintenance ADD COLUMN owner_username TEXT"
            )

        # Insert sample equipment only when the table is empty.
        cursor.execute("SELECT COUNT(*) FROM equipment")

        if cursor.fetchone()[0] == 0:
            equipment_items = [
                ("Digital Multimeter", 10, 10),
                ("Oscilloscope", 4, 4),
                ("Function Generator", 6, 6),
                ("Digital Trainer Kit", 8, 8)
            ]

            cursor.executemany(
                """
                INSERT INTO equipment (name, quantity, available)
                VALUES (?, ?, ?)
                """,
                equipment_items
            )

        connection.commit()
        print("Smart Lab database initialized successfully!")

    except sqlite3.Error:
        connection.rollback()
        raise

    finally:
        connection.close()


if __name__ == "__main__":
    initialize_database()
