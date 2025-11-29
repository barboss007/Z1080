# Z1080 Secure Vault

Z1080 — це простий, швидкий та безпечний парольний сейф з підтримкою:

- AES-256-GCM шифрування
- PBKDF2 + Salt
- CLI (Command Line Interface)
- GUI (Windows Desktop)
- Автоматичної збірки (GitHub Actions → PyInstaller)
- Формату *.zvault (Z1080 Secure Vault Format)

---

## Встановлення

### Windows executable (рекомендовано)

Завантажити останній реліз:  
`Z1080_CLI.exe`  
`Z1080_GUI.exe`  

Не потребує Python.

---

## Використання (CLI)

Перейдіть у теку з виконуваним файлом:

```powershell
cd <folder with EXE>
```

### Показати довідку:

```powershell
.\Z1080_CLI.exe --help
```

### Створити новий сейф:

```powershell
.\Z1080_CLI.exe new --path myvault.zvault
```

### Додати запис:

```powershell
.\Z1080_CLI.exe add --path myvault.zvault --title "GitHub" --username "andy" --password "MyPass123"
```

### Список записів:

```powershell
.\Z1080_CLI.exe list --path myvault.zvault
```

### Отримати запис по ID:

```powershell
.\Z1080_CLI.exe get --path myvault.zvault --id <ID>
```

---

## Використання (GUI)

Запустити:

```powershell
.\Z1080_GUI.exe
```

або відкрити конкретний сейф:

```powershell
.\Z1080_GUI.exe myvault.zvault
```

---

## Формат файлів

Розширення: `.zvault`

Всередині дані **завжди шифруються AES-256-GCM**, ключ генерується з пароля користувача (PBKDF2-HMAC-SHA256 + Salt).

---

## Build (для розробників)

```powershell
python -m pip install -r requirements.txt
pyinstaller --onefile src/z1080/cli.py
pyinstaller --onefile --windowed src/z1080/gui.py
```

Автоматичний build виконується через GitHub Actions → `build_windows.yml`.

---

## Структура проєкту

```
Z1080/
 ├─ src/
 │   └─ z1080/
 │       ├─ cli.py
 │       ├─ gui.py
 │       ├─ crypto.py
 │       ├─ __init__.py
 │       └─ assets/
 ├─ dist/ (output exe)
 ├─ .github/workflows/build_windows.yml
 └─ README.md
```

---

## Поточний статус

- AES-256-GCM encryption
- CLI (готовий)
- GUI (готовий)
- Автоматична збірка PyInstaller (GitHub Actions)
- Плановано: автопідстановка генератора пароля + синхронізація формату з CLI/GUI.

---

## Ліцензія

MIT — можна використовувати, змінювати і розповсюджувати.

