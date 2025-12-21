# GNU General Public License v3.0 or later
# This file is released under the GNU GPL v3 (or later) and may be redistributed under its terms.
# The perpose of this project was to try vibe coding, my original code is in https://github.com/RMNO21/Mort
import os
import sys
import json
import sqlite3
import threading
import queue
import time
import shutil
import subprocess
import re
from pathlib import Path
from datetime import datetime
from PIL import Image, ImageTk, ImageOps, ImageDraw
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
try:
    from ttkthemes import ThemedTk
    RootWindow = ThemedTk
except Exception:
    RootWindow = tk.Tk
APP_TITLE = "Media Manager Revamp"
SETTINGS_FILE = "mm_settings.json"
DB_FILE = "media_revamp.db"
THUMB_DIR = Path(".thumbs_revamp")
THUMB_DIR.mkdir(parents=True, exist_ok=True)
IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.webp', '.bmp', '.gif'}
VIDEO_EXTS = {'.mp4', '.mkv', '.mov', '.avi', '.webm', '.flv'}
AUDIO_EXTS = {'.mp3', '.aac', '.wav', '.flac'}
SUPPORTED = IMAGE_EXTS | VIDEO_EXTS | AUDIO_EXTS
DISPLAY_EXTS = VIDEO_EXTS
TV_RE = re.compile(r"(?ix)(?P<show>.+?)[. _-]*s(?P<season>\d{1,2})[. _-]*e(?P<episode>\d{1,2})")
DEFAULT_SETTINGS = {
    'theme': 'equilux',
    'thumbnail_size': 140,
    'columns': 5,
    'watch_folders': [],
    'scan_recursive': True,
    'hide_watched': False,
    'view_mode': 'list',
    'tree_column_widths': {
        '#0': 360,
        'type': 80,
        'size': 80,
        'watched': 80,
        'path': 320
    },
    'details_width': 240
}
WATCHED_LOG = "watched_log.json"
def normalize_path(p: str) -> str:
    try:
        return os.path.normcase(os.path.normpath(os.path.abspath(p)))
    except Exception:
        try:
            return os.path.normcase(os.path.normpath(p))
        except Exception:
            return p
def human_size(n):
    try:
        n = float(n)
    except Exception:
        return 'N/A'
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if n < 1024.0:
            return f"{n:3.1f} {unit}"
        n /= 1024.0
    return f"{n:.1f} PB"
def is_video(path: str) -> bool:
    return Path(path).suffix.lower() in VIDEO_EXTS
def is_image(path: str) -> bool:
    return Path(path).suffix.lower() in IMAGE_EXTS
def sanitize_filename(name: str) -> str:
    return re.sub(r'[\\/:*?"<>|]', '_', name).strip()
def open_target(path: str):
    try:
        if sys.platform.startswith('win'):
            os.startfile(path)
        elif sys.platform.startswith('darwin'):
            subprocess.Popen(['open', path])
        else:
            subprocess.Popen(['xdg-open', path])
    except Exception as e:
        messagebox.showerror('Open', str(e))
def reveal_target(path: str):
    try:
        if sys.platform.startswith('win'):
            subprocess.Popen(['explorer', '/select,', os.path.normpath(path)])
        elif sys.platform.startswith('darwin'):
            subprocess.Popen(['open', '-R', path])
        else:
            folder = os.path.dirname(path)
            subprocess.Popen(['xdg-open', folder])
    except Exception as e:
        messagebox.showerror('Reveal', str(e))
class DB:
    def __init__(self, path=DB_FILE):
        self.path = path
        self.conn = sqlite3.connect(self.path, check_same_thread=False)
        self._init()
        self.lock = threading.Lock()
        try:
            self.watched_map = self._load_watched_log()
        except Exception:
            self.watched_map = {}
    def _init(self):
        c = self.conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS media (
            path TEXT PRIMARY KEY,
            filename TEXT,
            mtime REAL,
            size INTEGER,
            media_type TEXT,
            show_name TEXT,
            season INTEGER,
            episode INTEGER,
            watched INTEGER DEFAULT 0
        )''')
        c.execute('CREATE INDEX IF NOT EXISTS idx_show ON media(show_name)')
        self.conn.commit()
    def _load_watched_log(self):
        p = Path(WATCHED_LOG)
        try:
            if not p.exists():
                p.write_text(json.dumps({}), encoding='utf-8')
                return {}
            data = json.loads(p.read_text(encoding='utf-8') or '{}')
            out = {}
            if isinstance(data, dict):
                for k, v in data.items():
                    try:
                        np = normalize_path(k)
                    except Exception:
                        np = k
                    if isinstance(v, dict):
                        watched = int(v.get('watched', 0))
                        name = v.get('name') or os.path.basename(k)
                    else:
                        try:
                            watched = int(v)
                        except Exception:
                            watched = 0
                        name = os.path.basename(k)
                    out[np] = {'watched': watched, 'name': name}
            return out
        except Exception:
            try:
                p.write_text(json.dumps({}), encoding='utf-8')
            except Exception:
                pass
            return {}
    def _save_watched_log(self):
        try:
            Path(WATCHED_LOG).write_text(json.dumps(self.watched_map, indent=2), encoding='utf-8')
        except Exception:
            pass
    def get(self, path: str):
        np = normalize_path(path)
        c = self.conn.cursor()
        c.execute('SELECT path,filename,mtime,size,media_type,show_name,season,episode,watched FROM media WHERE path=?', (np,))
        r = c.fetchone()
        return self._row_to_dict(r) if r else None
    def upsert(self, info: dict):
        with self.lock:
            try:
                info['path'] = normalize_path(info.get('path') or '')
            except Exception:
                info['path'] = info.get('path') or ''
            try:
                w = info.get('watched', None)
                if w is None:
                    entry = self.watched_map.get(info['path'])
                    if entry is not None:
                        w = int(entry.get('watched', 0))
                    else:
                        fn = info.get('filename') or os.path.basename(info.get('path') or '')
                        found = 0
                        for v in self.watched_map.values():
                            if v.get('name') == fn:
                                found = int(v.get('watched', 0))
                                break
                        w = found
                else:
                    w = int(w)
            except Exception:
                w = 0
            c = self.conn.cursor()
            c.execute('''INSERT OR REPLACE INTO media (path,filename,mtime,size,media_type,show_name,season,episode,watched)
						 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''', (
				info['path'], info['filename'], info['mtime'], info['size'], info['media_type'], info.get('show_name'), info.get('season'), info.get('episode'), int(w)
			))
            self.conn.commit()
            try:
                if info.get('watched', None) is not None or info['path'] in self.watched_map:
                    self.watched_map[info['path']] = {'watched': int(w), 'name': info.get('filename') or os.path.basename(info.get('path') or '')}
                    self._save_watched_log()
            except Exception:
                pass
    def delete(self, path: str):
        with self.lock:
            np = normalize_path(path)
            self.conn.execute('DELETE FROM media WHERE path=?', (np,))
            try:
                if np in getattr(self, 'watched_map', {}):
                    self.watched_map.pop(np, None)
                    self._save_watched_log()
            except Exception:
                pass
            self.conn.commit()
    def all(self):
        c = self.conn.cursor()
        c.execute('SELECT path,filename,mtime,size,media_type,show_name,season,episode,watched FROM media ORDER BY filename COLLATE NOCASE')
        rows = c.fetchall()
        return [self._row_to_dict(r) for r in rows]
    def search(self, q=None):
        c = self.conn.cursor()
        if q:
            q_like = f"%{q}%"
            c.execute('SELECT path,filename,mtime,size,media_type,show_name,season,episode,watched FROM media WHERE filename LIKE ? OR show_name LIKE ? ORDER BY filename COLLATE NOCASE', (q_like, q_like))
        else:
            c.execute('SELECT path,filename,mtime,size,media_type,show_name,season,episode,watched FROM media ORDER BY filename COLLATE NOCASE')
        return [self._row_to_dict(r) for r in c.fetchall()]
    def set_watched(self, path: str, watched: int):
        np = normalize_path(path)
        with self.lock:
            try:
                self.conn.execute('UPDATE media SET watched=? WHERE path=?', (int(watched), np))
                self.conn.commit()
            except Exception:
                try:
                    self.conn.rollback()
                except Exception:
                    pass
            try:
                self.watched_map[np] = {'watched': int(watched), 'name': os.path.basename(np)}
                self._save_watched_log()
            except Exception:
                pass
    def update_path(self, old: str, new: str):
        old_n = normalize_path(old)
        new_n = normalize_path(new)
        with self.lock:
            c = self.conn.cursor()
            c.execute('SELECT filename,mtime,size,media_type,show_name,season,episode,watched FROM media WHERE path=?', (old_n,))
            row = c.fetchone()
            if not row:
                return
            filename, mtime, size, media_type, show_name, season, episode, watched = row
            try:
                c.execute(
                    'INSERT OR REPLACE INTO media (path,filename,mtime,size,media_type,show_name,season,episode,watched) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                    (new_n, filename, mtime, size, media_type, show_name, season, episode, watched)
                )
                try:
                    if getattr(self, 'watched_map', None) and old_n in self.watched_map:
                        entry = self.watched_map.pop(old_n)
                        entry['name'] = os.path.basename(new_n)
                        self.watched_map[new_n] = entry
                        self._save_watched_log()
                except Exception:
                    pass
                if old_n != new_n:
                    c.execute('DELETE FROM media WHERE path=? AND path<>?', (old_n, new_n))
                self.conn.commit()
            except Exception:
                try:
                    c.execute('DELETE FROM media WHERE path=?', (old_n,))
                    c.execute(
                        'INSERT OR REPLACE INTO media (path,filename,mtime,size,media_type,show_name,season,episode,watched) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
                        (new_n, filename, mtime, size, media_type, show_name, season, episode, watched)
                    )
                    try:
                        if getattr(self, 'watched_map', None) and old_n in self.watched_map:
                            entry = self.watched_map.pop(old_n)
                            entry['name'] = os.path.basename(new_n)
                            self.watched_map[new_n] = entry
                            self._save_watched_log()
                    except Exception:
                        pass
                    self.conn.commit()
                except Exception:
                    self.conn.rollback()
    def _row_to_dict(self, r):
        return {
            'path': r[0], 'filename': r[1], 'mtime': r[2], 'size': r[3], 'media_type': r[4],
            'show_name': r[5], 'season': r[6], 'episode': r[7], 'watched': bool(r[8])
        }
class ThumbCache:
    def __init__(self, base=THUMB_DIR, size=140):
        self.base = Path(base)
        self.base.mkdir(parents=True, exist_ok=True)
        self.size = size
        self.mem = {}
    def thumb_path(self, path: str) -> Path:
        try:
            n = normalize_path(path)
            h = abs(hash(n))
        except Exception:
            h = abs(hash(path))
        return self.base / f"{h}_{self.size}.png"
    def get(self, path: str):
        if path in self.mem:
            return self.mem[path]
        tp = self.thumb_path(path)
        if tp.exists():
            try:
                im = Image.open(tp)
                tkimg = ImageTk.PhotoImage(im)
                self.mem[path] = tkimg
                return tkimg
            except Exception:
                return None
        return None
    def generate(self, path: str):
        tp = self.thumb_path(path)
        try:
            if is_image(path):
                img = Image.open(path).convert('RGB')
                img.thumbnail((self.size, self.size), Image.LANCZOS)
                img = ImageOps.fit(img, (self.size, self.size), Image.LANCZOS)
            else:
                img = Image.new('RGB', (self.size, self.size), (40, 40, 40))
                draw = ImageDraw.Draw(img)
                if is_video(path):
                    w, h = img.size
                    draw.polygon(((w*0.3, h*0.2), (w*0.3, h*0.8), (w*0.75, h*0.5)), fill=(255,255,255))
                else:
                    draw.text((8, 8), Path(path).suffix.replace('.', '').upper(), fill=(200,200,200))
            img.save(tp, 'PNG')
            return True
        except Exception:
            try:
                img = Image.new('RGB', (self.size, self.size), (50,50,50))
                img.save(tp, 'PNG')
                return True
            except Exception:
                return False
    def set_size(self, size: int):
        if size != self.size:
            self.size = size
            self.mem.clear()
class ThumbWorker(threading.Thread):
    def __init__(self, q: queue.Queue, cache: ThumbCache, callback):
        super().__init__(daemon=True)
        self.q = q
        self.cache = cache
        self.callback = callback
        self._stop = threading.Event()
    def run(self):
        while not self._stop.is_set():
            try:
                path = self.q.get(timeout=0.5)
            except queue.Empty:
                continue
            try:
                self.cache.generate(path)
                if self.callback:
                    try:
                        self.callback(path)
                    except Exception:
                        pass
            finally:
                try:
                    self.q.task_done()
                except Exception:
                    pass
    def stop(self):
        self._stop.set()
class Scanner(threading.Thread):
    def __init__(self, folders: list, db: DB, thumb_q: queue.Queue, recursive=True, ui_progress=None):
        super().__init__(daemon=True)
        self.folders = folders
        self.db = db
        self.thumb_q = thumb_q
        self.recursive = recursive
        self._stop = threading.Event()
        self.ui_progress = ui_progress
    def run(self):
        total = 0
        for folder in self.folders:
            if self._stop.is_set():
                break
            if not self.recursive:
                try:
                    with os.scandir(folder) as it:
                        for ent in it:
                            if self._stop.is_set(): break
                            if not ent.is_file(): continue
                            fn = ent.name
                            ext = Path(fn).suffix.lower()
                            if ext not in DISPLAY_EXTS:
                                continue
                            path = ent.path
                            try:
                                st = ent.stat()
                            except Exception:
                                continue
                            self._process_file(path, fn, st)
                            total += 1
                            if self.ui_progress and total % 10 == 0:
                                try:
                                    self.ui_progress(total, path)
                                except Exception:
                                    pass
                except Exception:
                    continue
            else:
                for root, dirs, files in os.walk(folder):
                    if self._stop.is_set():
                        break
                    for fn in files:
                        path = os.path.join(root, fn)
                        ext = Path(fn).suffix.lower()
                        if ext not in DISPLAY_EXTS:
                            continue
                        try:
                            st = os.stat(path)
                        except Exception:
                            continue
                        self._process_file(path, fn, st)
                        total += 1
                        if self.ui_progress and total % 10 == 0:
                            try:
                                self.ui_progress(total, path)
                            except Exception:
                                pass
                    if self._stop.is_set():
                        break
    def _clean_show_name(self, raw: str):
        s = re.sub(r'[._\-]+', ' ', raw).strip()
        s = re.sub(r'[\(\)\[\]\-]+$', '', s).strip()
        return s
    def _process_file(self, path, fn, st):
        norm = normalize_path(path)
        info = {
            'path': norm,
            'filename': fn,
            'mtime': st.st_mtime,
            'size': st.st_size,
            'media_type': 'video' if is_video(path) else ('image' if is_image(path) else 'audio'),
            'show_name': None,
            'season': None,
            'episode': None,
            'watched': None
        }
        m = TV_RE.search(fn)
        if m:
            raw = m.group('show')
            info['show_name'] = self._clean_show_name(raw)
            info['season'] = int(m.group('season'))
            info['episode'] = int(m.group('episode'))
        self.db.upsert(info)
        try:
            self.thumb_q.put_nowait(norm)
        except queue.Full:
            pass
    def stop(self):
        self._stop.set()
class App:
    def __init__(self, root=None):
        self.root = root or RootWindow()
        try:
            self.root.set_theme(DEFAULT_SETTINGS.get('theme','equilux'))
        except Exception:
            pass
        self.root.title(APP_TITLE)
        self.root.geometry('1200x800')
        self._apply_style()
        self.settings = self.load_settings()
        for k,v in DEFAULT_SETTINGS.items():
            if k not in self.settings:
                self.settings[k] = v
        self.db = DB()
        self.thumb_q = queue.Queue(maxsize=2000)
        self.thumb_cache = ThumbCache(size=self.settings.get('thumbnail_size', 140))
        self.thumb_worker = ThumbWorker(self.thumb_q, self.thumb_cache, self.on_thumb_ready)
        self.thumb_worker.start()
        self.items = []
        self.view_mode = self.settings.get('view_mode', 'list')
        self.selected_path = None
        self._resize_after_id = None
        self._save_cols_after = None
        self._progress_win = None
        self._progress_bar = None
        self._progress_label = None
        self._scanner_thread = None
        self._scanner_monitor = None
        self._expanded = set()
        self.build_ui()
        self.refresh_items()
        self.root.bind('<Configure>', self.on_config_resize)
    def _apply_style(self):
        bg = '#0f1724'
        panel = '#0b1220'
        card = '#0f1728'
        text = '#e6eef6'
        muted = '#94a3b8'
        heading = '#dff7ff'
        accent = '#39c0ff'
        accent_dark = '#1aa0d6'
        border = '#122033'
        self.colors = {
            'bg': bg, 'panel': panel, 'card': card, 'text': text,
            'muted': muted, 'heading': heading, 'accent': accent,
            'accent_dark': accent_dark, 'border': border
        }
        style = ttk.Style(self.root)
        try:
            style.theme_use('clam')
        except Exception:
            pass
        try:
            self.root.configure(bg=bg)
        except Exception:
            pass
        base_font = ('Segoe UI', 10)
        heading_font = ('Segoe UI', 11, 'bold')
        style.configure('TFrame', background=panel)
        style.configure('Card.TFrame', background=card, relief='flat')
        style.configure('TLabel', background=panel, foreground=text, font=base_font)
        style.configure('Heading.TLabel', background=panel, foreground=heading, font=heading_font)
        style.configure('Muted.TLabel', background=panel, foreground=muted, font=base_font)
        style.configure('TButton',
                        background=card,
                        foreground=text,
                        font=('Segoe UI Semibold', 10),
                        padding=(10, 6),
                        relief='flat')
        style.map('TButton',
                  background=[('active', border), ('pressed', border)],
                  foreground=[('disabled', muted)])
        style.configure('Accent.TButton',
                        background=accent,
                        foreground='#001217',
                        font=('Segoe UI Semibold', 10),
                        padding=(10, 6))
        style.map('Accent.TButton',
                  background=[('active', accent_dark), ('pressed', accent_dark)])
        style.configure('Dark.TEntry', fieldbackground=card, background=card, foreground=text)
        style.configure('Dark.TCombobox', fieldbackground=card, background=card, foreground=text)
        style.configure('TCombobox', fieldbackground=card, background=card, foreground=text)
        try:
            style.element_create('CustomDownArrow', 'image', '::tk::icons::downarrow')
        except Exception:
            pass
        style.configure('Treeview',
                        background=panel,
                        fieldbackground=panel,
                        foreground=text,
                        rowheight=28,
                        font=base_font,
                        bordercolor=border)
        style.configure('Treeview.Heading',
                        background=card,
                        foreground=heading,
                        font=heading_font,
                        relief='flat')
        style.map('Treeview',
                  background=[('selected', accent)],
                  foreground=[('selected', '#001217')])
        style.configure('Horizontal.TProgressbar',
                        troughcolor=panel,
                        background=accent,
                        thickness=8)
        style.configure('Vertical.TScrollbar',
                        troughcolor=panel,
                        background=card,
                        arrowcolor=muted,
                        bordercolor=border)
        style.configure('Small.TLabel', background=panel, foreground=muted, font=('Segoe UI', 9))
        self.style = style
    def load_settings(self):
        p = Path(SETTINGS_FILE)
        if p.exists():
            try:
                return json.loads(p.read_text(encoding='utf-8'))
            except Exception:
                pass
        return DEFAULT_SETTINGS.copy()
    def save_settings(self):
        try:
            Path(SETTINGS_FILE).write_text(json.dumps(self.settings, indent=2), encoding='utf-8')
        except Exception:
            pass
    def build_ui(self):
        top = ttk.Frame(self.root)
        top.pack(side='top', fill='x', padx=8, pady=8)
        ttk.Button(top, text='Add Folder', command=self.add_folder).pack(side='left')
        ttk.Button(top, text='Manage Folders', command=self.manage_folders).pack(side='left', padx=6)
        ttk.Button(top, text='Refresh', command=self.full_refresh).pack(side='left', padx=6)
        ttk.Label(top, text='Show:').pack(side='left', padx=(12,4))
        self.top_filter = tk.StringVar(value='All')
        sel_frame = ttk.Frame(top, style='Card.TFrame')
        sel_frame.pack(side='left', padx=(0,8))
        self.show_buttons = {}
        for val in ('All', 'Movies', 'TV Shows'):
            lbl = tk.Label(sel_frame, text=val, bd=0, padx=12, pady=6, cursor='hand2',
                           bg=self.colors['card'], fg=self.colors['text'], font=('Segoe UI', 10, 'normal'))
            lbl.pack(side='left', padx=(0,8))
            lbl.bind('<Button-1>', lambda e, v=val: self._on_show_select(v))
            self.show_buttons[val] = lbl
        self.top_filter.trace_add('write', lambda *a: self.refresh_items())
        try:
            self._refresh_show_buttons()
        except Exception:
            pass
        ttk.Button(top, text='Organize', command=self.organize_action).pack(side='right')
        mid = ttk.Frame(self.root)
        mid.pack(side='top', fill='x', padx=8)
        ttk.Label(mid, text='Search:').pack(side='left')
        self.search_var = tk.StringVar()
        e = ttk.Entry(mid, textvariable=self.search_var)
        e.pack(side='left', fill='x', expand=True, padx=6)
        e.bind('<Return>', lambda e: self.refresh_items())
        ttk.Button(mid, text='Search', command=self.refresh_items).pack(side='left', padx=6)
        main = ttk.PanedWindow(self.root, orient='horizontal')
        main.pack(fill='both', expand=True, padx=8, pady=8)
        self.left_frame = ttk.Frame(main)
        self.left_frame.pack(fill='both', expand=True)
        cols = ('type','size','watched','path')
        self.tree = ttk.Treeview(self.left_frame, columns=cols, show='tree headings', style='Treeview')
        self.tree.heading('#0', text='Title')
        self.tree.column('#0', width=int(self.settings.get('tree_column_widths', {}).get('#0', 360)), anchor='w', stretch=True)
        self.tree.heading('type', text='Type')
        self.tree.heading('size', text='Size')
        self.tree.heading('watched', text='Watched')
        self.tree.heading('path', text='Path')
        for k in cols:
            self.tree.column(k, width=int(self.settings.get('tree_column_widths', {}).get(k, DEFAULT_SETTINGS['tree_column_widths'].get(k, 100))), anchor='w', stretch=False)
        self.tree.pack(fill='both', expand=True, side='left')
        self.tree.bind('<Double-1>', self.on_tree_double)
        self.tree.bind('<Button-3>', self.on_tree_right)
        self.tree.bind('<ButtonRelease-1>', self._on_tree_col_release)
        self.tree_scroll = ttk.Scrollbar(self.left_frame, orient='vertical', command=self.tree.yview)
        self.tree.configure(yscrollcommand=self.tree_scroll.set)
        self.tree_scroll.pack(side='right', fill='y')
        self.thumb_canvas = tk.Canvas(self.left_frame, bg='#000000', highlightthickness=0)
        self.thumb_scroll = ttk.Scrollbar(self.left_frame, orient='vertical', command=self.thumb_canvas.yview)
        self.thumb_inner = ttk.Frame(self.thumb_canvas)
        self.thumb_canvas.create_window((0,0), window=self.thumb_inner, anchor='nw')
        self.thumb_canvas.configure(yscrollcommand=self.thumb_scroll.set)
        self.thumb_inner.bind('<Configure>', lambda e: self.thumb_canvas.configure(scrollregion=self.thumb_canvas.bbox('all')))
        main.add(self.left_frame, weight=1)
        self.status = ttk.Label(self.root, text='Ready', relief='sunken', anchor='w')
        self.status.pack(side='bottom', fill='x')
        self.ctx = tk.Menu(self.root, tearoff=0)
        self.ctx.add_command(label='Open', command=self.ctx_open)
        self.ctx.add_command(label='Open file location', command=self.ctx_reveal)
        self.ctx.add_separator()
        self.ctx.add_command(label='Mark Watched', command=lambda: self.ctx_set_watched(1))
        self.ctx.add_command(label='Mark Unwatched', command=lambda: self.ctx_set_watched(0))
        self.ctx.add_separator()
        self.ctx.add_command(label='Remove from DB', command=self.ctx_remove)
        self.ctx.add_command(label='Delete file', command=self.ctx_delete)
        self.set_view_mode(self.view_mode)
    def _save_column_widths(self):
        widths = {}
        try:
            widths['#0'] = self.tree.column('#0', option='width')
            for c in ('type','size','watched','path'):
                widths[c] = self.tree.column(c, option='width')
            self.settings['tree_column_widths'] = widths
            self.save_settings()
        except Exception:
            pass
    def _on_tree_col_release(self, event=None):
        try:
            if getattr(self, '_save_cols_after', None):
                try:
                    self.root.after_cancel(self._save_cols_after)
                except Exception:
                    pass
            self._save_cols_after = self.root.after(250, self._save_column_widths)
        except Exception:
            pass
    def on_config_resize(self, event):
        if self._resize_after_id:
            try:
                self.root.after_cancel(self._resize_after_id)
            except Exception:
                pass
        self._resize_after_id = self.root.after(200, self._on_resize)
    def _on_resize(self):
        if self.view_mode == 'thumb':
            self.render_thumbnails()
    def add_folder(self):
        d = filedialog.askdirectory()
        if not d:
            return
        wf = self.settings.get('watch_folders', [])
        if d not in wf:
            wf.append(d)
            self.settings['watch_folders'] = wf
            self.save_settings()
            self.refresh_items()
    def manage_folders(self):
        wf = self.settings.get('watch_folders', [])
        win = tk.Toplevel(self.root)
        win.title('Manage Watch Folders')
        win.geometry('600x300')
        listbox = tk.Listbox(win, bg='#000000', fg='#ffffff')
        listbox.pack(fill='both', expand=True)
        for f in wf:
            listbox.insert('end', f)
        def remove():
            sel = listbox.curselection()
            if not sel: return
            idx = sel[0]
            wf.pop(idx)
            self.settings['watch_folders'] = wf
            self.save_settings()
            listbox.delete(idx)
        ttk.Button(win, text='Remove Selected', command=remove).pack(pady=6)
    def refresh_items(self):
        try:
            self._capture_expanded()
        except Exception:
            self._expanded = set()
        folders = self.settings.get('watch_folders', [])
        if folders:
            self._start_scanner(folders)
        q = self.search_var.get().strip()
        if q:
            rows = self.db.search(q)
        else:
            rows = self.db.all()
        tf = self.top_filter.get()
        filtered = []
        for r in rows:
            if not is_video(r['path']):
                continue
            if tf == 'All':
                filtered.append(r)
            elif tf == 'Movies':
                if r['show_name'] is None and r['media_type']=='video':
                    filtered.append(r)
            elif tf == 'TV Shows':
                if r['show_name'] is not None and r['media_type']=='video':
                    filtered.append(r)
        if self.settings.get('hide_watched'):
            filtered = [r for r in filtered if not r['watched']]
        self.items = filtered
        if self.view_mode == 'list':
            self.render_list()
            try:
                self._restore_expanded()
            except Exception:
                pass
        else:
            self.render_thumbnails()
    def _update_scanner_status(self, count, path):
        try:
            name = os.path.basename(path) if path else ''
            self.status.config(text=f"Scanning... {count} files ({name})")
        except Exception:
            pass
    def _refresh_ui_only(self):
        try:
            q = self.search_var.get().strip()
            rows = self.db.search(q) if q else self.db.all()
            tf = self.top_filter.get()
            filtered = []
            for r in rows:
                if not is_video(r['path']):
                    continue
                if tf == 'All':
                    filtered.append(r)
                elif tf == 'Movies':
                    if r['show_name'] is None and r['media_type']=='video':
                        filtered.append(r)
                elif tf == 'TV Shows':
                    if r['show_name'] is not None and r['media_type']=='video':
                        filtered.append(r)
            if self.settings.get('hide_watched'):
                filtered = [r for r in filtered if not r['watched']]
            self.items = filtered
            if self.view_mode == 'list':
                try:
                    self.render_list()
                    self._restore_expanded()
                except Exception:
                    self.render_list()
            else:
                self.render_thumbnails()
        except Exception:
            pass
    def _start_scanner(self, folders):
        try:
            if getattr(self, '_scanner_thread', None) and getattr(self._scanner_thread, 'is_alive', lambda: False)():
                try:
                    self._scanner_thread.stop()
                except Exception:
                    pass
        except Exception:
            pass
        self._scanner_thread = Scanner(
            folders,
            self.db,
            self.thumb_q,
            recursive=self.settings.get('scan_recursive', True),
            ui_progress=lambda count, path: self.root.after(0, lambda: self._update_scanner_status(count, path))
        )
        self._scanner_thread.start()
        def monitor(sc):
            try:
                self.root.after(0, lambda: self.status.config(text='Scanning...'))
                while sc.is_alive():
                    time.sleep(0.25)
            finally:
                try:
                    self.root.after(0, lambda: (self._refresh_ui_only(), self.status.config(text='Ready')))
                except Exception:
                    pass
        self._scanner_monitor = threading.Thread(target=monitor, args=(self._scanner_thread,), daemon=True)
        self._scanner_monitor.start()
    def _synchronous_scan(self, progress_callback=None):
        folders = self.settings.get('watch_folders', [])
        recursive = self.settings.get('scan_recursive', True)
        results = []
        total_seen = 0
        for folder in folders:
            if not os.path.isdir(folder):
                continue
            if not recursive:
                try:
                    with os.scandir(folder) as it:
                        for ent in it:
                            if not ent.is_file(): continue
                            fn = ent.name
                            ext = Path(fn).suffix.lower()
                            if ext not in SUPPORTED: continue
                            try:
                                st = ent.stat()
                            except Exception:
                                continue
                            info = self._file_info_from_stat(ent.path, fn, st)
                            results.append(info)
                            total_seen += 1
                            if progress_callback and (total_seen % 20 == 0):
                                progress_callback(total_seen, info['path'])
                except Exception:
                    continue
            else:
                for root, dirs, files in os.walk(folder):
                    for fn in files:
                        path = os.path.join(root, fn)
                        ext = Path(fn).suffix.lower()
                        if ext not in SUPPORTED: continue
                        try:
                            st = os.stat(path)
                        except Exception:
                            continue
                        info = self._file_info_from_stat(path, fn, st)
                        results.append(info)
                        total_seen += 1
                        if progress_callback and (total_seen % 20 == 0):
                            progress_callback(total_seen, info['path'])
        return results
    def _file_info_from_stat(self, path, fn, st):
        show_name = None; season = None; episode = None
        m = TV_RE.search(fn)
        if m:
            raw = m.group('show')
            show_name = re.sub(r'[._\-]+', ' ', raw).strip()
            show_name = re.sub(r'[\(\)\[\]\-]+$', '', show_name).strip()
            try:
                season = int(m.group('season'))
                episode = int(m.group('episode'))
            except Exception:
                season = None; episode = None
        return {
            'path': path,
            'filename': fn,
            'mtime': st.st_mtime,
            'size': st.st_size,
            'media_type': 'video' if is_video(path) else ('image' if is_image(path) else 'audio'),
            'show_name': show_name,
            'season': season,
            'episode': episode,
            'watched': 0
        }
    def _show_progress(self, title='Working', message='Scanning...'):
        if self._progress_win:
            return
        win = tk.Toplevel(self.root)
        win.title(title)
        win.geometry('420x100')
        win.resizable(False, False)
        win.transient(self.root)
        win.grab_set()
        frm = ttk.Frame(win, padding=10)
        frm.pack(fill='both', expand=True)
        lbl = ttk.Label(frm, text=message)
        lbl.pack(anchor='w', pady=(0,6))
        pb = ttk.Progressbar(frm, mode='indeterminate', style='Horizontal.TProgressbar')
        pb.pack(fill='x', expand=True)
        pb.start(20)
        self._progress_win = win
        self._progress_bar = pb
        self._progress_label = lbl
        self.root.update_idletasks()
    def _hide_progress(self):
        try:
            if self._progress_bar:
                self._progress_bar.stop()
        except Exception:
            pass
        try:
            if self._progress_win:
                self._progress_win.grab_release()
                self._progress_win.destroy()
        except Exception:
            pass
        self._progress_win = None
        self._progress_bar = None
        self._progress_label = None
    def full_refresh(self):
        folders = self.settings.get('watch_folders', [])
        if not folders:
            messagebox.showinfo('Refresh', 'No watch folders configured.')
            return
        if not messagebox.askyesno('Refresh', 'Perform full refresh? This will rescan watch folders and remove DB entries for missing files.'):
            return
        def worker():
            try:
                self.root.after(0, lambda: (self.status.config(text='Full refresh...'), self._show_progress('Refreshing', 'Scanning watch folders...')))
                scanned = self._synchronous_scan(progress_callback=lambda count, path: self.root.after(0, lambda: self._update_progress_text(count, path)))
                current_paths = { normalize_path(i['path']) for i in scanned if i.get('path') }
                db_rows = self.db.all()
                watched_map = { r['path']: int(r['watched']) for r in db_rows }
                db_paths = { r['path'] for r in db_rows }
                to_delete = db_paths - current_paths
                for p in to_delete:
                    try:
                        try:
                            tp = self.thumb_cache.thumb_path(p)
                            if tp.exists():
                                tp.unlink()
                        except Exception:
                            pass
                        self.db.delete(p)
                    except Exception:
                        pass
                for info in scanned:
                    try:
                        info['path'] = normalize_path(info.get('path') or '')
                    except Exception:
                        info['path'] = info.get('path') or ''
                    info['watched'] = watched_map.get(info['path'], 0)
                    self.db.upsert(info)
                try:
                    self.thumb_cache.mem.clear()
                    for f in THUMB_DIR.glob('*'):
                        try:
                            f.unlink()
                        except Exception:
                            pass
                except Exception:
                    pass
                self.root.after(0, lambda: self.refresh_items())
            finally:
                self.root.after(0, lambda: (self._hide_progress(), self.status.config(text='Ready'), messagebox.showinfo('Refresh', 'Full refresh complete.')))
        threading.Thread(target=worker, daemon=True).start()
    def _update_progress_text(self, count, last_path):
        if self._progress_label:
            short = os.path.basename(last_path) if last_path else ''
            self._progress_label.config(text=f"Scanning... {count} files ({short})")
    def set_view_mode(self, mode: str):
        self.view_mode = 'list'
        self.settings['view_mode'] = 'list'
        self.save_settings()
        try:
            self.thumb_canvas.pack_forget()
            self.thumb_scroll.pack_forget()
        except Exception:
            pass
        try:
            self.tree.pack(fill='both', expand=True, side='left')
            self.tree_scroll.pack(side='right', fill='y')
        except Exception:
            pass
        self.render_list()
    def toggle_view(self):
        new = 'thumb' if self.view_mode == 'list' else 'list'
        self.set_view_mode(new)
    def render_list(self):
        for i in self.tree.get_children():
            self.tree.delete(i)
        tv_groups = {}
        movies = []
        for it in self.items:
            if it['show_name']:
                tv_groups.setdefault(it['show_name'], {}).setdefault(it['season'] or 1, []).append(it)
            else:
                movies.append(it)
        for show in sorted(tv_groups.keys(), key=lambda s: s.lower()):
            show_open = (show, None) in self._expanded
            show_id = self.tree.insert('', 'end', text=show, values=('', '', '', ''), open=show_open)
            for season in sorted(tv_groups[show].keys()):
                season_open = (show, season) in self._expanded
                season_id = self.tree.insert(show_id, 'end', text=f"Season {season}", values=('', '', '', ''), open=season_open)
                eps = sorted(tv_groups[show][season], key=lambda x: (x.get('episode') or 0))
                for ep in eps:
                    fn = ep['filename']
                    size = human_size(ep.get('size', 0))
                    w = 'Yes' if ep.get('watched') else 'No'
                    self.tree.insert(season_id, 'end', text=fn, values=(ep.get('media_type'), size, w, ep.get('path')))
        movies_sorted = sorted(movies, key=lambda m: m['filename'].lower())
        movies_root_open = ('Movies', None) in self._expanded
        movies_root = self.tree.insert('', 'end', text='Movies', values=('', '', '', ''), open=movies_root_open)
        for m in movies_sorted:
            fn = m['filename']
            size = human_size(m.get('size', 0))
            w = 'Yes' if m.get('watched') else 'No'
            self.tree.insert(movies_root, 'end', text=fn, values=(m.get('media_type'), size, w, m.get('path')))
    def render_thumbnails(self):
        for w in self.thumb_inner.winfo_children():
            w.destroy()
        size = int(self.settings.get('thumbnail_size', 140))
        cols = max(1, int(self.settings.get('columns', 5)))
        self.thumb_cache.set_size(size)
        pad = 8
        r = c = 0
        for it in self.items:
            p = it['path']
            frame = ttk.Frame(self.thumb_inner, width=size+10)
            frame.grid_propagate(False)
            frame.grid(row=r, column=c, padx=pad, pady=pad)
            img = self.thumb_cache.get(p)
            if not img:
                ph = Image.new('RGB', (size, size), (0, 0, 0))
                img = ImageTk.PhotoImage(ph)
                try:
                    self.thumb_q.put_nowait(p)
                except queue.Full:
                    pass
            lbl = tk.Label(frame, image=img, bd=0, bg='#000000')
            lbl.image = img
            lbl.path = p
            lbl.pack()
            lbl.bind('<Double-1>', lambda e, pp=p: self.open_and_mark(pp))
            lbl.bind('<Button-3>', lambda e, pp=p: self.on_thumb_right(e, pp))
            ttk.Label(frame, text=it['filename'], wraplength=size).pack()
            if it.get('watched'):
                chk = tk.Label(frame, text='✓', bg='#000000', fg='white')
                chk.place(in_=lbl, relx=0.02, rely=0.02)
            c += 1
            if c >= cols:
                c = 0; r += 1
    def on_thumb_right(self, event, path: str):
        self.selected_path = path
        try:
            self.ctx.tk_popup(event.x_root, event.y_root)
        finally:
            self.ctx.grab_release()
    def on_tree_double(self, event):
        iid = self.tree.focus()
        if not iid:
            return
        vals = self.tree.item(iid, 'values')
        path = ''
        if vals and len(vals) >= 4:
            path = vals[3]
        if path:
            self.open_and_mark(path)
        else:
            if self.tree.item(iid, 'open'):
                self.tree.item(iid, open=False)
            else:
                self.tree.item(iid, open=True)
    def on_tree_right(self, event):
        iid = self.tree.identify_row(event.y)
        if not iid:
            return
        vals = self.tree.item(iid, 'values')
        path = ''
        if vals and len(vals) >= 4:
            path = vals[3]
        self.selected_path = path or None
        try:
            self.ctx.tk_popup(event.x_root, event.y_root)
        finally:
            self.ctx.grab_release()
    def open_and_mark(self, path: str):
        if not path:
            return
        try:
            self.db.set_watched(path, 1)
            try:
                self._update_single_item_ui(path, watched=1)
            except Exception:
                self.refresh_items()
            open_target(path)
        except Exception:
            open_target(path)
    def ctx_open(self):
        if not getattr(self, 'selected_path', None): return
        self.open_and_mark(self.selected_path)
    def ctx_reveal(self):
        if not getattr(self, 'selected_path', None): return
        reveal_target(self.selected_path)
    def ctx_set_watched(self, val: int):
        if not getattr(self, 'selected_path', None): return
        self.db.set_watched(self.selected_path, val)
        self.refresh_items()
    def ctx_remove(self):
        if not getattr(self, 'selected_path', None): return
        self.db.delete(self.selected_path)
        self.refresh_items()
    def ctx_delete(self):
        if not getattr(self, 'selected_path', None): return
        if messagebox.askyesno('Delete', f'Delete file {self.selected_path}?'):
            try:
                os.remove(self.selected_path)
            except Exception as e:
                messagebox.showerror('Error', str(e))
            self.db.delete(self.selected_path)
            self.refresh_items()
    def toggle_watched_selected(self):
        sel = getattr(self, 'selected_path', None)
        if not sel:
            return
        rows = self.db.search(os.path.basename(sel))
        item = next((r for r in rows if r['path'] == sel), None)
        if not item:
            return
        new = 0 if item.get('watched') else 1
        self.db.set_watched(sel, new)
        self.refresh_items()
    def on_thumb_ready(self, path: str):
        self.root.after(0, lambda: self._update_thumb(path))
    def _update_thumb(self, path: str):
        for frame in self.thumb_inner.winfo_children():
            for widget in frame.winfo_children():
                if getattr(widget, 'path', None) == path:
                    img = self.thumb_cache.get(path)
                    if img:
                        widget.configure(image=img)
                        widget.image = img
    def organize_action(self):
        if not self.items:
            messagebox.showinfo('Organize', 'No items detected to organize')
            return
        self._show_organize_dialog()
    def _show_organize_dialog(self):
        win = tk.Toplevel(self.root)
        win.title('Organize Files')
        win.transient(self.root)
        win.resizable(False, False)
        try:
            win.grab_set()
        except Exception:
            pass
        frm = ttk.Frame(win, padding=12)
        frm.pack(fill='both', expand=True)
        ttk.Label(frm, text='Destination root:').grid(row=0, column=0, sticky='w')
        dest_var = tk.StringVar()
        dest_entry = ttk.Entry(frm, textvariable=dest_var, width=48)
        dest_entry.grid(row=1, column=0, columnspan=2, sticky='w', pady=(0,8))
        def browse():
            d = filedialog.askdirectory(parent=win, title='Select destination root')
            if d:
                dest_var.set(d)
        ttk.Button(frm, text='Browse...', command=browse).grid(row=1, column=2, padx=(8,0))
        ttk.Label(frm, text='Action:').grid(row=2, column=0, sticky='w', pady=(6,0))
        mode_var = tk.StringVar(value='move')
        r1 = ttk.Radiobutton(frm, text='Move (recommended: relocate files)', variable=mode_var, value='move')
        r2 = ttk.Radiobutton(frm, text='Copy (keep originals)', variable=mode_var, value='copy')
        r1.grid(row=3, column=0, columnspan=3, sticky='w')
        r2.grid(row=4, column=0, columnspan=3, sticky='w', pady=(0,6))
        ttk.Label(frm, text='Tip: choose Copy to keep originals; Move will update DB to new locations.', style='Small.TLabel').grid(row=5, column=0, columnspan=3, sticky='w', pady=(4,8))
        btn_fr = ttk.Frame(frm)
        btn_fr.grid(row=6, column=0, columnspan=3, sticky='e')
        def on_start():
            dest = dest_var.get().strip()
            if not dest:
                messagebox.showwarning('Organize', 'Please select a destination folder.', parent=win)
                return
            do_copy = True if mode_var.get() == 'copy' else False
            threading.Thread(target=self._organize_worker, args=(dest, do_copy), daemon=True).start()
            try:
                win.destroy()
            except Exception:
                pass
        def on_cancel():
            try:
                win.destroy()
            except Exception:
                pass
        ttk.Button(btn_fr, text='Start', command=on_start).pack(side='right', padx=(6,0))
        ttk.Button(btn_fr, text='Cancel', command=on_cancel).pack(side='right')
        win.bind('<Return>', lambda e: on_start())
        win.bind('<Escape>', lambda e: on_cancel())
        try:
            dest_entry.focus_set()
        except Exception:
            pass
    def _organize_worker(self, dest_root: str, do_copy: bool):
        try:
            self.root.after(0, lambda: self.status.config(text='Organizing...'))
        except Exception:
            pass
        updated_any = False
        for it in list(self.items):
            orig_path = it.get('path')
            if not orig_path:
                continue
            src = normalize_path(orig_path)
            if it.get('show_name'):
                show = sanitize_filename(it['show_name'])
                season = f"Season {it.get('season') or 1}"
                dest_dir = Path(dest_root) / 'TV Shows' / show / season
            else:
                dest_dir = Path(dest_root) / 'Movies'
            dest_dir.mkdir(parents=True, exist_ok=True)
            new_path_raw = str(dest_dir / os.path.basename(src))
            new = normalize_path(new_path_raw)
            try:
                if do_copy:
                    shutil.copy2(src, new_path_raw)
                    src_row = self.db.get(src)
                    watched_val = int(src_row['watched']) if src_row and src_row.get('watched') is not None else 0
                    info = {
                        'path': new,
                        'filename': os.path.basename(new),
                        'mtime': os.path.getmtime(new_path_raw) if os.path.exists(new_path_raw) else None,
                        'size': os.path.getsize(new_path_raw) if os.path.exists(new_path_raw) else None,
                        'media_type': 'video' if is_video(new_path_raw) else ('image' if is_image(new_path_raw) else 'audio'),
                        'show_name': it.get('show_name'),
                        'season': it.get('season'),
                        'episode': it.get('episode'),
                        'watched': int(watched_val)
                    }
                    self.db.upsert(info)
                    try:
                        self.thumb_q.put_nowait(new)
                    except queue.Full:
                        pass
                else:
                    shutil.move(src, new_path_raw)
                    self.db.update_path(src, new)
                updated_any = True
                try:
                    old_tp = self.thumb_cache.thumb_path(src)
                    if old_tp.exists():
                        old_tp.unlink()
                except Exception:
                    pass
                try:
                    new_tp = self.thumb_cache.thumb_path(new)
                    if new_tp.exists():
                        new_tp.unlink()
                except Exception:
                    pass
                try:
                    for entry in self.items:
                        if normalize_path(entry.get('path') or '') == src:
                            entry['path'] = new
                            entry['filename'] = os.path.basename(new)
                            break
                except Exception:
                    pass
            except Exception as e:
                print('organize error', e)
        try:
            self.thumb_cache.mem.clear()
        except Exception:
            pass
        def finish():
            try:
                if updated_any:
                    self._refresh_ui_only()
                self.status.config(text='Ready')
                messagebox.showinfo('Organize', 'Done')
            except Exception:
                try:
                    messagebox.showinfo('Organize', 'Done')
                except Exception:
                    pass
        try:
            self.root.after(0, finish)
        except Exception:
            finish()
    def close(self):
        try:
            self.thumb_worker.stop()
            try:
                self.thumb_worker.join(timeout=1)
            except Exception:
                pass
        except Exception:
            pass
        try:
            if hasattr(self, 'db') and getattr(self.db, 'conn', None):
                try:
                    self.db.conn.close()
                except Exception:
                    pass
        except Exception:
            pass
        try:
            self.save_settings()
        except Exception:
            pass
        try:
            if getattr(self, 'root', None):
                try:
                    self.root.destroy()
                except Exception:
                    pass
        except Exception:
            pass
    def _on_show_select(self, val: str):
        try:
            self.top_filter.set(val)
        except Exception:
            try:
                self.top_filter = tk.StringVar(value=val)
            except Exception:
                pass
        try:
            self._refresh_show_buttons()
        except Exception:
            pass
        try:
            self.refresh_items()
        except Exception:
            pass
    def _refresh_show_buttons(self):
        try:
            selected = self.top_filter.get() if getattr(self, 'top_filter', None) else 'All'
        except Exception:
            selected = 'All'
        for name, widget in getattr(self, 'show_buttons', {}).items():
            try:
                if name == selected:
                    widget.config(bg=self.colors.get('accent', '#39c0ff'), fg='#001217')
                else:
                    widget.config(bg=self.colors.get('card', '#0f1728'), fg=self.colors.get('text', '#e6eef6'))
            except Exception:
                try:
                    if name == selected:
                        widget.config(bg='#39c0ff', fg='#001217')
                    else:
                        widget.config(bg='#0f1728', fg='#e6eef6')
                except Exception:
                    pass
    def _capture_expanded(self):
        expanded = set()
        try:
            for top in self.tree.get_children(''):
                txt = self.tree.item(top, 'text')
                is_open = bool(self.tree.item(top, 'open'))
                if txt == 'Movies':
                    if is_open:
                        expanded.add(('Movies', None))
                    continue
                if is_open:
                    expanded.add((txt, None))
                for season_iid in self.tree.get_children(top):
                    season_txt = self.tree.item(season_iid, 'text')
                    season_open = bool(self.tree.item(season_iid, 'open'))
                    m = re.search(r'(\d+)', season_txt)
                    season_num = int(m.group(1)) if m else None
                    if season_open:
                        expanded.add((txt, season_num))
        except Exception:
            expanded = set()
        self._expanded = expanded
    def _restore_expanded(self):
        try:
            targets = getattr(self, '_expanded', set()) or set()
            for top in self.tree.get_children(''):
                txt = self.tree.item(top, 'text')
                if txt == 'Movies':
                    if ('Movies', None) in targets:
                        try: self.tree.item(top, open=True)
                        except Exception: pass
                    continue
                if (txt, None) in targets:
                    try: self.tree.item(top, open=True)
                    except Exception: pass
                for season_iid in self.tree.get_children(top):
                    season_txt = self.tree.item(season_iid, 'text')
                    m = re.search(r'(\d+)', season_txt)
                    season_num = int(m.group(1)) if m else None
                    if (txt, season_num) in targets:
                        try: self.tree.item(season_iid, open=True)
                        except Exception: pass
        except Exception:
            pass
    def _update_single_item_ui(self, path: str, watched: int = None):
        try:
            def walk(iid):
                vals = self.tree.item(iid, 'values') or ()
                if len(vals) >= 4 and vals[3] == path:
                    typ = vals[0] if len(vals) > 0 else ''
                    size = vals[1] if len(vals) > 1 else ''
                    w = vals[2] if len(vals) > 2 else ''
                    new_w = 'Yes' if watched else ('No' if watched == 0 else w)
                    try:
                        self.tree.item(iid, values=(typ, size, new_w, vals[3]))
                    except Exception:
                        pass
                    return True
                for child in self.tree.get_children(iid):
                    if walk(child):
                        return True
                return False
            for top in self.tree.get_children(''):
                if walk(top):
                    break
        except Exception:
            pass
if __name__ == '__main__':
    try:
        root = RootWindow()
    except Exception:
        root = tk.Tk()
    app = App(root)
    try:
        root.protocol('WM_DELETE_WINDOW', app.close)
    except Exception:
        pass
    try:
        root.mainloop()
    except KeyboardInterrupt:
        try:
            app.close()
        except Exception:
            pass
