import google.generativeai as genai
import speech_recognition as sr
from gtts import gTTS
from playsound import playsound
import os
import json
from datetime import datetime, timedelta
from dotenv import load_dotenv
load_dotenv()

# Import calendar functions (make sure the filename matches)
import calendar_tools

# --- CONFIGURATION ---
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
TODAY_DATE = datetime.now().strftime("%Y-%m-%d")

# --- INITIALIZATION ---
genai.configure(api_key=GEMINI_API_KEY)
generation_config = {
    "temperature": 0.7,
    "top_p": 1,
    "top_k": 1,
    "max_output_tokens": 2048,
}
model = genai.GenerativeModel(
    "gemini-1.5-flash",
    generation_config=generation_config
)

# --- PROMPT DEFINITION ---
SYSTEM_PROMPT = f"""
You are a "Smart Scheduler", a voice-enabled AI assistant that helps users find and schedule meetings.
Your goal is to have a natural conversation, gather necessary information, and use tools to interact with the user's Google Calendar.

Today's date is: {TODAY_DATE}.

You have access to the following tools. To use a tool, you MUST respond with a JSON object in the format:
{{"tool_call": {{"name": "<tool_name>", "arguments": {{"arg1": "value1", ...}}}}}}

Available Tools:
1. find_available_slots(duration_minutes: int, date_str: str)
   - Use this tool to find available slots in the user's calendar.
   - `duration_minutes`: The length of the meeting in minutes.
   - `date_str`: The specific date to check, which MUST be in 'YYYY-MM-DD' format.

2. schedule_meeting(title: str, duration_minutes: int, start_datetime: str, description: str = "")
   - Use this tool to actually schedule a meeting in the user's calendar.
   - `title`: The meeting title/subject
   - `duration_minutes`: The length of the meeting in minutes
   - `start_datetime`: The start time in 'YYYY-MM-DD HH:MM' format (24-hour)
   - `description`: Optional meeting description

Conversation Flow:
1. The user will start the conversation.
2. If you don't have enough information (e.g., meeting duration, date, or time), ask clarifying questions.
3. Use find_available_slots to check availability when needed.
4. When the user confirms a specific time, use schedule_meeting to create the meeting.
5. After you call a tool, you will receive a new message starting with "TOOL_RESPONSE:". Use this to formulate a natural response.
6. Parse natural language into the required tool arguments (convert times like "11:30 AM" to "11:30").
7. Handle conflicts gracefully and suggest alternatives.

Important: When scheduling, convert times properly:
- "11:30 AM" becomes "11:30"
- "2:00 PM" becomes "14:00"
- Always use 24-hour format for start_datetime
"""

def parse_time_to_24hour(time_str, date_str):
    """Convert time like '11:30 AM' to '2025-06-24 11:30' format"""
    try:
        # Handle various time formats
        time_str = time_str.strip().upper()
        
        # Parse time
        if 'AM' in time_str or 'PM' in time_str:
            time_part = time_str.replace('AM', '').replace('PM', '').strip()
            hour, minute = map(int, time_part.split(':'))
            
            if 'PM' in time_str and hour != 12:
                hour += 12
            elif 'AM' in time_str and hour == 12:
                hour = 0
                
        else:
            # Assume 24-hour format
            hour, minute = map(int, time_str.split(':'))
        
        return f"{date_str} {hour:02d}:{minute:02d}"
    except:
        return None

def listen_for_input():
    """Captures audio from the microphone and transcribes it to text."""
    r = sr.Recognizer()
    with sr.Microphone() as source:
        print("Listening...")
        r.pause_threshold = 1
        r.adjust_for_ambient_noise(source)
        audio = r.listen(source)

    try:
        text = r.recognize_google(audio)
        print(f"User said: {text}")
        return text
    except sr.UnknownValueError:
        print("Sorry, I did not understand that.")
        return None
    except sr.RequestError as e:
        print(f"Could not request results from Google Speech Recognition service; {e}")
        return None

def speak_response(text):
    """Converts text to speech and plays it."""
    print(f"Agent: {text}")
    try:
        tts = gTTS(text=text, lang='en')
        tts_file = "response.mp3"
        tts.save(tts_file)
        playsound(tts_file)
        os.remove(tts_file)
    except Exception as e:
        print(f"Error in TTS: {e}")

def main():
    """The main conversation loop for the agent."""
    print("Initializing Smart Scheduler...")
    
    # Test calendar connection first
    print("Testing calendar connection...")
    try:
        calendar_tools.get_calendar_service()
        print("✓ Calendar service connected successfully!")
    except Exception as e:
        print(f"✗ Calendar connection failed: {e}")
        print("Please ensure credentials.json is in the same directory and try again.")
        return
    
    # Initialize conversation history
    conversation_history = [
        {"role": "user", "parts": [SYSTEM_PROMPT]}, 
        {"role": "model", "parts": ["Hello! I'm your Smart Scheduler assistant. I can help you find available times and schedule meetings in your calendar. What would you like to schedule?"]}
    ]
    
    # Initial greeting
    speak_response("Hello! I'm your Smart Scheduler assistant. I can help you find available times and schedule meetings in your calendar. What would you like to schedule?")

    while True:
        # 1. Listen for user input
        user_input = listen_for_input()
        if not user_input:
            continue

        if user_input.lower() in ["exit", "quit", "goodbye", "stop"]:
            speak_response("Goodbye! Have a great day!")
            break

        # 2. Add user input to history and get model response
        conversation_history.append({"role": "user", "parts": [user_input]})
        
        convo = model.start_chat(history=conversation_history)
        response = convo.send_message(user_input)
        
        response_text = response.text.strip()
        
        # 3. Check if the model wants to call a tool
        try:
            # Check if response contains a tool call
            if "tool_call" in response_text and "{" in response_text:
                # Extract JSON from response
                json_start = response_text.find("{")
                json_end = response_text.rfind("}") + 1
                json_str = response_text[json_start:json_end]
                
                tool_call_data = json.loads(json_str)
                function_name = tool_call_data["tool_call"]["name"]
                function_args = tool_call_data["tool_call"]["arguments"]
                
                print(f"Executing tool: {function_name} with args: {function_args}")

                # 4. Execute the tool
                if function_name == "find_available_slots":
                    tool_result = calendar_tools.find_available_slots(**function_args)
                elif function_name == "schedule_meeting":
                    tool_result = calendar_tools.schedule_meeting(**function_args)
                else:
                    tool_result = json.dumps({"status": "error", "message": "Unknown tool."})

                print(f"Tool response: {tool_result}")

                # 5. Send tool result back to the model
                conversation_history.append({"role": "model", "parts": [response_text]})
                conversation_history.append({"role": "user", "parts": [f"TOOL_RESPONSE: {tool_result}"]})

                # Get the natural language response
                final_response = convo.send_message(f"TOOL_RESPONSE: {tool_result}")
                speak_response(final_response.text)
                conversation_history.append({"role": "model", "parts": [final_response.text]})

            else:
                # No tool call, just respond normally
                speak_response(response_text)
                conversation_history.append({"role": "model", "parts": [response_text]})

        except (json.JSONDecodeError, KeyError) as e:
            print(f"Error parsing tool call: {e}")
            # Treat as normal response
            speak_response(response_text)
            conversation_history.append({"role": "model", "parts": [response_text]})

if __name__ == "__main__":
    main()