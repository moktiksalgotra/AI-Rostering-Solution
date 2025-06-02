import sqlite3
import pandas as pd
from datetime import datetime
import json

class DatabaseHandler:
    def __init__(self, db_path='data/roster.db'):
        self.db_path = db_path
        self.initialize_database()

    def get_connection(self):
        """Create a database connection."""
        return sqlite3.connect(self.db_path)

    def initialize_database(self):
        """Initialize database with required tables."""
        try:
            print("Starting database initialization...")
            conn = self.get_connection()
            cursor = conn.cursor()

            # Create staff table
            print("Creating staff table...")
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS staff (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    role TEXT NOT NULL,
                    skills TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Create leave_requests table if it doesn't exist
            print("Creating leave_requests table if not exists...")
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS leave_requests (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    staff_member TEXT NOT NULL,
                    leave_type TEXT NOT NULL,
                    start_date DATE NOT NULL,
                    end_date DATE NOT NULL,
                    duration INTEGER NOT NULL,
                    reason TEXT,
                    status TEXT DEFAULT 'Pending',
                    submitted_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Verify tables exist
            print("Verifying tables...")
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            print(f"Found tables: {[table[0] for table in tables]}")

            conn.commit()
            print("Database initialization completed successfully.")
        except Exception as e:
            print(f"Error initializing database: {str(e)}")
            raise  # Re-raise the exception to see the full traceback
        finally:
            conn.close()

    def add_staff(self, name, role, skills):
        """Add a new staff member."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO staff (name, role, skills)
                VALUES (?, ?, ?)
            ''', (name, role, skills))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error adding staff: {str(e)}")
            return False
        finally:
            conn.close()

    def update_staff(self, staff_id, name, role, skills):
        """Update staff information."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE staff 
                SET name = ?, role = ?, skills = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (name, role, skills, staff_id))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error updating staff: {str(e)}")
            return False
        finally:
            conn.close()

    def delete_staff(self, staff_id):
        """Delete a staff member."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('DELETE FROM staff WHERE id = ?', (staff_id,))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error deleting staff: {str(e)}")
            return False
        finally:
            conn.close()

    def get_all_staff(self):
        """Get all staff members as a pandas DataFrame."""
        try:
            conn = self.get_connection()
            # Explicitly name columns in the query
            query = '''
                SELECT 
                    id as id,
                    name as name,
                    role as role,
                    skills as skills,
                    created_at as created_at,
                    updated_at as updated_at
                FROM staff
            '''
            df = pd.read_sql_query(query, conn)
            
            # Ensure all required columns are present
            required_columns = ['id', 'name', 'role', 'skills']
            if not all(col in df.columns for col in required_columns):
                print("Warning: Missing required columns in staff data")
                print(f"Expected: {required_columns}")
                print(f"Got: {df.columns.tolist()}")
                return pd.DataFrame(columns=required_columns)
            
            # Convert id to integer type
            df['id'] = df['id'].astype(int)
            
            # Ensure proper column order
            df = df[required_columns]
            
            return df
        except Exception as e:
            print(f"Error getting staff: {str(e)}")
            # Return empty DataFrame with correct columns
            return pd.DataFrame(columns=['id', 'name', 'role', 'skills'])
        finally:
            conn.close()

    def add_leave_request(self, staff_member, leave_type, start_date, end_date, duration, reason):
        """Add a new leave request."""
        try:
            print(f"Adding leave request for {staff_member}")
            print(f"Leave type: {leave_type}")
            print(f"Start date: {start_date}")
            print(f"End date: {end_date}")
            print(f"Duration: {duration}")
            print(f"Reason: {reason}")
            
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO leave_requests 
                (staff_member, leave_type, start_date, end_date, duration, reason)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (staff_member, leave_type, start_date, end_date, duration, reason))
            conn.commit()
            print("Leave request added successfully")
            return True
        except Exception as e:
            print(f"Error adding leave request: {str(e)}")
            return False
        finally:
            conn.close()

    def update_leave_status(self, leave_id, status):
        """Update leave request status."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE leave_requests 
                SET status = ?
                WHERE id = ?
            ''', (status, leave_id))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error updating leave status: {str(e)}")
            return False
        finally:
            conn.close()

    def get_all_leave_requests(self):
        """Get all leave requests as a list of dictionaries."""
        try:
            print("Fetching all leave requests...")
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, staff_member, leave_type, start_date, end_date, 
                       duration, reason, status, submitted_date
                FROM leave_requests
            ''')
            columns = [col[0] for col in cursor.description]
            leave_requests = []
            for row in cursor.fetchall():
                leave_request = dict(zip(columns, row))
                leave_requests.append(leave_request)
            print(f"Found {len(leave_requests)} leave requests")
            return leave_requests
        except Exception as e:
            print(f"Error getting leave requests: {str(e)}")
            return []
        finally:
            conn.close()

    def get_approved_leave_requests(self):
        """Get all approved leave requests as a list of dictionaries."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # First check if the table exists
            cursor.execute('''
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='leave_requests'
            ''')
            if not cursor.fetchone():
                print("Warning: leave_requests table does not exist. Creating it...")
                self.initialize_database()
            
            # Now get the approved leave requests
            cursor.execute('''
                SELECT id, staff_member, leave_type, start_date, end_date, 
                       duration, reason, status, submitted_date
                FROM leave_requests
                WHERE status = 'Approved'
            ''')
            
            columns = [col[0] for col in cursor.description]
            leave_requests = []
            for row in cursor.fetchall():
                leave_request = dict(zip(columns, row))
                leave_requests.append(leave_request)
            
            print(f"Found {len(leave_requests)} approved leave requests")
            return leave_requests
            
        except Exception as e:
            print(f"Error getting approved leave requests: {str(e)}")
            # Return empty list instead of None to prevent further errors
            return []
        finally:
            if 'conn' in locals():
                conn.close()

    def import_sample_data(self):
        """Import sample staff data if the database is empty."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Check if staff table is empty
            cursor.execute('SELECT COUNT(*) FROM staff')
            if cursor.fetchone()[0] == 0:
                sample_data = [
                    ('John Smith', 'Senior Nurse', 'Emergency,ICU'),
                    ('Mary Johnson', 'Nurse', 'Pediatrics,General'),
                    ('David Wilson', 'Doctor', 'Surgery,Emergency'),
                    ('Sarah Brown', 'Nurse', 'ICU,General'),
                    ('Michael Davis', 'Senior Doctor', 'Emergency,Surgery'),
                    ('Emma Wilson', 'Senior Nurse', 'ICU,Emergency'),
                    ('James Anderson', 'Doctor', 'General,Surgery'),
                    ('Lisa Chen', 'Nurse', 'Pediatrics,Emergency'),
                    ('Robert Taylor', 'Senior Doctor', 'Surgery,ICU'),
                    ('Jennifer Lee', 'Nurse', 'General,Emergency'),
                    ('William White', 'Doctor', 'ICU,Surgery'),
                    ('Maria Garcia', 'Senior Nurse', 'Emergency,General'),
                    ('Moktik', 'Doctor', 'Emergency,General')
                ]
                
                cursor.executemany('''
                    INSERT INTO staff (name, role, skills)
                    VALUES (?, ?, ?)
                ''', sample_data)
                
                conn.commit()
                return True
        except Exception as e:
            print(f"Error importing sample data: {str(e)}")
            return False
        finally:
            conn.close() 