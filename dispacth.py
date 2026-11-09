import webbrowser
import datetime
import subprocess

APPS = {
    # Google Chrome
    "chrome": 'start chrome --profile-directory="Profile 2"',
    "googlechrome": 'start chrome --profile-directory="Profile 2"',

    # Notepad
    "notepad": "start notepad",

    # File Manager / Explorer (handles "file manager", "file maner", "explorer", "files")
    "filemanager": "start explorer",
    "filemaner": "start explorer",
    "fileexplorer": "start explorer",
    "explorer": "start explorer",
    "files": "start explorer",

    # VLC Media Player (verified at C:\Program Files\VideoLAN\VLC\vlc.exe)
    "vlc": r'start "" "C:\Program Files\VideoLAN\VLC\vlc.exe"',
    "vlcmediaplayer": r'start "" "C:\Program Files\VideoLAN\VLC\vlc.exe"',
    "videolan": r'start "" "C:\Program Files\VideoLAN\VLC\vlc.exe"',

    # Task Manager (handles "task manager", "task manaer", "taskmgr")
    "taskmanager": "start taskmgr",
    "taskmanaer": "start taskmgr",
    "taskmgr": "start taskmgr",

    # Command Prompt
    "cmd": "start cmd",
    "commandprompt": "start cmd",
    "terminal": "start cmd",

    # Antigravity IDE (verified at C:\Users\akhil\AppData\Local\Programs\Antigravity IDE\Antigravity IDE.exe)
    "antigravity": r'start "" "C:\Users\akhil\AppData\Local\Programs\Antigravity IDE\Antigravity IDE.exe"',
    "antigravityide": r'start "" "C:\Users\akhil\AppData\Local\Programs\Antigravity IDE\Antigravity IDE.exe"',
}

def open_app(params):
    app = params.get("app", "").lower().strip()
    app_clean = app.replace(" ", "").replace("_", "").replace("-", "")

    for key, command in APPS.items():
        if key in app_clean or app_clean in key:
            print(f"[Dispatcher] Launching: {key}")
            subprocess.Popen(command, shell=True)
            return

    print(f"[Dispatcher] App '{app}' not found in dispatcher")

def web_search(params):
    query = params.get("query", "")
    print(f"[Dispatcher] Searching web: {query}")
    webbrowser.open(f"https://google.com/search?q={query}")

def get_time(params):
    current_time = datetime.datetime.now().strftime("%I:%M %p")
    print(f"[Dispatcher] Current Time: {current_time}")

def get_date(params):
    current_date = datetime.datetime.now().strftime("%A, %B %d, %Y")
    print(f"[Dispatcher] Current Date: {current_date}")

dispatcher = {
    "open_app": open_app,
    "web_search": web_search,
    "get_time": get_time,
    "get_date": get_date,
}

def execute(intent_json):
    intent = intent_json.get("intent")
    params = intent_json.get("params", {})
    if intent in dispatcher:
        dispatcher[intent](params)
