# Speech-to-Text Feature for Q-Roster AI Assistant

## Overview

The Q-Roster AI Assistant now includes speech-to-text functionality, allowing users to interact with the chatbot using voice commands. This feature makes the application more accessible and convenient for users who prefer voice input.

## Features

- **Voice Input**: Click the microphone button to start voice recording
- **Real-time Transcription**: Speech is converted to text in real-time using Google's Speech Recognition API
- **Seamless Integration**: Transcribed text automatically populates the chat input field
- **Error Handling**: Comprehensive error handling for various speech recognition scenarios
- **Visual Feedback**: Clear visual indicators for listening, processing, and success states

## How to Use

### 1. Basic Voice Input

1. Navigate to the chat interface in the Q-Roster AI Assistant
2. Click the **🎤** microphone button in the "Voice Input" section
3. When you see "🎤 Listening... Speak now!", start speaking clearly
4. Your speech will be transcribed and appear in the "Transcribed Text" area
5. Review the transcribed text and click **➤** to send the message

### 2. Voice Commands Examples

You can use voice commands for various tasks:

**Staff Management:**
- "Add Dr. Smith as a Senior Doctor with Emergency skills"
- "Show me the staff list"
- "Delete John Smith from the staff"

**Leave Management:**
- "Add annual leave for Sarah from 2024-06-01 to 2024-06-05"
- "Show me all leave requests"
- "Delete leave request for Mike"

**Roster Operations:**
- "Generate a 7-day roster with 3 shifts per day"
- "Show me the current roster"
- "What shifts is Dr. Johnson working this week?"

### 3. Tips for Better Recognition

- **Speak Clearly**: Enunciate your words clearly for better accuracy
- **Quiet Environment**: Use the feature in a quiet environment to reduce background noise
- **Normal Pace**: Speak at a normal pace - not too fast or too slow
- **Complete Phrases**: Speak complete phrases rather than individual words
- **Microphone Distance**: Keep a consistent distance from your microphone

## Technical Requirements

### Dependencies

The speech-to-text feature requires the following Python packages (already included in `requirements.txt`):

```
SpeechRecognition>=3.10.0
```

### System Requirements

- **Microphone**: A working microphone connected to your device
- **Internet Connection**: Required for Google Speech Recognition API
- **Browser Permissions**: Your browser must allow microphone access

### Browser Compatibility

- **Chrome**: Full support
- **Firefox**: Full support
- **Safari**: Full support
- **Edge**: Full support

## Troubleshooting

### Common Issues and Solutions

#### 1. "Microphone not available" Error

**Cause**: Microphone not detected or permissions not granted
**Solution**: 
- Check that your microphone is properly connected
- Grant microphone permissions to your browser
- Try refreshing the page

#### 2. "No speech detected" Error

**Cause**: No audio input detected within the timeout period
**Solution**:
- Ensure your microphone is working
- Speak louder or move closer to the microphone
- Check for background noise

#### 3. "Could not understand the speech" Error

**Cause**: Speech was detected but couldn't be transcribed
**Solution**:
- Speak more clearly and slowly
- Reduce background noise
- Try rephrasing your request

#### 4. "Speech recognition service error" Error

**Cause**: Network issues or service unavailable
**Solution**:
- Check your internet connection
- Try again in a few moments
- Contact support if the issue persists

### Testing the Feature

You can test the speech recognition functionality using the provided test script:

```bash
python test_speech.py
```

This script will:
1. Test microphone initialization
2. List available microphones
3. Perform a test speech recognition

## Security and Privacy

- **Local Processing**: Audio is processed locally before being sent to Google's API
- **No Storage**: Audio recordings are not stored on the server
- **Temporary Use**: Audio data is only used for transcription and is discarded immediately
- **Google Privacy**: Google's Speech Recognition API is subject to Google's privacy policy

## Customization

### Adjusting Timeout Settings

You can modify the timeout settings in `utils/speech_recognition.py`:

```python
# In the listen_and_convert method
audio = self.recognizer.listen(
    source, 
    timeout=5,        # Time to wait for speech to start (seconds)
    phrase_time_limit=10  # Maximum time for a single phrase (seconds)
)
```

### Changing Microphone Device

If you have multiple microphones, you can specify which one to use:

```python
# In the SpeechToText class
def set_microphone(self, device_index: int):
    self.microphone = sr.Microphone(device_index=device_index)
```

## Support

If you encounter any issues with the speech-to-text feature:

1. Check the troubleshooting section above
2. Run the test script to verify your setup
3. Contact support with specific error messages and system details

## Future Enhancements

Planned improvements for the speech-to-text feature:

- **Offline Recognition**: Support for offline speech recognition
- **Multiple Languages**: Support for multiple languages
- **Voice Commands**: Predefined voice commands for common actions
- **Audio Feedback**: Voice confirmation of actions
- **Custom Wake Words**: Custom wake words for hands-free operation 