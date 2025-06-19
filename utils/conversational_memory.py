import re
from datetime import datetime
from typing import Dict, Any, List
from difflib import SequenceMatcher

class ConversationalMemory:
    def __init__(self, max_context_length=10):
        self.conversation_history = []
        self.entity_context = {}  # Track entities mentioned (staff, dates, etc.)
        self.current_topic = None
        self.max_context_length = max_context_length
    
    def add_message(self, role: str, content: str):
        """Add a message to conversation history"""
        self.conversation_history.append({
            "role": role,
            "content": content,
            "timestamp": datetime.now()
        })
        
        # Keep conversation history manageable
        if len(self.conversation_history) > self.max_context_length * 2:
            self.conversation_history = self.conversation_history[-self.max_context_length:]
    
    def fuzzy_match_staff(self, text: str, staff_df, threshold: float = 0.7):
        """Return the best fuzzy match for a staff name in text, or None if not found."""
        best_match = None
        best_score = 0.0
        for _, staff in staff_df.iterrows():
            name = staff['name']
            score = SequenceMatcher(None, name.lower(), text.lower()).ratio()
            if score > best_score and score >= threshold:
                best_score = score
                best_match = staff
        return best_match

    def extract_entities(self, text: str, staff_df=None):
        """Extract entities from text and update context (now with fuzzy matching)."""
        entities = {}
        # Extract staff names (fuzzy and substring match)
        if staff_df is not None:
            # Try exact/substring match first
            for _, staff in staff_df.iterrows():
                name = staff['name']
                if name.lower() in text.lower():
                    entities['current_staff'] = {
                        'name': name,
                        'role': staff['role'],
                        'skills': staff['skills']
                    }
                    break
            # If not found, try fuzzy match
            if 'current_staff' not in entities:
                best_match = self.fuzzy_match_staff(text, staff_df)
                if best_match is not None:
                    entities['current_staff'] = {
                        'name': best_match['name'],
                        'role': best_match['role'],
                        'skills': best_match['skills']
                    }
        
        # Extract dates
        date_patterns = [
            r'\b\d{4}-\d{2}-\d{2}\b',  # YYYY-MM-DD
            r'\b(today|tomorrow|yesterday)\b',
            r'\b(monday|tuesday|wednesday|thursday|friday|saturday|sunday)\b'
        ]
        
        for pattern in date_patterns:
            matches = re.findall(pattern, text.lower())
            if matches:
                entities['dates'] = matches
        
        # Extract pronouns and resolve them
        pronouns = {
            'he': 'current_staff',
            'she': 'current_staff',
            'his': 'current_staff',
            'her': 'current_staff',
            'him': 'current_staff'
        }
        
        for pronoun, entity_type in pronouns.items():
            if pronoun in text.lower() and entity_type in self.entity_context:
                entities[pronoun] = self.entity_context[entity_type]
        
        # Update entity context
        self.entity_context.update(entities)
        return entities
    
    def resolve_pronouns(self, text: str) -> str:
        """Resolve pronouns in text using context"""
        resolved_text = text
        
        # Replace pronouns with actual names/entities
        if 'current_staff' in self.entity_context:
            staff = self.entity_context['current_staff']
            resolved_text = re.sub(r'\b(he|she)\b', staff['name'], resolved_text, flags=re.IGNORECASE)
            resolved_text = re.sub(r'\b(his|her)\b', f"{staff['name']}'s", resolved_text, flags=re.IGNORECASE)
            resolved_text = re.sub(r'\bhim\b', staff['name'], resolved_text, flags=re.IGNORECASE)
        
        return resolved_text
    
    def get_context_summary(self) -> str:
        """Get a summary of current conversation context"""
        context_parts = []
        
        if 'current_staff' in self.entity_context:
            staff = self.entity_context['current_staff']
            context_parts.append(f"Currently discussing: {staff['name']} ({staff['role']})")
        
        if 'dates' in self.entity_context:
            context_parts.append(f"Date context: {', '.join(self.entity_context['dates'])}")
        
        if self.current_topic:
            context_parts.append(f"Topic: {self.current_topic}")
        
        return "; ".join(context_parts) if context_parts else "No specific context"
    
    def clear_context(self):
        """Clear conversation context"""
        self.entity_context = {}
        self.current_topic = None 