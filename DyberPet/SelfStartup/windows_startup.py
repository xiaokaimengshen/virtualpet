import os
import sys
from sys import platform

APP_NAME = "DyberPet"


def _run_key():
    import winreg
    return winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Run"


def _build_command():
    if getattr(sys, "frozen", False):
        return f'"{os.path.abspath(sys.executable)}"'

    pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    python_bin = pythonw if os.path.exists(pythonw) else sys.executable
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
    entry = os.path.join(repo_root, "run_DyberPet.py")
    return f'"{python_bin}" "{entry}"'


def is_enabled():
    if platform != "win32":
        return False
    try:
        import winreg
        hive, subkey = _run_key()
        with winreg.OpenKey(hive, subkey, 0, winreg.KEY_READ) as key:
            value, _ = winreg.QueryValueEx(key, APP_NAME)
            return bool(value)
    except Exception:
        return False


def set_enabled(enabled: bool):
    if platform != "win32":
        return False
    try:
        import winreg
        hive, subkey = _run_key()
        with winreg.OpenKey(hive, subkey, 0, winreg.KEY_SET_VALUE) as key:
            if enabled:
                winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, _build_command())
            else:
                try:
                    winreg.DeleteValue(key, APP_NAME)
                except FileNotFoundError:
                    pass
        return True
    except Exception:
        return False

