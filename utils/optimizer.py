from ortools.sat.python import cp_model
import pandas as pd
from typing import List, Dict, Tuple
import numpy as np
from datetime import datetime, timedelta

class RosterOptimizer:
    def __init__(self):
        self.model = None
        self.solver = None
        self.last_error = None
        self.shift_mapping = {
            'Morning': 0,
            'Evening': 1,
            'Night': 2
        }
        self.debug_info = []

    def _log_debug(self, message: str):
        """Add debug information."""
        self.debug_info.append(message)
        print(f"Debug: {message}")

    def get_last_error(self) -> str:
        """Return the last error message with debug info."""
        if not self.last_error and self.debug_info:
            return f"Optimization failed with the following issues:\n" + "\n".join(self.debug_info)
        return self.last_error if self.last_error else "Unknown error occurred"

    def optimize_roster(
        self,
        staff_data: pd.DataFrame,
        num_days: int,
        shifts_per_day: int,
        min_staff_per_shift: int,
        max_shifts_per_week: int,
        staff_preferences: Dict = None,
        leave_requests: List[Dict] = None
    ) -> Tuple[pd.DataFrame, bool]:
        """
        Generate optimal roster considering staff leaves and preferences.
        """
        try:
            # Reset debug info
            self.debug_info = []
            self.last_error = None

            # Process leave requests
            staff_leaves = {}
            if leave_requests:
                for request in leave_requests:
                    if request['status'] == 'Approved':
                        staff_name = request['staff_member']
                        start_date = datetime.strptime(request['start_date'], '%Y-%m-%d')
                        end_date = datetime.strptime(request['end_date'], '%Y-%m-%d')
                        
                        # Get staff index
                        staff_idx = staff_data[staff_data['name'] == staff_name].index[0]
                        
                        # Mark all days in the leave period
                        current_date = start_date
                        while current_date <= end_date:
                            day_num = (current_date - datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)).days
                            if 0 <= day_num < num_days:
                                if staff_idx not in staff_leaves:
                                    staff_leaves[staff_idx] = set()
                                staff_leaves[staff_idx].add(day_num)
                            current_date += timedelta(days=1)

            # Input validation with detailed messages
            if staff_data is None or staff_data.empty:
                self.last_error = "No staff data provided"
                return None, False

            # Validate input parameters
            if num_days <= 0:
                self.last_error = "Number of days must be positive"
                return None, False
            if shifts_per_day <= 0:
                self.last_error = "Shifts per day must be positive"
                return None, False
            if min_staff_per_shift <= 0:
                self.last_error = "Minimum staff per shift must be positive"
                return None, False
            if max_shifts_per_week <= 0:
                self.last_error = "Maximum shifts per week must be positive"
                return None, False

            num_staff = len(staff_data)
            self._log_debug(f"Total staff members: {num_staff}")

            # Calculate minimum required staff with better error handling
            total_shifts = num_days * shifts_per_day
            total_slots_needed = total_shifts * min_staff_per_shift
            weeks_in_period = (num_days + 6) // 7
            max_available_slots = num_staff * max_shifts_per_week * weeks_in_period

            self._log_debug(f"Total shifts needed: {total_shifts}")
            self._log_debug(f"Total staff slots needed: {total_slots_needed}")
            self._log_debug(f"Maximum available staff slots: {max_available_slots}")
            self._log_debug(f"Weeks in period: {weeks_in_period}")

            if total_slots_needed > max_available_slots:
                self.last_error = (
                    f"Not enough staff capacity. Need {total_slots_needed} slots but only have {max_available_slots} available.\n"
                    f"Current parameters:\n"
                    f"- Staff members: {num_staff}\n"
                    f"- Days: {num_days}\n"
                    f"- Shifts per day: {shifts_per_day}\n"
                    f"- Min staff per shift: {min_staff_per_shift}\n"
                    f"- Max shifts per week: {max_shifts_per_week}\n"
                    f"Suggestions:\n"
                    f"1. Increase staff members (need at least {(total_slots_needed // max_shifts_per_week) + 1})\n"
                    f"2. Reduce min staff per shift (currently {min_staff_per_shift})\n"
                    f"3. Increase max shifts per week (currently {max_shifts_per_week})"
                )
                return None, False

            # Initialize model with more robust error handling
            try:
                self.model = cp_model.CpModel()
                self.solver = cp_model.CpSolver()
            except Exception as e:
                self.last_error = f"Failed to initialize optimization model: {str(e)}"
                return None, False

            # Create shift variables with leave constraints
            shifts = {}
            for staff in range(num_staff):
                for day in range(num_days):
                    # Check if staff is on leave
                    is_on_leave = staff in staff_leaves and day in staff_leaves[staff]
                    
                    for shift in range(shifts_per_day):
                        shifts[(staff, day, shift)] = self.model.NewBoolVar(
                            f'shift_s{staff}_d{day}_sh{shift}'
                        )
                        # If staff is on leave, they cannot be assigned any shifts
                        if is_on_leave:
                            self.model.Add(shifts[(staff, day, shift)] == 0)

            # Objective terms for optimization
            objective_terms = []

            # Constraint 1: Staff requirements per shift (with soft constraints)
            for day in range(num_days):
                for shift in range(shifts_per_day):
                    shift_staff = []
                    for staff in range(num_staff):
                        shift_staff.append(shifts[(staff, day, shift)])
                    
                    # Soft constraint for minimum staff with higher flexibility
                    min_staff_slack = self.model.NewIntVar(0, min_staff_per_shift, f'min_staff_slack_d{day}_s{shift}')
                    self.model.Add(sum(shift_staff) + min_staff_slack >= min_staff_per_shift)
                    objective_terms.append(min_staff_slack * 1000)  # High penalty for understaffing

            # Constraint 2: Maximum shifts per staff member (with soft weekly limits)
            for staff in range(num_staff):
                # Daily shifts constraint (hard constraint)
                for day in range(num_days):
                    day_shifts = []
                    for shift in range(shifts_per_day):
                        day_shifts.append(shifts[(staff, day, shift)])
                    self.model.Add(sum(day_shifts) <= 1)  # Max one shift per day

                # Weekly shifts constraint with more flexible soft limit
                for week in range(weeks_in_period):
                    week_start = week * 7
                    week_end = min((week + 1) * 7, num_days)
                    week_shifts = []
                    for day in range(week_start, week_end):
                        for shift in range(shifts_per_day):
                            week_shifts.append(shifts[(staff, day, shift)])
                    
                    # Soft constraint for weekly maximum with more flexibility
                    week_slack = self.model.NewIntVar(0, 3, f'week_slack_s{staff}_w{week}')  # Allow up to 3 extra shifts if needed
                    self.model.Add(sum(week_shifts) <= max_shifts_per_week + week_slack)
                    objective_terms.append(week_slack * 500)

            # Constraint 3: Rest periods (with more flexibility)
            for staff in range(num_staff):
                for day in range(num_days - 1):  # Modified to avoid index error
                    # No consecutive shifts (soft constraint)
                    evening_shift = shifts.get((staff, day, 1), None)
                    night_shift = shifts.get((staff, day, 2), None)
                    next_morning = shifts.get((staff, day + 1, 0), None)
                    
                    if all(v is not None for v in [evening_shift, night_shift, next_morning]):
                        rest_slack = self.model.NewBoolVar(f'rest_slack_s{staff}_d{day}')
                        self.model.Add(evening_shift + night_shift + next_morning <= 1 + rest_slack)
                        objective_terms.append(rest_slack * 750)  # High penalty but not as high as understaffing

            # Staff preferences (soft constraints with lower penalty)
            if staff_preferences:
                for staff_id, prefs in staff_preferences.items():
                    if isinstance(staff_id, int) and 0 <= staff_id < num_staff:
                        preferred_shift = prefs.get('preferred_shift')
                        if preferred_shift in self.shift_mapping:
                            shift_num = self.shift_mapping[preferred_shift]
                            for day in range(num_days):
                                pref_var = self.model.NewBoolVar(f'pref_s{staff_id}_d{day}')
                                self.model.Add(shifts[(staff_id, day, shift_num)] == 1).OnlyEnforceIf(pref_var)
                                objective_terms.append(pref_var * 10)  # Lower penalty for preferences

            # Set objective with error handling
            if objective_terms:
                try:
                    self.model.Minimize(sum(objective_terms))
                except Exception as e:
                    self.last_error = f"Failed to set optimization objective: {str(e)}"
                    return None, False

            # Solve with parameters and timeout
            self.solver.parameters.max_time_in_seconds = 120.0  # Increased timeout
            self.solver.parameters.num_search_workers = 8
            self.solver.parameters.log_search_progress = True

            self._log_debug("Starting optimization...")
            try:
                status = self.solver.Solve(self.model)
                self._log_debug(f"Optimization status: {status}")
            except Exception as e:
                self.last_error = f"Solver failed: {str(e)}"
                return None, False

            if status == cp_model.OPTIMAL or status == cp_model.FEASIBLE:
                # Convert solution to DataFrame
                roster_data = []
                total_assignments = 0

                for day in range(num_days):
                    date = (datetime.now() + timedelta(days=day)).strftime('%Y-%m-%d')
                    for shift in range(shifts_per_day):
                        staff_on_shift = []
                        for staff in range(num_staff):
                            # Skip staff on leave
                            if staff in staff_leaves and day in staff_leaves[staff]:
                                continue
                            
                            if self.solver.Value(shifts[(staff, day, shift)]) == 1:
                                staff_on_shift.append(staff_data.iloc[staff]['name'])
                                total_assignments += 1

                        if staff_on_shift:
                            roster_data.append({
                                'Day': day + 1,
                                'Date': date,
                                'Shift': shift + 1,
                                'Shift_Time': self._get_shift_time(shift),
                                'Staff': ', '.join(staff_on_shift),
                                'Staff_Count': len(staff_on_shift)
                            })

                self._log_debug(f"Total assignments made: {total_assignments}")
                
                if not roster_data:
                    self.last_error = "No valid assignments found in the solution"
                    return None, False

                roster_df = pd.DataFrame(roster_data)
                return roster_df, True

            self.last_error = (
                f"Could not find a feasible solution. Status: {status}. "
                f"This might be due to conflicting constraints, insufficient staff capacity, or too many approved leaves."
            )
            return None, False

        except Exception as e:
            self.last_error = f"Optimization error: {str(e)}"
            self._log_debug(f"Exception details: {str(e)}")
            return None, False

    def _get_shift_time(self, shift: int) -> str:
        """Convert shift number to time range."""
        shift_times = {
            0: "07:00-15:00",
            1: "15:00-23:00",
            2: "23:00-07:00"
        }
        return shift_times.get(shift, "Unknown")

    def calculate_roster_metrics(self, roster_df: pd.DataFrame) -> Dict:
        """Calculate various metrics for the generated roster."""
        try:
            if roster_df is None or roster_df.empty:
                return {
                    'total_shifts': 0,
                    'avg_staff_per_shift': 0,
                    'coverage': 0,
                    'staff_utilization': 0,
                    'preference_satisfaction': 0
                }

            metrics = {
                'total_shifts': len(roster_df),
                'avg_staff_per_shift': roster_df['Staff_Count'].mean(),
                'coverage': (roster_df['Staff_Count'] > 0).mean() * 100,
                'staff_utilization': self._calculate_staff_utilization(roster_df),
                'preference_satisfaction': self._calculate_preference_satisfaction(roster_df)
            }
            return metrics
        except Exception as e:
            print(f"Error calculating metrics: {str(e)}")
            return {
                'total_shifts': 0,
                'avg_staff_per_shift': 0,
                'coverage': 0,
                'staff_utilization': 0,
                'preference_satisfaction': 0
            }

    def _calculate_staff_utilization(self, roster_df: pd.DataFrame) -> float:
        """Calculate staff utilization percentage."""
        if roster_df is None or roster_df.empty:
            return 0.0
        total_possible_shifts = len(roster_df)
        actual_shifts = roster_df['Staff_Count'].sum()
        return (actual_shifts / total_possible_shifts) * 100

    def _calculate_preference_satisfaction(self, roster_df: pd.DataFrame) -> float:
        """Calculate how well staff preferences were satisfied."""
        try:
            if roster_df is None or roster_df.empty:
                return 0.0
            
            total_assignments = 0
            preferred_assignments = 0
            
            for _, row in roster_df.iterrows():
                staff_list = [s.strip() for s in row['Staff'].split(',')]
                shift_time = row['Shift_Time']
                
                for staff in staff_list:
                    total_assignments += 1
                    # Check if this shift matches the staff member's preferred shift
                    # This is a simplified calculation - you might want to enhance this
                    if (shift_time.startswith('07:00') and 'Morning' in staff) or \
                       (shift_time.startswith('15:00') and 'Evening' in staff) or \
                       (shift_time.startswith('23:00') and 'Night' in staff):
                        preferred_assignments += 1
            
            return (preferred_assignments / total_assignments * 100) if total_assignments > 0 else 0.0
        except Exception as e:
            print(f"Error calculating preference satisfaction: {str(e)}")
            return 0.0 