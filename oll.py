import os
import json
import re
import random
import datetime
from dotenv import load_dotenv
from huggingface_hub import InferenceClient

load_dotenv()
HF_TOKEN = os.environ.get("HF_TOKEN") or ""

# Official warm serverless model on Hugging Face
MODEL_ID = "meta-llama/Llama-3.2-3B-Instruct"

SYSTEM_PROMPT = """You are Bulma, an energetic, friendly, and smart AI assistant for your friend Abishek.
The user speaks to you via voice commands.

Respond ONLY with a valid JSON object. No explanations, no markdown ticks, no extra text.

JSON Schema:
{"intent": "<intent_name>", "params": {}, "reply": "<spoken reply>"}

Available intents:
- open_app: ONLY when the user wants to launch an app. params: {"app": "chrome", "notepad", "vlc", "file manager", "task manager", "cmd", or "antigravity"}
- web_search: when the user wants to search/find/look up anything. params: {"query": "search query"}
- get_time: user asks for current time. params: {}
- get_date: user asks for current date / day. params: {}
- general_chat: greetings, goodbyes, casual phrases (e.g. "see you next time", "how are you", "thanks"). params: {}

RULES:
- When the user asks to search (e.g. "Search Abhishek-005"), ALWAYS use "web_search".
- Never mistake names like "Abhishek" for greetings like "hi".
- Address him naturally as "Abishek" or "bro".
- Dynamic spoken reply examples:
  - User: "Search Abhishek-005" -> {"intent": "web_search", "params": {"query": "Abhishek-005"}, "reply": "On it bro, searching Abhishek-005!"}
  - User: "I will see you next time" -> {"intent": "general_chat", "params": {}, "reply": "See you next time, Abishek! Take care!"}
  - User: "how are you bro" -> {"intent": "general_chat", "params": {}, "reply": "I'm doing great, bro! What can I do for you?"}
"""

def dynamic_search_reply(query: str) -> str:
    phrases = [
        f"Ok Abishek, searching {query} for you!",
        f"On it bro, looking up {query}!",
        f"Sure thing Abishek, searching for {query}.",
        f"Gotcha bro, searching {query} right away!",
        f"Okie bro, checking {query} for you!"
    ]
    return random.choice(phrases)

def dynamic_app_reply(app_name: str) -> str:
    phrases = [
        f"Ok Abishek, opening {app_name} for you!",
        f"On it bro, launching {app_name} right now!",
        f"Sure thing bro, opening {app_name}!",
        f"Gotcha Abishek, starting {app_name}!"
    ]
    return random.choice(phrases)

def rule_based_fallback(user_text: str) -> dict:
    """
    Robust local intent parser:
    Priority-based matching with strict word boundaries to avoid substring false positives.
    """
    raw_text = user_text.strip()
    if not raw_text:
        return {
            "intent": "general_chat",
            "params": {},
            "reply": "I didn't catch anything, bro. Try speaking again!"
        }

    # Normalize lower case for command matching
    text_lower = raw_text.lower()
    
    # WAKE UP & SLEEP COMMANDS
    if any(re.search(p, text_lower) for p in [r"\bwake up bulma\b", r"\bwake up\b", r"\bhey bulma\b", r"\bbulma wake up\b"]):
        return {"intent": "wake_up", "params": {}, "reply": "I'm awake, Abishek! What do you need?"}

    if any(re.search(p, text_lower) for p in [r"\bgo to sleep\b", r"\bsleep\b", r"\btake a nap\b", r"\bstandby\b"]):
        return {"intent": "sleep", "params": {}, "reply": "Going to sleep, bro. Say 'wake up bulma' whenever you need me!"}

    # 1. EXPLICIT SEARCH (Check FIRST so "search abhishek" is never confused with "hi")
    search_match = re.match(r"^(?:search(?:\s+for)?|google|look\s+up|find)\s+(.+)$", text_lower)
    if search_match:
        # Extract the actual query from raw_text to preserve original casing/symbols like "Abhishek-005"
        prefix_len = len(text_lower) - len(search_match.group(1))
        query = raw_text[prefix_len:].strip()
        query = re.sub(r"\s+(?:in|on)\s+(?:chrome|google|the\s+web)$", "", query, flags=re.IGNORECASE).strip()
        return {"intent": "web_search", "params": {"query": query}, "reply": dynamic_search_reply(query)}

    # 2. OPEN APPLICATION
    app_match = re.match(r"^(?:open|launch|start)(?:\s+up)?\s+(.+)$", text_lower)
    if app_match:
        app_name = app_match.group(1).strip()
        # Clean filler words like 'bulma', 'please', 'bro' from app name
        app_name = re.sub(r"\b(bulma|please|bro|app)\b", "", app_name, flags=re.IGNORECASE).strip()
        return {"intent": "open_app", "params": {"app": app_name}, "reply": dynamic_app_reply(app_name)}

    known_apps = [
        "chrome", "google chrome", "notepad", "vlc", "vlc media player",
        "file manager", "file maner", "files", "explorer", "task manager",
        "task manaer", "taskmgr", "cmd", "command prompt", "terminal",
        "antigravity", "anti gravity"
    ]
    if text_lower in known_apps:
        return {"intent": "open_app", "params": {"app": text_lower}, "reply": dynamic_app_reply(text_lower)}

    # 3. DATE QUERY
    date_patterns = [r"\bwhat is today date\b", r"\btodays date\b", r"\btoday date\b", r"\bcurrent date\b", r"\bwhat date is it\b", r"\bwhats the date\b"]
    if any(re.search(p, text_lower) for p in date_patterns):
        today = datetime.datetime.now().strftime("%A, %B %d, %Y")
        return {"intent": "get_date", "params": {}, "reply": f"Today is {today}, Abishek!"}

    # 4. TIME QUERY
    time_patterns = [r"\bwhat time\b", r"\bwhat is the time\b", r"\bcurrent time\b", r"\btime is it\b", r"\bwhats the time\b"]
    if any(re.search(p, text_lower) for p in time_patterns) or text_lower == "time":
        now = datetime.datetime.now().strftime("%I:%M %p")
        return {"intent": "get_time", "params": {}, "reply": f"It's {now}, bro!"}

    # 5. FAREWELLS / GOODBYES
    farewell_patterns = [r"\bsee you\b", r"\bnext time\b", r"\bbye\b", r"\bgoodbye\b", r"\bcatch you later\b", r"\btake care\b", r"\bexit\b", r"\bquit\b"]
    if any(re.search(p, text_lower) for p in farewell_patterns):
        reply = random.choice([
            "See you next time, Abishek! Take care!",
            "Catch you later, bro!",
            "Bye Abishek, have a good one!"
        ])
        return {"intent": "general_chat", "params": {}, "reply": reply}

    # 6. GREETINGS (Strict word boundary: \bhi\b won't match inside 'abhishek')
    greeting_patterns = [r"\bhow are you\b", r"\bwhats up\b", r"\bhow you doing\b", r"\bhello\b", r"\bhi\b", r"\bhey\b", r"\bgood morning\b"]
    if any(re.search(p, text_lower) for p in greeting_patterns):
        reply = random.choice([
            "I'm doing great, Abishek! What's on your mind?",
            "Hey bro! Everything's good here. What can I do for you?",
            "Doing awesome, bro! Ready when you are."
        ])
        return {"intent": "general_chat", "params": {}, "reply": reply}

    # 7. THANK YOU
    if re.search(r"\b(thank you|thanks)\b", text_lower):
        return {"intent": "general_chat", "params": {}, "reply": "You're welcome, Abishek!"}

    # 8. QUESTION SEARCH (who is, where is, how to, what is)
    question_patterns = [r"^who is\b", r"^who was\b", r"^where is\b", r"^how to\b", r"^why is\b", r"^tell me about\b", r"^what is\b"]
    if any(re.search(p, text_lower) for p in question_patterns):
        return {"intent": "web_search", "params": {"query": raw_text}, "reply": dynamic_search_reply(raw_text)}

    # 9. GENERAL CHAT (anything else is casual talking, never an accidental search)
    return {
        "intent": "general_chat",
        "params": {},
        "reply": random.choice([
            "Got it, Abishek! Anything else you need?",
            "Cool bro! Let me know if you want to search or open anything.",
            "I hear you, bro!"
        ])
    }

def ask_ollama(user_text: str) -> dict:
    token = HF_TOKEN.strip()
    if not token or token == "YOUR_HF_TOKEN_HERE":
        return rule_based_fallback(user_text)

    try:
        client = InferenceClient(api_key=token)
        response = client.chat.completions.create(
            model=MODEL_ID,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_text}
            ],
            max_tokens=150,
            temperature=0.7,
        )

        content = response.choices[0].message.content.strip()
        content = re.sub(r"^```json\s*|^```\s*|```$", "", content, flags=re.MULTILINE).strip()
        parsed = json.loads(content)
        return parsed
    except Exception as e:
        return rule_based_fallback(user_text)

parse_intent = ask_ollama
