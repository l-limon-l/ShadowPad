import tkinter as tk
import ctypes
import ctypes.wintypes
import os
import sys
import gc
import json
import threading


GWL_EXSTYLE             = -20
WS_EX_TOOLWINDOW        = 0x00000080
WS_EX_APPWINDOW         = 0x00040000
WS_EX_NOACTIVATE        = 0x08000000
WDA_EXCLUDEFROMCAPTURE   = 0x00000011
WDA_MONITOR              = 0x00000001
GA_ROOT                  = 2
WM_HOTKEY                = 0x0312
MOD_CONTROL              = 0x0002
MOD_SHIFT                = 0x0004
VK_H                     = 0x48                                           
VK_Q                     = 0x51                                          

HOTKEY_TOGGLE = 1
HOTKEY_PANIC  = 2

SM_XVIRTUALSCREEN  = 76
SM_YVIRTUALSCREEN  = 77
SM_CXVIRTUALSCREEN = 78
SM_CYVIRTUALSCREEN = 79

WNDENUMPROC = ctypes.WINFUNCTYPE(
    ctypes.wintypes.BOOL,
    ctypes.wintypes.HWND,
    ctypes.wintypes.LPARAM,
)


C = {
    'canvas':    '#010102',
    'surf1':     '#0d0e11',
    'surf2':     '#161719',
    'surf3':     '#1e2028',
    'hair':      '#23252a',
    'primary':   '#5e6ad2',
    'pri_hov':   '#828fff',
    'ink':       '#f7f8f8',
    'ink_m':     '#d0d6e0',
    'ink_s':     '#8a8f98',
    'ink_t':     '#62666d',
}

F_BODY   = ('Segoe UI', 9)
F_BOLD   = ('Segoe UI', 9, 'bold')
F_EDITOR = ('Segoe UI', 11)

HIGHLIGHTS = {
    'hl_yellow': ('#FACC15', '#000000'),
    'hl_red':    ('#EF4444', '#FFFFFF'),
    'hl_green':  ('#22C55E', '#000000'),
    'hl_blue':   ('#38BDF8', '#000000'),
    'hl_purple': ('#A78BFA', '#000000'),
}

PERSISTENT_TAGS = frozenset({'bold', 'italic'} | set(HIGHLIGHTS.keys()))


BASE_DIR    = os.path.dirname(os.path.abspath(__file__))
NOTES_DIR   = os.path.join(BASE_DIR, 'notes')
CONFIG_FILE = os.path.join(BASE_DIR, 'config.json')

os.makedirs(NOTES_DIR, exist_ok=True)



def _lighten(hex_color, factor=0.3):
    """Lighten a hex colour for hover effects."""
    h = hex_color.lstrip('#')
    r, g, b = int(h[:2], 16), int(h[2:4], 16), int(h[4:], 16)
    r = min(255, int(r + (255 - r) * factor))
    g = min(255, int(g + (255 - g) * factor))
    b = min(255, int(b + (255 - b) * factor))
    return f'#{r:02x}{g:02x}{b:02x}'

class _Tooltip:
    """Lightweight tooltip that hides from screen capture."""

    def __init__(self, widget, text, delay=450):
        self.widget = widget
        self.text   = text
        self.delay  = delay
        self._tip   = None
        self._job   = None
        widget.bind('<Enter>',    self._schedule, add='+')
        widget.bind('<Leave>',    self._cancel,   add='+')
        widget.bind('<Button-1>', self._cancel,   add='+')

    def _schedule(self, _=None):
        self._cancel()
        self._job = self.widget.after(self.delay, self._show)

    def _cancel(self, _=None):
        if self._job:
            self.widget.after_cancel(self._job)
            self._job = None
        if self._tip:
            self._tip.destroy()
            self._tip = None

    def _show(self):
        x = self.widget.winfo_rootx() + self.widget.winfo_width() // 2
        y = self.widget.winfo_rooty() + self.widget.winfo_height() + 4
        tip = tk.Toplevel(self.widget)
        tip.overrideredirect(True)
        tip.attributes('-topmost', True)
        tip.geometry(f'+{x}+{y}')
        tk.Label(
            tip, text=self.text,
            bg=C['surf3'], fg=C['ink_m'],
            font=('Segoe UI', 8), padx=6, pady=3,
            highlightthickness=1, highlightbackground=C['hair'],
        ).pack()
        tip.update_idletasks()
                                                  
        try:
            hwnd = ctypes.windll.user32.GetAncestor(tip.winfo_id(), GA_ROOT)
            if not ctypes.windll.user32.SetWindowDisplayAffinity(
                    hwnd, WDA_EXCLUDEFROMCAPTURE):
                ctypes.windll.user32.SetWindowDisplayAffinity(
                    hwnd, WDA_MONITOR)
        except Exception:
            pass
        self._tip = tip

                                                                                

_mutex = ctypes.windll.kernel32.CreateMutexW(None, True,
                                             'StickyNote_Instance_4F2A')
if ctypes.windll.kernel32.GetLastError() == 183:                                  
    sys.exit(0)

                                                                                



class StickyNote:

    def __init__(self):
        self.config          = self._load_config()
        self.current         = self.config.get('current', 'Note 1')
        self._visible        = True
        self._panel_open     = self.config.get('panel_open', False)
        self._search_open    = False
        self._search_matches = []
        self._search_idx     = -1
        self._save_timer     = None
        self._drag_pending   = False
        self._resize_pending = False
        self._focus_grace    = False
        self._fmt_history     = []                                           
        self._fmt_redo_stack  = []                                           

        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes('-topmost', True)
        self._target_alpha = self.config.get('alpha', 0.93)
        self.root.attributes('-alpha', self._target_alpha)
        self.root.geometry(self.config.get('geometry', '340x280+80+80'))
        self.root.configure(bg=C['canvas'])

        self._enum_cb = self._make_enum_callback()

        self._migrate_notes()
        self._build_ui()
        self._init_text_tags()
        self._ensure_note(self.current)
        self._load_note(self.current)

        if self._panel_open:
            self._panel_open = False                                             
            self._toggle_panel()

        self.root.after(120, self._apply_win32)
        self.root.after(250, self._start_hotkey)
        self.root.after(300, self._validate_geometry)
        self.root.after(500, self._setup_focus_loss)

                                                                                   

    def _build_ui(self):
                                   
        tk.Frame(self.root, bg=C['primary'], height=2).pack(fill='x')

        self.bar = tk.Frame(self.root, bg=C['surf2'], height=30)
        self.bar.pack(fill='x')
        self.bar.pack_propagate(False)

        self.menu_btn = self._label_btn(self.bar, '≡', self._toggle_panel,
                                        font=('Segoe UI', 14), padx=8,
                                        tip='Notes List')
        self.menu_btn.pack(side='left')

        self.title_var = tk.StringVar(value=self.current)
        self.title_lbl = tk.Label(
            self.bar, textvariable=self.title_var,
            bg=C['surf2'], fg=C['ink_m'], font=F_BOLD, cursor='fleur',
        )
        self.title_lbl.pack(side='left', padx=4)

        self._label_btn(self.bar, '↩', self._undo,
                        font=('Segoe UI', 13), padx=5,
                        tip='Undo').pack(side='left')
        self._label_btn(self.bar, '↪', self._redo,
                        font=('Segoe UI', 13), padx=5,
                        tip='Redo').pack(side='left')

        self._label_btn(self.bar, '×', self._on_close,
                        hover_fg='#ff6b6b', padx=8,
                        tip='Close').pack(side='right')

        self._font_size = self.config.get('font_size', 11)
        self._label_btn(self.bar, 'А+',
                        lambda: self._change_font(+1), padx=4,
                        tip='Increase Font').pack(side='right')
        self.font_lbl = tk.Label(self.bar, text=str(self._font_size),
                                 bg=C['surf2'], fg=C['ink_t'],
                                 font=('Segoe UI', 8), width=2)
        self.font_lbl.pack(side='right')
        self._label_btn(self.bar, 'А−',
                        lambda: self._change_font(-1), padx=4,
                        tip='Decrease Font').pack(side='right')

        tk.Frame(self.bar, bg=C['hair'], width=1).pack(side='right',
                                                        fill='y', pady=6)

        self._label_btn(self.bar, '+',
                        lambda: self._change_alpha(+0.10), padx=5,
                        tip='Increase Opacity').pack(side='right')
        self.alpha_lbl = tk.Label(self.bar, text=self._alpha_text(),
                                  bg=C['surf2'], fg=C['ink_t'],
                                  font=('Segoe UI', 8), width=4)
        self.alpha_lbl.pack(side='right')
        self._label_btn(self.bar, '−',
                        lambda: self._change_alpha(-0.10), padx=5,
                        tip='Decrease Opacity').pack(side='right')

        self._locked = False
        self.lock_btn = self._label_btn(self.bar, '✎', self._toggle_lock,
                                        tip='Блокировка редактирования')
        self.lock_btn.pack(side='right')

        for w in (self.bar, self.title_lbl):
            w.bind('<ButtonPress-1>', self._drag_start)
            w.bind('<B1-Motion>',     self._drag_motion)

        self._build_format_bar()

        self.body = tk.Frame(self.root, bg=C['canvas'])
        self.body.pack(fill='both', expand=True)

        self.panel = tk.Frame(self.body, bg=C['canvas'], width=190)
        self.panel.pack_propagate(False)
        self._build_panel()

        self.panel_sep = tk.Frame(self.body, bg=C['hair'], width=1)

        self.editor_wrap = tk.Frame(self.body, bg=C['surf1'])
        self.editor_wrap.pack(side='left', fill='both', expand=True)

        self.text = tk.Text(
            self.editor_wrap,
            font=('Segoe UI', self._font_size),
            wrap=tk.WORD,
            bg=C['surf1'], fg=C['ink'], relief='flat',
            padx=12, pady=10,
            insertbackground=C['primary'],
            selectbackground=C['surf3'],
            selectforeground=C['ink'],
            undo=True,
        )
        self.text.pack(fill='both', expand=True)
        self.text.bind('<KeyRelease>', self._auto_save)

        self.text.bind('<Control-b>',     lambda e: (self._toggle_tag('bold'), 'break'))
        self.text.bind('<Control-i>',     lambda e: (self._toggle_tag('italic'), 'break'))
        self.text.bind('<Control-f>',     lambda e: (self._toggle_search(), 'break'))
        self.text.bind('<Control-Key-1>', lambda e: self._apply_highlight('hl_yellow'))
        self.text.bind('<Control-Key-2>', lambda e: self._apply_highlight('hl_red'))
        self.text.bind('<Control-Key-3>', lambda e: self._apply_highlight('hl_green'))
        self.text.bind('<Control-Key-4>', lambda e: self._apply_highlight('hl_blue'))
        self.text.bind('<Control-Key-5>', lambda e: self._apply_highlight('hl_purple'))
        self.text.bind('<Control-Key-0>', lambda e: self._clear_formatting())

        self.text.focus_set()

        self._build_search_bar()

        self._build_ctx_menu()

        self.grip = tk.Label(
            self.root, text='◢', bg=C['surf1'], fg=C['hair'],
            font=('Segoe UI', 10), cursor='size_nw_se',
        )
        self.grip.place(relx=1.0, rely=1.0, anchor='se')
        self.grip.bind('<ButtonPress-1>', self._resize_start)
        self.grip.bind('<B1-Motion>',     self._resize_motion)


    def _build_format_bar(self):
        """Compact formatting toolbar (24 px)."""
        self.fmt_bar = tk.Frame(self.root, bg=C['surf2'], height=24)
        self.fmt_bar.pack(fill='x')
        self.fmt_bar.pack_propagate(False)

        self._fmt_btn(self.fmt_bar, 'B',
                      lambda: self._toggle_tag('bold'),
                      font=('Segoe UI', 9, 'bold'),
                      tip='Bold')
        self._fmt_btn(self.fmt_bar, 'I',
                      lambda: self._toggle_tag('italic'),
                      font=('Segoe UI', 9, 'italic'),
                      tip='Italic')

        tk.Frame(self.fmt_bar, bg=C['hair'], width=1
                 ).pack(side='left', fill='y', pady=4, padx=4)

        _HL_TIPS = {
            'hl_yellow': 'Yellow',
            'hl_red':    'Red',
            'hl_green':  'Green',
            'hl_blue':   'Blue',
            'hl_purple': 'Purple',
        }
        for key, (bg_c, _fg_c) in HIGHLIGHTS.items():
            dot = tk.Label(self.fmt_bar, text='●', bg=C['surf2'], fg=bg_c,
                           font=('Segoe UI', 10), cursor='hand2', padx=3)
            dot.pack(side='left')
            dot.bind('<Button-1>', lambda _, k=key: self._apply_highlight(k))
            dot.bind('<Enter>',
                     lambda _, d=dot, c=bg_c: d.config(fg=_lighten(c)))
            dot.bind('<Leave>',
                     lambda _, d=dot, c=bg_c: d.config(fg=c))
            _Tooltip(dot, _HL_TIPS.get(key, key))

        tk.Frame(self.fmt_bar, bg=C['hair'], width=1
                 ).pack(side='left', fill='y', pady=4, padx=4)

        self._fmt_btn(self.fmt_bar, '⊘', self._clear_formatting,
                      tip='Clear Formatting')

        tk.Frame(self.fmt_bar, bg=C['hair'], width=1
                 ).pack(side='left', fill='y', pady=4, padx=4)

        self._fmt_btn(self.fmt_bar, '↩', self._fmt_undo,
                      font=('Segoe UI', 11),
                      tip='Undo Formatting')
        self._fmt_btn(self.fmt_bar, '↪', self._fmt_redo,
                      font=('Segoe UI', 11),
                      tip='Redo Formatting')

        self._fmt_btn(self.fmt_bar, '🔍', self._toggle_search,
                      padx=6, side='right',
                      tip='Search')

    def _fmt_btn(self, parent, text, cmd, font=F_BODY, padx=5,
                 side='left', tip=None):
        btn = tk.Label(parent, text=text, bg=C['surf2'], fg=C['ink_t'],
                       font=font, cursor='hand2', padx=padx)
        btn.pack(side=side)
        btn.bind('<Button-1>', lambda _: cmd())
        btn.bind('<Enter>',    lambda _: btn.config(fg=C['ink']))
        btn.bind('<Leave>',    lambda _: btn.config(fg=C['ink_t']))
        if tip:
            _Tooltip(btn, tip)
        return btn

    def _label_btn(self, parent, text, cmd, font=F_BODY,
                   hover_fg=None, padx=6, tip=None):
        lbl = tk.Label(parent, text=text, bg=C['surf2'], fg=C['ink_s'],
                       font=font, cursor='hand2', padx=padx)
        hfg = hover_fg or C['ink']
        lbl.bind('<Button-1>', lambda _: cmd())
        lbl.bind('<Enter>',    lambda _: lbl.config(fg=hfg))
        lbl.bind('<Leave>',    lambda _: lbl.config(fg=C['ink_s']))
        if tip:
            _Tooltip(lbl, tip)
        return lbl

                                                                                   

    def _init_text_tags(self):
        """Configure persistent and transient formatting tags."""
        self.text.tag_configure('bold',
                                font=('Segoe UI', self._font_size, 'bold'))
        self.text.tag_configure('italic',
                                font=('Segoe UI', self._font_size, 'italic'))
        for key, (bg_c, fg_c) in HIGHLIGHTS.items():
            self.text.tag_configure(key, background=bg_c, foreground=fg_c)

        self.text.tag_configure('search_hit',
                                background='#2a2d4a')
        self.text.tag_configure('search_current',
                                background=C['primary'], foreground='#ffffff')
        self.text.tag_raise('search_hit')
        self.text.tag_raise('search_current')

    def _update_tag_fonts(self):
        """Sync font-based tags after font-size change."""
        self.text.tag_configure('bold',
                                font=('Segoe UI', self._font_size, 'bold'))
        self.text.tag_configure('italic',
                                font=('Segoe UI', self._font_size, 'italic'))


    def _snapshot_tags(self, start, end):
        """Capture all persistent tags in [start, end) range."""
        snap = []
        for tag in PERSISTENT_TAGS:
            ranges = self.text.tag_ranges(tag)
            for i in range(0, len(ranges), 2):
                rs = str(ranges[i])
                re = str(ranges[i + 1])
                                                                            
                if (self.text.compare(re, '>', start)
                        and self.text.compare(rs, '<', end)):
                    snap.append((tag, rs, re))
        return snap

    def _restore_snapshot(self, start, end, snap):
        """Remove all persistent tags in range, then re-apply snapshot."""
        for tag in PERSISTENT_TAGS:
            self.text.tag_remove(tag, start, end)
        for tag, rs, re in snap:
            try:
                self.text.tag_add(tag, rs, re)
            except tk.TclError:
                pass

    def _record_fmt(self, start, end, before_snap):
        """Record a formatting change for undo."""
        after_snap = self._snapshot_tags(start, end)
        self._fmt_history.append({
            'start': start, 'end': end,
            'before': before_snap, 'after': after_snap,
        })
        self._fmt_redo_stack.clear()                                                       

    def _fmt_undo(self):
        """Undo last formatting action."""
        if not self._fmt_history:
            return
        entry = self._fmt_history.pop()
                                                         
        current = self._snapshot_tags(entry['start'], entry['end'])
        self._restore_snapshot(entry['start'], entry['end'], entry['before'])
        self._fmt_redo_stack.append({
            'start': entry['start'], 'end': entry['end'],
            'before': entry['before'], 'after': current,
        })
        self._auto_save()

    def _fmt_redo(self):
        """Redo last undone formatting action."""
        if not self._fmt_redo_stack:
            return
        entry = self._fmt_redo_stack.pop()
        before = self._snapshot_tags(entry['start'], entry['end'])
        self._restore_snapshot(entry['start'], entry['end'], entry['after'])
        self._fmt_history.append({
            'start': entry['start'], 'end': entry['end'],
            'before': before, 'after': entry['after'],
        })
        self._auto_save()


    def _toggle_tag(self, tag_name):
        """Toggle bold / italic on selection."""
        if self._locked:
            return
        try:
            sel_s = self.text.index('sel.first')
            sel_e = self.text.index('sel.last')
        except tk.TclError:
            return                                                                        

        before = self._snapshot_tags(sel_s, sel_e)
        if self._selection_has_tag(tag_name, sel_s, sel_e):
            self.text.tag_remove(tag_name, sel_s, sel_e)
        else:
            self.text.tag_add(tag_name, sel_s, sel_e)
        self._record_fmt(sel_s, sel_e, before)
        self._auto_save()

    def _apply_highlight(self, color_key):
        """Apply / toggle highlight colour on selection."""
        if self._locked:
            return
        try:
            sel_s = self.text.index('sel.first')
            sel_e = self.text.index('sel.last')
        except tk.TclError:
            return

        before = self._snapshot_tags(sel_s, sel_e)
        if self._selection_has_tag(color_key, sel_s, sel_e):
            self.text.tag_remove(color_key, sel_s, sel_e)
        else:
            for key in HIGHLIGHTS:
                self.text.tag_remove(key, sel_s, sel_e)
            self.text.tag_add(color_key, sel_s, sel_e)
        self._record_fmt(sel_s, sel_e, before)
        self._auto_save()

    def _clear_formatting(self):
        """Remove all persistent formatting from selection."""
        if self._locked:
            return
        try:
            sel_s = self.text.index('sel.first')
            sel_e = self.text.index('sel.last')
        except tk.TclError:
            return
        before = self._snapshot_tags(sel_s, sel_e)
        for tag in PERSISTENT_TAGS:
            self.text.tag_remove(tag, sel_s, sel_e)
        self._record_fmt(sel_s, sel_e, before)
        self._auto_save()

    def _selection_has_tag(self, tag_name, sel_s, sel_e):
        """Return True if *tag_name* covers the entire selection."""
        ranges = self.text.tag_ranges(tag_name)
        for i in range(0, len(ranges), 2):
            rs = self.text.index(str(ranges[i]))
            re = self.text.index(str(ranges[i + 1]))
            if (self.text.compare(rs, '<=', sel_s)
                    and self.text.compare(re, '>=', sel_e)):
                return True
        return False

                                                                                  

    def _build_search_bar(self):
        self.search_frame = tk.Frame(self.editor_wrap, bg=C['surf2'],
                                     height=32)
        self.search_frame.pack_propagate(False)

        tk.Label(self.search_frame, text='🔍', bg=C['surf2'], fg=C['ink_t'],
                 font=('Segoe UI', 9)).pack(side='left', padx=(8, 4))

        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(
            self.search_frame, textvariable=self.search_var,
            bg=C['surf3'], fg=C['ink'], font=F_BODY, relief='flat',
            insertbackground=C['primary'],
            highlightthickness=1,
            highlightcolor=C['primary'],
            highlightbackground=C['hair'],
        )
        self.search_entry.pack(side='left', fill='x', expand=True,
                               padx=4, pady=5)
        self.search_var.trace_add('write', lambda *_: self._do_search())
        self.search_entry.bind('<Return>',       lambda _: self._next_match())
        self.search_entry.bind('<Shift-Return>',  lambda _: self._prev_match())
        self.search_entry.bind('<Escape>',        lambda _: self._close_search())

        self.search_counter = tk.Label(self.search_frame, text='',
                                       bg=C['surf2'], fg=C['ink_t'],
                                       font=('Segoe UI', 8))
        self.search_counter.pack(side='left', padx=4)

        for sym, fn in (('↑', self._prev_match), ('↓', self._next_match)):
            b = tk.Label(self.search_frame, text=sym, bg=C['surf2'],
                         fg=C['ink_s'], font=('Segoe UI', 11),
                         cursor='hand2', padx=4)
            b.pack(side='left')
            b.bind('<Button-1>', lambda _, f=fn: f())
            b.bind('<Enter>',    lambda _, w=b: w.config(fg=C['ink']))
            b.bind('<Leave>',    lambda _, w=b: w.config(fg=C['ink_s']))

        cx = tk.Label(self.search_frame, text='×', bg=C['surf2'],
                      fg=C['ink_s'], font=('Segoe UI', 11),
                      cursor='hand2', padx=8)
        cx.pack(side='right')
        cx.bind('<Button-1>', lambda _: self._close_search())
        cx.bind('<Enter>',    lambda _: cx.config(fg='#ff6b6b'))
        cx.bind('<Leave>',    lambda _: cx.config(fg=C['ink_s']))


    def _toggle_search(self):
        if self._search_open:
            self._close_search()
        else:
            self._show_search()

    def _show_search(self):
        if self._search_open:
            self.search_entry.focus_set()
            self.search_entry.select_range(0, 'end')
            return

        self.text.pack_forget()
        self.search_frame.pack(side='bottom', fill='x')
        self.text.pack(fill='both', expand=True)
        self._search_open = True
        self.search_entry.focus_set()

        try:
            sel = self.text.get('sel.first', 'sel.last')
            if sel and len(sel) < 200:
                self.search_var.set(sel)
                self.search_entry.select_range(0, 'end')
        except tk.TclError:
            pass

    def _close_search(self):
        if not self._search_open:
            return
        self.search_frame.pack_forget()
        self._search_open = False
        self._clear_search_tags()
        self._search_matches.clear()
        self._search_idx = -1
        self.search_counter.config(text='')
        self.search_var.set('')
        self.text.focus_set()

    def _do_search(self):
        """Incremental search — highlight all matches."""
        self._clear_search_tags()
        self._search_matches.clear()
        self._search_idx = -1

        query = self.search_var.get()
        if not query:
            self.search_counter.config(text='')
            return

        start = '1.0'
        while True:
            pos = self.text.search(query, start, stopindex='end', nocase=True)
            if not pos:
                break
            end = f'{pos}+{len(query)}c'
            self._search_matches.append((pos, end))
            self.text.tag_add('search_hit', pos, end)
            start = end

        total = len(self._search_matches)
        if total:
            self._search_idx = 0
            self._highlight_current_match()
            self.search_counter.config(text=f'1 / {total}')
        else:
            self.search_counter.config(text='0')

    def _highlight_current_match(self):
        self.text.tag_remove('search_current', '1.0', 'end')
        if 0 <= self._search_idx < len(self._search_matches):
            s, e = self._search_matches[self._search_idx]
            self.text.tag_add('search_current', s, e)
            self.text.see(s)

    def _next_match(self):
        if not self._search_matches:
            return
        self._search_idx = (self._search_idx + 1) % len(self._search_matches)
        self._highlight_current_match()
        self.search_counter.config(
            text=f'{self._search_idx + 1} / {len(self._search_matches)}')

    def _prev_match(self):
        if not self._search_matches:
            return
        self._search_idx = (self._search_idx - 1) % len(self._search_matches)
        self._highlight_current_match()
        self.search_counter.config(
            text=f'{self._search_idx + 1} / {len(self._search_matches)}')

    def _clear_search_tags(self):
        self.text.tag_remove('search_hit',     '1.0', 'end')
        self.text.tag_remove('search_current', '1.0', 'end')

                                                                                   

    def _build_panel(self):
        hdr = tk.Frame(self.panel, bg=C['canvas'])
        hdr.pack(fill='x')
        tk.Label(hdr, text='Заметки', bg=C['canvas'], fg=C['ink_m'],
                 font=F_BOLD, pady=9).pack(side='left', padx=10)

        add = tk.Label(hdr, text='+', bg=C['canvas'], fg=C['ink_s'],
                       font=('Segoe UI', 14), cursor='hand2', padx=8)
        add.pack(side='right')
        add.bind('<Button-1>', lambda _: self._new_note())
        add.bind('<Enter>',    lambda _: add.config(fg=C['primary']))
        add.bind('<Leave>',    lambda _: add.config(fg=C['ink_s']))

        tk.Frame(self.panel, bg=C['hair'], height=1).pack(fill='x')

        self.notes_list = tk.Frame(self.panel, bg=C['canvas'])
        self.notes_list.pack(fill='both', expand=True)
        self._refresh_list()

    def _refresh_list(self):
        for w in self.notes_list.winfo_children():
            w.destroy()
        notes = self._list_notes()
        if not notes:
            self._ensure_note(self.current)
            notes = self._list_notes()
        for name in notes:
            self._note_row(name)

    def _note_row(self, name):
        active = (name == self.current)
        bg = C['surf3'] if active else C['canvas']

        row = tk.Frame(self.notes_list, bg=bg, cursor='hand2')
        row.pack(fill='x')

        dot = tk.Label(row, text='●' if active else ' ',
                       bg=bg, fg=C['primary'] if active else bg,
                       font=('Segoe UI', 7), width=2)
        dot.pack(side='left', padx=(6, 0), pady=7)

        lbl = tk.Label(row, text=name, bg=bg,
                       fg=C['ink'] if active else C['ink_m'],
                       font=F_BODY, anchor='w', cursor='hand2')
        lbl.pack(side='left', fill='x', expand=True, pady=7)

        del_btn = tk.Label(row, text='×', bg=bg, fg=C['ink_t'],
                           font=('Segoe UI', 10), cursor='hand2', padx=8)
        del_btn.pack(side='right')

        ren_btn = tk.Label(row, text='✎', bg=bg, fg=C['ink_t'],
                           font=('Segoe UI', 10), cursor='hand2', padx=4)
        ren_btn.pack(side='right')

        def on_enter(_):
            if name != self.current:
                for w in (row, lbl, dot, del_btn, ren_btn):
                    w.config(bg=C['surf2'])

        def on_leave(_):
            if name != self.current:
                for w in (row, lbl, dot, del_btn, ren_btn):
                    w.config(bg=C['canvas'])

        for w in (row, lbl, dot):
            w.bind('<Button-1>', lambda _, n=name: self._switch_note(n))
            w.bind('<Enter>', on_enter)
            w.bind('<Leave>', on_leave)

        ren_btn.bind('<Button-1>', lambda _, n=name: self._rename_note(n))
        ren_btn.bind('<Enter>',    lambda _: ren_btn.config(fg=C['ink']))
        ren_btn.bind('<Leave>',    lambda _: ren_btn.config(fg=C['ink_t']))

        del_btn.bind('<Button-1>', lambda _, n=name: self._delete_note(n))
        del_btn.bind('<Enter>',    lambda _: del_btn.config(fg='#ff6b6b'))
        del_btn.bind('<Leave>',    lambda _: del_btn.config(fg=C['ink_t']))

    def _toggle_panel(self):
        if self._panel_open:
            self.panel_sep.pack_forget()
            self.panel.pack_forget()
            self._panel_open = False
        else:
            self.panel.pack(side='left', fill='y',
                            before=self.editor_wrap)
            self.panel_sep.pack(side='left', fill='y',
                                before=self.editor_wrap)
            self._panel_open = True

                                                                                   

    def _build_ctx_menu(self):
        self._ctx_popup = None

        actions = [
            ('Undo', self._undo),
            ('Redo', self._redo),
            None,
            ('Cut',            lambda: self.text.event_generate('<<Cut>>')),
            ('Copy',          lambda: self.text.event_generate('<<Copy>>')),
            ('Paste',            lambda: self.text.event_generate('<<Paste>>')),
            None,
            ('Select All',         lambda: self.text.tag_add('sel', '1.0', 'end')),
            None,
            ('Bold', lambda: self._toggle_tag('bold')),
            ('Italic', lambda: self._toggle_tag('italic')),
            ('Clear Formatting', self._clear_formatting),
            None,
            ('Search', self._toggle_search),
        ]

        def show_ctx(e):
            if self._ctx_popup and self._ctx_popup.winfo_exists():
                self._ctx_popup.destroy()

            pop = tk.Toplevel(self.root)
            pop.withdraw()
            pop.overrideredirect(True)
            pop.attributes('-topmost', True)
            pop.configure(bg=C['surf2'],
                          highlightthickness=1,
                          highlightbackground=C['hair'])
            self._ctx_popup = pop

            for item in actions:
                if item is None:
                    tk.Frame(pop, bg=C['hair'], height=1).pack(fill='x',
                                                                pady=2)
                else:
                    label, cmd = item
                    row = tk.Label(pop, text=label, bg=C['surf2'],
                                   fg=C['ink'], font=F_BODY, anchor='w',
                                   padx=16, pady=5, cursor='hand2')
                    row.pack(fill='x')
                    row.bind('<Enter>',
                             lambda _, r=row: r.config(bg=C['surf3']))
                    row.bind('<Leave>',
                             lambda _, r=row: r.config(bg=C['surf2']))

                    def on_click(_, fn=cmd, p=pop):
                        p.destroy()
                        fn()
                    row.bind('<Button-1>', on_click)

            pop.update_idletasks()
            self._hide_all_process_windows()
            pop.geometry(f'+{e.x_root}+{e.y_root}')
            pop.deiconify()
            pop.focus_set()
            pop.bind('<FocusOut>',
                     lambda _: pop.destroy() if pop.winfo_exists() else None)

        self.text.bind('<Button-3>', show_ctx)

                                                                                   

    @staticmethod
    def _safe_name(name):
        return ''.join(c if (c.isalnum() or c in ' _-') else '_' for c in name)

    def _note_path(self, name):
        return os.path.join(NOTES_DIR, self._safe_name(name) + '.json')

    def _list_notes(self):
        names = set()
        for f in os.listdir(NOTES_DIR):
            if f.endswith('.json'):
                names.add(f[:-5])
        return sorted(names)

    def _migrate_notes(self):
        """One-time migration: .txt → .json (keeps .txt as backup)."""
        for f in os.listdir(NOTES_DIR):
            if not f.endswith('.txt'):
                continue
            name = f[:-4]
            json_p = os.path.join(NOTES_DIR, name + '.json')
            txt_p  = os.path.join(NOTES_DIR, f)
            if os.path.exists(json_p):
                continue
            try:
                with open(txt_p, 'r', encoding='utf-8') as fh:
                    content = fh.read()
                with open(json_p, 'w', encoding='utf-8') as fh:
                    json.dump({'text': content, 'tags': []}, fh,
                              ensure_ascii=False)
            except Exception:
                pass

    def _ensure_note(self, name):
        p = self._note_path(name)
        if not os.path.exists(p):
            with open(p, 'w', encoding='utf-8') as f:
                json.dump({'text': '', 'tags': []}, f, ensure_ascii=False)

    def _load_note(self, name):
        self._ensure_note(name)
        path = self._note_path(name)
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if 'text' not in data:
                raise ValueError
        except (json.JSONDecodeError, ValueError, KeyError):
            with open(path, 'r', encoding='utf-8') as f:
                data = {'text': f.read(), 'tags': []}

        self.text.config(state='normal')
        self.text.delete('1.0', 'end')

        for tag in PERSISTENT_TAGS:
            self.text.tag_remove(tag, '1.0', 'end')

        self.text.insert('1.0', data.get('text', ''))
        self._apply_tags_data(data.get('tags', []))
        self.text.edit_reset()

        if self._locked:
            self.text.config(state='disabled')

    def _save_current(self):
        txt  = self.text.get('1.0', 'end-1c')
        tags = self._get_tags_data()
        with open(self._note_path(self.current), 'w', encoding='utf-8') as f:
            json.dump({'text': txt, 'tags': tags}, f, ensure_ascii=False)

    def _get_tags_data(self):
        result = []
        for tag in PERSISTENT_TAGS:
            ranges = self.text.tag_ranges(tag)
            for i in range(0, len(ranges), 2):
                result.append({
                    'tag':   tag,
                    'start': str(ranges[i]),
                    'end':   str(ranges[i + 1]),
                })
        return result

    def _apply_tags_data(self, tags_data):
        for item in tags_data:
            try:
                self.text.tag_add(item['tag'], item['start'], item['end'])
            except (tk.TclError, KeyError):
                pass


    def _auto_save(self, _=None):
        """Schedule save 500 ms after last keystroke (debounce)."""
        if self._save_timer:
            self.root.after_cancel(self._save_timer)
        self._save_timer = self.root.after(500, self._do_save)

    def _do_save(self):
        self._save_timer = None
        self._save_current()

    def _flush_save(self):
        """Cancel pending debounce and save immediately."""
        if self._save_timer:
            self.root.after_cancel(self._save_timer)
            self._save_timer = None
        self._save_current()


    def _switch_note(self, name):
        self._flush_save()
        if self._search_open:
            self._close_search()
        self.current = name
        self.title_var.set(name)
        self._load_note(name)
        self._refresh_list()

    def _new_note(self):
        existing = self._list_notes()
        i = 1
        while True:
            name = f'Note {i}'
            if not any(name == e or str(i) in e for e in existing):
                break
            i += 1
        self._ensure_note(name)
        self._switch_note(name)

    def _rename_note(self, old_name):
        dialog = tk.Toplevel(self.root)
        dialog.overrideredirect(True)
        dialog.attributes('-topmost', True)
        dialog.configure(bg=C['surf3'], highlightthickness=1, highlightbackground=C['hair'])
        
        x = self.root.winfo_rootx() + (self.root.winfo_width() // 2) - 100
        y = self.root.winfo_rooty() + (self.root.winfo_height() // 2) - 40
        dialog.geometry(f'200x80+{x}+{y}')
        
        tk.Label(dialog, text='New name:', bg=C['surf3'], fg=C['ink_m'], font=F_BODY).pack(pady=(10, 5))
        entry = tk.Entry(dialog, bg=C['surf1'], fg=C['ink'], font=F_BODY, insertbackground=C['ink'], relief='flat')
        entry.pack(fill='x', padx=15)
        entry.insert(0, old_name)
        entry.select_range(0, 'end')
        entry.focus_set()
        
        result = [None]
        
        def on_ok(e=None):
            result[0] = entry.get()
            dialog.destroy()
            
        def on_cancel(e=None):
            dialog.destroy()
            
        entry.bind('<Return>', on_ok)
        entry.bind('<Escape>', on_cancel)
        dialog.bind('<FocusOut>', on_cancel)
        
        dialog.update_idletasks()
        try:
            hwnd = ctypes.windll.user32.GetAncestor(dialog.winfo_id(), GA_ROOT)
            if not ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, WDA_EXCLUDEFROMCAPTURE):
                ctypes.windll.user32.SetWindowDisplayAffinity(hwnd, WDA_MONITOR)
        except Exception:
            pass
            
        self.root.wait_window(dialog)
        
        new_name = result[0]
        if not new_name or new_name == old_name:
            return
        
        new_name = self._safe_name(new_name)
        if not new_name:
            return
            
        existing = self._list_notes()
        if new_name in existing:
            return
            
        old_p = self._note_path(old_name)
        new_p = self._note_path(new_name)
        if os.path.exists(old_p):
            os.rename(old_p, new_p)
            
        if self.current == old_name:
            self.current = new_name
            self.title_var.set(new_name)
            
        self._refresh_list()

    def _delete_note(self, name):
        p = self._note_path(name)
        if os.path.exists(p):
            os.remove(p)
        notes = self._list_notes()
        if name == self.current:
            if not notes:
                new_name = 'Note 1'
                self._ensure_note(new_name)
                notes = [new_name]
            self.current = notes[0]
            self.title_var.set(notes[0])
            self._load_note(notes[0])
            self._refresh_list()
        else:
            self._refresh_list()

                                                                                   

    def _get_hwnd(self):
        child = self.root.winfo_id()
        root  = ctypes.windll.user32.GetAncestor(child, GA_ROOT)
        return root if root else child

    def _apply_win32(self):
        self.root.update_idletasks()
        hwnd = self._get_hwnd()
        ex = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        ex = (ex | WS_EX_TOOLWINDOW) & ~WS_EX_APPWINDOW
        ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex)
        self._hide_all_process_windows()

    def _make_enum_callback(self):
        """Create a GC-safe EnumWindows callback pinned to self."""
        pid = os.getpid()

        @WNDENUMPROC
        def cb(hwnd, _):
            proc_id = ctypes.c_ulong(0)
            ctypes.windll.user32.GetWindowThreadProcessId(
                hwnd, ctypes.byref(proc_id))
            if proc_id.value == pid:
                ok = ctypes.windll.user32.SetWindowDisplayAffinity(
                    hwnd, WDA_EXCLUDEFROMCAPTURE)
                if not ok:
                    ctypes.windll.user32.SetWindowDisplayAffinity(
                        hwnd, WDA_MONITOR)
            return True

        return cb

    def _hide_all_process_windows(self):
        ctypes.windll.user32.EnumWindows(self._enum_cb, 0)


    def _start_hotkey(self):
        def loop():
            r1 = ctypes.windll.user32.RegisterHotKey(
                None, HOTKEY_TOGGLE,
                MOD_CONTROL | MOD_SHIFT, VK_H)
            r2 = ctypes.windll.user32.RegisterHotKey(
                None, HOTKEY_PANIC,
                MOD_CONTROL | MOD_SHIFT, VK_Q)

            if not r1:
                pass                                                      
            if not r2:
                pass                                

            msg = ctypes.wintypes.MSG()
            while ctypes.windll.user32.GetMessageW(
                    ctypes.byref(msg), None, 0, 0) > 0:
                if msg.message == WM_HOTKEY:
                    if msg.wParam == HOTKEY_TOGGLE:
                        self.root.after(0, self._toggle_visible)
                    elif msg.wParam == HOTKEY_PANIC:
                                                                                             
                        os._exit(0)

        t = threading.Thread(target=loop, daemon=True)
        t.start()


    def _toggle_visible(self):
        if self._visible:
            self._fade_out(lambda: self.root.withdraw())
            self._visible = False
        else:
            self.root.attributes('-alpha', 0.0)
            self.root.deiconify()
            self.root.lift()
            self._visible = True
            self._focus_grace = True
            self.root.after(1200,
                            lambda: setattr(self, '_focus_grace', False))
            self.root.after(30, self._apply_win32)
            self.root.after(50, self._fade_in)
            self.root.after(60, lambda: self.text.focus_set())


    def _panic_exit(self):
        """Emergency exit: wipe RAM, kill process."""
        try:
            self.text.delete('1.0', 'end')
        except Exception:
            pass
        self.current = ''
        gc.collect()
        os._exit(0)

                                                                                   

    def _setup_focus_loss(self):
        if self.config.get('auto_hide_on_focus_loss', False):
            self._poll_focus()

    def _poll_focus(self):
        """Check every 800 ms if foreground window belongs to us."""
        if self._visible and not self._focus_grace:
            try:
                fg = ctypes.windll.user32.GetForegroundWindow()
                my = self._get_hwnd()
                if fg != my and fg != 0:
                    proc_id = ctypes.c_ulong(0)
                    ctypes.windll.user32.GetWindowThreadProcessId(
                        fg, ctypes.byref(proc_id))
                    if proc_id.value != os.getpid():
                        self._flush_save()
                        self.root.withdraw()
                        self._visible = False
            except Exception:
                pass
        self.root.after(800, self._poll_focus)

                                                                                   

    def _drag_start(self, e):
        self._dx, self._dy = e.x, e.y

    def _drag_motion(self, e):
        self._pending_x = self.root.winfo_x() + e.x - self._dx
        self._pending_y = self.root.winfo_y() + e.y - self._dy
        if not self._drag_pending:
            self._drag_pending = True
            self.root.after(16, self._apply_drag)

    def _apply_drag(self):
        self.root.geometry(f'+{self._pending_x}+{self._pending_y}')
        self._drag_pending = False

    def _resize_start(self, e):
        self._rx, self._ry = e.x_root, e.y_root
        self._rw = self.root.winfo_width()
        self._rh = self.root.winfo_height()

    def _resize_motion(self, e):
        self._pending_w = max(240, self._rw + e.x_root - self._rx)
        self._pending_h = max(160, self._rh + e.y_root - self._ry)
        if not self._resize_pending:
            self._resize_pending = True
            self.root.after(16, self._apply_resize)

    def _apply_resize(self):
        self.root.geometry(f'{self._pending_w}x{self._pending_h}')
        self._resize_pending = False

                                                                                   

    def _toggle_lock(self):
        self._locked = not self._locked
        if self._locked:
            self.text.config(state='disabled', cursor='arrow')
            self.lock_btn.config(text='⊘', fg=C['primary'])
        else:
            self.text.config(state='normal', cursor='xterm')
            self.lock_btn.config(text='✎', fg=C['ink_s'])
            self.text.focus_force()

                                                                                   

    def _alpha_text(self):
        return f"{int(round(self._target_alpha, 1) * 100)}%"

    def _change_font(self, delta):
        self._font_size = max(8, min(32, self._font_size + delta))
        self.text.config(font=('Segoe UI', self._font_size))
        self.font_lbl.config(text=str(self._font_size))
        self._update_tag_fonts()

    def _change_alpha(self, delta):
        self._target_alpha = round(
            max(0.2, min(1.0, self._target_alpha + delta)), 1)
        self.root.attributes('-alpha', self._target_alpha)
        self.alpha_lbl.config(text=self._alpha_text())

                                                                                   

    def _undo(self):
        try:
            self.text.edit_undo()
            self._auto_save()
        except tk.TclError:
            pass

    def _redo(self):
        try:
            self.text.edit_redo()
            self._auto_save()
        except tk.TclError:
            pass

                                                                                   

    def _fade_out(self, callback=None):
        current = self._target_alpha
        steps   = 8
        step_v  = current / steps

        def step(i):
            if i >= steps:
                self.root.attributes('-alpha', 0.0)
                if callback:
                    callback()
                return
            self.root.attributes('-alpha',
                                 max(0.0, current - step_v * (i + 1)))
            self.root.after(15, lambda: step(i + 1))

        step(0)

    def _fade_in(self):
        target = self._target_alpha
        steps  = 8
        step_v = target / steps

        def step(i):
            if i >= steps:
                self.root.attributes('-alpha', target)
                return
            self.root.attributes('-alpha', min(target, step_v * (i + 1)))
            self.root.after(15, lambda: step(i + 1))

        step(0)

                                                                                   

    def _load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                pass
        return {}

    def _save_config(self):
        data = {
            'geometry':                self.root.geometry(),
            'alpha':                   self._target_alpha,
            'current':                 self.current,
            'font_size':               self._font_size,
            'panel_open':              self._panel_open,
            'auto_hide_on_focus_loss': self.config.get(
                'auto_hide_on_focus_loss', False),
        }
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _validate_geometry(self):
        """Ensure window is on a visible monitor area."""
        self.root.update_idletasks()
        x = self.root.winfo_x()
        y = self.root.winfo_y()
        sm = ctypes.windll.user32
        vx = sm.GetSystemMetrics(SM_XVIRTUALSCREEN)
        vy = sm.GetSystemMetrics(SM_YVIRTUALSCREEN)
        vw = sm.GetSystemMetrics(SM_CXVIRTUALSCREEN)
        vh = sm.GetSystemMetrics(SM_CYVIRTUALSCREEN)
        if x < vx or x > vx + vw - 50 or y < vy or y > vy + vh - 50:
            self.root.geometry('+80+80')

    def _on_close(self):

        try:
            ctypes.windll.user32.UnregisterHotKey(None, HOTKEY_TOGGLE)
            ctypes.windll.user32.UnregisterHotKey(None, HOTKEY_PANIC)
        except Exception:
            pass
        self._flush_save()
        self._save_config()
        self.root.destroy()

    def run(self):
        self.root.mainloop()

                                                                                

if __name__ == '__main__':
    StickyNote().run()
