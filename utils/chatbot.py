import requests
import json
from typing import List, Dict, Any
import pandas as pd
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class RosteringChatbot:
    def __init__(self, api_key: str = None, data_handler=None, optimizer=None):
        self.api_key = api_key or os.getenv('OPENROUTER_API_KEY')
        print(f"Debug - API Key found: {'Yes' if self.api_key else 'No'}")
        print(f"Debug - API Key length: {len(self.api_key) if self.api_key else 0}")
        if not self.api_key:
            raise ValueError("OpenRouter API key not found. Please set OPENROUTER_API_KEY in .env file")
        self.data_handler = data_handler
        self.optimizer = optimizer
        self.conversation_history = []
        self.api_url = "https://openrouter.ai/api/v1/chat/completions"
    
    def chat(self, user_input: str) -> str:
        """
        Process user input and return response.
        Args:
            user_input: The user's input text
        Returns:
            str: The chatbot's response
        """
        try:
            # Add current context to conversation
            context = self._get_context()
            
            # Prepare messages for the API call
            messages = [
                {"role": "system", "content": self._get_system_prompt()},
                {"role": "system", "content": f"Current context:\n{context}"},
                *self.conversation_history,
                {"role": "user", "content": user_input}
            ]
            
            # Get AI response
            response = self._call_openrouter(messages)
            
            # Clean up HTML-like elements from response
            response = response.replace('<span class=\'bubble-tail\'></span>', '')
            response = response.replace('<div class=\'chat-timestamp\'>', '')
            response = response.replace('</div>', '')
            response = response.strip()
            
            # Parse and execute any actions in the response
            action_data = self._parse_action(response)
            
            # Debug information
            print(f"Parsed action: {action_data}")
            
            # Execute action and get result
            result = self._execute_action(action_data)
            
            # Add to conversation history
            self.conversation_history.append({"role": "user", "content": user_input})
            
            # Format final response based on action result
            final_response = response
            if action_data["action"] != "NONE" and action_data["action"] != "ERROR":
                final_response = f"{response}\n\nAction Result: {result}"
            elif action_data["action"] == "ERROR":
                final_response = f"{response}\n\nError: {result}"
            
            # Add assistant response to history
            self.conversation_history.append({"role": "assistant", "content": final_response})
            
            # Keep conversation history manageable
            if len(self.conversation_history) > 10:
                self.conversation_history = self.conversation_history[-10:]
            
            return final_response
            
        except Exception as e:
            error_msg = f"An error occurred: {str(e)}\nPlease try again with your request."
            self.conversation_history.append({"role": "assistant", "content": error_msg})
            return error_msg

    def _get_system_prompt(self) -> str:
        """Get the system prompt for the chatbot."""
        return """You are an AI assistant integrated with a hospital roster management system. You must EXACTLY follow these formats for actions:

        To add staff, you must respond *only* with the following lines and nothing else before or after if you are performing this action:
        Let me help you add a new staff member.
        ADD_STAFF
        Name: [staff name]
        Role: [exact role - must be one of: Senior Doctor, Doctor, Senior Nurse, Nurse, Specialist]
        Skills: [comma-separated list of: Emergency, ICU, General, Surgery, Pediatrics]

        To delete staff, you must respond *only* with the following line and nothing else before or after if you are performing this action:
        I will help you remove this staff member.
        DELETE_STAFF: [exact staff name]

        To add leave, you must respond *only* with the following lines and nothing else before or after if you are performing this action:
        I will help you submit a leave request.
        ADD_LEAVE
        Staff: [exact staff name]
        Type: [must be one of: Annual Leave, Sick Leave, Personal Leave, Emergency Leave, Study Leave]
        Start: [YYYY-MM-DD]
        End: [YYYY-MM-DD]
        Reason: [reason for leave]
        Priority: [must be one of: High, Medium, Low]

        To check upcoming leave, you must respond *only* with the following lines and nothing else before or after if you are performing this action:
        I will help you check upcoming leave.
        CHECK_LEAVE
        Days: [number of days to look ahead]
        Staff: [exact staff name or "ALL"]

        To view leave requests, you must respond *only* with the following lines and nothing else before or after if you are performing this action:
        I will help you view leave requests.
        VIEW_LEAVE
        Staff: [exact staff name or "ALL"]
        Status: [must be one of: Pending, Approved, Rejected, ALL]
        Period: [must be one of: Past, Current, Future, ALL]

        To update leave status, you must respond *only* with the following lines and nothing else before or after if you are performing this action:
        I will help you update the leave request status.
        UPDATE_LEAVE
        Request ID: [leave request ID]
        Status: [must be one of: Approved, Rejected]
        Comment: [optional comment for the status update]

        To generate a roster, you must respond *only* with the following lines and nothing else before or after if you are performing this action:
        I will help you generate a roster.
        GENERATE_ROSTER
        Days: [number of days]
        Shifts: [number of shifts per day]
        Min Staff: [minimum staff per shift]
        Max Shifts: [maximum shifts per week]

        For any other queries, or if you are providing information or asking for clarification, provide a helpful response *without* including any of the action keywords (ADD_STAFF, DELETE_STAFF, ADD_LEAVE, CHECK_LEAVE, VIEW_LEAVE, UPDATE_LEAVE, GENERATE_ROSTER) or their parameter formats (Name:, Role:, Staff:, etc.) in your response. 
        If the user's query is short, unclear, ambiguous, or a simple negative/affirmative response (e.g., "no", "yes", "ok", "not sure"), do NOT perform any action. Instead, ask for clarification (e.g., "Okay, what would you like to do next?" or "Understood. How can I assist you further?"), provide a general greeting, or wait for a more specific command. Do NOT include examples of command formats in these clarification messages.
        Only use an action command block (as defined above) if the user's intent is clear and they have explicitly requested an action and provided all necessary information. 
        Never modify the format of these action command blocks.
        Always verify names against the current staff list before actions.
        """

    def _get_context(self) -> str:
        """Get current context about staff and leave data."""
        try:
            staff_df = self.data_handler.staff_data
            staff_info = "Current Staff:\n"
            for _, staff in staff_df.iterrows():
                staff_info += f"- {staff['name']} ({staff['role']}): {staff['skills']}\n"
            
            return staff_info
        except Exception as e:
            return f"Error getting context: {str(e)}"

    def _call_openrouter(self, messages: List[Dict[str, str]]) -> str:
        """Make API call to OpenRouter."""
        print(f"Debug - Making API call with key: {self.api_key[:10]}...")  # Only print first 10 chars for security
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:8501",  # For OpenRouter tracking
        }
        
        data = {
            "model": "mistralai/mistral-7b-instruct",  # Using Mistral as it's powerful and cost-effective
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 1000
        }
        
        try:
            response = requests.post(self.api_url, headers=headers, json=data)
            response.raise_for_status()
            return response.json()['choices'][0]['message']['content']
        except Exception as e:
            return f"Error calling AI model: {str(e)}"

    def _parse_action(self, response: str) -> Dict[str, Any]:
        """Parse the AI response to extract actions and parameters."""
        try:
            # Initialize variables
            name = role = skills = None
            leave_data = {}
            roster_data = {}
            view_leave_data = {}
            update_leave_data = {}
            check_leave_data = {}
            
            lines = [line.strip() for line in response.split('\n') if line.strip()]
            
            action_type = "NONE"
            action_params = {}
            
            # Find the primary action keyword
            action_keyword_found = False
            for i, line in enumerate(lines):
                if line == "ADD_STAFF" and not action_keyword_found:
                    action_type = "ADD_STAFF"
                    action_keyword_found = True
                    # Parse parameters for ADD_STAFF from subsequent lines
                    for j in range(i + 1, len(lines)):
                        sub_line = lines[j]
                        if sub_line.startswith("Name:"):
                            name = sub_line.replace("Name:", "").strip()
                        elif sub_line.startswith("Role:"):
                            role = sub_line.replace("Role:", "").strip()
                        elif sub_line.startswith("Skills:"):
                            skills = sub_line.replace("Skills:", "").strip()
                        # Stop parsing if another command keyword or unrelated text is found
                        elif sub_line in ["DELETE_STAFF:", "ADD_LEAVE", "GENERATE_ROSTER", "VIEW_LEAVE", "UPDATE_LEAVE"] or not (sub_line.startswith("Name:") or sub_line.startswith("Role:") or sub_line.startswith("Skills:")):
                            break
                    if all([name, role, skills]):
                        valid_roles = ["Senior Doctor", "Doctor", "Senior Nurse", "Nurse", "Specialist"]
                        valid_skills = ["Emergency", "ICU", "General", "Surgery", "Pediatrics"]
                        if role not in valid_roles:
                            return {"action": "ERROR", "params": {"error": f"Invalid role. Must be one of: {', '.join(valid_roles)}"}}
                        skills_list = [s.strip() for s in skills.split(',')]
                        if not all(skill in valid_skills for skill in skills_list):
                            return {"action": "ERROR", "params": {"error": f"Invalid skills. Must be from: {', '.join(valid_skills)}"}}
                        action_params = {"name": name, "role": role, "skills": skills}
                    else:
                        missing = [field for field, val in [("name", name), ("role", role), ("skills", skills)] if not val]
                        return {"action": "ERROR", "params": {"error": f"Missing required staff information: {', '.join(missing)} for ADD_STAFF."}}
                    break # Found and processed ADD_STAFF

                elif line.startswith("DELETE_STAFF:") and not action_keyword_found:
                    action_type = "DELETE_STAFF"
                    action_keyword_found = True
                    name = line.split("DELETE_STAFF:")[1].strip()
                    if name:
                        action_params = {"name": name}
                    else:
                        return {"action": "ERROR", "params": {"error": "Missing name for DELETE_STAFF."}}
                    break # Found and processed DELETE_STAFF

                elif line == "ADD_LEAVE" and not action_keyword_found:
                    action_type = "ADD_LEAVE"
                    action_keyword_found = True
                    # Parse parameters for ADD_LEAVE from subsequent lines
                    for j in range(i + 1, len(lines)):
                        sub_line = lines[j]
                        if sub_line.startswith("Staff:"):
                            leave_data["staff_member"] = sub_line.split("Staff:")[1].strip()
                        elif sub_line.startswith("Type:"):
                            leave_data["leave_type"] = sub_line.split("Type:")[1].strip()
                        elif sub_line.startswith("Start:"):
                            leave_data["start_date"] = sub_line.split("Start:")[1].strip()
                        elif sub_line.startswith("End:"):
                            leave_data["end_date"] = sub_line.split("End:")[1].strip()
                        elif sub_line.startswith("Reason:"):
                            leave_data["reason"] = sub_line.split("Reason:")[1].strip()
                        elif sub_line.startswith("Priority:"):
                            leave_data["priority"] = sub_line.split("Priority:")[1].strip()
                        # Stop parsing if another command keyword or unrelated text is found
                        elif sub_line in ["ADD_STAFF", "DELETE_STAFF:", "GENERATE_ROSTER", "VIEW_LEAVE", "UPDATE_LEAVE"]:
                            break
                    required_fields = ["staff_member", "leave_type", "start_date", "end_date", "priority"]
                    if all(field in leave_data for field in required_fields):
                        # Validate leave type and priority
                        valid_leave_types = ["Annual Leave", "Sick Leave", "Personal Leave", "Emergency Leave", "Study Leave"]
                        valid_priorities = ["High", "Medium", "Low"]
                        if leave_data["leave_type"] not in valid_leave_types:
                            return {"action": "ERROR", "params": {"error": f"Invalid leave type. Must be one of: {', '.join(valid_leave_types)}"}}
                        if leave_data["priority"] not in valid_priorities:
                            return {"action": "ERROR", "params": {"error": f"Invalid priority. Must be one of: {', '.join(valid_priorities)}"}}
                        action_params = leave_data
                    else:
                        missing = [field for field in required_fields if field not in leave_data]
                        return {"action": "ERROR", "params": {"error": f"Missing required leave information: {', '.join(missing)} for ADD_LEAVE."}}
                    break

                elif line == "VIEW_LEAVE" and not action_keyword_found:
                    action_type = "VIEW_LEAVE"
                    action_keyword_found = True
                    # Parse parameters for VIEW_LEAVE from subsequent lines
                    for j in range(i + 1, len(lines)):
                        sub_line = lines[j]
                        if sub_line.startswith("Staff:"):
                            view_leave_data["staff"] = sub_line.split("Staff:")[1].strip()
                        elif sub_line.startswith("Status:"):
                            view_leave_data["status"] = sub_line.split("Status:")[1].strip()
                        elif sub_line.startswith("Period:"):
                            view_leave_data["period"] = sub_line.split("Period:")[1].strip()
                        # Stop parsing if another command keyword or unrelated text is found
                        elif sub_line in ["ADD_STAFF", "DELETE_STAFF:", "GENERATE_ROSTER", "ADD_LEAVE", "UPDATE_LEAVE"]:
                            break
                    required_fields = ["staff", "status", "period"]
                    if all(field in view_leave_data for field in required_fields):
                        # Validate status and period
                        valid_statuses = ["Pending", "Approved", "Rejected", "ALL"]
                        valid_periods = ["Past", "Current", "Future", "ALL"]
                        if view_leave_data["status"] not in valid_statuses:
                            return {"action": "ERROR", "params": {"error": f"Invalid status. Must be one of: {', '.join(valid_statuses)}"}}
                        if view_leave_data["period"] not in valid_periods:
                            return {"action": "ERROR", "params": {"error": f"Invalid period. Must be one of: {', '.join(valid_periods)}"}}
                        action_params = view_leave_data
                    else:
                        missing = [field for field in required_fields if field not in view_leave_data]
                        return {"action": "ERROR", "params": {"error": f"Missing required view leave information: {', '.join(missing)} for VIEW_LEAVE."}}
                    break

                elif line == "UPDATE_LEAVE" and not action_keyword_found:
                    action_type = "UPDATE_LEAVE"
                    action_keyword_found = True
                    # Parse parameters for UPDATE_LEAVE from subsequent lines
                    for j in range(i + 1, len(lines)):
                        sub_line = lines[j]
                        if sub_line.startswith("Request ID:"):
                            update_leave_data["request_id"] = sub_line.split("Request ID:")[1].strip()
                        elif sub_line.startswith("Status:"):
                            update_leave_data["status"] = sub_line.split("Status:")[1].strip()
                        elif sub_line.startswith("Comment:"):
                            update_leave_data["comment"] = sub_line.split("Comment:")[1].strip()
                        # Stop parsing if another command keyword or unrelated text is found
                        elif sub_line in ["ADD_STAFF", "DELETE_STAFF:", "GENERATE_ROSTER", "ADD_LEAVE", "VIEW_LEAVE"]:
                            break
                    required_fields = ["request_id", "status"]
                    if all(field in update_leave_data for field in required_fields):
                        # Validate status
                        valid_statuses = ["Approved", "Rejected"]
                        if update_leave_data["status"] not in valid_statuses:
                            return {"action": "ERROR", "params": {"error": f"Invalid status. Must be one of: {', '.join(valid_statuses)}"}}
                        action_params = update_leave_data
                    else:
                        missing = [field for field in required_fields if field not in update_leave_data]
                        return {"action": "ERROR", "params": {"error": f"Missing required update leave information: {', '.join(missing)} for UPDATE_LEAVE."}}
                    break

                elif line == "GENERATE_ROSTER" and not action_keyword_found:
                    action_type = "GENERATE_ROSTER"
                    action_keyword_found = True
                    # Parse parameters for GENERATE_ROSTER from subsequent lines
                    for j in range(i + 1, len(lines)):
                        sub_line = lines[j]
                        if sub_line.startswith("Days:"):
                            roster_data["num_days"] = int(sub_line.split("Days:")[1].strip())
                        elif sub_line.startswith("Shifts:"):
                            roster_data["shifts_per_day"] = int(sub_line.split("Shifts:")[1].strip())
                        elif sub_line.startswith("Min Staff:"):
                            roster_data["min_staff_per_shift"] = int(sub_line.split("Min Staff:")[1].strip())
                        elif sub_line.startswith("Max Shifts:"):
                            roster_data["max_shifts_per_week"] = int(sub_line.split("Max Shifts:")[1].strip())
                        # Stop parsing if another command keyword or unrelated text is found
                        elif sub_line in ["ADD_STAFF", "DELETE_STAFF:", "ADD_LEAVE", "VIEW_LEAVE", "UPDATE_LEAVE"] or not (sub_line.startswith("Days:") or sub_line.startswith("Shifts:") or sub_line.startswith("Min Staff:") or sub_line.startswith("Max Shifts:")):
                            break
                    required_fields = ["num_days", "shifts_per_day", "min_staff_per_shift", "max_shifts_per_week"]
                    if all(field in roster_data for field in required_fields):
                        action_params = roster_data
                    else:
                        missing = [field for field in required_fields if field not in roster_data]
                        return {"action": "ERROR", "params": {"error": f"Missing required roster information: {', '.join(missing)} for GENERATE_ROSTER."}}
                    break # Found and processed GENERATE_ROSTER

                elif line == "CHECK_LEAVE" and not action_keyword_found:
                    action_type = "CHECK_LEAVE"
                    action_keyword_found = True
                    # Parse parameters for CHECK_LEAVE from subsequent lines
                    for j in range(i + 1, len(lines)):
                        sub_line = lines[j]
                        if sub_line.startswith("Days:"):
                            check_leave_data["days"] = int(sub_line.split("Days:")[1].strip())
                        elif sub_line.startswith("Staff:"):
                            check_leave_data["staff"] = sub_line.split("Staff:")[1].strip()
                        # Stop parsing if another command keyword or unrelated text is found
                        elif sub_line in ["ADD_STAFF", "DELETE_STAFF:", "GENERATE_ROSTER", "ADD_LEAVE", "VIEW_LEAVE", "UPDATE_LEAVE"]:
                            break
                    required_fields = ["days", "staff"]
                    if all(field in check_leave_data for field in required_fields):
                        action_params = check_leave_data
                    else:
                        missing = [field for field in required_fields if field not in check_leave_data]
                        return {"action": "ERROR", "params": {"error": f"Missing required check leave information: {', '.join(missing)} for CHECK_LEAVE."}}
                    break
            
            if action_type != "NONE" and not action_params and action_keyword_found: # Action keyword found but params missing/invalid
                 if action_type == "ADD_STAFF": return {"action": "ERROR", "params": {"error": "Missing/invalid parameters for ADD_STAFF."}}
                 if action_type == "DELETE_STAFF": return {"action": "ERROR", "params": {"error": "Missing name for DELETE_STAFF."}}
                 if action_type == "ADD_LEAVE": return {"action": "ERROR", "params": {"error": "Missing/invalid parameters for ADD_LEAVE."}}
                 if action_type == "VIEW_LEAVE": return {"action": "ERROR", "params": {"error": "Missing/invalid parameters for VIEW_LEAVE."}}
                 if action_type == "UPDATE_LEAVE": return {"action": "ERROR", "params": {"error": "Missing/invalid parameters for UPDATE_LEAVE."}}
                 if action_type == "GENERATE_ROSTER": return {"action": "ERROR", "params": {"error": "Missing/invalid parameters for GENERATE_ROSTER."}}

            return {"action": action_type, "params": action_params}
            
        except Exception as e:
            print(f"Error during _parse_action: {str(e)}") # Debug
            return {"action": "ERROR", "params": {"error": f"Internal error parsing action: {str(e)}"}}

    def _execute_action(self, action_data: Dict[str, Any]) -> str:
        """Execute the parsed action."""
        action = action_data["action"]
        params = action_data["params"]
        
        # Ensure Streamlit is available for session state manipulation
        import streamlit as st

        try:
            if action == "ADD_STAFF":
                success = self.data_handler.add_staff_member(
                    params["name"],
                    params["role"],
                    params["skills"]
                )
                if success:
                    # Re-initialize chatbot in session state with the updated data_handler
                    # This ensures the chatbot's internal context for subsequent calls is also fresh.
                    st.session_state.chatbot = RosteringChatbot(self.api_key, self.data_handler, self.optimizer)
                    st.session_state.trigger_rerun_for_add = True # Signal app.py
                    return f"Successfully added {params['name']}"
                else:
                    return "Failed to add staff member"
            
            elif action == "DELETE_STAFF":
                staff_df = self.data_handler.staff_data
                staff_name_to_delete = params["name"]
                staff_to_delete = staff_df[staff_df['name'] == staff_name_to_delete]
                if not staff_to_delete.empty:
                    staff_id = staff_to_delete.iloc[0]['id']
                    success = self.data_handler.delete_staff_member(staff_id)
                    if success:
                        # Re-initialize chatbot in session state with the updated data_handler
                        st.session_state.chatbot = RosteringChatbot(self.api_key, self.data_handler, self.optimizer)
                        st.session_state.trigger_rerun_for_delete = True # Signal app.py
                        return f"Staff member '{staff_name_to_delete}' deleted successfully."
                    return f"Failed to delete staff member '{staff_name_to_delete}'."
                return f"Staff member '{staff_name_to_delete}' not found."
            
            elif action == "ADD_LEAVE":
                # Calculate duration
                start_date = datetime.strptime(params["start_date"], "%Y-%m-%d")
                end_date = datetime.strptime(params["end_date"], "%Y-%m-%d")
                duration = (end_date - start_date).days + 1
                
                success = self.data_handler.db.add_leave_request(
                    params["staff_member"],
                    params["leave_type"],
                    params["start_date"],
                    params["end_date"],
                    duration,
                    params.get("reason", ""),
                    params["priority"]
                )
                return f"Successfully added leave request for {params['staff_member']}" if success else "Failed to add leave request"

            elif action == "VIEW_LEAVE":
                leave_requests = self.data_handler.db.get_leave_requests(
                    staff_name=params["staff"] if params["staff"] != "ALL" else None,
                    status=params["status"] if params["status"] != "ALL" else None,
                    period=params["period"]
                )
                
                if not leave_requests:
                    return "No leave requests found matching the criteria."
                
                # Format leave requests into a readable string
                result = "Leave Requests:\n"
                for req in leave_requests:
                    result += f"\nRequest ID: {req['id']}\n"
                    result += f"Staff: {req['staff_name']}\n"
                    result += f"Type: {req['leave_type']}\n"
                    result += f"Start: {req['start_date']}\n"
                    result += f"End: {req['end_date']}\n"
                    result += f"Status: {req['status']}\n"
                    result += f"Priority: {req['priority']}\n"
                    if req.get('reason'):
                        result += f"Reason: {req['reason']}\n"
                    result += "-" * 40 + "\n"
                
                return result

            elif action == "UPDATE_LEAVE":
                success = self.data_handler.db.update_leave_request(
                    params["request_id"],
                    params["status"],
                    params.get("comment", "")
                )
                return f"Successfully updated leave request status to {params['status']}" if success else "Failed to update leave request status"

            elif action == "GENERATE_ROSTER":
                # Get staff preferences
                staff_preferences = self.data_handler.get_staff_preferences()
                
                # Get approved leave requests
                leave_requests = self.data_handler.db.get_approved_leave_requests()
                
                # Generate roster
                roster_df, success = self.optimizer.optimize_roster(
                    self.data_handler.staff_data,
                    params["num_days"],
                    params["shifts_per_day"],
                    params["min_staff_per_shift"],
                    params["max_shifts_per_week"],
                    staff_preferences,
                    leave_requests
                )
                
                if success:
                    # Update session state with the new roster
                    st.session_state.roster_df = roster_df
                    st.session_state.last_update = datetime.now()
                    st.session_state.trigger_rerun_for_roster = True # Signal app.py
                    
                    # Calculate metrics
                    metrics = self.optimizer.calculate_roster_metrics(roster_df)
                    return f"""Successfully generated roster with the following metrics:
                    - Staff Utilization: {metrics['staff_utilization']:.1f}%
                    - Coverage: {metrics['coverage']:.1f}%
                    - Preference Satisfaction: {metrics['preference_satisfaction']:.1f}%"""
                else:
                    error_message = self.optimizer.get_last_error()
                    return f"Failed to generate roster: {error_message}"

            elif action == "CHECK_LEAVE":
                # Get current date
                current_date = datetime.now().date()
                end_date = current_date + timedelta(days=params["days"])
                
                # Get leave requests
                leave_requests = self.data_handler.db.get_leave_requests(
                    staff_name=params["staff"] if params["staff"] != "ALL" else None,
                    status="Approved",
                    period="Future"
                )
                
                if not leave_requests:
                    return f"No approved leave requests found for the next {params['days']} days."
                
                # Filter leave requests for the specified period
                upcoming_leaves = []
                for req in leave_requests:
                    start_date = datetime.strptime(req["start_date"], "%Y-%m-%d").date()
                    end_date_req = datetime.strptime(req["end_date"], "%Y-%m-%d").date()
                    
                    if start_date <= end_date and end_date_req >= current_date:
                        upcoming_leaves.append(req)
                
                if not upcoming_leaves:
                    return f"No approved leave requests found for the next {params['days']} days."
                
                # Format the response
                result = f"Upcoming Leave Requests for the next {params['days']} days:\n\n"
                for req in upcoming_leaves:
                    result += f"Staff: {req['staff_name']}\n"
                    result += f"Type: {req['leave_type']}\n"
                    result += f"Start: {req['start_date']}\n"
                    result += f"End: {req['end_date']}\n"
                    result += f"Priority: {req['priority']}\n"
                    if req.get('reason'):
                        result += f"Reason: {req['reason']}\n"
                    result += "-" * 40 + "\n"
                
                return result

            elif action == "ERROR":
                return f"Error processing request: {params.get('error', 'Unknown error')}"
            
            return "No action taken"
        except Exception as e:
            return f"Error executing action: {str(e)}"