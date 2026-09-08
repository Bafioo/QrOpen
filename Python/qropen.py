import html
import mimetypes
import queue
import re
import secrets
import shutil
import subprocess
import sys
import threading
import time
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tkinter import Tk, filedialog, messagebox, ttk


APP_NAME = "QrOpen"
MAX_UPLOAD = 10 * 1024**3
TUNNEL_URL = re.compile(r"https://[a-z0-9-]+\.trycloudflare\.com")


def resource_path(*parts):
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return base.joinpath(*parts)


def start_quick_tunnel(port, timeout=30):
    executable = shutil.which("cloudflared")
    if not executable:
        raise RuntimeError("cloudflared was not found. Install it and try again.")

    process = subprocess.Popen(
        [executable, "tunnel", "--url", f"http://127.0.0.1:{port}"],
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )
    lines = queue.Queue()

    def read_output():
        for line in process.stdout:
            lines.put(line)
        lines.put(None)

    threading.Thread(target=read_output, daemon=True).start()
    deadline = time.monotonic() + timeout
    public_url = None
    while time.monotonic() < deadline:
        try:
            line = lines.get(timeout=min(0.5, deadline - time.monotonic()))
        except queue.Empty:
            continue
        if line is None:
            break
        if match := TUNNEL_URL.search(line):
            public_url = match.group(0)
        if public_url and "Registered tunnel connection" in line:
            return process, public_url

    stop_process(process)
    raise RuntimeError("Cloudflare Quick Tunnel could not start. Check your internet connection and cloudflared configuration.")


def stop_process(process):
    if process and process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=3)
        except subprocess.TimeoutExpired:
            process.kill()


def available_name(folder, name):
    name = safe_name(name)
    candidate = folder / name
    stem, suffix = candidate.stem, candidate.suffix
    number = 1
    while candidate.exists() or candidate.with_suffix(candidate.suffix + ".part").exists():
        candidate = folder / f"{stem} ({number}){suffix}"
        number += 1
    return candidate


def safe_name(name):
    name = urllib.parse.unquote(name).replace("\\", "/").split("/")[-1]
    name = "".join(character for character in name if character >= " " and character != "\x7f")
    return name.strip(" .")[:240] or "file"


def format_size(size):
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}"
        size /= 1024


def make_handler(folder, token):
    class TransferHandler(BaseHTTPRequestHandler):
        def do_GET(self):
            path = urllib.parse.urlsplit(self.path).path
            if path.rstrip("/") == f"/{token}":
                self.send_page()
                return
            prefix = f"/{token}/files/"
            if path.startswith(prefix):
                self.send_file(urllib.parse.unquote(path[len(prefix) :]))
                return
            self.send_error(404)

        def do_POST(self):
            if urllib.parse.urlsplit(self.path).path != f"/{token}/upload":
                self.send_error(404)
                return
            try:
                size = int(self.headers.get("Content-Length", ""))
            except ValueError:
                size = -1
            if size < 0 or size > MAX_UPLOAD:
                self.send_error(413, "File too large or missing size")
                return

            name = self.headers.get("X-Filename", "file")
            target = available_name(folder, name)
            partial = target.with_suffix(target.suffix + ".part")
            remaining = size
            try:
                with partial.open("xb") as output:
                    while remaining:
                        chunk = self.rfile.read(min(1024 * 1024, remaining))
                        if not chunk:
                            raise ConnectionError("Upload interrupted")
                        output.write(chunk)
                        remaining -= len(chunk)
                partial.replace(target)
            except (OSError, ConnectionError) as error:
                partial.unlink(missing_ok=True)
                self.send_error(500, str(error))
                return
            self.send_response(201)
            self.end_headers()

        def send_page(self):
            rows = []
            for item in sorted(folder.iterdir(), key=lambda p: p.name.lower()):
                if not item.is_file() or item.is_symlink() or item.name.endswith(".part"):
                    continue
                quoted = urllib.parse.quote(item.name)
                label = html.escape(item.name)
                size = format_size(item.stat().st_size)
                rows.append(f'<li><a href="files/{quoted}" download>{label}</a><small>{size}</small></li>')
            files = "".join(rows) or "<li>No files</li>"
            page = PAGE.replace("{{FILES}}", files).encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(page)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", "default-src 'self'; style-src 'unsafe-inline'; script-src 'unsafe-inline'")
            self.end_headers()
            self.wfile.write(page)

        def send_file(self, name):
            target = folder / safe_name(name)
            if not target.is_file() or target.is_symlink():
                self.send_error(404)
                return
            size = target.stat().st_size
            self.send_response(200)
            self.send_header("Content-Type", mimetypes.guess_type(target.name)[0] or "application/octet-stream")
            self.send_header("Content-Length", str(size))
            self.send_header("Content-Disposition", f"attachment; filename*=UTF-8''{urllib.parse.quote(target.name)}")
            self.send_header("Cache-Control", "no-store, private")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            try:
                with target.open("rb") as source:
                    while chunk := source.read(1024 * 1024):
                        self.wfile.write(chunk)
            except (BrokenPipeError, ConnectionResetError):
                pass

        def log_message(self, _format, *_args):
            pass

    return TransferHandler


PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>QrOpen</title><style>
*{box-sizing:border-box}body{margin:0;background:#fdfcfc;color:#201d1d;font:16px/1.5 Consolas,"Liberation Mono","Courier New",monospace}main{max-width:680px;margin:auto;padding:48px 24px 64px}
header{margin-bottom:32px}.wordmark{font-size:38px;font-weight:700;line-height:1.2}header p{margin:8px 0 0;color:#646262;font-size:14px}
.terminal{margin-bottom:48px;padding:32px;background:#201d1d;color:#fdfcfc}.terminal strong{display:block;font-size:16px}.terminal p{margin:32px 0 4px;padding:10px 12px;border-radius:4px;background:#302c2c}.terminal small{color:#9a9898}
section.transfer{padding:24px 0;border-top:1px solid #dedada}h2{margin:0 0 16px;font-size:16px}input{width:100%;padding:12px;background:#f8f7f7;color:#201d1d;border:1px solid #dedada;border-radius:4px;font:inherit}
input:focus{background:#fdfcfc;border-color:#201d1d;outline:0}input::file-selector-button{margin-right:12px;padding:6px 12px;border:1px solid #646262;border-radius:4px;background:#fdfcfc;color:#201d1d;font:inherit;cursor:pointer}
button{width:100%;margin-top:12px;padding:6px 20px;border:1px solid #201d1d;border-radius:4px;background:#201d1d;color:#fdfcfc;font:500 16px/2 Consolas,"Liberation Mono","Courier New",monospace;cursor:pointer}button:active{background:#0f0000}button:disabled{background:#f1eeee;color:#9a9898;border-color:#f1eeee;cursor:default}
progress{width:100%;margin-top:12px;accent-color:#201d1d}#status{min-height:24px;margin-top:8px;color:#646262}ul{list-style:none;padding:0;margin:0}li{display:flex;gap:10px;padding:12px 0;border-bottom:1px solid #dedada}li::before{content:"[+]";font-weight:700}a{color:#201d1d;text-decoration:underline;overflow-wrap:anywhere}small{margin-left:auto;white-space:nowrap;color:#646262}
@media(max-width:640px){main{padding:32px 18px 48px}.wordmark{font-size:28px}.terminal{padding:24px 18px;margin-bottom:32px}li{font-size:14px}}
</style></head><body><main><header><div class="wordmark">QROPEN</div><p>[ INTERNET FILE TRANSFER ]</p></header><section class="terminal"><strong>[x] secure tunnel active</strong><p>computer &lt;-&gt; smartphone</p><small>works across different networks</small></section><section class="transfer"><h2>[+] Send to computer</h2><input id="picker" type="file" multiple><button id="send">Send files</button><progress id="progress" value="0" max="1" hidden></progress><div id="status" role="status"></div></section><section class="transfer"><h2>[+] Download from computer</h2><ul>{{FILES}}</ul></section></main>
<script>
const picker=document.querySelector('#picker'),button=document.querySelector('#send'),bar=document.querySelector('#progress'),status=document.querySelector('#status');
button.onclick=async()=>{if(!picker.files.length)return;button.disabled=true;bar.hidden=false;let done=0;
try{for(const file of picker.files){status.textContent=`Sending ${file.name}...`;const response=await fetch('upload',{method:'POST',headers:{'X-Filename':encodeURIComponent(file.name),'Content-Type':'application/octet-stream'},body:file});if(!response.ok)throw Error(`${response.status} ${response.statusText}`);bar.value=++done/picker.files.length}status.textContent='Transfer complete.';setTimeout(()=>location.reload(),500)}
catch(error){status.textContent=`Error: ${error.message}`;button.disabled=false}};
</script></body></html>"""


class App:
    def __init__(self):
        self.root = Tk()
        self.root.title(APP_NAME)
        self.root.resizable(False, False)
        self.root.configure(background="#fdfcfc")
        desktop = Path.home() / "Desktop"
        self.folder = desktop if desktop.is_dir() else Path.home()
        self.token = secrets.token_urlsafe(24)
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(self.folder, self.token))
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        try:
            self.tunnel, public_url = start_quick_tunnel(self.server.server_port)
        except RuntimeError as error:
            self.server.shutdown()
            self.server.server_close()
            messagebox.showerror(APP_NAME, str(error))
            self.root.destroy()
            raise SystemExit from error
        self.url = f"{public_url}/{self.token}/"
        self.build_ui()
        self.root.eval("tk::PlaceWindow . center")
        self.root.protocol("WM_DELETE_WINDOW", self.close)

    def build_ui(self):
        import qrcode
        from PIL import ImageTk

        self.window_icon = ImageTk.PhotoImage(file=resource_path("images", "file-folder-white.png"))
        self.root.iconphoto(True, self.window_icon)

        canvas = "#fdfcfc"
        ink = "#201d1d"
        muted = "#646262"
        hairline = "#dedada"
        mono = "Consolas"

        style = ttk.Style(self.root)
        style.theme_use("clam")
        style.configure("Main.TFrame", background=canvas)
        style.configure("Hero.TFrame", background=ink)
        style.configure("Rule.TSeparator", background=hairline)
        style.configure("Title.TLabel", background=canvas, foreground=ink, font=(mono, 24, "bold"))
        style.configure("Body.TLabel", background=canvas, foreground="#424245", font=(mono, 10))
        style.configure("Meta.TLabel", background=canvas, foreground=muted, font=(mono, 9))
        style.configure("Link.TLabel", background=canvas, foreground=ink, font=(mono, 9, "underline"))
        style.configure("Primary.TButton", background=ink, foreground=canvas, borderwidth=0, padding=(18, 9), font=(mono, 10, "bold"))
        style.map("Primary.TButton", background=[("pressed", "#0f0000"), ("active", "#302c2c")])
        style.configure("Secondary.TButton", background=canvas, foreground=ink, bordercolor="#646262", borderwidth=1, padding=(18, 8), font=(mono, 10))
        style.map("Secondary.TButton", background=[("pressed", "#f1eeee"), ("active", "#f8f7f7")])

        frame = ttk.Frame(self.root, padding=(28, 24), style="Main.TFrame")
        frame.grid()
        frame.columnconfigure((0, 1), weight=1, uniform="actions")
        ttk.Label(frame, text="QROPEN", style="Title.TLabel", anchor="center").grid(row=0, column=0, columnspan=2, sticky="ew")
        ttk.Label(frame, text="[ INTERNET FILE TRANSFER ]", style="Meta.TLabel", anchor="center").grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 18))

        hero = ttk.Frame(frame, padding=22, style="Hero.TFrame")
        hero.grid(row=2, column=0, columnspan=2)
        image = qrcode.make(self.url).resize((244, 244))
        self.qr_image = ImageTk.PhotoImage(image)
        ttk.Label(hero, image=self.qr_image, background=canvas).grid()

        ttk.Label(frame, text="Scan with your phone", style="Body.TLabel", anchor="center").grid(row=3, column=0, columnspan=2, sticky="ew", pady=(18, 4))
        link = ttk.Label(frame, text=self.url, cursor="hand2", style="Link.TLabel", anchor="center", justify="center", wraplength=300)
        link.grid(row=4, column=0, columnspan=2, sticky="ew")
        link.bind("<Button-1>", lambda _event: webbrowser.open(self.url))

        ttk.Separator(frame, style="Rule.TSeparator").grid(row=5, column=0, columnspan=2, sticky="ew", pady=18)
        ttk.Label(frame, text="[+] SHARED FOLDER", style="Meta.TLabel", anchor="center").grid(row=6, column=0, columnspan=2, sticky="ew")
        self.folder_label = ttk.Label(frame, text=str(self.folder), width=40, style="Body.TLabel", anchor="center")
        self.folder_label.grid(row=7, column=0, columnspan=2, sticky="ew", pady=(4, 16))
        ttk.Button(frame, text="Change folder", command=self.change_folder, style="Primary.TButton").grid(row=8, column=0, sticky="ew", padx=(0, 4))
        ttk.Button(frame, text="Close", command=self.close, style="Secondary.TButton").grid(row=8, column=1, sticky="ew", padx=(4, 0))
        ttk.Label(frame, text="[x] secure tunnel active", style="Meta.TLabel", anchor="center").grid(row=9, column=0, columnspan=2, sticky="ew", pady=(18, 0))

    def change_folder(self):
        chosen = filedialog.askdirectory(initialdir=self.folder)
        if not chosen:
            return
        self.folder = Path(chosen)
        self.server.RequestHandlerClass = make_handler(self.folder, self.token)
        self.folder_label.configure(text=str(self.folder))

    def close(self):
        stop_process(self.tunnel)
        self.server.shutdown()
        self.server.server_close()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


if __name__ == "__main__":
    App().run()
