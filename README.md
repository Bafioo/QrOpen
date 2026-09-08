<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="images/file-folder-white.png">
    <source media="(prefers-color-scheme: light)" srcset="images/file-folder.png">
    <img src="images/file-folder.png" alt="QrOpen logo" width="88">
  </picture>
</p>

<h1 align="center">QrOpen</h1>

<p align="center">
  Two-way file transfer between computers and smartphones.<br>
  No phone app or account. Just a temporary HTTPS tunnel and a QR code.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-201d1d?style=flat-square&logo=python&logoColor=fdfcfc" alt="Python 3.10 or newer">
  <img src="https://img.shields.io/badge/OS-Windows%20%7C%20Linux-201d1d?style=flat-square" alt="Windows and Linux">
  <img src="https://img.shields.io/badge/transfer-Internet-201d1d?style=flat-square" alt="Internet transfer">
</p>

---

QrOpen starts a local HTTP server, exposes it through a temporary Cloudflare HTTPS URL, and displays a QR code. The computer and smartphone can use different networks.

```text
smartphone --HTTPS--> Cloudflare edge --Tunnel--> QrOpen on 127.0.0.1
```

## `[+]` Features

- `[+]` Transfer files from **computer to smartphone** through a browser.
- `[+]` Transfer one or more files from **smartphone to computer**.
- `[+]` Temporary public HTTPS address and QR code ready at every launch.
- `[+]` Choose the shared folder from the desktop interface.
- `[+]` Stream uploads and downloads without loading entire files into memory.
- `[+]` Rename duplicates automatically: `photo (1).jpg`, `photo (2).jpg`.
- `[+]` Minimal desktop interface for Windows and Linux.
- `[+]` No account, database, domain, port forwarding, or router setup.

## `[>]` Usage

1. Connect the computer to the Internet.
2. Start QrOpen and wait for the Quick Tunnel URL.
3. Select the folder to share if needed.
4. Scan the QR code with the smartphone.
5. Download listed files or select files to send to the computer.
6. Close QrOpen to stop the server.

## `[$]` Installation

### Windows — executable

QrOpen requires `cloudflared` on the computer. Install it first:

```powershell
winget install --id Cloudflare.cloudflared
```

Then download `QrOpen.exe` from the [latest release](https://github.com/Bafioo/QrOpen/releases/latest) and run it. Python and installation are not required.

> The executable is not digitally signed. Windows SmartScreen may display a warning on first launch.

### Windows — source code

Requires Python 3.10 or newer.

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r .\Python\requirements.txt
.\.venv\Scripts\python.exe .\Python\qropen.py
```

### Linux — source code

Install Python, `venv`, Tk, and [`cloudflared`](https://developers.cloudflare.com/tunnel/downloads/). On Debian or Ubuntu:

```bash
sudo apt install python3 python3-venv python3-tk
python3 -m venv .venv
./.venv/bin/python -m pip install -r Python/requirements.txt
./.venv/bin/python Python/qropen.py
```

## `[x]` Security

- The public link contains a new high-entropy random token for every launch.
- The origin server listens only on `127.0.0.1`; Cloudflare Tunnel is its only public route.
- Received filenames are sanitized to prevent access outside the shared folder.
- Symbolic links and incomplete `.part` files are excluded from listings.
- Existing files are never overwritten.
- Each uploaded file is limited to **100 MB**, matching Cloudflare's Free-plan request limit.
- The server stops when the application closes.

Traffic between the browser and Cloudflare uses HTTPS, and `cloudflared` creates the outbound tunnel to the local server. No inbound router port is opened. Cloudflare remains an intermediary for transferred data.

Anyone with the QR code or full link can read and upload files while the server is running. Share it only with trusted people, select a folder without sensitive data, and close QrOpen immediately after the transfer.

Cloudflare Quick Tunnels are intended for testing and development, provide no uptime SLA, and allow up to 200 concurrent in-flight requests. The public URL changes at every launch. Downloads have no fixed response-body limit, but connection speed and timeout constraints still apply. Use a named Cloudflare Tunnel for production.

Quick Tunnels may not start when `~/.cloudflared/config.yaml` exists. Move that configuration out of the directory temporarily or use a named tunnel instead.

## `[?]` Testing

Run tests from the project root:

```bash
python -m unittest discover -s Python -p "test_*.py" -v
```

## `[#]` Build

PyInstaller creates a binary only for the operating system running the build. Build on Windows for an `.exe`, or on Linux for a Linux binary.

```bash
python -m pip install pyinstaller
cd FileExe
python -m PyInstaller --clean QrOpen.spec
```

Output:

```text
FileExe/dist/QrOpen.exe   # Windows
FileExe/dist/QrOpen       # Linux
```

## `[/]` Structure

```text
QrOpen/
├── Python/
│   ├── qropen.py          # application and local server
│   ├── test_qropen.py     # transfer and filename safety tests
│   └── requirements.txt
├── FileExe/
│   └── QrOpen.spec        # PyInstaller configuration
├── images/                # Windows and GUI icons
├── DESIGN.md              # visual guidelines
├── README.md
└── .gitignore
```

## `[+]` Contributing

Issues and pull requests are welcome. Keep changes small, run the tests, and do not include `build/`, `dist/`, virtual environments, or personal files.

---

<p align="center"><code>[x] local · temporary · two-way</code></p>
