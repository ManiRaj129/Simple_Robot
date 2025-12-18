#!/usr/bin/env python3
"""
Groq LLM utilities with conversation memory.

Features:
- Remembers last 100 Q&A exchanges
- Handles multi-user context (different people's info kept separate)
- Automatically trims old memory
"""

import json
import os
import urllib.request
import urllib.error
from pathlib import Path
from datetime import datetime

GROQ_API_KEY = "[Placeholder Need to replace with the API KEY]"
GROQ_MODEL = "llama-3.3-70b-versatile"  

# Memory settings
MEMORY_FILE = Path(__file__).parent / "logs" / "robot_memory.json"
MAX_MEMORY_ENTRIES = 100

# Valid objects the detection model can find
VALID_OBJECTS = [
    "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train", "truck",
    "boat", "traffic light", "fire hydrant", "stop sign", "parking meter", "bench",
    "bird", "cat", "dog", "horse", "sheep", "cow", "elephant", "bear", "zebra",
    "giraffe", "backpack", "umbrella", "handbag", "tie", "suitcase", "frisbee",
    "skis", "snowboard", "sports ball", "kite", "baseball bat", "baseball glove",
    "skateboard", "surfboard", "tennis racket", "bottle", "wine glass", "cup",
    "fork", "knife", "spoon", "bowl", "banana", "apple", "sandwich", "orange",
    "broccoli", "carrot", "hot dog", "pizza", "donut", "cake", "chair", "couch",
    "potted plant", "bed", "dining table", "toilet", "tv", "laptop", "mouse",
    "remote", "keyboard", "cell phone", "microwave", "oven", "toaster", "sink",
    "refrigerator", "book", "clock", "vase", "scissors", "teddy bear", "hair drier",
    "toothbrush"
]

BASE_SYSTEM_PROMPT = f"""You are a robot assistant with memory of past conversations. You have a witty, playful, and humorous personality. Your responses should be clever, lighthearted, and funny whenever possible (but never mean or offensive). You must respond with ONLY a JSON object in this exact format:
{{
    "find": "<object>" or "",
    "follow": "true" or "",
    "emotion": "happy" or "sad" or "angry" or "neutral" or "surprised" or "confused",
    "response": "<your spoken response>",
    "command": "right" or "left" or "back" or "front" or ""
}}

Rules:
1. If user asks to find/look for an object that IS in the valid list, set "find" to the exact object name, "emotion" to "neutral", and "response" to a short, funny sentence like "Looking for <object>! If it runs away, I'll chase it!" Set "follow" and "command" to "".
2. If user asks to find something NOT in the valid list, set "find" to "", "emotion" to "sad", and "response" to a humorous apology like "Sorry, I can't recognize that object. My robot eyes must need an upgrade!"
3. If user asks to follow them, set "follow" to "true", "emotion" to "neutral", other fields "", and make the response playful (e.g., "Following you! I hope you know where we're going.").
4. If user asks to move/turn, set "command" to the direction and "response" to a brief, witty confirmation (e.g., "Turning left! I promise not to get dizzy.").
5. For general conversation, set "response" and "emotion" appropriately, and make the response clever, funny, or playful. Other fields are "".
6. ONLY these objects are valid for "find": {', '.join(VALID_OBJECTS)}
7. Keep responses short (1-2 sentences max), but always try to add a touch of humor or wit.
8. If the input is nonsense or doesn't make sense, set "emotion" to "neutral" and "response" to a funny clarification like ""

IMPORTANT - Memory & Multi-User Rules:
9. You have memory of past conversations shown below. Use this to remember facts people told you.
10. DIFFERENT PEOPLE may talk to you. If someone says "my name is X" or "my favorite Y is Z", that info belongs to THAT PERSON ONLY.
11. Do NOT ask for the user's name unless it is strictly required to answer a FIRST-PERSON question (one that uses pronouns like "my", "me", "mine", or asks about the speaker's personal facts). If the question is a generic/factual request (time, date, general facts, or requests about OTHER people), answer it without asking for the current speaker's name.

11a. If you mention a fact from memory about another person (e.g., "Ethan's favorite color is green"), DO NOT immediately follow that by asking the current speaker "Who are you?" unless the user's original question required identifying the speaker. In other words: mentioning someone else's memory is allowed, but do not convert that into a prompt for the current user's identity unless necessary to fulfill the original request.
12. If someone asks about another person's info (e.g., "what's Ethan's favorite food?"), you CAN answer if you know it from memory.
13. If you don't have info about something, say "I don't know that yet" or "I don't remember you telling me that."
14. CRITICAL: When someone says "my name is X" or "I'm X" IN THE SAME MESSAGE as a question, they are IDENTIFYING themselves so you can answer using X's stored info from memory. Look up X in memory and answer their question!
15. CRITICAL FOLLOW-UP RULE: If your previous response asked a clarifying question (who are you, which one, what do you mean, etc.) and the user's current input is a short answer to that clarification, you MUST use their answer to go back and properly address the ORIGINAL request/question from before. Don't just acknowledge the clarification - complete the original task!

Respond with ONLY the JSON, no other text."""


# ================== Memory Functions ==================
def load_memory() -> list:
    """Load conversation memory from file."""
    try:
        if MEMORY_FILE.exists():
            with open(MEMORY_FILE, "r") as f:
                return json.load(f)
    except Exception as e:
        print(f"[Memory] Load error: {e}")
    return []


def save_memory(memory: list):
    """Save conversation memory to file, keeping only last MAX_MEMORY_ENTRIES."""
    try:
        MEMORY_FILE.parent.mkdir(parents=True, exist_ok=True)
        # Keep only the most recent entries
        trimmed = memory[-MAX_MEMORY_ENTRIES:]
        with open(MEMORY_FILE, "w") as f:
            json.dump(trimmed, f, indent=2)
    except Exception as e:
        print(f"[Memory] Save error: {e}")


def add_to_memory(user_query: str, robot_response: str, speaker: str = "unknown"):
    """Add a Q&A pair to memory."""
    memory = load_memory()
    entry = {
        "timestamp": datetime.now().isoformat(),
        "speaker": speaker,
        "user": user_query,
        "robot": robot_response
    }
    memory.append(entry)
    save_memory(memory)
    return entry


def clear_memory():
    """Clear all memory."""
    save_memory([])
    print("[Memory] Cleared")


def format_memory_for_prompt(memory: list) -> str:
    """Format memory entries for inclusion in system prompt."""
    if not memory:
        return "No previous conversations."
    
    # Extract key facts from memory
    facts = []
    conversations = []
    
    for entry in memory:
        user_msg = entry.get("user", "").lower()
        robot_msg = entry.get("robot", "")
        
        # Try to extract facts like "X's favorite Y is Z"
        # Look for patterns like "my name is X and my favorite Y is Z"
        if "my name is" in user_msg or "i'm " in user_msg or "i am " in user_msg:
            # Extract name
            name = None
            if "my name is " in user_msg:
                name = user_msg.split("my name is ")[1].split()[0].strip(".,!?")
            elif "i'm " in user_msg:
                name = user_msg.split("i'm ")[1].split()[0].strip(".,!?")
            elif "i am " in user_msg:
                name = user_msg.split("i am ")[1].split()[0].strip(".,!?")
            
            if name:
                name = name.capitalize()
                # Look for "favorite X is Y" pattern
                if "favorite" in user_msg and " is " in user_msg:
                    try:
                        after_favorite = user_msg.split("favorite")[1]
                        thing = after_favorite.split(" is ")[0].strip()
                        value = after_favorite.split(" is ")[1].split()[0].strip(".,!?")
                        facts.append(f"FACT: {name}'s favorite {thing} is {value}")
                    except:
                        pass
        
        conversations.append(f"User: {entry.get('user', '')}")
        conversations.append(f"Robot: {robot_msg}")
    
    result = ""
    if facts:
        result += "KNOWN FACTS:\n" + "\n".join(facts) + "\n\n"
    result += "RECENT CONVERSATION:\n" + "\n".join(conversations[-20:])  # last 10 exchanges
    
    return result


def build_system_prompt() -> str:
    """Build system prompt with memory included."""
    memory = load_memory()
    memory_text = format_memory_for_prompt(memory)
    
    return f"""{BASE_SYSTEM_PROMPT}

=== CONVERSATION MEMORY (last {len(memory)} exchanges) ===
{memory_text}
=== END MEMORY ==="""


def ask_groq(query: str, speaker: str = "unknown") -> dict:
    """
    Query Groq and return parsed JSON.
    
    Args:
        query: The user's question/command
        speaker: Name of the person speaking (if known), or "unknown"
    
    Returns:
        dict with find, follow, emotion, response, command fields
    """
    if not GROQ_API_KEY:
        return {"error": "GROQ_API_KEY not set"}
    
    # Build prompt with memory
    system_prompt = build_system_prompt()
    
    # Include speaker info in the user message if known
    if speaker and speaker != "unknown":
        user_message = f"[Current speaker: {speaker}] {query}"
    else:
        user_message = f"[Current speaker: unknown] {query}"
    
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = json.dumps({
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ],
        "max_tokens": 200,
        "temperature": 0.2
    }).encode()
    
    try:
        req = urllib.request.Request(url, data=data, headers=headers)
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode())
            content = result["choices"][0]["message"]["content"].strip()
            
            # Parse JSON
            try:
                parsed = json.loads(content)
            except json.JSONDecodeError:
                # Try to extract JSON
                import re
                match = re.search(r'\{[^{}]*\}', content, re.DOTALL)
                if match:
                    parsed = json.loads(match.group())
                else:
                    return {"error": f"Invalid JSON: {content[:100]}"}
            
            # Ensure all fields exist with correct defaults
            response_dict = {
                "find": parsed.get("find", ""),
                "follow": parsed.get("follow", ""),
                "emotion": parsed.get("emotion", "neutral"),
                "response": parsed.get("response", ""),
                "command": parsed.get("command", "")
            }
            
            # Save to memory
            robot_response = response_dict.get("response", "")
            if robot_response:
                add_to_memory(query, robot_response, speaker)
            
            return response_dict
            
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.read().decode()[:100]}"}
    except Exception as e:
        return {"error": str(e)}


def ask_groq_simple(system_prompt: str, user_query: str, timeout: int = 15) -> dict:
    """Call Groq API with a custom system prompt and return parsed JSON or raw content.

    This bypasses the BASE_SYSTEM_PROMPT so callers can run small helper checks
    (for example: "is this follow-up related?"). Returns a dict parsed from JSON
    if possible, otherwise returns {"content": <raw string>} or {"error": ...}.
    """
    if not GROQ_API_KEY:
        return {"error": "GROQ_API_KEY not set"}

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json"
    }

    data = json.dumps({
        "model": GROQ_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_query}
        ],
        "max_tokens": 150,
        "temperature": 0.0
    }).encode()

    try:
        req = urllib.request.Request(url, data=data, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            result = json.loads(resp.read().decode())
            content = result["choices"][0]["message"]["content"].strip()
            try:
                parsed = json.loads(content)
                return parsed
            except json.JSONDecodeError:
                return {"content": content}
    except urllib.error.HTTPError as e:
        return {"error": f"HTTP {e.code}: {e.read().decode()[:200]}"}
    except Exception as e:
        return {"error": str(e)}


def main():
    """Interactive test mode."""
    import pprint
    while True:
        try:
            user_input = input("me: ").strip()
            if not user_input:
                continue
            if user_input.lower() in ("quit", "exit", "q"):
                break
            if user_input.lower() == "clear":
                clear_memory()
                continue
            if user_input.lower() == "debug":
                print("\n=== SYSTEM PROMPT BEING SENT ===")
                print(build_system_prompt())
                print("=== END ===\n")
                continue
            
            result = ask_groq(user_input)
            
            if "error" in result:
                print(f"error: {result['error']}\n")
            else:
                print(f"you: {result}\n")
                
        except KeyboardInterrupt:
            break


if __name__ == "__main__":
    main()