<p align="center">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="images/file-folder-white.png">
    <source media="(prefers-color-scheme: light)" srcset="images/file-folder.png">
    <img src="images/file-folder.png" alt="Logo QrOpen" width="88">
  </picture>
</p>

<h1 align="center">QrOpen</h1>

<p align="center">
  Trasferimento file bidirezionale tra computer e smartphone.<br>
  Nessuna app sul telefono. Nessun cloud. Solo rete locale e QR code.
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-201d1d?style=flat-square&logo=python&logoColor=fdfcfc" alt="Python 3.10 o superiore">
  <img src="https://img.shields.io/badge/OS-Windows%20%7C%20Linux-201d1d?style=flat-square" alt="Windows e Linux">
  <img src="https://img.shields.io/badge/trasferimento-LAN-201d1d?style=flat-square" alt="Trasferimento su rete locale">
</p>

---

QrOpen apre un server HTTP temporaneo sul computer e mostra un QR code. Scansionalo dallo smartphone per scaricare i file condivisi o inviarne di nuovi al computer.

## `[+]` Funzioni

- `[+]` Trasferimento **PC → smartphone** tramite browser.
- `[+]` Trasferimento **smartphone → PC**, anche di più file.
- `[+]` QR code e indirizzo pronti a ogni avvio.
- `[+]` Scelta della cartella condivisa dalla GUI.
- `[+]` Upload e download in streaming, senza caricare l'intero file in memoria.
- `[+]` Rinomina automatica dei duplicati: `foto (1).jpg`, `foto (2).jpg`.
- `[+]` Interfaccia desktop minimale per Windows e Linux.
- `[+]` Nessun account, database, tunnel o servizio cloud.

## `[>]` Uso

1. Collega computer e smartphone alla stessa rete Wi-Fi.
2. Avvia QrOpen.
3. Scegli la cartella da condividere, se necessario.
4. Scansiona il QR code con lo smartphone.
5. Scarica i file elencati oppure seleziona quelli da inviare al computer.
6. Chiudi QrOpen per arrestare il server.

## `[$]` Installazione

### Windows — eseguibile

Scarica `QrOpen.exe` dalla sezione **Releases** ed eseguilo. Non richiede installazione né Python.

> L'eseguibile non è firmato digitalmente. Windows SmartScreen potrebbe mostrare un avviso al primo avvio.

### Windows — codice sorgente

Richiede Python 3.10 o superiore.

```powershell
py -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r .\Python\requirements.txt
.\.venv\Scripts\python.exe .\Python\qropen.py
```

### Linux — codice sorgente

Installa Python, `venv` e Tk. Su Debian/Ubuntu:

```bash
sudo apt install python3 python3-venv python3-tk
python3 -m venv .venv
./.venv/bin/python -m pip install -r Python/requirements.txt
./.venv/bin/python Python/qropen.py
```

## `[x]` Sicurezza

- Il link contiene un token casuale nuovo a ogni avvio.
- I nomi ricevuti vengono ripuliti per impedire percorsi esterni alla cartella condivisa.
- La lista esclude link simbolici e file `.part` incompleti.
- I file esistenti non vengono sovrascritti.
- Ogni upload è limitato a **10 GiB**.
- Il server termina quando chiudi l'app.

QrOpen usa HTTP locale senza cifratura. Chi possiede il QR o il link può leggere e caricare file finché il server resta aperto. Usalo solo su reti fidate e condividi una cartella senza dati riservati.

## `[?]` Verifica

Esegui i test dalla radice del progetto:

```bash
python -m unittest discover -s Python -p "test_*.py" -v
```

## `[#]` Build

PyInstaller crea un binario solo per il sistema sul quale viene eseguito. Compila su Windows per ottenere `.exe` e su Linux per ottenere il binario Linux.

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

## `[/]` Struttura

```text
QrOpen/
├── Python/
│   ├── qropen.py          # applicazione e server locale
│   ├── test_qropen.py     # test di trasferimento e sicurezza nomi
│   └── requirements.txt
├── FileExe/
│   └── QrOpen.spec        # configurazione PyInstaller
├── images/                # icone Windows e GUI
├── DESIGN.md              # linee guida visive
├── README.md
└── .gitignore
```

## `[+]` Contribuire

Issue e pull request sono benvenute. Mantieni le modifiche piccole, esegui i test e non includere cartelle `build/`, `dist/`, ambienti virtuali o file personali.

---

<p align="center"><code>[x] locale · temporaneo · bidirezionale</code></p>
