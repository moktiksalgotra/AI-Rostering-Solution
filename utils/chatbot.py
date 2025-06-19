import requests
import json
from typing import List, Dict, Any
import pandas as pd
from datetime import datetime, timedelta
import os
from dotenv import load_dotenv
import re


# Load environment variables
load_dotenv()

class RosteringChatbot:
    def __init__(self, api_key: str = None, data_handler=None, optimizer=None):
        self.api_key = api_key or os.getenv('GROQ_API_KEY')
        print(f"Debug - API Key found: {'Yes' if self.api_key else 'No'}")
        print(f"Debug - API Key length: {len(self.api_key) if self.api_key else 0}")
        if not self.api_key:
            raise ValueError("Groq API key not found. Please set GROQ_API_KEY in .env file")
        self.data_handler = data_handler
        self.optimizer = optimizer
        self.conversation_history = []
        self.api_url = "https://api.groq.com/openai/v1/chat/completions"
        
    
    def chat(self, user_input: str) -> str:
        """
        Process user input and return response.
        Args:
            user_input: The user's input text
        Returns:
            str: The chatbot's response
        """
        try:
            # Check for common general queries first
            user_input_lower = user_input.lower()
            
            # Check for roster generation intent first
            if "generate" in user_input_lower and any(phrase in user_input_lower for phrase in ["roster", "schedule", "shifts"]):
                # For generation, we can be more direct
                intent_data = {"intent": "GENERATE_ROSTER", "parameters": {}} # Simplified for generation
                return self._execute_generate_roster(intent_data["parameters"])
            
            # Handle staff list queries
            staff_query_words = ['staff', 'staffs', 'team', 'member', 'members', 'doctor', 'doctors', 'nurse', 'nurses']
            view_query_words = ['show', 'view', 'list', 'see', 'display', 'current', 'all', 'who are', 'what are']
            action_query_words = ['add', 'new', 'create', 'delete', 'remove', 'roster', 'schedule', 'shift']
            table_requested = 'table' in user_input_lower

            if any(word in user_input_lower for word in staff_query_words) and \
               any(word in user_input_lower for word in view_query_words) and \
               not any(word in user_input_lower for word in action_query_words):
                return self._get_staff_list_response(table=table_requested)

            # Handle roster view queries
            if any(phrase in user_input_lower for phrase in ["show roster", "view roster", "current roster", "display roster"]) and "generate" not in user_input_lower:
                return self._get_roster_response()
            
            # Handle leave view queries only (not add/delete)
            leave_view_phrases = ["show leave", "view leave", "see leave", "list leave", "show vacation", "view vacation", "see vacation", "list vacation", "show absence", "view absence", "see absence", "list absence"]
            if any(phrase in user_input_lower for phrase in leave_view_phrases):
                return self._get_leave_response()
            
            # Handle staff profile queries (e.g., 'who is moktik', 'details of moktik', 'tell me about michael davis')
            profile_patterns = [
                r"who is ([a-zA-Z\s\.]+)",
                r"details of ([a-zA-Z\s\.]+)",
                r"show details for ([a-zA-Z\s\.]+)",
                r"show profile of ([a-zA-Z\s\.]+)",
                r"profile of ([a-zA-Z\s\.]+)",
                r"tell me about ([a-zA-Z\s\.]+)"
            ]
            for pattern in profile_patterns:
                match = re.search(pattern, user_input_lower)
                if match:
                    staff_name = match.group(1).strip()
                    # Always fetch fresh staff data from the database
                    staff_df = self.data_handler.db.get_all_staff()
                    # Normalize names for comparison
                    staff_df['name_normalized'] = staff_df['name'].astype(str).str.lower().str.strip()
                    staff_name_normalized = staff_name.lower().strip()
                    found = staff_df[staff_df['name_normalized'].str.contains(staff_name_normalized)]
                    if not found.empty:
                        staff = found.iloc[0]
                        response = f"Here are the details for {staff['name']} (from the staff database):\n\n"
                        response += f"• **Role:** {staff['role']}\n"
                        response += f"• **Skills:** {staff['skills']}\n"
                        response += "If you want to know about their roster or leave, just ask!"
                        return response
                    else:
                        return f"I'm sorry, but I couldn't find a staff member named '{staff_name}'. Please check the name and try again. You can view the staff list by asking 'show staff list'."
            
            # Handle queries about a staff member's role (e.g., 'is lisa chen a doctor or nurse')
            role_keywords = ['role', 'position', 'doctor', 'nurse', 'specialist']
            action_keywords = ['add', 'new', 'create', 'delete', 'remove', 'roster', 'schedule', 'shift', 'leave', 'generate']
            
            is_role_query = any(word in user_input_lower for word in role_keywords)
            is_action_query = any(word in user_input_lower for word in action_keywords)

            if is_role_query and not is_action_query:
                staff_df = self.data_handler.db.get_all_staff()
                staff_df['name_lower'] = staff_df['name'].str.lower()
                
                found_staff = None
                
                for _, staff_row in staff_df.iterrows():
                    if re.search(r'\b' + re.escape(staff_row['name_lower']) + r'\b', user_input_lower):
                        found_staff = staff_row
                        break
                
                if found_staff is not None:
                    staff_name = found_staff['name']
                    staff_role = found_staff['role']
                    return f"{staff_name}'s role is {staff_role}."

            # Extract intent and parameters using NLP
            intent_data = self._extract_intent_and_parameters(user_input)
            
            # Execute action if intent is detected
            if intent_data["intent"] != "NONE":
                result = self._execute_intent(intent_data)
                return self._clean_response(result)
            
            # If no specific intent, use general conversation
            context = self._retrieve_relevant_context(user_input)
            
            # Prepare messages for the API call
            messages = [
                {"role": "system", "content": self._get_system_prompt()},
                {"role": "system", "content": f"Relevant context for this query:\n{context}"},
                *self.conversation_history,
                {"role": "user", "content": user_input}
            ]
            
            # Get AI response
            response = self._call_groq(messages)
            
            # Clean up HTML-like elements from response (centralized cleanup)
            response = re.sub(r'<[^>]+>', '', response)  # Remove all HTML tags
            response = response.strip()
            
            # Add to conversation history
            self.conversation_history.append({"role": "user", "content": user_input})
            self.conversation_history.append({"role": "assistant", "content": response})
            
            # Keep conversation history manageable
            if len(self.conversation_history) > 10:
                self.conversation_history = self.conversation_history[-10:]
            
            # Always clean the response before returning
            return self._clean_response(response)
            
        except Exception as e:
            error_msg = f"I apologize, but I encountered an error while processing your request: {str(e)}. Please try again with your request."
            self.conversation_history.append({"role": "assistant", "content": error_msg})
            return self._clean_response(error_msg)

        return self._simple_keyword_fallback(user_input)

    def _simple_keyword_fallback(self, user_input):
        """Simple keyword-based fallback for when semantic search fails"""
        user_input_lower = user_input.lower()
        # Always fetch fresh staff data from the database
        staff_df = self.data_handler.db.get_all_staff()
        
        # Try to match staff name and field
        for _, staff in staff_df.iterrows():
            name = staff['name']
            name_lower = name.lower()
            if name_lower in user_input_lower:
                # Check for skills
                if 'skill' in user_input_lower:
                    return f"{name}'s skills are: {staff['skills']}."
                # Check for role
                if 'role' in user_input_lower or 'position' in user_input_lower:
                    return f"{name}'s role is: {staff['role']}."
                # Check for name
                if 'name' in user_input_lower:
                    return f"The staff member's name is: {name}."
                # General info
                if any(word in user_input_lower for word in ['info', 'information', 'details', 'about', 'profile']):
                    return f"{name}: Role - {staff['role']}, Skills - {staff['skills']}."
        
        return "I'm sorry, but I couldn't find the information you requested. You can ask about staff (name, skills, role), roster, or leave data. For example: 'What are the skills of Dr. Smith?', 'Show me the roster for John', or 'Who is on leave next week?'"

    def _format_semantic_staff_answer(self, query, staff):
        # Try to answer based on query keywords
        q = query.lower()
        if 'skill' in q:
            return f"{staff['name']}'s skills are: {staff['skills']}."
        if 'role' in q or 'position' in q:
            return f"{staff['name']}'s role is: {staff['role']}."
        if 'name' in q:
            return f"The staff member's name is: {staff['name']}."
        return f"{staff['name']}: Role - {staff['role']}, Skills - {staff['skills']}."

    def _format_semantic_leave_answer(self, query, leave):
        return f"{leave['staff_member']} has {leave['leave_type']} from {leave['start_date']} to {leave['end_date']} (Status: {leave['status']})."

    def _format_semantic_roster_answer(self, query, row):
        return f"On {row['Date']} (Weekday: {row.get('Weekday', '')}), staff scheduled: {row['Staff']} for shift {row['Shift']} {row.get('Shift Time', '')}."

    def _get_staff_list_response(self, table: bool = False) -> str:
        """Generate a response showing the current staff list."""
        try:
            # Always fetch fresh staff data from the database
            staff_df = self.data_handler.db.get_all_staff()
            
            if staff_df.empty:
                return "Currently, there are no staff members in the database. You can add staff members by saying something like 'Add Dr. Smith as a Senior Doctor with Emergency skills'."
            
            if table:
                # Return as markdown table
                display_df = staff_df[['name', 'role', 'skills']].copy()
                headers = '| Name | Role | Skills |\n'
                separators = '|---|---|---|\n'
                rows = '\n'.join(
                    f"| {row['name']} | {row['role']} | {row['skills']} |" for _, row in display_df.iterrows()
                )
                table_md = headers + separators + rows
                response = f"Here's the current staff list in table format (total {len(staff_df)} members):\n\n{table_md}\n\nYou can add new staff members, delete existing ones, or view specific staff information. Just let me know what you'd like to do!"
                return response
            else:
                response = f"Here's the current staff list with {len(staff_df)} members:\n\n"
                for _, staff in staff_df.iterrows():
                    response += f"• **{staff['name']}** - {staff['role']}\n"
                    response += f"  Skills: {staff['skills']}\n\n"
                response += "You can add new staff members, delete existing ones, or view specific staff information. Just let me know what you'd like to do!"
                return response
        except Exception as e:
            return f"I'm sorry, but I encountered an error while retrieving the staff list: {str(e)}. Please try again."

    def _get_roster_response(self) -> str:
        """Generate a response about the current roster."""
        try:
            # Always fetch fresh roster data from the database
            roster_df = self.data_handler.db.get_roster()
            if roster_df is not None and not roster_df.empty:
                table = self._df_to_markdown_table(roster_df, max_rows=20)
                return f"📅Current Roster\n\n{table}\n\nIf you need to generate a new roster, just let me know the parameters like number of days and shifts per day."
            else:
                return "The roster is currently empty. You can generate a new roster by saying something like 'Generate a 7-day roster with 3 shifts per day'."
        except Exception as e:
            return f"I'm sorry, but I encountered an error while retrieving the roster: {str(e)}. Please try again."

    def _get_leave_response(self) -> str:
        """Generate a response about leave requests."""
        try:
            # Always fetch fresh leave data from the database
            leave_requests = self.data_handler.db.get_all_leave_requests()
            
            if not leave_requests:
                return "Currently, there are no leave requests in the system. You can add leave requests by saying something like 'Add annual leave for John from 2024-03-15 to 2024-03-20'."
            
            response = f"Here are the current leave requests ({len(leave_requests)} total):\n\n"
            
            for req in leave_requests[-5:]:  # Show last 5 requests
                response += f"• **{req['staff_member']}** - {req['leave_type']}\n"
                response += f"  {req['start_date']} to {req['end_date']} ({req['duration']} days)\n"
                response += f"  Status: {req['status']}\n\n"
            
            if len(leave_requests) > 5:
                response += f"... and {len(leave_requests) - 5} more requests.\n\n"
            
            response += "You can add new leave requests, view specific ones, or update existing ones. Just let me know what you'd like to do!"
            
            return response
            
        except Exception as e:
            return f"I'm sorry, but I encountered an error while retrieving leave requests: {str(e)}. Please try again."

    def _extract_intent_and_parameters(self, user_input: str) -> Dict[str, Any]:
        """
        Use NLP to extract intent and parameters from natural language input.
        This function uses LLM-based extraction with a robust regex/keyword fallback for synonyms/typos.
        # TODO: Integrate semantic search for even more flexible question handling.
        """
        try:
            # Prepare context for intent extraction
            context = self._get_intent_extraction_context()
            
            # Create messages for intent extraction
            messages = [
                {"role": "system", "content": self._get_intent_extraction_prompt()},
                {"role": "system", "content": f"Available context:\n{context}"},
                {"role": "user", "content": user_input}
            ]
            
            # Get AI response for intent extraction
            response = self._call_groq(messages)
            
            # Check if we got an API error
            if response.startswith("API_"):
                print(f"API Error detected: {response}")
                print("Falling back to manual intent extraction...")
                return self._manual_intent_extraction(user_input)
            
            # Parse the structured response
            intent_data = self._parse_intent_response(response)
            
            # If parsing failed, try to extract intent manually
            if intent_data["intent"] == "NONE":
                print("AI parsing returned NONE intent, trying manual extraction...")
                intent_data = self._manual_intent_extraction(user_input)
            
            return intent_data
            
        except Exception as e:
            print(f"Error during intent extraction: {str(e)}")
            # Fallback to manual extraction
            return self._manual_intent_extraction(user_input)

    def _get_intent_extraction_prompt(self) -> str:
        """Get the prompt for intent extraction."""
        return """You are an intent extraction system for a hospital roster management chatbot. 

Your task is to analyze user input and extract the intent and relevant parameters. Respond ONLY with a JSON object in this exact format:

{
    "intent": "INTENT_TYPE",
    "parameters": {
        "param1": "value1",
        "param2": "value2"
    },
    "confidence": 0.95
}

Available intents:
1. "ADD_STAFF" - User wants to add a new staff member
   Parameters: name (string), role (string), skills (string or list)
   
2. "DELETE_STAFF" - User wants to delete a staff member
   Parameters: name (string)
   
3. "ADD_LEAVE" - User wants to add a leave request
   Parameters: staff_member (string), leave_type (string), start_date (YYYY-MM-DD), end_date (YYYY-MM-DD), reason (string, optional)
   
4. "VIEW_LEAVE" - User wants to view leave requests
   Parameters: staff (string, can be "ALL"), status (string, can be "ALL"), period (string)
   
5. "UPDATE_LEAVE" - User wants to update a leave request
   Parameters: request_id (string), status (string), comment (string, optional)
   
6. "GENERATE_ROSTER" - User wants to generate a new roster.
   Parameters: num_days (integer), shifts_per_day (integer), min_staff_per_shift (integer), max_shifts_per_week (integer)
   
7. "VIEW_ROSTER" - User wants to see the current roster in the chat.
   Parameters: None
   
8. "CHECK_LEAVE" - User wants to check upcoming leave
   Parameters: days (integer), staff (string, can be "ALL")
   
9. "QUERY_ROSTER" - User wants to query the roster for staff, day, or date
   Parameters: staff_name (string), role (string), weekday (string), date (YYYY-MM-DD)
   
10. "DELETE_LEAVE" - User wants to delete a leave request
    Parameters: request_id (string) or staff_member (string) and date (YYYY-MM-DD)
   
11. "NONE" - No specific intent detected

Valid roles: ["Senior Doctor", "Doctor", "Senior Nurse", "Nurse", "Specialist"]
Valid skills: ["Emergency", "ICU", "General", "Surgery", "Pediatrics"]
Valid leave types: ["Annual Leave", "Sick Leave", "Personal Leave", "Emergency Leave", "Study Leave"]
Valid statuses: ["Approved", "Pending", "Rejected"]
Valid periods: ["Past", "Current", "Future", "ALL"]

Extract parameters from natural language. If a parameter is missing or unclear, set it to null or an appropriate default.
If multiple values are mentioned for a parameter, use the most specific or relevant one.
For skills, if multiple skills are mentioned, combine them with commas.
For dates, convert to YYYY-MM-DD format if possible, otherwise use null.

Examples:
- "Add Dr. Smith as a Senior Doctor with Emergency and ICU skills" → ADD_STAFF with name="Dr. Smith", role="Senior Doctor", skills="Emergency,ICU"
- "John needs annual leave from March 15 to March 20" → ADD_LEAVE with staff_member="John", leave_type="Annual Leave", start_date="2024-03-15", end_date="2024-03-20"
- "Show me the current roster" → VIEW_ROSTER
- "Generate a 7-day roster" → GENERATE_ROSTER with num_days=7
- "Show me all leave requests" → VIEW_LEAVE with staff="ALL", status="ALL", period="ALL"

Respond with ONLY the JSON object, no additional text."""

    def _get_intent_extraction_context(self) -> str:
        """Get context information for intent extraction."""
        try:
            # Always fetch fresh staff data from the database
            staff_df = self.data_handler.db.get_all_staff()
            staff_info = "Current Staff:\n"
            for _, staff in staff_df.iterrows():
                staff_info += f"- {staff['name']} ({staff['role']}): {staff['skills']}\n"
            # Always fetch fresh leave data from the database
            leave_requests = self.data_handler.db.get_all_leave_requests()
            leave_info = f"\nLeave Requests: {len(leave_requests)} total"
            return staff_info + leave_info
        except Exception as e:
            return f"Error getting context: {str(e)}"

    def _parse_intent_response(self, response: str) -> Dict[str, Any]:
        """Parse the AI response for intent extraction."""
        try:
            # Clean the response and extract JSON
            response = response.strip()
            
            # Remove any markdown formatting
            if response.startswith("```json"):
                response = response[7:]
            if response.endswith("```"):
                response = response[:-3]
            
            response = response.strip()
            
            # Parse JSON
            intent_data = json.loads(response)
            
            # Validate the structure
            if not isinstance(intent_data, dict):
                return {"intent": "NONE", "parameters": {}, "confidence": 0.0}
            
            if "intent" not in intent_data:
                return {"intent": "NONE", "parameters": {}, "confidence": 0.0}
            
            # Ensure parameters is a dict
            if "parameters" not in intent_data or not isinstance(intent_data["parameters"], dict):
                intent_data["parameters"] = {}
            
            # Ensure confidence is a number
            if "confidence" not in intent_data or not isinstance(intent_data["confidence"], (int, float)):
                intent_data["confidence"] = 0.0
            
            return intent_data
            
        except json.JSONDecodeError as e:
            print(f"JSON parsing error: {str(e)}")
            print(f"Response was: {response}")
            return {"intent": "NONE", "parameters": {}, "confidence": 0.0}
        except Exception as e:
            print(f"Error parsing intent response: {str(e)}")
            return {"intent": "NONE", "parameters": {}, "confidence": 0.0}

    def _manual_intent_extraction(self, user_input: str) -> Dict[str, Any]:
        """Manual intent extraction as fallback."""
        user_input_lower = user_input.lower()
        import re
        
        # Intent: Generate Roster
        if "generate" in user_input_lower and any(p in user_input_lower for p in ["roster", "schedule", "shift"]):
            # Extract parameters if available
            days_match = re.search(r"(\d+)\s*day", user_input_lower)
            params = {}
            if days_match:
                params["num_days"] = int(days_match.group(1))
            return {"intent": "GENERATE_ROSTER", "parameters": params, "confidence": 0.95}

        # Intent: View Roster (if not generating)
        view_roster_keywords = ["show", "view", "display", "see", "what's", "what is"]
        if any(k in user_input_lower for k in view_roster_keywords) and "roster" in user_input_lower:
            # Ensure it's not a query for a specific person/day
            if not re.search(r"(of|for|on)\s+([a-zA-Z0-9\s]+)", user_input_lower):
                 return {"intent": "VIEW_ROSTER", "parameters": {}, "confidence": 0.95}

        # Query roster for staff, day, or date
        query_match = re.search(r"roster for ([a-zA-Z\s]+)", user_input_lower)
        if query_match:
            return {"intent": "QUERY_ROSTER", "parameters": {"staff_name": query_match.group(1).strip()}, "confidence": 0.9}
        
        # Roster viewing patterns (these should only show in chat, never rerun/tab change)
        roster_view_patterns = [
            r"\b(show|view|display|see|what(?:'s| is)) (?:me )?(?:the )?(?:current )?roster( data)?\b",
            r"\bview (?:the )?roster( data)?\b",
            r"\bshow (?:the )?roster( data)?\b",
            r"\bwhat(?:'s| is) (?:the )?roster( data)?\b",
            r"\broster( data)?\b"
        ]
        for pattern in roster_view_patterns:
            if re.search(pattern, user_input_lower):
                # If the query does NOT mention a staff name, date, or role/weekday, treat as VIEW_ROSTER
                if not re.search(r"(shift timings? of|who is working on|which (doctor|nurse|staff|employee|specialist) is available on|show me [a-zA-Z\s]+'s shifts)", user_input_lower):
                    return {
                        "intent": "VIEW_ROSTER",
                        "parameters": {},
                        "confidence": 0.95
                    }
        # Query roster for staff or day (only if not a generic view request)
        staff_match = re.search(r"shift timings? of ([a-zA-Z\s]+)", user_input_lower)
        if staff_match:
            staff_name = staff_match.group(1).strip().title()
            return {"intent": "QUERY_ROSTER", "parameters": {"staff_name": staff_name}, "confidence": 0.95}
        available_on_day = re.search(r"which (doctor|nurse|staff|employee|specialist) is available on ([a-zA-Z]+)", user_input_lower)
        if available_on_day:
            role = available_on_day.group(1).title()
            day = available_on_day.group(2).title()
            return {"intent": "QUERY_ROSTER", "parameters": {"role": role, "weekday": day}, "confidence": 0.95}
        who_on_date = re.search(r"who is working on (\d{4}-\d{2}-\d{2})", user_input_lower)
        if who_on_date:
            date = who_on_date.group(1)
            return {"intent": "QUERY_ROSTER", "parameters": {"date": date}, "confidence": 0.95}
        staff_shifts = re.search(r"show me ([a-zA-Z\s]+)'s shifts", user_input_lower)
        if staff_shifts:
            staff_name = staff_shifts.group(1).strip().title()
            return {"intent": "QUERY_ROSTER", "parameters": {"staff_name": staff_name}, "confidence": 0.95}
        # Fallback: if 'roster' is in the query, treat as VIEW_ROSTER (but not generate)
        if 'roster' in user_input_lower and 'generate' not in user_input_lower:
            return {"intent": "VIEW_ROSTER", "parameters": {}, "confidence": 0.9}
        
        # Check for ADD_STAFF intent
        if any(word in user_input_lower for word in ["add", "create", "new"]) and any(word in user_input_lower for word in ["staff", "doctor", "nurse", "member"]):
            # Try to extract name, role, and skills
            import re
            
            # Extract name (usually after "add" or "create")
            name_match = re.search(r'(?:add|create)\s+([A-Za-z\s]+?)(?:\s+as|\s+with|\s+skills|$)', user_input, re.IGNORECASE)
            name = name_match.group(1).strip() if name_match else None
            
            # If no name found, try to extract from the beginning
            if not name:
                # Look for patterns like "Add Dr. Smith" or "Add John Smith"
                name_match = re.search(r'(?:add|create)\s+([A-Za-z\s\.]+?)(?:\s+as|\s+with|\s+skills|$)', user_input, re.IGNORECASE)
                name = name_match.group(1).strip() if name_match else None
            
            # Extract role
            roles = ["Senior Doctor", "Doctor", "Senior Nurse", "Nurse", "Specialist"]
            role = None
            for r in roles:
                if r.lower() in user_input_lower:
                    role = r
                    break
            
            # Extract skills - look for skills mentioned in the text
            skills = ["Emergency", "ICU", "General", "Surgery", "Pediatrics"]
            found_skills = []
            for skill in skills:
                if skill.lower() in user_input_lower:
                    found_skills.append(skill)
            
            # If no skills found, try to extract from "skills are" or "skills in" patterns
            if not found_skills:
                skills_match = re.search(r'skills?\s+(?:are|in)\s+([A-Za-z\s,]+)', user_input, re.IGNORECASE)
                if skills_match:
                    skills_text = skills_match.group(1).strip()
                    for skill in skills:
                        if skill.lower() in skills_text.lower():
                            found_skills.append(skill)
            
            # If still no skills, try to extract from "with" patterns
            if not found_skills:
                with_match = re.search(r'with\s+([A-Za-z\s,]+)', user_input, re.IGNORECASE)
                if with_match:
                    with_text = with_match.group(1).strip()
                    for skill in skills:
                        if skill.lower() in with_text.lower():
                            found_skills.append(skill)
            
            if name and role and found_skills:
                return {
                    "intent": "ADD_STAFF",
                    "parameters": {
                        "name": name,
                        "role": role,
                        "skills": ",".join(found_skills)
                    },
                    "confidence": 0.8
                }
            elif name and role:
                # If we have name and role but no skills, ask for skills
                return {
                    "intent": "ADD_STAFF",
                    "parameters": {
                        "name": name,
                        "role": role,
                        "skills": None
                    },
                    "confidence": 0.6
                }
        
        # Check for DELETE_STAFF intent
        if any(word in user_input_lower for word in ["delete", "remove", "fire", "terminate"]) and any(word in user_input_lower for word in ["staff", "doctor", "nurse", "member", "employee"]):
            import re
            
            # Try multiple patterns to extract the name
            name = None
            
            # Pattern 1: "delete/remove/fire [name]"
            patterns = [
                r'(?:delete|remove|fire|terminate)\s+([A-Za-z\s\.]+?)(?:\s+from|\s+the|\s+staff|\s+member|$)',
                r'(?:delete|remove|fire|terminate)\s+([A-Za-z\s\.]+?)(?:\s+as|\s+with|\s+skills|$)',
                r'(?:delete|remove|fire|terminate)\s+([A-Za-z\s\.]+?)(?:\s+who|\s+that|\s+has|$)'
            ]
            
            for pattern in patterns:
                name_match = re.search(pattern, user_input, re.IGNORECASE)
                if name_match:
                    name = name_match.group(1).strip()
                    break
            
            # If still no name, try to extract from the beginning
            if not name:
                # Look for patterns like "Delete Dr. Smith" or "Remove John Smith"
                name_match = re.search(r'(?:delete|remove|fire|terminate)\s+([A-Za-z\s\.]+?)(?:\s+from|\s+the|$)', user_input, re.IGNORECASE)
                name = name_match.group(1).strip() if name_match else None
            
            # Clean up the name (remove extra words)
            if name:
                # Remove common words that might be captured
                name = re.sub(r'\b(?:from|the|staff|member|employee|who|that|has|as|with|skills)\b', '', name, flags=re.IGNORECASE)
                name = name.strip()
                
                # If name is too short or contains invalid characters, try to extract better
                if len(name) < 2 or not re.match(r'^[A-Za-z\s\.]+$', name):
                    # Try to find a proper name in the input
                    words = user_input.split()
                    for i, word in enumerate(words):
                        if word.lower() in ['delete', 'remove', 'fire', 'terminate']:
                            if i + 1 < len(words):
                                potential_name = words[i + 1]
                                if re.match(r'^[A-Za-z]+$', potential_name):
                                    name = potential_name
                                    break
            
            if name and len(name) >= 2:
                return {
                    "intent": "DELETE_STAFF",
                    "parameters": {"name": name},
                    "confidence": 0.8
                }
        
        # Check for ADD_LEAVE intent (improved)
        add_leave_patterns = [
            # e.g. add leave for moktik for 2 days annual leave
            r"add leave for ([a-zA-Z]+) for (\d+) days? ([a-zA-Z ]+)?",
            # e.g. moktik needs 2 days annual leave from tomorrow
            r"([a-zA-Z]+) needs (\d+) days? ([a-zA-Z ]+)? from ([a-zA-Z0-9\-]+)",
            # e.g. add leave for moktik from 2024-06-01 to 2024-06-02
            r"add leave for ([a-zA-Z]+) from (\d{4}-\d{2}-\d{2}) to (\d{4}-\d{2}-\d{2}) ?([a-zA-Z ]+)?",
            # e.g. add annual leave for moktik from 2024-06-01 to 2024-06-02
            r"add ([a-zA-Z ]+) for ([a-zA-Z]+) from (\d{4}-\d{2}-\d{2}) to (\d{4}-\d{2}-\d{2})",
            # e.g. add leave for moktik for 2 days
            r"add leave for ([a-zA-Z]+) for (\d+) days?"
        ]
        for pattern in add_leave_patterns:
            m = re.search(pattern, user_input_lower)
            if m:
                from datetime import datetime, timedelta
                today = datetime.now().date()
                params = {}
                if pattern == add_leave_patterns[0]:
                    # add leave for moktik for 2 days annual leave
                    params['staff_member'] = m.group(1).capitalize()
                    duration = int(m.group(2))
                    params['duration'] = duration
                    params['leave_type'] = m.group(3).strip().title() if m.group(3) else 'Annual Leave'
                    params['start_date'] = today.strftime('%Y-%m-%d')
                    params['end_date'] = (today + timedelta(days=duration-1)).strftime('%Y-%m-%d')
                elif pattern == add_leave_patterns[1]:
                    # moktik needs 2 days annual leave from tomorrow
                    params['staff_member'] = m.group(1).capitalize()
                    duration = int(m.group(2))
                    params['duration'] = duration
                    params['leave_type'] = m.group(3).strip().title() if m.group(3) else 'Annual Leave'
                    from_date = m.group(4)
                    # Parse 'from' date (support 'tomorrow', 'today', or YYYY-MM-DD)
                    if from_date == 'tomorrow':
                        start = today + timedelta(days=1)
                    elif from_date == 'today':
                        start = today
                    else:
                        try:
                            start = datetime.strptime(from_date, '%Y-%m-%d').date()
                        except Exception:
                            start = today
                    params['start_date'] = start.strftime('%Y-%m-%d')
                    params['end_date'] = (start + timedelta(days=duration-1)).strftime('%Y-%m-%d')
                elif pattern == add_leave_patterns[2]:
                    # add leave for moktik from 2024-06-01 to 2024-06-02
                    params['staff_member'] = m.group(1).capitalize()
                    params['start_date'] = m.group(2)
                    params['end_date'] = m.group(3)
                    params['leave_type'] = m.group(4).strip().title() if m.group(4) else 'Annual Leave'
                    # Calculate duration
                    try:
                        start_dt = datetime.strptime(params['start_date'], '%Y-%m-%d')
                        end_dt = datetime.strptime(params['end_date'], '%Y-%m-%d')
                        params['duration'] = (end_dt - start_dt).days + 1
                    except Exception:
                        params['duration'] = 1
                elif pattern == add_leave_patterns[3]:
                    # add annual leave for moktik from 2024-06-01 to 2024-06-02
                    params['leave_type'] = m.group(1).strip().title()
                    params['staff_member'] = m.group(2).capitalize()
                    params['start_date'] = m.group(3)
                    params['end_date'] = m.group(4)
                    try:
                        start_dt = datetime.strptime(params['start_date'], '%Y-%m-%d')
                        end_dt = datetime.strptime(params['end_date'], '%Y-%m-%d')
                        params['duration'] = (end_dt - start_dt).days + 1
                    except Exception:
                        params['duration'] = 1
                elif pattern == add_leave_patterns[4]:
                    # add leave for moktik for 2 days
                    params['staff_member'] = m.group(1).capitalize()
                    duration = int(m.group(2))
                    params['duration'] = duration
                    params['leave_type'] = 'Annual Leave'
                    params['start_date'] = today.strftime('%Y-%m-%d')
                    params['end_date'] = (today + timedelta(days=duration-1)).strftime('%Y-%m-%d')
                return {
                    "intent": "ADD_LEAVE",
                    "parameters": params,
                    "confidence": 0.9
                }
        # fallback: old logic
        if any(word in user_input_lower for word in ["leave", "vacation", "absence"]) and any(word in user_input_lower for word in ["add", "request", "need"]):
            return {
                "intent": "ADD_LEAVE",
                "parameters": {},
                "confidence": 0.6
            }
        
        # Check for VIEW_LEAVE intent
        if any(word in user_input_lower for word in ["show", "view", "see", "list"]) and any(word in user_input_lower for word in ["leave", "vacation", "absence"]):
            return {
                "intent": "VIEW_LEAVE",
                "parameters": {"staff": "ALL", "status": "ALL", "period": "ALL"},
                "confidence": 0.8
            }
        
        # Check for DELETE_LEAVE intent
        if any(word in user_input_lower for word in ["delete", "remove", "cancel"]) and any(word in user_input_lower for word in ["leave", "vacation", "absence", "request"]):
            import re
            # Try to extract request ID
            id_match = re.search(r'request\s*(\d+)', user_input_lower)
            if id_match:
                return {
                    "intent": "DELETE_LEAVE",
                    "parameters": {"request_id": id_match.group(1)},
                    "confidence": 0.9
                }
            # Try to extract staff name and date
            name_match = re.search(r'(?:for|of)\s+([A-Za-z]+)', user_input_lower)
            date_match = re.search(r'on\s+(\d{4}-\d{2}-\d{2})', user_input_lower)
            params = {}
            if name_match:
                params["staff_member"] = name_match.group(1)
            if date_match:
                params["date"] = date_match.group(1)
            if params:
                return {
                    "intent": "DELETE_LEAVE",
                    "parameters": params,
                    "confidence": 0.7
                }
            return {
                "intent": "DELETE_LEAVE",
                "parameters": {},
                "confidence": 0.5
            }
        
        return {"intent": "NONE", "parameters": {}, "confidence": 0.0}

    def _execute_intent(self, intent_data: Dict[str, Any]) -> str:
        """Execute the detected intent and return a human-readable response."""
        intent = intent_data["intent"]
        params = intent_data["parameters"]
        confidence = intent_data.get("confidence", 0.0)
        
        # If confidence is too low, ask for clarification
        if confidence < 0.7:
            return self._ask_for_clarification(intent, params)
        
        # Ensure Streamlit is available for session state manipulation
        import streamlit as st

        try:
            if intent == "ADD_STAFF":
                return self._execute_add_staff(params)
            
            elif intent == "DELETE_STAFF":
                return self._execute_delete_staff(params)
            
            elif intent == "ADD_LEAVE":
                return self._execute_add_leave(params)
            
            elif intent == "DELETE_LEAVE":
                return self._execute_delete_leave(params)
            
            elif intent == "VIEW_LEAVE":
                return self._execute_view_leave(params)
            
            elif intent == "UPDATE_LEAVE":
                return self._execute_update_leave(params)
            
            elif intent == "GENERATE_ROSTER":
                # Always navigate to roster tab for generation
                return self._execute_generate_roster(params)
            
            elif intent == "VIEW_ROSTER":
                # Show roster in chat
                return self._get_roster_response()
            
            elif intent == "CHECK_LEAVE":
                return self._execute_check_leave(params)
            
            elif intent == "QUERY_ROSTER":
                return self._execute_query_roster(params)
            
            else:
                return "I'm not sure what you'd like me to do. Could you please rephrase your request?"
                
        except Exception as e:
            return f"I apologize, but I encountered an error while processing your request: {str(e)}. Please try again."

    def _ask_for_clarification(self, intent: str, params: Dict[str, Any]) -> str:
        """Ask for clarification when intent confidence is low."""
        if intent == "ADD_STAFF":
            missing = []
            if not params.get("name"):
                missing.append("staff member's name")
            if not params.get("role"):
                missing.append("their role")
            if not params.get("skills"):
                missing.append("their skills")
            
            if missing:
                return f"I'd like to help you add a new staff member, but I need some clarification. Could you please provide: {', '.join(missing)}?"
            else:
                return "I think you want to add a new staff member, but I'm not entirely sure. Could you please rephrase your request?"
        
        elif intent == "ADD_LEAVE":
            missing = []
            if not params.get("staff_member"):
                missing.append("who is requesting leave")
            if not params.get("leave_type"):
                missing.append("what type of leave")
            if not params.get("start_date"):
                missing.append("when the leave starts")
            if not params.get("end_date"):
                missing.append("when the leave ends")
            
            if missing:
                return f"I'd like to help you add a leave request, but I need some clarification. Could you please provide: {', '.join(missing)}?"
            else:
                return "I think you want to add a leave request, but I'm not entirely sure. Could you please rephrase your request?"
        
        else:
            return "I'm not entirely sure what you'd like me to do. Could you please rephrase your request more clearly?"

    def _execute_add_staff(self, params: Dict[str, Any]) -> str:
        """Execute ADD_STAFF intent."""
        name = params.get("name")
        role = params.get("role")
        skills = params.get("skills")
        
        if not name or not role or not skills:
            missing = []
            if not name: missing.append("name")
            if not role: missing.append("role")
            if not skills: missing.append("skills")
            return f"I need the following information to add a staff member: {', '.join(missing)}. Could you please provide these details?"
        
        # Validate role and skills
        valid_roles = ["Senior Doctor", "Doctor", "Senior Nurse", "Nurse", "Specialist"]
        valid_skills = ["Emergency", "ICU", "General", "Surgery", "Pediatrics"]
        
        if role not in valid_roles:
            return f"I'm sorry, but '{role}' is not a valid role. Valid roles are: {', '.join(valid_roles)}"
        
        # Convert skills to list if it's a string
        if isinstance(skills, str):
            skills_list = [s.strip() for s in skills.split(',')]
        else:
            skills_list = skills
        
        # Validate skills
        invalid_skills = [skill for skill in skills_list if skill not in valid_skills]
        if invalid_skills:
            return f"I'm sorry, but the following skills are not valid: {', '.join(invalid_skills)}. Valid skills are: {', '.join(valid_skills)}"
        
        # Add staff member
        import streamlit as st
        success = self.data_handler.add_staff_member(name, role, ', '.join(skills_list))
        
        if success:
            # Refresh the data handler's staff data without re-initializing the chatbot
            self.data_handler.staff_data = self.data_handler.db.get_all_staff()
            
            return f"Perfect! I've successfully added {name} as a {role} with skills in {', '.join(skills_list)} to the staff database. They are now available for roster assignments."
        else:
            return f"I'm sorry, but I encountered an error while adding {name} to the database. Please try again or contact support if the issue persists."

    def _execute_delete_staff(self, params: Dict[str, Any]) -> str:
        """Execute DELETE_STAFF intent."""
        name = params.get("name")
        
        if not name:
            return "I need the name of the staff member you'd like to delete. Could you please provide their name?"
        
        import streamlit as st
        staff_df = self.data_handler.staff_data
        
        if staff_df.empty:
            return "There are no staff members in the database."
        
        # Enhanced name normalization:
        # 1. Strip whitespace
        # 2. Convert to lowercase
        # 3. Remove titles (Dr., Mr., Mrs., etc)
        # 4. Remove extra spaces between words
        name_normalized = name.strip().lower()
        name_normalized = re.sub(r'^(dr\.|mr\.|mrs\.|ms\.|prof\.)\s+', '', name_normalized)
        name_normalized = ' '.join(name_normalized.split())
        
        # Create normalized version of staff names
        staff_df = staff_df.copy()
        staff_df['name_normalized'] = staff_df['name'].astype(str).apply(lambda x: ' '.join(
            re.sub(r'^(dr\.|mr\.|mrs\.|ms\.|prof\.)\s+', '', x.strip().lower()).split()
        ))
        
        # Try exact match first (normalized)
        staff_to_delete = staff_df[staff_df['name_normalized'] == name_normalized]
        
        # If not found, try contained match (normalized)
        if staff_to_delete.empty:
            staff_to_delete = staff_df[staff_df['name_normalized'].str.contains(name_normalized, na=False)]
        
        # If still not found, try fuzzy matching
        if staff_to_delete.empty:
            from difflib import SequenceMatcher
            
            def similarity_ratio(a, b):
                return SequenceMatcher(None, a, b).ratio()
            
            # Calculate similarity scores
            similarity_scores = staff_df['name_normalized'].apply(
                lambda x: similarity_ratio(x, name_normalized)
            )
            
            # Find closest matches (similarity > 0.6)
            close_matches = staff_df[similarity_scores > 0.6]
            
            if not close_matches.empty:
                matches = close_matches['name'].tolist()
                return f"I couldn't find an exact match for '{name}'. Did you mean one of these: {', '.join(matches)}? Please specify the exact name you want to delete."
            else:
                # Show available staff names to help the user
                available_names = staff_df['name'].tolist()
                return f"I couldn't find a staff member named '{name}' in the database. Available staff members are: {', '.join(available_names)}. Please check the spelling and try again."
        
        # If multiple matches found, ask for clarification
        if len(staff_to_delete) > 1:
            matches = staff_to_delete['name'].tolist()
            return f"I found multiple staff members with similar names: {', '.join(matches)}. Please specify the exact name you want to delete."
        
        # Get the exact name and ID
        exact_name = staff_to_delete.iloc[0]['name']
        staff_id = int(staff_to_delete.iloc[0]['id'])  # Ensure ID is an integer
        role = staff_to_delete.iloc[0]['role']
        
        print(f"[DEBUG] Found staff member to delete: {exact_name} (ID: {staff_id}, Role: {role})")
        
        # Double-check the ID exists in the database
        import sqlite3
        conn = self.data_handler.db.get_connection()
        try:
            cursor = conn.cursor()
            cursor.execute('SELECT id FROM staff WHERE id = ?', (staff_id,))
            if not cursor.fetchone():
                print(f"[DEBUG] ID {staff_id} not found in database, refreshing data...")
                # Refresh the data handler's staff data
                self.data_handler.staff_data = self.data_handler.db.get_all_staff()
                return f"I encountered a synchronization issue. Please try deleting {exact_name} again."
        finally:
            conn.close()
        
        # Confirm deletion
        success = self.data_handler.delete_staff_member(staff_id)
        
        if success:
            # Refresh the data handler's staff data
            self.data_handler.staff_data = self.data_handler.db.get_all_staff()
            return f"I've successfully removed {exact_name} ({role}) from the staff database. They are no longer available for roster assignments."
        else:
            # If deletion failed, try to provide more specific error information
            return f"I encountered an error while trying to remove {exact_name} from the database. This might be because the staff member was already deleted or there was a database error. Please try again, and if the problem persists, contact support."

    def _execute_add_leave(self, params: Dict[str, Any]) -> str:
        """Execute ADD_LEAVE intent."""
        staff_member = params.get("staff_member")
        leave_type = params.get("leave_type")
        start_date = params.get("start_date")
        end_date = params.get("end_date")
        reason = params.get("reason", "")
        
        if not staff_member or not leave_type or not start_date or not end_date:
            missing = []
            if not staff_member: missing.append("staff member name")
            if not leave_type: missing.append("leave type")
            if not start_date: missing.append("start date")
            if not end_date: missing.append("end date")
            return f"I need the following information to add a leave request: {', '.join(missing)}. Could you please provide these details?"
        
        # Validate leave type
        valid_leave_types = ["Annual Leave", "Sick Leave", "Personal Leave", "Emergency Leave", "Study Leave"]
        
        if leave_type not in valid_leave_types:
            return f"I'm sorry, but '{leave_type}' is not a valid leave type. Valid types are: {', '.join(valid_leave_types)}"
        
        # Calculate duration
        try:
            start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            duration = (end_dt - start_dt).days + 1
        except ValueError:
            return "I'm sorry, but the date format is invalid. Please provide dates in YYYY-MM-DD format."
        
        # Add leave request (automatically approved since system doesn't have pending logic)
        success = self.data_handler.db.add_leave_request(
            staff_member, leave_type, start_date, end_date, duration, reason
        )
        
        if success:
            return f"Perfect! I've successfully added a {leave_type} request for {staff_member} from {start_date} to {end_date} ({duration} days). The request has been automatically approved and is ready for roster planning."
        else:
            return f"I'm sorry, but I encountered an error while adding the leave request for {staff_member}. Please try again or contact support if the issue persists."

    def _execute_view_leave(self, params: Dict[str, Any]) -> str:
        """Execute VIEW_LEAVE intent."""
        staff = params.get("staff", "ALL")
        status = params.get("status", "ALL")
        period = params.get("period", "ALL")
        
        # Validate parameters
        valid_statuses = ["Approved", "Pending", "Rejected", "ALL"]
        valid_periods = ["Past", "Current", "Future", "ALL"]
        
        if status not in valid_statuses:
            return f"I'm sorry, but '{status}' is not a valid status. Valid statuses are: {', '.join(valid_statuses)}"
        
        if period not in valid_periods:
            return f"I'm sorry, but '{period}' is not a valid period. Valid periods are: {', '.join(valid_periods)}"
        
        # Get leave requests
        leave_requests = self.data_handler.db.get_leave_requests(
            staff_name=staff if staff != "ALL" else None,
            status=status if status != "ALL" else None,
            period=period
        )
        
        if not leave_requests:
            return "No leave requests found matching your criteria."
        
        # Format response
        result = f"Here are the leave requests"
        if staff != "ALL":
            result += f" for {staff}"
        if status != "ALL":
            result += f" with {status} status"
        if period != "ALL":
            result += f" in the {period.lower()} period"
        result += ":\n\n"
        
        for req in leave_requests:
            result += f"• {req['staff_name']} - {req['leave_type']}\n"
            result += f"  {req['start_date']} to {req['end_date']} ({req['duration']} days)\n"
            result += f"  Status: {req['status']}\n"
            if req.get('reason'):
                result += f"  Reason: {req['reason']}\n"
            result += "\n"
        
        return result

    def _execute_update_leave(self, params: Dict[str, Any]) -> str:
        """Execute UPDATE_LEAVE intent."""
        request_id = params.get("request_id")
        status = params.get("status")
        comment = params.get("comment", "")
        
        if not request_id or not status:
            missing = []
            if not request_id: missing.append("request ID")
            if not status: missing.append("new status")
            return f"I need the following information to update a leave request: {', '.join(missing)}. Could you please provide these details?"
        
        # Validate status
        valid_statuses = ["Approved", "Pending", "Rejected"]
        if status not in valid_statuses:
            return f"I'm sorry, but '{status}' is not a valid status. Valid statuses are: {', '.join(valid_statuses)}"
        
        # Update leave request
        success = self.data_handler.db.update_leave_request(request_id, status, comment)
        
        if success:
            return f"Perfect! I've successfully updated leave request {request_id} to {status} status."
        else:
            return f"I'm sorry, but I encountered an error while updating leave request {request_id}. Please check the request ID and try again."

    def _execute_generate_roster(self, params: Dict[str, Any]) -> str:
        """Execute GENERATE_ROSTER intent."""
        try:
            # Ensure all parameters are set and are integers
            num_days = params.get("num_days")
            if num_days is None:
                num_days = 7
            else:
                num_days = int(num_days)
            shifts_per_day = params.get("shifts_per_day")
            if shifts_per_day is None:
                shifts_per_day = 3
            else:
                shifts_per_day = int(shifts_per_day)
            min_staff_per_shift = params.get("min_staff_per_shift")
            if min_staff_per_shift is None:
                min_staff_per_shift = 2
            else:
                min_staff_per_shift = int(min_staff_per_shift)
            max_shifts_per_week = params.get("max_shifts_per_week")
            if max_shifts_per_week is None:
                max_shifts_per_week = 5
            else:
                max_shifts_per_week = int(max_shifts_per_week)
            
            # Validate parameters
            if num_days <= 0 or shifts_per_day <= 0 or min_staff_per_shift <= 0 or max_shifts_per_week <= 0:
                return "I'm sorry, but all roster parameters must be positive numbers. Please provide valid values."
            
            import streamlit as st
            
            # Validate staff data
            if self.data_handler.staff_data is None or self.data_handler.staff_data.empty:
                return "I'm sorry, but there are no staff members in the database. Please add some staff members first."
            
            # Get approved leaves for the roster period
            approved_leaves = [
                request for request in st.session_state.leave_requests
                if request['status'] == 'Approved'
            ] if hasattr(st.session_state, 'leave_requests') else None
            
            # Generate roster
            roster_df, success = self.optimizer.optimize_roster(
                self.data_handler.staff_data,
                num_days,
                shifts_per_day,
                min_staff_per_shift,
                max_shifts_per_week,
                self.data_handler.get_staff_preferences(),
                leave_requests=approved_leaves
            )
            
            if success and roster_df is not None and not roster_df.empty:
                # Add weekday to the roster DataFrame
                roster_df['Weekday'] = pd.to_datetime(roster_df['Date']).dt.strftime('%A')
                
                # Add shift mapping for better display
                shift_time_map = {
                    1: "07:00-15:00",
                    2: "15:00-23:00",
                    3: "23:00-07:00"
                }
                roster_df['Shift Time'] = roster_df['Shift'].map(shift_time_map)
                
                # Add staff count column
                roster_df['Staff_Count'] = roster_df['Staff'].apply(lambda x: len(x.split(',')) if isinstance(x, str) and x.strip() != 'No staff assigned' else 0)
                
                # Calculate metrics
                metrics = self.optimizer.calculate_roster_metrics(roster_df)
                
                # Save roster to database
                if self.data_handler.db.save_roster(roster_df):
                    print("Roster saved to database successfully")
                else:
                    print("Warning: Failed to save roster to database")
                
                # Format the roster for display
                table = self._df_to_markdown_table(roster_df)
                
                # Update session state
                st.session_state.roster_df = roster_df
                st.session_state.last_update = datetime.now()
                st.session_state.current_page = "📅 Roster Generation"
                # Only set trigger_rerun_for_roster here for navigation
                st.session_state.trigger_rerun_for_roster = True
                st.session_state.roster_df = roster_df
                st.session_state.last_update = datetime.now()
                st.session_state.current_page = "📅 Roster Generation"
                st.rerun()
                
                return (
                    f"✅ The roster has been generated successfully!\n\n"
                    f"📊 **Roster Metrics:**\n"
                    f"• Staff Utilization: {metrics['staff_utilization']:.1f}%\n"
                    f"• Coverage: {metrics['coverage']:.1f}%\n"
                    f"• Preference Satisfaction: {metrics['preference_satisfaction']:.1f}%\n\n"
                    f"Here's a preview of the roster:\n\n{table}\n\n"
                    f"I've switched to the Roster Generation tab where you can view the complete roster in different formats."
                )
            else:
                error_message = self.optimizer.get_last_error()
                return (
                    f"❌ I encountered an error while generating the roster:\n\n"
                    f"{error_message}\n\n"
                    f"Please check that you have:\n"
                    f"1. Sufficient staff members for the required shifts\n"
                    f"2. Reasonable constraints (min staff per shift, max shifts per week)\n"
                    f"3. No conflicting leave requests\n\n"
                    f"You can adjust these parameters and try again."
                )
                
        except Exception as e:
            return f"❌ An unexpected error occurred while generating the roster: {str(e)}. Please try again or contact support if the issue persists."

    def _execute_check_leave(self, params: Dict[str, Any]) -> str:
        """Execute CHECK_LEAVE intent."""
        days = params.get("days", 7)
        staff = params.get("staff", "ALL")
        
        if days <= 0:
            return "I'm sorry, but the number of days must be positive. Please provide a valid number."
        
        # Get current date and calculate end date
        current_date = datetime.now().date()
        end_date = current_date + timedelta(days=days)
        
        # Get leave requests
        leave_requests = self.data_handler.db.get_leave_requests(
            staff_name=staff if staff != "ALL" else None,
            status="Approved",
            period="Future"
        )
        
        if not leave_requests:
            return f"No approved leave requests found for the next {days} days."
        
        # Filter leave requests for the specified period
        upcoming_leaves = []
        for req in leave_requests:
            start_date = datetime.strptime(req["start_date"], "%Y-%m-%d").date()
            end_date_req = datetime.strptime(req["end_date"], "%Y-%m-%d").date()
            
            if start_date <= end_date and end_date_req >= current_date:
                upcoming_leaves.append(req)
        
        if not upcoming_leaves:
            return f"No approved leave requests found for the next {days} days."
        
        # Format response
        result = f"Here are the upcoming leave requests for the next {days} days"
        if staff != "ALL":
            result += f" for {staff}"
        result += ":\n\n"
        
        for req in upcoming_leaves:
            result += f"• {req['staff_name']} - {req['leave_type']}\n"
            result += f"  {req['start_date']} to {req['end_date']} ({req['duration']} days)\n"
            if req.get('reason'):
                result += f"  Reason: {req['reason']}\n"
            result += "\n"
        
        return result

    def _execute_query_roster(self, params: Dict[str, Any]) -> str:
        """Handle queries about the roster for staff, day, or date."""
        try:
            staff_name = params.get("staff_name")
            role = params.get("role")
            weekday = params.get("weekday")
            date = params.get("date")
            roster_df = self.data_handler.db.get_roster()
            if roster_df is None or roster_df.empty:
                return "No roster data available."
            roster_df['Date'] = pd.to_datetime(roster_df['Date'])
            response = ""
            if staff_name:
                # Show all shifts for the staff member
                mask = roster_df['Staff'].str.contains(staff_name, case=False, na=False)
                staff_shifts = roster_df[mask]
                if staff_shifts.empty:
                    return f"No shifts found for {staff_name}."
                table = self._df_to_markdown_table(staff_shifts, max_rows=20)
                return f"Here are the shifts for {staff_name} in the current roster:\n\n{table}"
            elif role and weekday:
                # Show all staff of a role working on a given weekday
                mask = (roster_df['Weekday'].str.lower() == weekday.lower()) & (roster_df['Staff'].str.contains(role, case=False, na=False))
                day_shifts = roster_df[roster_df['Weekday'].str.lower() == weekday.lower()]
                if day_shifts.empty:
                    return f"No {role}s found working on {weekday}."
                result = f"{role}s working on {weekday}:\n"
                for _, row in day_shifts.iterrows():
                    staff_list = row['Staff']
                    for staff in staff_list.split(','):
                        if role.lower() in staff.lower():
                            result += f"• {staff.strip()} ({row['Shift Time']})\n"
                return result if result.strip() != f"{role}s working on {weekday}:" else f"No {role}s found working on {weekday}."
            elif date:
                # Show all staff working on a specific date
                mask = roster_df['Date'] == pd.to_datetime(date)
                date_shifts = roster_df[mask]
                if date_shifts.empty:
                    return f"No staff found working on {date}."
                table = self._df_to_markdown_table(date_shifts, max_rows=20)
                return f"Here are the shifts for {date}:\n\n{table}"
            else:
                return "Please specify a staff name, role and weekday, or date for the roster query."
        except Exception as e:
            return f"I apologize, but I encountered an error while processing your roster query: {str(e)}. Please try again."

    def _df_to_markdown_table(self, df, max_rows=5):
        if df is None or df.empty:
            return "No roster data available."
        display_df = df.head(max_rows)
        headers = "| " + " | ".join(display_df.columns) + " |\n"
        separators = "|" + "---|" * len(display_df.columns) + "\n"
        rows = "\n".join(
            "| " + " | ".join(str(cell) for cell in row) + " |" for row in display_df.values.tolist()
        )
        return headers + separators + rows

    def _retrieve_relevant_context(self, user_input: str) -> str:
        """
        Retrieve relevant information from the database for the user query (RAG layer).
        Args:
            user_input: The user's input text
        Returns:
            str: Relevant context string
        """
        try:
            user_input_lower = user_input.lower()
            # Staff-related queries
            if any(word in user_input_lower for word in ["staff", "doctor", "nurse", "specialist", "employee", "team"]):
                # Check if it's a roster query for a specific staff member
                if any(word in user_input_lower for word in ["roster", "shift", "schedule"]):
                    # Try to extract staff name
                    staff_name = None
                    for role in ["doctor", "nurse", "specialist"]:
                        if role in user_input_lower:
                            # Look for words around the role
                            words = user_input_lower.split()
                            try:
                                idx = words.index(role)
                                if idx > 0:  # Check word before role
                                    staff_name = words[idx-1].capitalize()
                                elif idx < len(words)-1:  # Check word after role
                                    staff_name = words[idx+1].capitalize()
                            except ValueError:
                                continue
                    
                    if staff_name:
                        return self._get_staff_roster_response(staff_name)
                
                # Always fetch fresh staff data from the database
                staff_df = self.data_handler.db.get_all_staff()
                staff_info = "Staff List:\n"
                for _, staff in staff_df.iterrows():
                    staff_info += f"- {staff['name']} ({staff['role']}): {staff['skills']}\n"
                return staff_info
                
            # Leave-related queries
            elif any(word in user_input_lower for word in ["leave", "vacation", "absence", "holiday"]):
                leave_requests = self.data_handler.db.get_all_leave_requests()
                if not leave_requests:
                    return "No leave requests found in the system."
                leave_info = "Recent Leave Requests:\n"
                for req in leave_requests[-5:]:  # Show last 5 leave requests
                    leave_info += f"- {req['staff_member']} | {req['leave_type']} | {req['start_date']} to {req['end_date']} | Status: Approved\n"
                return leave_info
                
            # Roster-related queries
            elif any(word in user_input_lower for word in ["roster", "shift", "schedule"]):
                roster_df = self.data_handler.db.get_roster()
                if not roster_df.empty:
                    table = self._df_to_markdown_table(roster_df)
                    return f"**Here is the latest roster data (showing up to 5 rows):**\n\n{table}\n\n*If you need more information or the roster for the rest of the week, please let me know!*"
                else:
                    return "The roster is currently empty."
                    
            # General queries
            else:
                staff_df = self.data_handler.db.get_all_staff()
                leave_requests = self.data_handler.db.get_all_leave_requests()
                
                if len(leave_requests) == 0:
                    context = f"There are {len(staff_df)} staff members and currently no leave requests in the system."
                else:
                    context = f"There are {len(staff_df)} staff members and {len(leave_requests)} leave requests in the system."
                return context
        except Exception as e:
            return f"Error retrieving context: {str(e)}"

    def _get_system_prompt(self) -> str:
        """Get the system prompt for the chatbot."""
        return (
            "You are Q-Roster AI Assistant, a professional, helpful AI assistant for hospital roster management. "
            "IMPORTANT: Always respond in English only, regardless of the user's input language. "
            "Always answer in a clear, human-like, and professional tone. "
            "Use the provided context to answer accurately. "
            "If the user asks for actions (like adding staff, leave, etc.) and provides all required info, respond with the exact command block as specified. "
            "Otherwise, answer naturally and do not show technical command formats. "
            "If the user's query is unclear or lacks info, ask clarifying questions in a friendly way. "
            "Never invent data; only use what is in the context. "
            "If you don't know, say so politely. "
            "Remember: Always respond in English, even if the user writes in another language."
        )

    def _get_context(self) -> str:
        """Get current context about staff and leave data."""
        try:
            # Always fetch fresh staff data from the database
            staff_df = self.data_handler.db.get_all_staff()
            staff_info = "Current Staff:\n"
            for _, staff in staff_df.iterrows():
                staff_info += f"- {staff['name']} ({staff['role']}): {staff['skills']}\n"
            return staff_info
        except Exception as e:
            return f"Error getting context: {str(e)}"

    def _call_groq(self, messages: List[Dict[str, str]]) -> str:
        """Make API call to Groq with retry mechanism for rate limiting."""
        print(f"Debug - Making API call with key: {self.api_key[:10]}...")  # Only print first 10 chars for security
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        
        data = {
            "model": "llama-3.1-8b-instant",  # Using Llama 3.1 8B instant model on Groq
            "messages": messages,
            "temperature": 0.7,
            "max_tokens": 1000
        }
        
        # Retry mechanism for rate limiting
        max_retries = 3
        retry_delay = 2  # seconds
        
        for attempt in range(max_retries):
            try:
                response = requests.post(self.api_url, headers=headers, json=data)
                
                # Handle rate limiting and other errors
                if response.status_code == 429:
                    if attempt < max_retries - 1:
                        print(f"Rate limit hit, retrying in {retry_delay} seconds... (attempt {attempt + 1}/{max_retries})")
                        import time
                        time.sleep(retry_delay)
                        retry_delay *= 2  # Exponential backoff
                        continue
                    else:
                        return "API_RATE_LIMIT_ERROR: Too many requests. Please wait a moment and try again."
                elif response.status_code == 401:
                    return "API_AUTH_ERROR: Invalid API key. Please check your OpenRouter API key."
                elif response.status_code == 403:
                    return "API_FORBIDDEN_ERROR: Access denied. Please check your API key permissions."
                elif response.status_code >= 400:
                    return f"API_ERROR_{response.status_code}: {response.text}"
                
                response.raise_for_status()
                return response.json()['choices'][0]['message']['content']
                
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    print(f"Request failed, retrying in {retry_delay} seconds... (attempt {attempt + 1}/{max_retries})")
                    import time
                    time.sleep(retry_delay)
                    retry_delay *= 2
                    continue
                else:
                    return f"API_REQUEST_ERROR: {str(e)}"
            except Exception as e:
                return f"API_ERROR: {str(e)}"
        
        return "API_ERROR: Max retries exceeded"

    def refresh_data_handler(self):
        """Refresh the data handler reference to get updated staff data."""
        if hasattr(self, 'data_handler') and self.data_handler:
            self.data_handler.staff_data = self.data_handler.db.get_all_staff()

    def _get_staff_roster_response(self, staff_name=None, date=None) -> str:
        """Get roster information for a specific staff member."""
        try:
            roster_entries = self.data_handler.db.get_staff_roster(staff_name, date)
            
            if not roster_entries:
                if staff_name and date:
                    return f"No roster entries found for {staff_name} on {date}."
                elif staff_name:
                    return f"No roster entries found for {staff_name}."
                else:
                    return "No roster entries found."
            
            response = ""
            if staff_name:
                response = f"📅 Roster for {staff_name}:\n\n"
            else:
                response = "📅 Current Roster:\n\n"
            
            # Group entries by date
            current_date = None
            for entry in roster_entries:
                if current_date != entry['Date']:
                    current_date = entry['Date']
                    response += f"\n**{entry['Weekday']}, {entry['Date']}**\n"
                response += f"• {entry['Shift Time']}: {entry['Staff']}\n"
            
            return response
            
        except Exception as e:
            return f"I'm sorry, but I encountered an error while retrieving the roster: {str(e)}. Please try again."

    def _clean_response(self, response: str) -> str:
        """
        Clean response from HTML tags and ensure proper formatting.
        This method ensures no HTML tags are left in the final response.
        """
        import re
        # First pass: remove all HTML tags
        cleaned = re.sub(r'<[^>]+>', '', response).strip()
        # Second pass: fix any HTML entities
        cleaned = cleaned.replace('&lt;', '<').replace('&gt;', '>').replace('&amp;', '&')
        return cleaned

    def _execute_delete_leave(self, params: Dict[str, Any]) -> str:
        """Execute DELETE_LEAVE intent."""
        request_id = params.get("request_id")
        staff_member = params.get("staff_member")
        date = params.get("date")
        # If request_id is provided, delete directly
        if request_id:
            success = self.data_handler.db.delete_leave_request(request_id)
            if success:
                return f"Leave request {request_id} has been deleted."
            else:
                return f"Could not find or delete leave request {request_id}. Please check the ID and try again."
        # If staff_member and date are provided, try to find the leave request
        leave_requests = self.data_handler.db.get_all_leave_requests()
        filtered = leave_requests
        if staff_member:
            filtered = [r for r in filtered if r['staff_member'].lower() == staff_member.lower()]
        if date:
            filtered = [r for r in filtered if r['start_date'] <= date <= r['end_date']]
        if len(filtered) == 1:
            req_id = filtered[0]['id']
            success = self.data_handler.db.delete_leave_request(req_id)
            if success:
                return f"Leave request for {filtered[0]['staff_member']} from {filtered[0]['start_date']} to {filtered[0]['end_date']} has been deleted."
            else:
                return f"Could not delete the leave request. Please try again."
        elif len(filtered) > 1:
            ids = ', '.join(str(r['id']) for r in filtered)
            return f"Multiple leave requests found. Please specify the request ID to delete. Matching IDs: {ids}"
        else:
            return "No matching leave request found to delete. Please check the details and try again."