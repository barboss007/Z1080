import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import secrets
import string
import unicodedata

# ---------- Генератор Z1080 для GUI ----------

# Обмежений (безпечний) алфавіт – латиниця + цифри + кілька знаків
LIMITED_ALPHABET = (
    string.ascii_letters +
    string.digits +
    "!@#$%^&*_-+=?"
)

# Побудуємо «повний» Unicode-алфавіт (без керівних та сурогатів)
def build_full_alphabet():
    chars = []

    # Базова багатомовна площина: пропускаємо керівні символи
    for cp in range(0x21, 0xD7FF):
        ch = chr(cp)
        if unicodedata.category(ch)[0] != "C":
            chars.append(ch)

    for cp in range(0xE000, 0xFFFD):
        ch = chr(cp)
        if unicodedata.category(ch)[0] != "C":
            chars.append(ch)

    # За бажанням можна додати ще діапазони вище, але це вже дуже багато
    return "".join(chars)

FULL_ALPHABET = build_full_alphabet()


def generate_secret(length: int = 16, limited: bool = False) -> str:
    """Генерує секрет довжини length.
    limited=True -> використовуємо LIMITED_ALPHABET,
    інакше FULL_ALPHABET (дуже великий Unicode-алфавіт).
    """
    if length <= 0:
        raise ValueError("Довжина має бути додатною")

    alphabet = LIMITED_ALPHABET if limited else FULL_ALPHABET
    return "".join(secrets.choice(alphabet) for _ in range(length))


# ---------- Tkinter GUI ----------

class Z1080GUI(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Z1080 Experimental GUI")
        self.geometry("700x260")
        self.resizable(False, False)

        # Збережемо поточний секрет
        self.current_secret = ""

        self._build_widgets()

    def _build_widgets(self):
        padding = {"padx": 10, "pady": 5}

        # Довжина
        length_frame = ttk.Frame(self)
        length_frame.pack(fill="x", **padding)

        ttk.Label(length_frame, text="Довжина пароля:").pack(side="left")

        self.length_var = tk.StringVar(value="16")
        self.length_entry = ttk.Entry(length_frame, width=6, textvariable=self.length_var)
        self.length_entry.pack(side="left", padx=5)

        # Галочка «обмежений алфавіт»
        self.limited_var = tk.BooleanVar(value=False)
        self.limited_check = ttk.Checkbutton(
            length_frame,
            text="Обмежений алфавіт (латиниця + цифри + !@#$...)",
            variable=self.limited_var
        )
        self.limited_check.pack(side="left", padx=10)

        # Поле з результатом
        result_frame = ttk.Frame(self)
        result_frame.pack(fill="both", expand=True, **padding)

        ttk.Label(result_frame, text="Z1080 Secret:").pack(anchor="w")

        self.result_text = tk.Text(
            result_frame,
            height=4,
            wrap="word"
        )
        self.result_text.pack(fill="both", expand=True)
        self.result_text.configure(state="disabled")

        # Кнопки
        buttons_frame = ttk.Frame(self)
        buttons_frame.pack(fill="x", **padding)

        self.generate_button = ttk.Button(
            buttons_frame, text="Згенерувати", command=self.on_generate
        )
        self.generate_button.pack(side="left")

        self.copy_button = ttk.Button(
            buttons_frame, text="Копіювати в буфер", command=self.on_copy
        )
        self.copy_button.pack(side="left", padx=5)

        self.save_button = ttk.Button(
            buttons_frame, text="Зберегти в файл", command=self.on_save
        )
        self.save_button.pack(side="left", padx=5)

        ttk.Button(buttons_frame, text="Вихід", command=self.destroy).pack(
            side="right"
        )

    # ---------- Обробники кнопок ----------

    def on_generate(self):
        # зчитуємо довжину
        try:
            length = int(self.length_var.get())
            if length <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Помилка", "Довжина має бути додатним цілим числом.")
            return

        limited = self.limited_var.get()

        try:
            secret = generate_secret(length=length, limited=limited)
        except Exception as e:
            messagebox.showerror("Помилка генерації", str(e))
            return

        self.current_secret = secret

        # показуємо в текстовому полі
        self.result_text.configure(state="normal")
        self.result_text.delete("1.0", "end")
        self.result_text.insert("1.0", secret)
        self.result_text.configure(state="disabled")

        # бонус: в буфер обміну
        try:
            self.clipboard_clear()
            self.clipboard_append(secret)
        except Exception:
            # якщо щось піде не так з буфером – просто ігноруємо
            pass

    def on_copy(self):
        if not self.current_secret:
            messagebox.showinfo("Копіювання", "Спочатку згенеруй секрет.")
            return
        try:
            self.clipboard_clear()
            self.clipboard_append(self.current_secret)
            messagebox.showinfo("Копіювання", "Секрет скопійовано в буфер обміну.")
        except Exception as e:
            messagebox.showerror("Помилка копіювання", str(e))

    def on_save(self):
        if not self.current_secret:
            messagebox.showinfo("Збереження", "Спочатку згенеруй секрет.")
            return

        filename = filedialog.asksaveasfilename(
            title="Зберегти секрет у файл",
            defaultextension=".txt",
            filetypes=[("Текстові файли", "*.txt"), ("Усі файли", "*.*")]
        )
        if not filename:
            return  # користувач натиснув Cancel

        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(self.current_secret + "\n")
            messagebox.showinfo("Збереження", f"Секрет збережено у файл:\n{filename}")
        except Exception as e:
            messagebox.showerror("Помилка збереження", str(e))


if __name__ == "__main__":
    app = Z1080GUI()
    app.mainloop()
