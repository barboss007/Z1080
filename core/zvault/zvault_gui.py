import os
import sys
import json
import shutil
import tkinter as tk
from tkinter import filedialog, messagebox, ttk, simpledialog
import secrets
import string
from datetime import datetime

from zvault import save_zvault, load_zvault  # зашифрований формат


class SimpleVault:
    """Мінімальний контейнер, щоб мати self.vault.entries."""
    def __init__(self, entries=None):
        if entries is None:
            entries = []
        self.entries = entries


class ZVaultApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Z1080 Secure Vault")

        self.vault = None           # SimpleVault
        self.vault_path = None      # шлях до файлу .zvault
        self.master_password = None # поки що просто зберігаємо

        # Статус блокування сейфу
        self.is_locked = False
        self.idle_timeout_ms = 5 * 60 * 1000  # 5 хвилин неактивності
        self.idle_job = None

        self.icon_path = self.get_icon_path()
        if self.icon_path:
            try:
                self.root.iconbitmap(self.icon_path)
            except Exception:
                pass

        self.setup_theme()
        self.build_ui()
        self.setup_idle_timer_bindings()

    # ------------------------------------------------------------------ #
    # Пошук іконки (працює і в .exe)
    # ------------------------------------------------------------------ #
    def get_icon_path(self) -> str | None:
        """Знайти zvault.ico поруч із скриптом або в каталозі PyInstaller."""
        base_dir = getattr(sys, "_MEIPASS", os.path.dirname(__file__))
        icon_path = os.path.join(base_dir, "zvault.ico")
        return icon_path if os.path.exists(icon_path) else None

    # ------------------------------------------------------------------ #
    # ТЕМА (Dark Mode)
    # ------------------------------------------------------------------ #
    def setup_theme(self):
        style = ttk.Style(self.root)
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        bg = "#1e1e1e"
        fg = "#ffffff"
        accent = "#3a96dd"
        entry_bg = "#2d2d30"
        entry_fg = "#ffffff"

        self.root.configure(bg=bg)

        style.configure(
            "TLabel",
            background=bg,
            foreground=fg,
        )
        style.configure(
            "TButton",
            padding=6,
            background="#2d2d30",
            foreground=fg,
            borderwidth=1,
        )
        style.map(
            "TButton",
            background=[("active", "#3c3c3c")],
        )

        style.configure(
            "Treeview",
            background="#252526",
            foreground=fg,
            fieldbackground="#252526",
            rowheight=22,
            borderwidth=0,
        )
        style.map(
            "Treeview",
            background=[("selected", accent)],
            foreground=[("selected", "#ffffff")],
        )

        style.configure(
            "Treeview.Heading",
            background="#3c3c3c",
            foreground=fg,
        )

    # ------------------------------------------------------------------ #
    # UI
    # ------------------------------------------------------------------ #
    def build_ui(self):
        # ----- Меню (File / Vault) -----
        menubar = tk.Menu(self.root, tearoff=0)

        file_menu = tk.Menu(menubar, tearoff=0, bg="#2d2d30", fg="#ffffff")
        file_menu.add_command(label="Export entries to JSON...", command=self.export_json)
        file_menu.add_command(label="Import entries from JSON...", command=self.import_json)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=file_menu)

        vault_menu = tk.Menu(menubar, tearoff=0, bg="#2d2d30", fg="#ffffff")
        vault_menu.add_command(
            label="Lock now",
            command=lambda: self.lock_vault(auto=False),
            state="disabled",
        )
        vault_menu.add_command(
            label="Unlock",
            command=self.unlock_vault,
            state="disabled",
        )
        menubar.add_cascade(label="Vault", menu=vault_menu)

        self.root.config(menu=menubar)
        self.vault_menu = vault_menu

        # ----- Верхні кнопки -----
        top_frame = ttk.Frame(self.root)
        top_frame.pack(side="top", fill="x", padx=8, pady=8)

        btn_frame = ttk.Frame(top_frame)
        btn_frame.pack(side="left", anchor="w")

        self.btn_open = ttk.Button(btn_frame, text="Open Vault", command=self.open_vault)
        self.btn_open.pack(side="left", padx=(0, 5))

        self.btn_save = ttk.Button(btn_frame, text="Save Vault", command=self.save_vault)
        self.btn_save.pack(side="left", padx=(0, 5))
        self.btn_save.config(state="disabled")

        self.btn_add = ttk.Button(btn_frame, text="Add Entry", command=self.add_entry_dialog)
        self.btn_add.pack(side="left", padx=(0, 5))
        self.btn_add.config(state="disabled")

        # ----- Таблиця (Treeview) -----
        tree_frame = ttk.Frame(self.root)
        tree_frame.pack(side="top", fill="both", expand=True, padx=8, pady=(0, 8))

        columns = ("title", "username", "website")
        self.tree = ttk.Treeview(
            tree_frame,
            columns=columns,
            show="headings",
            selectmode="browse",
        )
        self.tree.heading("title", text="Title")
        self.tree.heading("username", text="Username")
        self.tree.heading("website", text="Website")

        self.tree.column("title", width=250)
        self.tree.column("username", width=150)
        self.tree.column("website", width=300)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscroll=vsb.set)

        self.tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        self.tree.bind("<Double-1>", self.on_tree_double_click)

        # ----- Статус -----
        status_frame = ttk.Frame(self.root)
        status_frame.pack(side="bottom", fill="x", padx=8, pady=(0, 4))

        self.status_label = ttk.Label(status_frame, text="No vault loaded")
        self.status_label.pack(side="left")

        self.lock_label = ttk.Label(status_frame, text="Unlocked", foreground="#00ff00")
        self.lock_label.pack(side="right")

    # ------------------------------------------------------------------ #
    # Idle timer
    # ------------------------------------------------------------------ #
    def setup_idle_timer_bindings(self):
        events = [
            "<Motion>",
            "<KeyPress>",
            "<Button>",
            "<ButtonRelease>",
            "<MouseWheel>",
        ]
        for ev in events:
            self.root.bind_all(ev, self.on_user_activity)

        self.reset_idle_timer()

    def on_user_activity(self, event=None):
        if not self.is_locked and self.vault:
            self.reset_idle_timer()

    def reset_idle_timer(self):
        if self.idle_job is not None:
            self.root.after_cancel(self.idle_job)
            self.idle_job = None

        if self.vault and not self.is_locked:
            self.idle_job = self.root.after(self.idle_timeout_ms, self.on_idle_timeout)

    def on_idle_timeout(self):
        self.lock_vault(auto=True)

    # ------------------------------------------------------------------ #
    # Відкриття сейфу
    # ------------------------------------------------------------------ #
    def open_vault(self):
        filename = filedialog.askopenfilename(
            filetypes=[("ZVault files", "*.zvault"), ("All files", "*.*")]
        )
        if not filename:
            return

        password = simpledialog.askstring(
            "Master Password",
            "Enter master password:",
            show="*",
            parent=self.root,
        )
        if password is None:
            # натиснуто Cancel
            return

        try:
            # читаємо зашифрований сейф і розшифровуємо entries
            entries = load_zvault(filename, password)

            # загортаємо список у SimpleVault, щоб далі працювати через self.vault.entries
            self.vault = SimpleVault(entries)
            self.vault_path = filename
            self.master_password = password
            self.is_locked = False

            # оновлюємо таблицю
            self.refresh_entries()
            self.btn_add.config(state="normal")
            self.btn_save.config(state="normal")

            # меню Vault
            if hasattr(self, "vault_menu"):
                try:
                    self.vault_menu.entryconfig("Lock now", state="normal")
                    self.vault_menu.entryconfig("Unlock", state="disabled")
                except Exception:
                    pass

            # скидаємо таймер неактивності
            self.reset_idle_timer()

            messagebox.showinfo("Success", "Vault opened successfully.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open vault:\n{e}")

    # ------------------------------------------------------------------ #
    # Блокування / розблокування сейфу
    # ------------------------------------------------------------------ #
    def lock_vault(self, auto: bool = False):
        if not self.vault or self.is_locked:
            return

        self.is_locked = True

        # кнопки
        self.btn_add.config(state="disabled")
        self.btn_save.config(state="disabled")

        # статус
        self.lock_label.config(text="Locked", foreground="#ff5555")
        if auto:
            self.status_label.config(text="Vault locked (idle timeout)")
            message = "Vault locked due to inactivity."
        else:
            self.status_label.config(text="Vault locked")
            message = "Vault has been locked."

        # очищаємо таблицю
        for row in self.tree.get_children():
            self.tree.delete(row)
        self.tree.insert("", "end", values=("*** Vault locked ***", "", ""))

        self.reset_idle_timer()

        if not auto:
            messagebox.showinfo("Vault locked", message)

    def unlock_vault(self):
        if not self.vault or not self.is_locked:
            return

        password = simpledialog.askstring(
            "Master Password",
            "Enter master password:",
            show="*",
            parent=self.root,
        )
        if password is None:
            return

        try:
            entries = load_zvault(self.vault_path, password)
            self.vault = SimpleVault(entries)
            self.master_password = password
            self.is_locked = False

            self.refresh_entries()
            self.btn_add.config(state="normal")
            self.btn_save.config(state="normal")

            if hasattr(self, "vault_menu"):
                try:
                    self.vault_menu.entryconfig("Lock now", state="normal")
                    self.vault_menu.entryconfig("Unlock", state="disabled")
                except Exception:
                    pass

            self.lock_label.config(text="Unlocked", foreground="#00ff00")
            self.status_label.config(text="Vault unlocked")
            self.reset_idle_timer()

            messagebox.showinfo("Unlocked", "Vault unlocked.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to unlock vault:\n{e}")

    # ------------------------------------------------------------------ #
    # Оновлення таблиці
    # ------------------------------------------------------------------ #
    def refresh_entries(self):
        for row in self.tree.get_children():
            self.tree.delete(row)

        if not self.vault or self.is_locked:
            return

        entries = getattr(self.vault, "entries", None)
        if not entries:
            return

        for entry in entries:
            title = entry.get("title", "")
            username = entry.get("username", "")
            website = entry.get("url", "") or entry.get("website", "")
            self.tree.insert("", "end", values=(title, username, website))

        self.status_label.config(
            text=f"Vault: {os.path.basename(self.vault_path)} ({len(entries)} entries)"
        )

    # ------------------------------------------------------------------ #
    # Подвійний клік по запису (копіювання пароля в буфер)
    # ------------------------------------------------------------------ #
    def on_tree_double_click(self, event):
        if self.is_locked or not self.vault:
            return

        item_id = self.tree.focus()
        if not item_id:
            return

        index = self.tree.index(item_id)
        entries = getattr(self.vault, "entries", None) or []
        if index < 0 or index >= len(entries):
            return

        entry = entries[index]
        password = entry.get("password", "")
        if not password:
            messagebox.showinfo("Password", "No password set for this entry.")
            return

        try:
            self.root.clipboard_clear()
            self.root.clipboard_append(password)
            self.root.update_idletasks()
        except Exception as e:
            messagebox.showerror("Clipboard", f"Failed to copy password:\n{e}")
            return

        self.status_label.config(text="Password copied to clipboard (will clear in 15s)")
        self.root.after(15000, self.clear_clipboard)

    def clear_clipboard(self):
        try:
            self.root.clipboard_clear()
            self.root.update_idletasks()
        except Exception:
            pass
        self.status_label.config(text=f"Vault: {os.path.basename(self.vault_path)}")

    # ------------------------------------------------------------------ #
    # Резервні копії
    # ------------------------------------------------------------------ #
    def create_backup(self, path: str):
        """Створити резервну копію файлу vault перед перезаписом."""
        if not os.path.exists(path):
            return

        base_dir = os.path.dirname(path)
        base_name = os.path.basename(path)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{base_name}.{timestamp}.bak"
        backup_path = os.path.join(base_dir, backup_name)

        try:
            shutil.copy2(path, backup_path)
        except Exception:
            # не валимо GUI, якщо backup не вдався
            pass

    # ------------------------------------------------------------------ #
    # Збереження сейфу
    # ------------------------------------------------------------------ #
    def save_vault(self, auto: bool = False):
        """Зберегти сейф у файл. auto=True = тихе автозбереження без вікон."""
        if not self.vault:
            if not auto:
                messagebox.showwarning("No vault", "Open a vault first.")
            return

        if self.is_locked:
            if not auto:
                messagebox.showwarning("Locked", "Unlock vault first.")
            return

        path = self.vault_path
        if not path:
            if auto:
                return
            path = filedialog.asksaveasfilename(
                defaultextension=".zvault",
                filetypes=[("ZVault files", "*.zvault"), ("All files", "*.*")],
                title="Save vault as...",
            )
            if not path:
                return
            self.vault_path = path

        # беремо список entries з self.vault
        entries = getattr(self.vault, "entries", None)
        if entries is None:
            if not auto:
                messagebox.showerror("Error", "Vault has no entries list.")
            return

        try:
            # якщо файл вже існує — робимо резервну копію
            if os.path.exists(path):
                self.create_backup(path)

            # шифруємо і записуємо сейф у форматі Z1080/ZVAULT
            save_zvault(path, self.master_password, entries)

            if not auto:
                messagebox.showinfo("Saved", f"Vault saved to:\n{path}")
        except Exception as e:
            if not auto:
                messagebox.showerror("Error", f"Failed to save vault:\n{e}")

    # ------------------------------------------------------------------ #
    # Додавання нового запису (з генератором паролів)
    # ------------------------------------------------------------------ #
    def add_entry_dialog(self):
        if not self.vault:
            messagebox.showwarning("No vault", "Open a vault first.")
            return

        if self.is_locked:
            messagebox.showwarning("Locked", "Unlock vault first.")
            return

        win = tk.Toplevel(self.root)
        win.title("Add New Entry")
        if self.icon_path:
            try:
                win.iconbitmap(self.icon_path)
            except Exception:
                pass

        frm = ttk.Frame(win, padding=10)
        frm.pack(fill="both", expand=True)

        # Title
        ttk.Label(frm, text="Title:").grid(row=0, column=0, sticky="e", pady=2)
        title_var = tk.StringVar()
        ttk.Entry(frm, textvariable=title_var, width=40).grid(row=0, column=1, sticky="w")

        # Username
        ttk.Label(frm, text="Username:").grid(row=1, column=0, sticky="e", pady=2)
        username_var = tk.StringVar()
        ttk.Entry(frm, textvariable=username_var, width=40).grid(row=1, column=1, sticky="w")

        # Password
        ttk.Label(frm, text="Password:").grid(row=2, column=0, sticky="e", pady=2)
        password_var = tk.StringVar()
        password_entry = ttk.Entry(frm, textvariable=password_var, width=40, show="*")
        password_entry.grid(row=2, column=1, sticky="w")

        # Генератор паролів
        gen_frame = ttk.Frame(frm)
        gen_frame.grid(row=3, column=1, sticky="w", pady=4)

        ttk.Label(gen_frame, text="Length:").pack(side="left")
        length_var = tk.IntVar(value=16)
        length_spin = ttk.Spinbox(gen_frame, from_=4, to=128, textvariable=length_var, width=5)
        length_spin.pack(side="left", padx=(4, 8))

        use_lower = tk.BooleanVar(value=True)
        use_upper = tk.BooleanVar(value=True)
        use_digits = tk.BooleanVar(value=True)
        use_symbols = tk.BooleanVar(value=True)

        ttk.Checkbutton(gen_frame, text="a-z", variable=use_lower).pack(side="left")
        ttk.Checkbutton(gen_frame, text="A-Z", variable=use_upper).pack(side="left")
        ttk.Checkbutton(gen_frame, text="0-9", variable=use_digits).pack(side="left")
        ttk.Checkbutton(gen_frame, text="!@#", variable=use_symbols).pack(side="left")

        def generate_password():
            length = length_var.get()
            alphabet = ""

            if use_lower.get():
                alphabet += string.ascii_lowercase
            if use_upper.get():
                alphabet += string.ascii_uppercase
            if use_digits.get():
                alphabet += string.digits
            if use_symbols.get():
                # дружній набір спецсимволів
                alphabet += "!@#$%^&*()-_=+[]{};:,.?/"

            if length <= 0 or not alphabet:
                messagebox.showwarning(
                    "Generator",
                    "Select character sets and length > 0.",
                    parent=win,
                )
                return

            pwd = "".join(secrets.choice(alphabet) for _ in range(length))
            password_var.set(pwd)
            password_entry.focus_set()
            password_entry.select_range(0, tk.END)

        ttk.Button(gen_frame, text="Generate", command=generate_password).pack(
            side="left", padx=(8, 0)
        )

        # URL + Notes
        ttk.Label(frm, text="URL:").grid(row=4, column=0, sticky="e", pady=2)
        url_var = tk.StringVar()
        ttk.Entry(frm, textvariable=url_var, width=40).grid(row=4, column=1, sticky="w")

        ttk.Label(frm, text="Notes:").grid(row=5, column=0, sticky="ne", pady=2)
        notes_txt = tk.Text(frm, width=40, height=4)
        notes_txt.grid(row=5, column=1, sticky="w")

        # Кнопки збереження
        btns = ttk.Frame(frm)
        btns.grid(row=6, column=0, columnspan=2, pady=(8, 0))

        def on_save():
            title = title_var.get().strip()
            username = username_var.get().strip()
            password = password_var.get()
            url = url_var.get().strip()
            notes = notes_txt.get("1.0", "end").strip()

            if not title:
                messagebox.showwarning("Validation", "Title is required.", parent=win)
                return

            try:
                # Якщо раптом є метод add_entry(...) – використовуємо його
                if hasattr(self.vault, "add_entry"):
                    self.vault.add_entry(
                        title=title,
                        username=username,
                        password=password,
                        url=url,
                        notes=notes,
                    )
                else:
                    # Інакше працюємо напряму зі списком dict-ів
                    if not hasattr(self.vault, "entries") or self.vault.entries is None:
                        self.vault.entries = []

                    new_entry = {
                        "title": title,
                        "username": username,
                        "password": password,
                        "url": url,
                        "notes": notes,
                    }
                    self.vault.entries.append(new_entry)

                # оновлюємо таблицю
                self.refresh_entries()

                # автозбереження (тихо)
                self.save_vault(auto=True)

                # закриваємо діалог
                win.destroy()

            except Exception as e:
                messagebox.showerror("Error", f"Failed to add entry:\n{e}", parent=win)

        ttk.Button(btns, text="Save", command=on_save).pack(side="left", padx=(0, 5))
        ttk.Button(btns, text="Cancel", command=win.destroy).pack(side="left")

        win.bind("<Return>", lambda event: on_save())
        frm.grid_columnconfigure(1, weight=1)

    # ------------------------------------------------------------------ #
    # Експорт / імпорт JSON (для відладки / міграцій)
    # ------------------------------------------------------------------ #
    def export_json(self):
        if not self.vault or self.is_locked:
            messagebox.showwarning("Export", "Unlock a vault first.")
            return

        path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Export entries to JSON...",
        )
        if not path:
            return

        entries = getattr(self.vault, "entries", None) or []
        try:
            with open(path, "w", encoding="utf-8") as f:
                json.dump({"entries": entries}, f, ensure_ascii=False, indent=2)
            messagebox.showinfo("Export", f"Entries exported to:\n{path}")
        except Exception as e:
            messagebox.showerror("Export", f"Failed to export JSON:\n{e}")

    def import_json(self):
        if not self.vault or self.is_locked:
            messagebox.showwarning("Import", "Unlock a vault first.")
            return

        path = filedialog.askopenfilename(
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            title="Import entries from JSON...",
        )
        if not path:
            return

        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            messagebox.showerror("Import", f"Failed to read JSON:\n{e}")
            return

        # очікуємо {"entries":[...]} або просто [...]
        if isinstance(data, dict) and "entries" in data:
            entries = data["entries"]
        else:
            entries = data

        if not isinstance(entries, list):
            messagebox.showerror("Import", "Invalid JSON format (expected list of entries).")
            return

        imported = 0
        if not hasattr(self.vault, "entries") or self.vault.entries is None:
            self.vault.entries = []

        for item in entries:
            if not isinstance(item, dict):
                continue

            new_entry = {
                "title": item.get("title", ""),
                "username": item.get("username", ""),
                "password": item.get("password", ""),
                "url": item.get("url", "") or item.get("website", ""),
                "notes": item.get("notes", ""),
            }
            self.vault.entries.append(new_entry)
            imported += 1

        self.refresh_entries()
        self.save_vault(auto=True)

        messagebox.showinfo("Import", f"Imported {imported} entries.")

def main():
    root = tk.Tk()
    app = ZVaultApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()