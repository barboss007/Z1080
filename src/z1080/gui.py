import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import secrets
import pyperclip
from datetime import datetime

# ---- Unicode full-spectrum alphabet (≈149 000 символів) ----
# Додані ключові групи Unicode: латиниця, грецька, кандзі, математичні символи, emoji, технічні символи.
UNICODE_ALPHABET = "".join(
    chr(i) for i in range(0x20, 0x1FAF0)
    if (
        chr(i).isprintable()
        and not chr(i).isspace()
        and i not in range(0x7F, 0xA0)
    )
)

# ---- Import backend ----
try:
    # Normal run via package
    from z1080.crypto import save_zvault, load_zvault, generate_passglyph_password
except ImportError:
    # Running as standalone script (PyInstaller mode)
    from crypto import save_zvault, load_zvault, generate_passglyph_password



class ZVaultApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Z1080 Secure Vault")
        self.vault_path = None
        self.vault_entries = []
        self.master_password = None

        self._build_ui()

    # ---------------- GUI -----------------

    def _build_ui(self):
        frame_top = tk.Frame(self.root)
        frame_top.pack(pady=10)

        btn_open = tk.Button(frame_top, text="Open Vault", command=self.open_vault)
        btn_open.grid(row=0, column=0, padx=5)

        btn_save = tk.Button(frame_top, text="Save Vault", command=self.save_vault)
        btn_save.grid(row=0, column=1, padx=5)

        btn_add = tk.Button(frame_top, text="Add Entry", command=self.add_entry_window)
        btn_add.grid(row=0, column=2, padx=5)

        # Table
        columns = ("Title", "Username", "URL", "Mode")
        self.table = ttk.Treeview(self.root, columns=columns, show="headings")
        for c in columns:
            self.table.heading(c, text=c)
            self.table.column(c, width=180)
        self.table.pack(fill="both", expand=True, padx=10, pady=10)

    # ---------------- Vault Ops -----------------

    def open_vault(self):
        path = filedialog.askopenfilename(
            title="Open ZVault",
            filetypes=[("ZVault Files", "*.zvault"), ("All Files", "*.*")]
        )
        if not path:
            return

        pw = self._ask_password("Enter Master Password:")
        if not pw:
            return

        try:
            entries = load_zvault(path, pw)
            self.vault_entries = entries
            self.vault_path = path
            self.master_password = pw
            self._refresh_table()
            messagebox.showinfo("OK", "Vault successfully decrypted.")
        except Exception as e:
            messagebox.showerror("Error", f"Failed to open vault:\n{e}")

    def save_vault(self):
        if self.vault_path is None:
            path = filedialog.asksaveasfilename(
                title="Save Vault",
                defaultextension=".zvault",
                filetypes=[("ZVault Files", "*.zvault")]
            )
            if not path:
                return
            self.vault_path = path

        if not self.master_password:
            self.master_password = self._ask_password("Set Master Password:")

        try:
            save_zvault(self.vault_path, self.master_password, self.vault_entries)
            messagebox.showinfo("Saved", "Vault saved successfully.")
        except Exception as e:
            messagebox.showerror("Error", f"Save failed:\n{e}")

    # ---------------- Add Entry -----------------

    def add_entry_window(self):
        win = tk.Toplevel(self.root)
        win.title("Add Entry")

        tk.Label(win, text="Title:").grid(row=0, column=0)
        entry_title = tk.Entry(win, width=30)
        entry_title.grid(row=0, column=1)

        tk.Label(win, text="Username:").grid(row=1, column=0)
        entry_user = tk.Entry(win, width=30)
        entry_user.grid(row=1, column=1)

        tk.Label(win, text="URL:").grid(row=2, column=0)
        entry_url = tk.Entry(win, width=30)
        entry_url.grid(row=2, column=1)

        tk.Label(win, text="Notes:").grid(row=3, column=0)
        entry_notes = tk.Entry(win, width=30)
        entry_notes.grid(row=3, column=1)

        # --- Password mode selection ---
        mode_var = tk.StringVar(value="plain")
        tk.Label(win, text="Mode:").grid(row=4, column=0)

        ttk.Radiobutton(win, text="Store password", variable=mode_var, value="plain").grid(row=4, column=1, sticky="w")
        ttk.Radiobutton(win, text="Z1080 Secret (deterministic)", variable=mode_var, value="glyph").grid(row=5, column=1, sticky="w")

        # ---------------- Password field ----------------
        tk.Label(win, text="Password / Glyph:").grid(row=6, column=0)
        entry_pass = tk.Entry(win, width=30)
        entry_pass.grid(row=6, column=1)

        # --- Generator buttons ---
        btn_gen_std = tk.Button(win, text="Generate (Std)", command=lambda: entry_pass.insert(0, secrets.token_urlsafe(16)))
        btn_gen_z1080 = tk.Button(win, text="Generate Z1080 Secret", command=lambda: entry_pass.insert(0, self.generate_unicode_password(24)))
        btn_copy = tk.Button(win, text="Copy", command=lambda: pyperclip.copy(entry_pass.get()))

        btn_gen_std.grid(row=7, column=0, pady=5)
        btn_gen_z1080.grid(row=7, column=1, sticky="w")
        btn_copy.grid(row=7, column=2)

        # --- Confirm ---
        def apply():
            mode = mode_var.get()
            password = entry_pass.get() if mode == "plain" else ""
            glyph = entry_pass.get() if mode == "glyph" else ""

            self.vault_entries.append({
                "id": datetime.utcnow().isoformat(),
                "title": entry_title.get(),
                "username": entry_user.get(),
                "url": entry_url.get(),
                "notes": entry_notes.get(),
                "password": password,
                "glyph": glyph,
                "mode": mode
            })
            self._refresh_table()
            win.destroy()

        tk.Button(win, text="Add", command=apply).grid(row=8, column=1, pady=10)

    # ---------------- Helpers -----------------

    def generate_unicode_password(self, length: int = 24):
        return "".join(secrets.choice(UNICODE_ALPHABET) for _ in range(length))

    def _refresh_table(self):
        for row in self.table.get_children():
            self.table.delete(row)
        for e in self.vault_entries:
            self.table.insert("", tk.END, values=(e["title"], e["username"], e["url"], e["mode"]))

    @staticmethod
    def _ask_password(prompt: str):
        win = tk.Toplevel()
        win.title("Password Required")
        tk.Label(win, text=prompt).pack()
        entry = tk.Entry(win, show="•", width=30)
        entry.pack(pady=5)
        result = {"pw": None}

        def ok():
            result["pw"] = entry.get()
            win.destroy()

        tk.Button(win, text="OK", command=ok).pack(pady=5)
        win.wait_window()
        return result["pw"]


def main():
    root = tk.Tk()
    ZVaultApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()