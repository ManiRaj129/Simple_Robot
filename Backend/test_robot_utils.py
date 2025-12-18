#!/usr/bin/env python3
"""
Robot Utils Tester - Simple CLI tool

Usage:
  python test_robot_utils.py              # Show menu
  python test_robot_utils.py --listen     # Test voice listener
  python test_robot_utils.py --utils      # Test TTS, LLM, Detection
"""

import asyncio
import time
import sys
import subprocess

# ANSI colors
GREEN = "\033[92m"
YELLOW = "\033[93m"
RED = "\033[91m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"

# Store test results
results = []


def print_header(text):
    print(f"\n{BOLD}{CYAN}{'='*50}")
    print(f"  {text}")
    print(f"{'='*50}{RESET}\n")


def add_result(name, passed, duration, details=""):
    """Store result for summary."""
    results.append({
        "name": name,
        "passed": passed,
        "duration": duration,
        "details": details
    })
    status = f"{GREEN}✓ PASS{RESET}" if passed else f"{YELLOW}⚠ WARN{RESET}"
    print(f"  {name:<25} {status}  {duration:.2f}s  {details}")


def print_summary():
    """Print final test summary."""
    print(f"\n{BOLD}{'='*60}")
    print(f"  TEST SUMMARY")
    print(f"{'='*60}{RESET}")
    print(f"\n{'Name':<25} {'Status':<12} {'Time':<10} Details")
    print("-" * 60)
    
    total_time = 0
    passed = 0
    warned = 0
    
    for r in results:
        status = f"{GREEN}✓ PASS{RESET}" if r["passed"] else f"{YELLOW}⚠ WARN{RESET}"
        print(f"{r['name']:<25} {status:<20} {r['duration']:<10.2f} {r['details'][:25]}")
        total_time += r["duration"]
        if r["passed"]:
            passed += 1
        else:
            warned += 1
    
    print("-" * 60)
    print(f"\n{BOLD}Results:{RESET}")
    print(f"  {GREEN}✓ Passed:{RESET}  {passed}")
    print(f"  {YELLOW}⚠ Warnings:{RESET} {warned}")
    print(f"  Total time: {total_time:.2f}s\n")


async def test_tts():
    """Test TTS."""
    from robot_utils import speak, _have_piper
    
    print(f"\n{CYAN}[TTS]{RESET} Checking Piper...")
    if not _have_piper():
        add_result("speak()", False, 0, "Piper not available")
        return
    
    text = "Hello, testing speech."
    print(f"{CYAN}[TTS]{RESET} Speaking: \"{text}\"")
    
    start = time.perf_counter()
    success = await speak(text)
    duration = time.perf_counter() - start
    
    add_result("speak()", success, duration, text[:30])


async def test_llm():
    """Test LLM."""
    from robot_utils import ask_llm, LLM_AVAILABLE
    import json
    
    if not LLM_AVAILABLE:
        add_result("ask_llm()", False, 0, "LLM not available")
        return
    
    queries = [
        ("find a cup", "find"),
        ("turn left", "command"),
        ("follow me", "follow"),
        ("what time is it?", "response"),
    ]
    
    for query, expected_field in queries:
        print(f"\n{CYAN}[LLM]{RESET} Query: \"{query}\"")
        
        start = time.perf_counter()
        result = await ask_llm(query)
        duration = time.perf_counter() - start
        
        print(f"       {json.dumps(result)}")
        add_result(f"ask_llm({expected_field})", True, duration, query[:20])


async def test_detection():
    """Test object detection - shows all objects with position info."""
    from robot_utils import get_objects_at, cleanup_detector
    
    print(f"\n{CYAN}[Detection]{RESET} Initializing camera and YOLO...")
    
    start = time.perf_counter()
    objects = await get_objects_at()
    duration = time.perf_counter() - start
    
    if objects:
        print(f"       Found {len(objects)} object(s):")
        for obj in objects:
            print(f"         - {obj['name']}: {obj['direction']}, area={obj['area']:.0f}px², conf={obj['confidence']:.2f}")
        add_result("get_objects_at()", True, duration, f"{len(objects)} objects")
        
        # Show follow example: find largest person
        people = [o for o in objects if o["name"] == "person"]
        if people:
            largest = max(people, key=lambda x: x["area"])
            print(f"\n       [Follow example] Closest person: {largest['direction']}, area={largest['area']:.0f}px²")
    else:
        add_result("get_objects_at()", False, duration, "No objects detected")
    
    cleanup_detector()
    print(f"{CYAN}[Detection]{RESET} Camera released")


def test_listener():
    """Test the voice listener by running it."""
    print_header("Voice Listener Test")
    print(f"Running voice_listener.py in test mode...")
    print(f"Say '{BOLD}hey robot{RESET}' followed by a command.")
    print(f"Press Ctrl+C to stop.\n")
    
    try:
        subprocess.run([sys.executable, "voice_listener.py", "--test"])
    except KeyboardInterrupt:
        print(f"\n{CYAN}Listener stopped.{RESET}")


async def run_utils_tests():
    """Run TTS, LLM, Detection, and Follow tests."""
    results.clear()
    print_header("Robot Utils Tests")
    
    print(f"{BOLD}Testing TTS...{RESET}")
    await test_tts()
    
    print(f"\n{BOLD}Testing LLM...{RESET}")
    await test_llm()
    
    print(f"\n{BOLD}Testing Detection...{RESET}")
    await test_detection()
    
    print_summary()


def show_menu():
    """Show interactive menu."""
    print_header("Robot Utils Tester")
    print("  1. Test Utils (TTS, LLM, Detection)")
    print("  2. Test Voice Listener (wake word)")
    print("  q. Quit")
    print()
    
    choice = input(f"{BOLD}Select option:{RESET} ").strip().lower()
    
    if choice == "1":
        asyncio.run(run_utils_tests())
    elif choice == "2":
        test_listener()
    elif choice == "q":
        print("Goodbye!")
    else:
        print(f"{RED}Invalid option{RESET}")


def main():
    if "--listen" in sys.argv:
        test_listener()
    elif "--utils" in sys.argv:
        asyncio.run(run_utils_tests())
    else:
        show_menu()


if __name__ == "__main__":
    main()
