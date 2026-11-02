import sys
from typing import Dict, Tuple

KEY_PATHS = [
    r"Software\Classes\*\shell\WhoLocked",
    r"Software\Classes\Directory\shell\WhoLocked",
]
MENU_LABEL = "Who is locking this?"


def get_command_string() -> str:
    """Build the command line executed when the context menu item is clicked."""
    return 'cmd.exe /k who-locked inspect "%1"'


def is_context_menu_installed() -> bool:
    """Check if the context menu entries exist in the user registry."""
    if sys.platform != "win32":
        return False

    import winreg

    for key_path in KEY_PATHS:
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_READ):
                pass
        except OSError:
            return False
    return True


def install_context_menu() -> Tuple[bool, str]:
    """Register the Explorer context menu item in HKEY_CURRENT_USER."""
    if sys.platform != "win32":
        return False, "Context menu registration is only supported on Windows."

    import winreg

    cmd = get_command_string()
    try:
        for key_path in KEY_PATHS:
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, key_path) as key:
                winreg.SetValueEx(key, "", 0, winreg.REG_SZ, MENU_LABEL)
                winreg.SetValueEx(key, "Icon", 0, winreg.REG_SZ, "shell32.dll,47")

            cmd_key_path = f"{key_path}\\command"
            with winreg.CreateKey(winreg.HKEY_CURRENT_USER, cmd_key_path) as cmd_key:
                winreg.SetValueEx(cmd_key, "", 0, winreg.REG_SZ, cmd)

        return True, "Successfully registered 'Who is locking this?' in Explorer context menu."
    except Exception as exc:
        return False, f"Failed to register context menu: {exc}"


def uninstall_context_menu() -> Tuple[bool, str]:
    """Remove the Explorer context menu item from HKEY_CURRENT_USER."""
    if sys.platform != "win32":
        return False, "Context menu removal is only supported on Windows."

    import winreg

    removed_any = False
    for key_path in KEY_PATHS:
        try:
            # Delete subkey 'command' first
            try:
                winreg.DeleteKey(winreg.HKEY_CURRENT_USER, f"{key_path}\\command")
            except FileNotFoundError:
                pass
            winreg.DeleteKey(winreg.HKEY_CURRENT_USER, key_path)
            removed_any = True
        except FileNotFoundError:
            pass
        except Exception as exc:
            return False, f"Failed to remove context menu entry {key_path}: {exc}"

    if removed_any:
        return True, "Removed 'Who is locking this?' from Explorer context menu."
    return True, "Context menu entry was not registered."
