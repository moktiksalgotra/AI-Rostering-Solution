import pandas as pd
import numpy as np
from typing import Dict, List, Optional
import json
from datetime import datetime, timedelta
from utils.database import DatabaseHandler

class DataHandler:
    def __init__(self):
        self.db = DatabaseHandler()
        self.staff_data = self.db.get_all_staff()
        
        # Verify staff data has required columns and proper structure
        required_columns = ['id', 'name', 'role', 'skills']
        if (self.staff_data.empty or 
            not all(col in self.staff_data.columns for col in required_columns) or 
            len(self.staff_data) == 0):
            print("Initializing database with sample data...")
            self.db.import_sample_data()
            self.staff_data = self.db.get_all_staff()
            
            # Double-check the data structure
            if not all(col in self.staff_data.columns for col in required_columns):
                raise ValueError(f"Failed to initialize staff data with required columns: {required_columns}")
        
        self.shift_patterns = None
        
    def load_staff_data(self, file=None):
        """Load staff data from Excel file and store in database."""
        try:
            if file is not None:
                df = pd.read_excel(file)
                # Ensure required columns exist
                required_columns = ['name', 'role', 'skills']
                if not all(col in df.columns for col in required_columns):
                    raise ValueError(f"Excel file must contain columns: {required_columns}")
                
                # Store each staff member in the database
                for _, row in df.iterrows():
                    self.db.add_staff(row['name'], row['role'], row['skills'])
            
            # Refresh staff data from database
            self.staff_data = self.db.get_all_staff()
            
            # Verify the data has the correct structure
            if self.staff_data.empty or not all(col in self.staff_data.columns for col in ['id', 'name', 'role', 'skills']):
                print("Warning: Staff data not properly loaded, reinitializing...")
                self.db.import_sample_data()
                self.staff_data = self.db.get_all_staff()
            
            return self.staff_data
        except Exception as e:
            print(f"Error loading staff data: {str(e)}")
            return None

    def create_sample_staff_data(self):
        """Create and store sample staff data."""
        self.db.import_sample_data()
        self.staff_data = self.db.get_all_staff()
        return self.staff_data

    def add_staff_member(self, name, role, skills):
        """Add a new staff member to the database."""
        if self.db.add_staff(name, role, skills):
            self.staff_data = self.db.get_all_staff()
            return True
        return False

    def update_staff_member(self, staff_id, name, role, skills):
        """Update an existing staff member."""
        if self.db.update_staff(staff_id, name, role, skills):
            self.staff_data = self.db.get_all_staff()
            return True
        return False

    def delete_staff_member(self, staff_id):
        """Delete a staff member from the database."""
        if self.db.delete_staff(staff_id):
            self.staff_data = self.db.get_all_staff()
            return True
        return False

    def save_staff_data(self, file_path: str) -> None:
        """Save staff data to Excel file."""
        if self.staff_data is not None:
            self.staff_data.to_excel(file_path, index=False)
        else:
            raise ValueError("No staff data available to save")

    def create_shift_patterns(self) -> Dict:
        """Create default shift patterns."""
        self.shift_patterns = {
            'Morning': {'start': '07:00', 'end': '15:00'},
            'Evening': {'start': '15:00', 'end': '23:00'},
            'Night': {'start': '23:00', 'end': '07:00'}
        }
        return self.shift_patterns

    def save_roster(self, roster_df: pd.DataFrame, file_path: str) -> None:
        """Save generated roster to Excel file."""
        try:
            roster_df.to_excel(file_path, index=False)
        except Exception as e:
            raise Exception(f"Error saving roster: {str(e)}")

    def get_staff_preferences(self):
        """Get staff shift preferences."""
        preferences = {}
        if self.staff_data is not None:
            for idx, staff in self.staff_data.iterrows():
                # Simple preference assignment based on role
                if 'Senior' in staff['role']:
                    preferences[idx] = {'preferred_shift': 'Morning'}
                elif 'Doctor' in staff['role']:
                    preferences[idx] = {'preferred_shift': 'Evening'}
                else:
                    preferences[idx] = {'preferred_shift': 'Night'}
        return preferences

    def validate_roster(self, roster_df: pd.DataFrame) -> List[str]:
        """Validate roster against business rules and constraints."""
        errors = []
        if roster_df is None:
            errors.append("No roster data provided")
            return errors

        # Check for empty shifts
        empty_shifts = roster_df[roster_df['Staff'].isna() | (roster_df['Staff'] == '')]
        if not empty_shifts.empty:
            errors.append(f"Found {len(empty_shifts)} empty shifts")

        # Check for staff working consecutive shifts
        for staff in self.staff_data['name']:
            staff_shifts = roster_df[roster_df['Staff'].str.contains(staff, na=False)]
            if len(staff_shifts) > 0:
                consecutive_shifts = 0
                for i in range(len(staff_shifts) - 1):
                    if (staff_shifts.iloc[i+1]['Day'] == staff_shifts.iloc[i]['Day'] and 
                        staff_shifts.iloc[i+1]['Shift'] == staff_shifts.iloc[i]['Shift'] + 1):
                        consecutive_shifts += 1
                if consecutive_shifts > 0:
                    errors.append(f"{staff} has {consecutive_shifts} consecutive shifts")

        return errors

    def export_roster_to_json(self, roster_df: pd.DataFrame, file_path: str) -> None:
        """Export roster to JSON format."""
        if roster_df is not None:
            roster_dict = roster_df.to_dict(orient='records')
            with open(file_path, 'w') as f:
                json.dump(roster_dict, f, indent=2)
        else:
            raise ValueError("No roster data available to export") 