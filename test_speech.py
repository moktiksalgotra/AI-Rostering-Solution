#!/usr/bin/env python3
"""
Test script for speech recognition functionality
"""

import speech_recognition as sr
import sys

def test_microphone():
    """Test if microphone is working"""
    try:
        # Initialize recognizer and microphone
        recognizer = sr.Recognizer()
        microphone = sr.Microphone()
        
        print("🎤 Testing microphone...")
        print("Available microphones:")
        for i, name in enumerate(sr.Microphone.list_microphone_names()):
            print(f"  {i}: {name}")
        
        # Test microphone access
        with microphone as source:
            print("Adjusting for ambient noise...")
            recognizer.adjust_for_ambient_noise(source, duration=1)
            print("✅ Microphone initialized successfully!")
            
        return True
        
    except Exception as e:
        print(f"❌ Error initializing microphone: {str(e)}")
        return False

def test_speech_recognition():
    """Test speech recognition with a simple phrase"""
    try:
        recognizer = sr.Recognizer()
        microphone = sr.Microphone()
        
        print("\n🎤 Testing speech recognition...")
        print("Please say something when prompted...")
        
        with microphone as source:
            recognizer.adjust_for_ambient_noise(source, duration=0.5)
            print("🎵 Listening... (speak now)")
            
            audio = recognizer.listen(source, timeout=5, phrase_time_limit=10)
            print("🎵 Processing...")
            
            text = recognizer.recognize_google(audio)
            print(f"✅ Transcribed: '{text}'")
            
            return True, text
            
    except sr.WaitTimeoutError:
        print("❌ No speech detected within timeout period")
        return False, "No speech detected"
    except sr.UnknownValueError:
        print("❌ Could not understand the speech")
        return False, "Could not understand speech"
    except sr.RequestError as e:
        print(f"❌ Speech recognition service error: {str(e)}")
        return False, f"Service error: {str(e)}"
    except Exception as e:
        print(f"❌ Error during speech recognition: {str(e)}")
        return False, f"Error: {str(e)}"

def main():
    """Main test function"""
    print("🔊 Speech Recognition Test")
    print("=" * 40)
    
    # Test 1: Microphone initialization
    if not test_microphone():
        print("\n❌ Microphone test failed. Please check your microphone settings.")
        sys.exit(1)
    
    # Test 2: Speech recognition
    success, text = test_speech_recognition()
    
    if success:
        print("\n✅ All tests passed! Speech recognition is working correctly.")
        print(f"📝 Transcribed text: '{text}'")
    else:
        print(f"\n❌ Speech recognition test failed: {text}")
        print("Please check your microphone and internet connection.")

if __name__ == "__main__":
    main() 