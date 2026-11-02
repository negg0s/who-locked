# who-locked

[![CI](https://github.com/negg0s/who-locked/actions/workflows/ci.yml/badge.svg)](https://github.com/negg0s/who-locked/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

A Windows command-line utility for finding which processes are holding locks on a file or folder. It can inspect open handles through the Windows Restart Manager API, scan directory trees for locked sub-files, monitor lock transitions in real time, or terminate offending processes and clean stubborn directories.

Requirements: Windows 10 or newer, Python 3.9 or newer.

## Why this exists

When Windows displays:

```text
The action can't be completed because the file is open in another program
```

it often does not say which process is responsible. Developers encounter this when removing `node_modules`, deleting virtual environments, clearing build caches, or overwriting binary outputs.

`who-locked` queries the Windows Restart Manager API (`rstrtmgr.dll`) to find the exact processes holding open handles on the file or directory.

## Install

```powershell
pip install -e . --no-cache-dir
```

For development:

```powershell
pip install -e . --no-cache-dir
pip install pytest --no-cache-dir
```

## Quick start

Inspect a locked file or folder:

```powershell
who-locked inspect "C:\path\to\locked_file.txt"
```

Example output:

```text
Target: C:\src\app\build\app.exe
Type:   File
Status: LOCKED by 1 process(es)

PID      NAME                     TYPE           MEMORY       USER
---------------------------------------------------------------------------
14820    app.exe                  Console        48.2 MB      DESKTOP\user
```

Add `--verbose` to view full executable paths, parent processes, and command-line arguments:

```powershell
who-locked inspect "C:\path\to\locked_file.txt" --verbose
```

Output formats for scripts and pipelines:

```powershell
# JSON format:
who-locked inspect "C:\path\to\locked_file.txt" --format json

# Space-separated PIDs only (pipe-friendly):
who-locked inspect "C:\path\to\locked_file.txt" --format pids

# CSV format:
who-locked inspect "C:\path\to\locked_file.txt" --format csv

# Quiet mode (exit code only: 0=free, 1=locked, 2=error):
who-locked inspect "C:\path\to\locked_file.txt" -q
```

Example pipe into PowerShell process termination:

```powershell
who-locked inspect "C:\path\to\locked_file.txt" --format pids | Stop-Process -Force
```

## Scanning directory trees

When deleting large directories (such as `node_modules` or `.venv`), nested files can block the folder from being removed. Use `tree` to locate each locked file:

```powershell
who-locked tree "C:\projects\my-app\node_modules"
```

Example output:

```text
Root:    C:\projects\my-app\node_modules
Scanned: 1240 file(s)

Found 2 locked item(s):

  * @esbuild\win32-x64\esbuild.exe
      -> PID 9120 (esbuild.exe, Console, 14.2 MB, parent: node.exe)
  * .cache\build.lock
      -> PID 4410 (node.exe, Console, 88.5 MB, parent: cmd.exe)

Summary by locking process:
  - PID 4410 (node.exe): 1 file(s)
  - PID 9120 (esbuild.exe): 1 file(s)
```

## Cleaning stubborn directories

When `rmdir /s /q` or `Remove-Item -Recurse -Force` fails because a background process holds a handle, use `clean`:

```powershell
who-locked clean "C:\projects\my-app\node_modules"
```

This scans the folder tree for locks, prompts to terminate locking processes, waits for handles to close, and deletes the directory.

Use `--dry-run` to preview without making any changes:

```powershell
who-locked clean "C:\projects\my-app\node_modules" --dry-run
```

Use `-y` or `--yes` to proceed without prompts:

```powershell
who-locked clean "C:\projects\my-app\node_modules" --yes
```

## Real-time lock monitoring

Watch a file or folder and track when locks are acquired and released:

```powershell
who-locked watch "C:\path\to\output.bin"
```

Example output:

```text
Watching C:\path\to\output.bin for lock changes (interval: 0.5s, press Ctrl+C to stop)...
[17:15:02.124] [LOCKED] Locked by: cl.exe (PID 8412)
[17:15:05.450] [FREE]   Target is free after 3.326s
```

Automation flags:
- `--exit-on-free`: Exit immediately when the target becomes free.
- `--exit-on-lock`: Exit immediately when a lock is detected.
- `--beep`: Sound console bell on state change.

## Releasing locks

Terminate processes holding a file:

```powershell
who-locked release "C:\path\to\locked_file.txt"
```

When multiple processes hold handles, use interactive mode to select which PIDs to terminate:

```powershell
who-locked release "C:\path\to\locked_file.txt" -i
```

Skip confirmation:

```powershell
who-locked release "C:\path\to\locked_file.txt" --yes
```

If a process ignores graceful termination, pass `-f` or `--force`:

```powershell
who-locked release "C:\path\to\locked_file.txt" --force --yes
```

## Safety guardrails

`who-locked` includes built-in protections against accidental system instability:
- Refuses to terminate protected system kernel processes (PID 0, PID 4).
- Refuses to terminate critical Windows processes (`smss.exe`, `csrss.exe`, `wininit.exe`, `winlogon.exe`, `services.exe`, `lsass.exe`).
- Refuses to terminate its own process.

## Waiting for locks to clear

In build scripts or CI pipelines, wait until a process finishes writing and releases its handle:

```powershell
who-locked wait "C:\path\to\output.bin" --timeout 15.0
```

Returns exit code 0 when the file is free, or exit code 1 if the timeout expires.

## Shell completion

Generate tab-completion script for PowerShell:

```powershell
who-locked completion powershell | Out-String | Invoke-Expression
```

Add that command to `$PROFILE` for permanent tab-completion.
For Bash:

```bash
eval "$(who-locked completion bash)"
```

## Explorer context menu integration

Add a "Who is locking this?" item to the Windows Explorer right-click context menu:

```powershell
who-locked menu install
```

This writes to `HKEY_CURRENT_USER\Software\Classes` and does not require administrator rights.

To remove it:

```powershell
who-locked menu uninstall
```

Check status:

```powershell
who-locked menu status
```

## Diagnostics

Verify Windows Restart Manager availability and permissions:

```powershell
who-locked doctor
```

Example output:

```text
Environment Diagnostics:
  [OK]   Operating System             Windows 11 (Build 10.0.26200)
  [OK]   Restart Manager API          rstrtmgr.dll loaded
  [OK]   Administrator Privileges     Standard User
  [OK]   Explorer Context Menu        Not installed (use 'who-locked menu install')

System is ready for lock inspection.
```

## Development

Run tests and check text compliance:

```powershell
pytest
python tools/check_text.py
```

## License

MIT. See [LICENSE](LICENSE).
