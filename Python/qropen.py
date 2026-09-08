import html
import mimetypes
import secrets
import socket
import sys
import threading
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from tkinter import Tk, filedialog, messagebox, ttk


APP_NAME = "QrOpen"
MAX_UPLOAD = 10 * 1024**3


def resource_path(*parts):
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    return base.joinpath(*parts)


def local_ip():
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.connect(("8.8.8.8", 80))
        return sock.getsockname()[0]
    except OSError:
        return "127.0.0.1"
    finally:
        sock.close()


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
                self.send_error(413, "File troppo grande o dimensione mancante")
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
                            raise ConnectionError("Upload interrotto")
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
            files = "".join(rows) or "<li>Nessun file</li>"
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
<html lang="it"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>QrOpen</title><style>
*{box-sizing:border-box}body{font:16px system-ui;margin:0;background:#f4f5f7;color:#171717}main{max-width:650px;margin:auto;padding:24px}
.box{background:white;border-radius:16px;padding:20px;box-shadow:0 4px 20px #0001;margin-bottom:18px}h1,h2{margin-top:0}
input{width:100%;padding:28px 12px;border:2px dashed #777;border-radius:12px}button{width:100%;margin-top:12px;padding:12px;border:0;border-radius:10px;background:#1769e0;color:white;font-weight:700}
button:disabled{opacity:.55}progress{width:100%;margin-top:12px}ul{list-style:none;padding:0;margin:0}li{display:flex;gap:12px;padding:11px 0;border-bottom:1px solid #ddd}a{color:#075dc7;overflow-wrap:anywhere}small{margin-left:auto;white-space:nowrap;color:#666}#status{min-height:24px}
</style></head><body><main><h1>QrOpen</h1><section class="box"><h2>Invia al PC</h2><input id="picker" type="file" multiple><button id="send">Invia</button><progress id="progress" value="0" max="1" hidden></progress><div id="status" role="status"></div></section><section class="box"><h2>Scarica dal PC</h2><ul>{{FILES}}</ul></section></main>
<script>
const picker=document.querySelector('#picker'),button=document.querySelector('#send'),bar=document.querySelector('#progress'),status=document.querySelector('#status');
button.onclick=async()=>{if(!picker.files.length)return;button.disabled=true;bar.hidden=false;let done=0;
try{for(const file of picker.files){status.textContent=`Invio ${file.name}...`;const response=await fetch('upload',{method:'POST',headers:{'X-Filename':encodeURIComponent(file.name),'Content-Type':'application/octet-stream'},body:file});if(!response.ok)throw Error(`${response.status} ${response.statusText}`);bar.value=++done/picker.files.length}status.textContent='Invio completato.';setTimeout(()=>location.reload(),500)}
catch(error){status.textContent=`Errore: ${error.message}`;button.disabled=false}};
</script></body></html>"""


class App:
    def __init__(self):
        self.root = Tk()
        self.root.title(APP_NAME)
        self.root.resizable(False, False)
        self.root.configure(background="#fdfcfc")
        desktop = Path.home() / "Desktop"
        self.folder = desktop if desktop.is_dir() else Path.home()
        self.token = secrets.token_urlsafe(12)
        self.server = ThreadingHTTPServer(("0.0.0.0", 0), make_handler(self.folder, self.token))
        self.url = f"http://{local_ip()}:{self.server.server_port}/{self.token}/"
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
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
        ttk.Label(frame, text="[ LAN FILE TRANSFER ]", style="Meta.TLabel", anchor="center").grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 18))

        hero = ttk.Frame(frame, padding=22, style="Hero.TFrame")
        hero.grid(row=2, column=0, columnspan=2)
        image = qrcode.make(self.url).resize((244, 244))
        self.qr_image = ImageTk.PhotoImage(image)
        ttk.Label(hero, image=self.qr_image, background=canvas).grid()

        ttk.Label(frame, text="Scansiona dal telefono", style="Body.TLabel", anchor="center").grid(row=3, column=0, columnspan=2, sticky="ew", pady=(18, 4))
        link = ttk.Label(frame, text=self.url, cursor="hand2", style="Link.TLabel", anchor="center")
        link.grid(row=4, column=0, columnspan=2, sticky="ew")
        link.bind("<Button-1>", lambda _event: webbrowser.open(self.url))

        ttk.Separator(frame, style="Rule.TSeparator").grid(row=5, column=0, columnspan=2, sticky="ew", pady=18)
        ttk.Label(frame, text="[+] CARTELLA CONDIVISA", style="Meta.TLabel", anchor="center").grid(row=6, column=0, columnspan=2, sticky="ew")
        self.folder_label = ttk.Label(frame, text=str(self.folder), width=40, style="Body.TLabel", anchor="center")
        self.folder_label.grid(row=7, column=0, columnspan=2, sticky="ew", pady=(4, 16))
        ttk.Button(frame, text="Cambia cartella", command=self.change_folder, style="Primary.TButton").grid(row=8, column=0, sticky="ew", padx=(0, 4))
        ttk.Button(frame, text="Chiudi", command=self.close, style="Secondary.TButton").grid(row=8, column=1, sticky="ew", padx=(4, 0))
        ttk.Label(frame, text="[x] server attivo", style="Meta.TLabel", anchor="center").grid(row=9, column=0, columnspan=2, sticky="ew", pady=(18, 0))

    def change_folder(self):
        chosen = filedialog.askdirectory(initialdir=self.folder)
        if not chosen:
            return
        self.folder = Path(chosen)
        self.server.RequestHandlerClass = make_handler(self.folder, self.token)
        self.folder_label.configure(text=str(self.folder))

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.root.destroy()

    def run(self):
        if local_ip() == "127.0.0.1":
            messagebox.showwarning(APP_NAME, "Rete locale non trovata. Collega PC e telefono alla stessa rete Wi-Fi.")
        self.root.mainloop()


if __name__ == "__main__":
    App().run()
