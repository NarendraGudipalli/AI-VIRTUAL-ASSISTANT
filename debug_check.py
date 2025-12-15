import sys
try:
    import dotenv
    import twilio
    import fastapi
    import uvicorn
    with open("debug_status.txt", "w") as f:
        f.write("SUCCESS: All imports worked.\n")
except ImportError as e:
    with open("debug_status.txt", "w") as f:
        f.write(f"ERROR: {e}\n")
except Exception as e:
    with open("debug_status.txt", "w") as f:
        f.write(f"EXCEPTION: {e}\n")
