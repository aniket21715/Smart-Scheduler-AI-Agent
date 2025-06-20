# The Smart Scheduler AI Agent

This project is an implementation of a voice-enabled AI agent that helps users find available time slots in their Google Calendar.

## Features
- **Voice Interaction**: Uses speech-to-text and text-to-speech for a hands-free conversational experience.
- **Natural Language Understanding**: Powered by Google's Gemini model to understand user requests.
- **Google Calendar Integration**: Connects to the Google Calendar API to find available meeting times in real-time.
- **Stateful Conversation**: Remembers the context of the conversation to ask clarifying questions.

## Design Choices & How It Works

This agent is built using a manual stack approach with Python at its core, as outlined in the assignment.

1.  **Orchestration (main.py)**: The central logic is a Python script that manages the conversation flow. It initializes the system, runs a main loop to listen for user input, and coordinates between the different components.

2.  **Conversational Engine (Google Gemini)**: I chose Google's Gemini model (`gemini-1.5-flash`) for its strong instruction-following capabilities and free-tier access via an API key. A detailed system prompt (`SYSTEM_PROMPT`) guides the model on its persona, the tools it has access to, and the specific format (JSON) it must use to call those tools.

3.  **Tool Integration (calendar_tools.py)**: The ability to interact with Google Calendar is abstracted into a set of "tools" in `calendar_tools.py`. The Gemini model doesn't call the API directly; instead, it generates a structured JSON request that the Python script then uses to execute the correct function. This is a secure and standard way to integrate LLMs with external APIs.

4.  **Voice (STT/TTS)**:
    *   **Speech-to-Text**: The `speech_recognition` library is used to capture microphone input and transcribe it using Google's free web speech API.
    *   **Text-to-Speech**: The `gTTS` library is used to convert the agent's text responses into an MP3 file, which is then played using `playsound`. This provides a simple, free, and effective voice output.

## How to Set Up and Run the Project

### Prerequisites
- Python 3.8+
- A Google Account

### 1. Clone the Repository
```bash
git clone https://github.com/aniket21715/Smart-Scheduler-AI-Agent/
cd  Smart-Scheduler-AI-Agent 
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure API Keys and Credentials

**Google Gemini API Key:**
1.  Go to [Google AI Studio](https://aistudio.google.com/) to create an API key.
2.  Open the `main.py` file and replace `"YOUR_GEMINI_API_KEY"` with the key you generated.

**Google Calendar API Credentials:**
1.  Follow the instructions [here](https://developers.google.com/calendar/api/quickstart/python#authorize_credentials_for_a_desktop_application) to enable the Google Calendar API and download your OAuth 2.0 credentials.
2.  **Crucially**, rename the downloaded JSON file to `credentials.json` and place it in the root directory of this project.

### 4. Run the Agent
Execute the main script from your terminal:
```bash
python main.py
```
- **First-time run**: Your web browser will automatically open, asking you to authorize the application to access your Google Calendar. Please approve the request. This will create a `token.json` file in your directory to store your credentials for future runs.
- **Start Talking**: Once you see "Listening..." in the terminal, you can start speaking to the agent. Try saying, "I need to schedule a meeting."

---
