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
                    status TEXT DEFAULT 'Approved',
                    submitted_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Create roster table if it doesn't exist
            print("Creating roster table if not exists...")
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS roster (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE NOT NULL,
                    weekday TEXT NOT NULL,
                    shift INTEGER NOT NULL,
                    shift_time TEXT NOT NULL,
                    staff TEXT NOT NULL,
                    staff_count INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Verify tables exist
            print("Verifying tables...")
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            print(f"Found tables: {[table[0] for table in tables]}")

            conn.commit()
            print("Database initialization completed successfully.")
            
            # Fix any existing pending leave requests
            self.fix_pending_leave_requests()
            
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
        conn = None
        try:
            print(f"[DEBUG] Attempting to delete staff with id: {staff_id}")
            conn = self.get_connection()
            
            # Start transaction
            conn.execute("BEGIN IMMEDIATE TRANSACTION")
            
            cursor = conn.cursor()
            
            # First check if staff exists and get their details
            cursor.execute('SELECT name, role FROM staff WHERE id = ?', (staff_id,))
            staff = cursor.fetchone()
            if not staff:
                print(f"[DEBUG] No staff found with id: {staff_id}")
                if conn:
                    conn.rollback()
                return False
                
            staff_name, staff_role = staff
            print(f"[DEBUG] Found staff member: {staff_name} ({staff_role})")
                
            # Check if staff has any active leave requests
            cursor.execute('SELECT COUNT(*) FROM leave_requests WHERE staff_member = ? AND end_date >= date("now")', (staff_name,))
            active_leaves = cursor.fetchone()[0]
            if active_leaves > 0:
                print(f"[DEBUG] Staff has {active_leaves} active leave requests")
                print(f"[DEBUG] Proceeding with deletion and cleaning up leave requests")
                
            # Delete any leave requests for this staff member
            cursor.execute('DELETE FROM leave_requests WHERE staff_member = ?', (staff_name,))
            leaves_deleted = cursor.rowcount
            print(f"[DEBUG] Deleted {leaves_deleted} leave requests")
            
            # Now delete the staff member
            cursor.execute('DELETE FROM staff WHERE id = ?', (staff_id,))
            staff_deleted = cursor.rowcount
            print(f"[DEBUG] Staff deletion affected {staff_deleted} rows")
            
            if staff_deleted > 0:
                # Commit transaction only if we actually deleted something
                conn.commit()
                print(f"[DEBUG] Successfully deleted staff member: {staff_name} ({staff_role})")
                return True
            else:
                # Something went wrong, rollback
                conn.rollback()
                print(f"[DEBUG] Failed to delete staff member: no rows affected")
                return False
            
        except sqlite3.Error as e:
            print(f"[DEBUG] SQLite error deleting staff: {str(e)}")
            if conn:
                conn.rollback()
            return False
        except Exception as e:
            print(f"[DEBUG] Unexpected error deleting staff: {str(e)}")
            if conn:
                conn.rollback()
            return False
        finally:
            if conn:
                if conn.in_transaction:
                    conn.rollback()
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
                (staff_member, leave_type, start_date, end_date, duration, reason, status)
                VALUES (?, ?, ?, ?, ?, ?, 'Approved')
            ''', (staff_member, leave_type, start_date, end_date, duration, reason))
            conn.commit()
            print("Leave request added successfully with Approved status")
            return True
        except Exception as e:
            print(f"Error adding leave request: {str(e)}")
            return False
        finally:
            conn.close()

    def update_leave_request(self, request_id, status, comment=""):
        """Update leave request status and add comment."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # First, let's add the comment column if it doesn't exist
            try:
                cursor.execute('ALTER TABLE leave_requests ADD COLUMN comment TEXT')
                conn.commit()
            except sqlite3.OperationalError:
                # Column already exists, ignore the error
                pass
            
            cursor.execute('''
                UPDATE leave_requests 
                SET status = ?, comment = ?
                WHERE id = ?
            ''', (status, comment, request_id))
            conn.commit()
            return True
        except Exception as e:
            print(f"Error updating leave request: {str(e)}")
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

    def get_leave_requests(self, staff_name=None, status=None, period=None):
        """Get leave requests with optional filtering."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Build the query with optional filters
            query = '''
                SELECT id, staff_member, leave_type, start_date, end_date, 
                       duration, reason, status, submitted_date
                FROM leave_requests
                WHERE 1=1
            '''
            params = []
            
            # Filter by staff name
            if staff_name and staff_name != "ALL":
                query += " AND staff_member = ?"
                params.append(staff_name)
            
            # Filter by status
            if status and status != "ALL":
                query += " AND status = ?"
                params.append(status)
            
            # Filter by period
            if period and period != "ALL":
                current_date = datetime.now().date()
                if period == "Past":
                    query += " AND end_date < ?"
                    params.append(current_date.isoformat())
                elif period == "Current":
                    query += " AND start_date <= ? AND end_date >= ?"
                    params.append(current_date.isoformat())
                    params.append(current_date.isoformat())
                elif period == "Future":
                    query += " AND start_date > ?"
                    params.append(current_date.isoformat())
            
            cursor.execute(query, params)
            
            columns = [col[0] for col in cursor.description]
            leave_requests = []
            for row in cursor.fetchall():
                leave_request = dict(zip(columns, row))
                # Add staff_name field for compatibility
                leave_request['staff_name'] = leave_request['staff_member']
                leave_requests.append(leave_request)
            
            print(f"Found {len(leave_requests)} leave requests matching criteria")
            return leave_requests
            
        except Exception as e:
            print(f"Error getting leave requests: {str(e)}")
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
                    ('Moktik', 'Doctor', 'Emergency,General'),
                    ('Gagan', 'Doctor', 'ICU,Surgery')
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

    def reset_leave_requests(self):
        """Reset leave requests table - clear all leave requests while keeping staff data intact."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Clear all leave requests
            cursor.execute('DELETE FROM leave_requests')
            conn.commit()
            
            print("Leave requests table has been reset successfully.")
            return True
        except Exception as e:
            print(f"Error resetting leave requests: {str(e)}")
            return False
        finally:
            conn.close()

    def fix_pending_leave_requests(self):
        """Fix any pending leave requests by updating them to approved status."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Check if there are any pending leave requests
            cursor.execute('SELECT COUNT(*) FROM leave_requests WHERE status = "Pending"')
            pending_count = cursor.fetchone()[0]
            
            if pending_count > 0:
                print(f"Found {pending_count} pending leave requests. Updating them to approved status...")
                
                # Update all pending requests to approved
                cursor.execute('''
                    UPDATE leave_requests 
                    SET status = 'Approved'
                    WHERE status = 'Pending'
                ''')
                conn.commit()
                
                print(f"Successfully updated {pending_count} pending leave requests to approved status.")
                return True
            else:
                print("No pending leave requests found.")
                return True
                
        except Exception as e:
            print(f"Error fixing pending leave requests: {str(e)}")
            return False
        finally:
            conn.close()

    def reset_database(self):
        """Reset the entire database and re-import sample data."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Drop existing tables
            cursor.execute('DROP TABLE IF EXISTS staff')
            cursor.execute('DROP TABLE IF EXISTS leave_requests')
            cursor.execute('DROP TABLE IF EXISTS roster')  # Add roster table to reset
            
            # Recreate tables
            self.initialize_database()
            
            # Import sample data
            self.import_sample_data()
            
            conn.commit()
            print("Database reset successfully with sample data.")
            return True
        except Exception as e:
            print(f"Error resetting database: {str(e)}")
            return False
        finally:
            conn.close()

    def clear_roster(self):
        """Clear all roster data from the database."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('DELETE FROM roster')
            conn.commit()
            print("Roster data cleared successfully.")
            return True
        except Exception as e:
            print(f"Error clearing roster data: {str(e)}")
            return False
        finally:
            conn.close()

    def save_roster(self, roster_df):
        """Save roster data to the database."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Clear existing roster data
            cursor.execute('DELETE FROM roster')
            
            # Insert new roster data
            for _, row in roster_df.iterrows():
                cursor.execute('''
                    INSERT INTO roster (date, weekday, shift, shift_time, staff, staff_count)
                    VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    row['Date'],
                    row['Weekday'],
                    row['Shift'],
                    row['Shift Time'],
                    row['Staff'],
                    row['Staff_Count']
                ))
            
            conn.commit()
            return True
        except Exception as e:
            print(f"Error saving roster: {str(e)}")
            return False
        finally:
            conn.close()

    def get_roster(self):
        """Get roster data from the database."""
        try:
            conn = self.get_connection()
            query = '''
                SELECT 
                    date as Date,
                    weekday as Weekday,
                    shift as Shift,
                    shift_time as "Shift Time",
                    staff as Staff,
                    staff_count as Staff_Count
                FROM roster
                ORDER BY date, shift
            '''
            df = pd.read_sql_query(query, conn)
            return df
        except Exception as e:
            print(f"Error getting roster: {str(e)}")
            return pd.DataFrame()
        finally:
            conn.close()

    def get_staff_roster(self, staff_name=None, date=None):
        """Get roster data for a specific staff member and/or date."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            query = '''
                SELECT 
                    date as Date,
                    weekday as Weekday,
                    shift_time as "Shift Time",
                    staff as Staff
                FROM roster
                WHERE 1=1
            '''
            params = []
            
            if staff_name:
                query += " AND staff LIKE ?"
                params.append(f"%{staff_name}%")
            
            if date:
                query += " AND date = ?"
                params.append(date)
            
            query += " ORDER BY date, shift"
            
            cursor.execute(query, params)
            columns = [col[0] for col in cursor.description]
            roster = []
            for row in cursor.fetchall():
                roster_entry = dict(zip(columns, row))
                roster.append(roster_entry)
            
            return roster
        except Exception as e:
            print(f"Error getting staff roster: {str(e)}")
            return []
        finally:
            conn.close()

    def delete_leave_request(self, request_id):
        """Delete a leave request by its ID."""
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('DELETE FROM leave_requests WHERE id = ?', (request_id,))
            conn.commit()
            return cursor.rowcount > 0
        except Exception as e:
            print(f"Error deleting leave request: {str(e)}")
            return False
        finally:
            conn.close() 