import math
import tkinter as tk
from tkinter import ttk, messagebox

# Спробуємо використати бібліотечну функцію з пакета z1080
try:
    from z1080.core import generate_secret
except ImportError:
    # Fallback: простий генератор (якщо пакет раптом не імпортується)
    import secrets
    import unicodedata

    def is_usable_codepoint(cp: int) -> bool:
        ch = chr(cp)
        cat = unicodedata.category(ch)
        # Відкидаємо керуючі символи, сурогати і т.п.
        if cat.startswith("C"):
            return False
        # Можеш додати ще фільтри за бажанням
        return True

    # Кешуємо алфавіт
    _ALPHABET = [chr(cp) for cp in range(0x21, 0x10FFFF) if is_usable_codepoint(cp)]
    _N = len(_ALPHABET)

    def generate_secret(length: int = 16) -> str:
        return "".join(secrets.choice(_ALPHABET) for _ in range(length))


# Якщо ти хочеш точно відповідати розрахункам ентропії –
# тут N має бути тим самим, що й в основному генераторі.
# Якщо імпорт вдався, можна приблизно вважати:
N_APPROX = 149_000          # ≈ розмір алфавіту
H_PER_CHAR = math.log2(N_APPROX)  # біти на символ


class Z1080GUI(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("Z1080 Unicode Password Generator")
        self.geometry("600x260")
        self.minsize(500, 220)

        self._build_widgets()

    def _build_widgets(self):
        # Основний контейнер
        main = ttk.Frame(self, padding=10)
        main.pack(fill="both", expand=True)

        # --- Рядок з налаштуванням довжини ---
        length_frame = ttk.Frame(main)
        length_frame.pack(fill="x", pady=(0, 10))

        ttk.Label(length_frame, text="Довжина пароля:").pack(side="left")

        self.length_var = tk.IntVar(value=16)
        length_spin = ttk.Spinbox(
            length_frame,
            from_=4,
            to=256,
            textvariable=self.length_var,
            width=5
        )
        length_spin.pack(side="left", padx=(5, 15))

        # Поле для показу ентропії
        self.entropy_label_var = tk.StringVar()
        entropy_label = ttk.Label(length_frame, textvariable=self.entropy_label_var)
        entropy_label.pack(side="left")

        self._update_entropy_label()

        # оновлювати ентропію при зміні довжини
        def on_length_change(*_):
            try:
                self._update_entropy_label()
            except Exception:
                pass

        self.length_var.trace_add("write", on_length_change)

        # --- Кнопки ---
        btn_frame = ttk.Frame(main)
        btn_frame.pack(fill="x", pady=(0, 10))

        gen_btn = ttk.Button(btn_frame, text="Згенерувати", command=self.on_generate)
        gen_btn.pack(side="left")

        copy_btn = ttk.Button(btn_frame, text="Копіювати в буфер", command=self.on_copy)
        copy_btn.pack(side="left", padx=(10, 0))

        clear_btn = ttk.Button(btn_frame, text="Очистити", command=self.on_clear)
        clear_btn.pack(side="left", padx=(10, 0))

        # --- Поле з результатом ---
        ttk.Label(main, text="Z1080 Secret:").pack(anchor="w")

        self.secret_text = tk.Text(main, height=4, wrap="word", font=("Consolas", 14))
        self.secret_text.pack(fill="both", expand=True)

    def _update_entropy_label(self):
        length = int(self.length_var.get())
        bits = length * H_PER_CHAR
        self.entropy_label_var.set(f"Оціночна ентропія ≈ {bits:.1f} біт")

    def on_generate(self):
        try:
            length = int(self.length_var.get())
            if length <= 0:
                raise ValueError("length must be positive")

            secret = generate_secret(length=length)

            self.secret_text.delete("1.0", "end")
            self.secret_text.insert("1.0", secret)

        except Exception as e:
            messagebox.showerror("Помилка", f"Не вдалось згенерувати пароль:\n{e}")

    def on_copy(self):
        secret = self.secret_text.get("1.0", "end").strip()
        if not secret:
            messagebox.showinfo("Копіювання", "Немає що копіювати – поле порожнє.")
            return

        self.clipboard_clear()
        self.clipboard_append(secret)
        self.update()  # щоб буфер обміну не очищався після закриття
        messagebox.showinfo("Копіювання", "Пароль скопійовано в буфер обміну.")

    def on_clear(self):
        self.secret_text.delete("1.0", "end")


def main():
    app = Z1080GUI()
    app.mainloop()


if __name__ == "__main__":
    main()
