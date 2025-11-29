import argparse
from getpass import getpass
import uuid
from typing import Any, Dict, List

from .crypto import save_zvault, load_zvault, _utc_now_iso, generate_passglyph_password


# ---------------------------------------------------------------------------
# Допоміжна функція для створення запису
# ---------------------------------------------------------------------------

def _make_entry(
    title: str,
    username: str,
    password: str,
    url: str = "",
    notes: str = "",
    mode: str = "plain",
    glyph: str = "",
) -> Dict[str, Any]:
    """
    mode:
      - 'plain'  : у записі зберігається готовий пароль
      - 'glyph'  : пароль генерується з PassGlyph/мнемоніки
    glyph:
      - рядок із символами-гліфами / мнемонікою, якщо mode='glyph'
    """
    now = _utc_now_iso()
    return {
        "id": str(uuid.uuid4()),
        "title": title,
        "username": username,
        "password": password,
        "url": url,
        "notes": notes,
        "mode": mode,
        "glyph": glyph,
        "created": now,
        "updated": now,
    }


# ---------------------------------------------------------------------------
# Команди CLI
# ---------------------------------------------------------------------------

def cmd_new(args: argparse.Namespace) -> None:
    """Створити новий порожній сейф."""
    master = getpass("Master password (new vault): ")
    save_zvault(args.path, master, [])
    print(f"Created empty vault at: {args.path}")


def cmd_add(args: argparse.Namespace) -> None:
    """Додати звичайний запис у сейф (mode='plain')."""
    master = getpass("Master password: ")

    try:
        entries = load_zvault(args.path, master)
    except FileNotFoundError:
        entries = []

    entry = _make_entry(
        title=args.title,
        username=args.username,
        password=args.password,
        url=args.url or "",
        notes=args.notes or "",
    )
    entries.append(entry)
    save_zvault(args.path, master, entries)

    print("Entry added:")
    print(f"  id:       {entry['id']}")
    print(f"  title:    {entry['title']}")
    print(f"  username: {entry['username']}")


def cmd_add_glyph(args: argparse.Namespace) -> None:
    """Додати запис у режимі 'glyph' (пароль не зберігається у сейфі)."""
    master = getpass("Master password: ")

    try:
        entries = load_zvault(args.path, master)
    except FileNotFoundError:
        entries = []

    entry = _make_entry(
        title=args.title,
        username=args.username,
        password="",              # пароль НЕ зберігаємо
        url=args.url or "",
        notes=args.notes or "",
        mode="glyph",
        glyph=args.glyph or "",
    )
    entries.append(entry)
    save_zvault(args.path, master, entries)

    print("Glyph entry added:")
    print(f"  id:       {entry['id']}")
    print(f"  title:    {entry['title']}")
    print(f"  username: {entry['username']}")
    print(f"  glyph:    {entry['glyph']}")
    print(f"  mode:     {entry['mode']}")


def cmd_list(args: argparse.Namespace) -> None:
    """Показати список записів."""
    master = getpass("Master password: ")
    entries = load_zvault(args.path, master)

    if not entries:
        print("Vault is empty.")
        return

    print(f"{'ID':36}  {'TITLE':20}  {'USERNAME':20}  URL")
    print("-" * 90)
    for e in entries:
        print(
            f"{e['id']}  "
            f"{e['title'][:20]:20}  "
            f"{(e['username'] or '')[:20]:20}  "
            f"{e.get('url', '')}"
        )


def cmd_get(args: argparse.Namespace) -> None:
    """Показати один запис по ID.
       Якщо запис у режимі 'glyph' – пароль генерується динамічно."""
    master = getpass("Master password: ")
    entries = load_zvault(args.path, master)

    for e in entries:
        if e["id"] == args.id:
            print("\n=== ENTRY ===")
            print("ID:        ", e["id"])
            print("Title:     ", e["title"])
            print("Username:  ", e["username"])
            print("URL:       ", e.get("url", ""))
            print("Notes:     ", e.get("notes", ""))
            print("Mode:      ", e.get("mode", "plain"))
            print("Glyph:     ", e.get("glyph", ""))

            if e.get("mode") == "glyph":
                pwd = generate_passglyph_password(
                    master_password=master,
                    glyph=e.get("glyph", ""),
                    title=e.get("title", ""),
                    username=e.get("username", ""),
                )
                print("\nGenerated Password:", pwd)
                print("(based on master + glyph + entry metadata)")
            else:
                print("\nStored Password:", e["password"])
            return

    print("Entry not found:", args.id)


def cmd_gui(args: argparse.Namespace) -> None:
    """Запустити графічний інтерфейс Z1080 Secure Vault."""
    from . import gui as gui_app
    gui_app.main()


# ---------------------------------------------------------------------------
# Точка входу CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="zvault",
        description="Z-1080 / ZVAULT CLI",
    )

    parser.add_argument(
        "--path",
        default="vault.zvault",
        help="Path to vault file (default: vault.zvault)",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    # new
    p_new = subparsers.add_parser("new", help="Create new empty vault")
    p_new.set_defaults(func=cmd_new)

    # add
    p_add = subparsers.add_parser("add", help="Add entry")
    p_add.add_argument("--title", required=True)
    p_add.add_argument("--username", required=True)
    p_add.add_argument("--password", required=True)
    p_add.add_argument("--url")
    p_add.add_argument("--notes")
    p_add.set_defaults(func=cmd_add)

    # add-glyph
    p_addg = subparsers.add_parser("add-glyph", help="Add entry in glyph mode")
    p_addg.add_argument("--title", required=True)
    p_addg.add_argument("--username", required=True)
    p_addg.add_argument(
        "--password",
        required=False,
        help="(ignored for glyph mode)",
    )
    p_addg.add_argument(
        "--glyph",
        required=True,
        help="PassGlyph / mnemonic key",
    )
    p_addg.add_argument("--url", required=False, help="Optional URL for entry")
    p_addg.add_argument("--notes", required=False, help="Optional notes for entry")
    p_addg.set_defaults(func=cmd_add_glyph)

    # list
    p_list = subparsers.add_parser("list", help="List entries")
    p_list.set_defaults(func=cmd_list)

    # get
    p_get = subparsers.add_parser("get", help="Show single entry by id")
    p_get.add_argument("--id", required=True)
    p_get.set_defaults(func=cmd_get)

    # gui
    p_gui = subparsers.add_parser("gui", help="Launch graphical interface")
    p_gui.set_defaults(func=cmd_gui)

    # запуск відповідної команди
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()