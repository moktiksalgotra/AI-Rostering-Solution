import speech_recognition as sr
import streamlit as st
import tempfile
import os
from typing import Optional, Tuple
import time
from difflib import SequenceMatcher

class SpeechToText:
    def __init__(self, data_handler=None):
        self.recognizer = sr.Recognizer()
        self.microphone = None
        self.data_handler = data_handler
        self._initialize_microphone()
    
    def _initialize_microphone(self):
        """Initialize the microphone for speech recognition."""
        try:
            # Try to get the default microphone
            self.microphone = sr.Microphone()
            # Adjust for ambient noise
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
        except Exception as e:
            st.error(f"Error initializing microphone: {str(e)}")
            self.microphone = None
    
    def _get_staff_names(self):
        """Get list of staff names for name correction."""
        try:
            if self.data_handler and hasattr(self.data_handler, 'db'):
                staff_df = self.data_handler.db.get_all_staff()
                if not staff_df.empty:
                    return staff_df['name'].tolist()
        except:
            pass
        return []
    
    def _correct_names_in_text(self, text: str) -> str:
        """Correct names in transcribed text using staff database."""
        staff_names = self._get_staff_names()
        if not staff_names:
            return text
        
        words = text.split()
        corrected_words = []
        
        for word in words:
            # Check if word might be a name (capitalized or similar to staff names)
            if word[0].isupper() or any(self._similarity(word, name) > 0.6 for name in staff_names):
                best_match = None
                best_score = 0
                
                for name in staff_names:
                    # Check exact match first
                    if word.lower() == name.lower():
                        best_match = name
                        break
                    
                    # Check similarity
                    score = self._similarity(word.lower(), name.lower())
                    if score > best_score and score > 0.6:
                        best_score = score
                        best_match = name
                
                if best_match:
                    corrected_words.append(best_match)
                else:
                    corrected_words.append(word)
            else:
                corrected_words.append(word)
        
        return ' '.join(corrected_words)
    
    def _similarity(self, a: str, b: str) -> float:
        """Calculate similarity between two strings."""
        return SequenceMatcher(None, a, b).ratio()
    
    def listen_and_convert(self, timeout: int = 5, phrase_time_limit: int = 10) -> Tuple[bool, str]:
        """
        Listen for speech and convert to text with name correction.
        
        Args:
            timeout: Maximum time to wait for speech to start
            phrase_time_limit: Maximum time for a single phrase
            
        Returns:
            Tuple of (success: bool, text: str)
        """
        if not self.microphone:
            return False, "Microphone not available"
        
        try:
            with self.microphone as source:
                st.info("🎤 Listening... Speak now!")
                
                # Listen for audio input
                audio = self.recognizer.listen(
                    source, 
                    timeout=timeout, 
                    phrase_time_limit=phrase_time_limit
                )
                
                st.success("🎵 Processing speech...")
                
                # Convert speech to text
                text = self.recognizer.recognize_google(audio)
                
                if text.strip():
                    # Apply name correction
                    corrected_text = self._correct_names_in_text(text.strip())
                    
                    # Show correction if different
                    if corrected_text != text.strip():
                        st.info(f"🔧 Corrected: '{text.strip()}' → '{corrected_text}'")
                    
                    st.success(f"✅ Transcribed: {corrected_text}")
                    return True, corrected_text
                else:
                    return False, "No speech detected"
                    
        except sr.WaitTimeoutError:
            return False, "No speech detected within timeout period"
        except sr.UnknownValueError:
            return False, "Could not understand the speech"
        except sr.RequestError as e:
            return False, f"Speech recognition service error: {str(e)}"
        except Exception as e:
            return False, f"Error during speech recognition: {str(e)}"
    
    def get_available_microphones(self) -> list:
        """Get list of available microphones."""
        try:
            return sr.Microphone.list_microphone_names()
        except Exception as e:
            st.error(f"Error getting microphone list: {str(e)}")
            return []
    
    def set_microphone(self, device_index: int) -> bool:
        """Set a specific microphone by device index."""
        try:
            self.microphone = sr.Microphone(device_index=device_index)
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
            return True
        except Exception as e:
            st.error(f"Error setting microphone: {str(e)}")
            return False

def create_speech_input_component():
    """
    Create a speech input component for Streamlit.
    Returns the transcribed text if successful.
    """
    stt = SpeechToText()
    
    # Create a container for the speech input
    speech_container = st.container()
    
    with speech_container:
        col1, col2 = st.columns([1, 4])
        
        with col1:
            # Microphone button
            if st.button("🎤", help="Click to start voice input", key="speech_button"):
                st.session_state.speech_active = True
        
        with col2:
            # Show status and transcribed text
            if st.session_state.get('speech_active', False):
                success, text = stt.listen_and_convert()
                
                if success:
                    st.session_state.transcribed_text = text
                    st.session_state.speech_active = False
                    st.rerun()
                else:
                    st.error(text)
                    st.session_state.speech_active = False
                    st.rerun()
            
            # Display transcribed text if available
            if st.session_state.get('transcribed_text'):
                st.text_area(
                    "Transcribed Text",
                    value=st.session_state.transcribed_text,
                    key="transcribed_text_area",
                    height=100
                )
                
                # Clear button for transcribed text
                if st.button("Clear", key="clear_transcribed"):
                    st.session_state.transcribed_text = ""
                    st.rerun()
    
    return st.session_state.get('transcribed_text', "")

def initialize_speech_session_state():
    """Initialize session state variables for speech recognition."""
    if 'speech_active' not in st.session_state:
        st.session_state.speech_active = False
    if 'transcribed_text' not in st.session_state:
        st.session_state.transcribed_text = "" 