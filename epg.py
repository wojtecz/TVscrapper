import tkinter as tk
from tkinter import ttk, messagebox
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import os

URL = "https://epg.ovh/pl.xml"
EPG_FILE = "epg.xml"
FAV_FILE = "favorites.txt"
HIDDEN_FILE = "hidden_channels.txt"


def parse_time(value):
    try:
        return datetime.strptime(value[:14], "%Y%m%d%H%M%S")
    except:
        return None


class EPGApp:
    def __init__(self, root):
        self.root = root
        self.root.title("EPG Viewer")
        self.root.geometry("1200x950")

        self.channels = []
        self.programmes = []
        self.favorites = set()
        self.hidden = set()
        self.show_only_fav = tk.BooleanVar(value=False)
        self.search_fav_programs = tk.BooleanVar(value=False)
        self.channel_filter = tk.StringVar()
        self.program_filter = tk.StringVar()

        self.load_favorites()
        self.load_hidden()
        self.create_ui()
        self.load_epg()

    # ---------- UI ----------
    def create_ui(self):
        self.create_menu()

        left = tk.Frame(self.root, width=260)
        left.pack(side=tk.LEFT, fill=tk.Y)

        middle = tk.Frame(self.root)
        middle.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        bottom = tk.Frame(self.root)
        bottom.pack(side=tk.BOTTOM, fill=tk.BOTH, expand=True)

        # Szukaj kanału
        tk.Label(left, text="Szukaj kanału").pack(anchor="w")
        search = tk.Entry(left, textvariable=self.channel_filter)
        search.pack(fill=tk.X)
        search.bind("<KeyRelease>", lambda e: self.refresh_channel_list())

        # Kanały
        tk.Label(left, text="Kanały").pack()
        self.channel_list = tk.Listbox(left, selectmode=tk.EXTENDED)
        self.channel_list.pack(fill=tk.BOTH, expand=True)
        self.channel_list.bind("<<ListboxSelect>>", self.on_channel_select)

        tk.Checkbutton(
            left,
            text="Pokaż tylko ulubione",
            variable=self.show_only_fav,
            command=self.refresh_channel_list
        ).pack(anchor="w")

        tk.Button(left, text="⭐ Dodaj / Usuń ulubiony", command=self.toggle_favorite).pack(fill=tk.X)
        tk.Button(left, text="🚫 Usuń kanał", command=self.hide_channel).pack(fill=tk.X)

        # Szukaj programu
        tk.Label(middle, text="Szukaj programu").pack(anchor="w")
        search_prog = tk.Entry(middle, textvariable=self.program_filter)
        search_prog.pack(fill=tk.X)
        search_prog.bind("<KeyRelease>", lambda e: self.on_channel_select(None))

        # Checkbox: wyszukiwanie w ulubionych kanałach
        tk.Checkbutton(
            middle,
            text="Szukaj programów tylko w ulubionych kanałach",
            variable=self.search_fav_programs,
            command=lambda: self.on_channel_select(None)
        ).pack(anchor="w")

        # Programy
        tk.Label(middle, text="Programy").pack()
        self.program_list = ttk.Treeview(
            middle, columns=("channel", "start", "stop", "title"), show="headings"
        )
        self.program_list.heading("channel", text="Kanał")
        self.program_list.heading("start", text="Start")
        self.program_list.heading("stop", text="Stop")
        self.program_list.heading("title", text="Tytuł")
        self.program_list.pack(fill=tk.BOTH, expand=True)
        self.program_list.bind("<<TreeviewSelect>>", self.on_program_select)

        # Szczegóły – DUŻE + SCROLL
        tk.Label(bottom, text="Szczegóły").pack(anchor="w")

        details_frame = tk.Frame(bottom)
        details_frame.pack(fill=tk.BOTH, expand=True)

        scrollbar = tk.Scrollbar(details_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.details = tk.Text(
            details_frame,
            wrap="word",
            yscrollcommand=scrollbar.set,
            height=25,
            font=("Segoe UI", 10)
        )
        self.details.pack(fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.details.yview)

    def create_menu(self):
        menu = tk.Menu(self.root)
        self.root.config(menu=menu)

        file_menu = tk.Menu(menu, tearoff=0)
        menu.add_cascade(label="Plik", menu=file_menu)
        file_menu.add_command(label="Odśwież EPG (internet)", command=self.download_epg)
        file_menu.add_separator()
        file_menu.add_command(label="Zamknij", command=self.root.quit)

    # ---------- FAVORITES / HIDDEN ----------
    def load_favorites(self):
        if os.path.exists(FAV_FILE):
            with open(FAV_FILE, "r", encoding="utf-8") as f:
                self.favorites = set(line.strip() for line in f)

    def save_favorites(self):
        with open(FAV_FILE, "w", encoding="utf-8") as f:
            for c in sorted(self.favorites):
                f.write(c + "\n")

    def load_hidden(self):
        if os.path.exists(HIDDEN_FILE):
            with open(HIDDEN_FILE, "r", encoding="utf-8") as f:
                self.hidden = set(line.strip() for line in f)

    def save_hidden(self):
        with open(HIDDEN_FILE, "w", encoding="utf-8") as f:
            for c in sorted(self.hidden):
                f.write(c + "\n")

    # ---------- EPG ----------
    def load_epg(self):
        if os.path.exists(EPG_FILE):
            self.load_epg_from_file()
        else:
            self.download_epg()

    def load_epg_from_file(self):
        tree = ET.parse(EPG_FILE)
        root = tree.getroot()
        self.parse_epg(root)

    def download_epg(self):
        try:
            r = requests.get(URL)
            r.encoding = "utf-8"
            with open(EPG_FILE, "w", encoding="utf-8") as f:
                f.write(r.text)

            root = ET.fromstring(r.text)
            self.parse_epg(root)
            messagebox.showinfo("EPG", "EPG odświeżone")
        except Exception as e:
            messagebox.showerror("Błąd", str(e))

    def parse_epg(self, root):
        self.channels = [
            c.get("id") for c in root.findall("channel")
            if c.get("id") not in self.hidden
        ]
        self.programmes = root.findall("programme")
        self.refresh_channel_list()

    # ---------- CHANNELS ----------
    def refresh_channel_list(self):
        self.channel_list.delete(0, tk.END)

        text = self.channel_filter.get().lower()

        channels = [
            c for c in self.channels
            if c not in self.hidden and text in c.lower()
        ]

        if self.show_only_fav.get():
            channels = [c for c in channels if c in self.favorites]

        favs = [c for c in channels if c in self.favorites]
        rest = [c for c in channels if c not in self.favorites]

        for c in favs + rest:
            label = f"⭐ {c}" if c in self.favorites else c
            self.channel_list.insert(tk.END, label)

    def get_selected_channels(self):
        return [
            self.channel_list.get(i).replace("⭐ ", "")
            for i in self.channel_list.curselection()
        ]

    def toggle_favorite(self):
        channels = self.get_selected_channels()
        if not channels:
            return

        for c in channels:
            if c in self.favorites:
                self.favorites.remove(c)
            else:
                self.favorites.add(c)

        self.save_favorites()
        self.refresh_channel_list()

    def hide_channel(self):
        channels = self.get_selected_channels()
        if not channels:
            return

        for c in channels:
            self.hidden.add(c)
            self.favorites.discard(c)

        self.save_hidden()
        self.save_favorites()
        self.refresh_channel_list()
        self.program_list.delete(*self.program_list.get_children())
        self.details.delete("1.0", tk.END)

    # ---------- PROGRAMMES ----------
    def on_channel_select(self, event):
        self.program_list.delete(*self.program_list.get_children())
        self.details.delete("1.0", tk.END)

        # Jeśli checkbox "Szukaj tylko w ulubionych", bierzemy wszystkie ulubione kanały
        if self.search_fav_programs.get():
            channels = list(self.favorites)
        else:
            channels = self.get_selected_channels()

        if not channels:
            return

        now = datetime.now()
        limit = now - timedelta(hours=1)

        for p in self.programmes:
            channel_id = p.get("channel")
            if channel_id not in channels:
                continue

            start_dt = parse_time(p.get("start", ""))
            stop_dt = parse_time(p.get("stop", ""))

            if not start_dt or start_dt < limit:
                continue

            title = p.findtext("title", "")
            filter_text = self.program_filter.get().lower()
            if filter_text and filter_text not in title.lower():
                continue

            start_str = start_dt.strftime("%d.%m %H:%M")
            stop_str = stop_dt.strftime("%H:%M") if stop_dt else ""

            # Dodanie kanału w Treeview
            self.program_list.insert("", tk.END, values=(channel_id, start_str, stop_str, title))

    def on_program_select(self, event):
        self.details.delete("1.0", tk.END)
        item = self.program_list.selection()
        if not item:
            return

        title = self.program_list.item(item)["values"][3]

        for p in self.programmes:
            if p.findtext("title") == title:
                self.details.insert(tk.END, f"Kanał: {p.get('channel')}\n")
                self.details.insert(tk.END, f"Tytuł: {title}\n")
                self.details.insert(tk.END, f"Rok: {p.findtext('date','')}\n")
                self.details.insert(tk.END, f"Kategoria: {p.findtext('category','')}\n\n")
                self.details.insert(tk.END, p.findtext("desc", "") + "\n\n")

                credits = p.find("credits")
                if credits is not None:
                    self.details.insert(tk.END, "Obsada:\n")
                    for a in credits.findall("actor"):
                        self.details.insert(tk.END, f"- {a.text}\n")
                break


if __name__ == "__main__":
    root = tk.Tk()
    app = EPGApp(root)
    root.mainloop()
