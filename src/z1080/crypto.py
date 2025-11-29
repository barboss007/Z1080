import hashlib
import json
import base64
import os
import uuid  #додали
from hashlib import pbkdf2_hmac
from datetime import datetime
from typing import List, Dict, Any
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
PASSGLYPH_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789!@#$%^*-_+"
PASSGLYPH_DEFAULT_LEN = 20



class ZVault:
    """
    Z-1080 Secure Vault Format (ZVF-1.0)
    Base implementation — no encryption yet.
    """

    VAULT_VERSION = 1

    def __init__(self):
        self.created = datetime.utcnow().isoformat()
        self.updated = self.created
        self.entries = []

    def add_entry(self, title, username=None, password=None, url=None, notes=None):
        entry = {
            "id": str(uuid.uuid4()),
            "title": title,
            "username": username,
            "password": password,
            "url": url,
            "notes": notes,
            "created": datetime.utcnow().isoformat(),
            "updated": datetime.utcnow().isoformat()
        }
        self.entries.append(entry)
        self.updated = datetime.utcnow().isoformat()
        return entry

    def remove_entry(self, entry_id):
        before = len(self.entries)
        self.entries = [e for e in self.entries if e["id"] != entry_id]
        after = len(self.entries)
        self.updated = datetime.utcnow().isoformat()
        return before != after

    def to_dict(self):
        return {
            "vault_version": self.VAULT_VERSION,
            "created": self.created,
            "updated": self.updated,
            "entries": self.entries
        }

    def save(self, filepath):
        """ Save vault to JSON file (unencrypted stage) """
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, indent=4, ensure_ascii=False)
        return True

    @staticmethod
    def load(filepath):
        """ Load vault from JSON file """
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)

        vault = ZVault()
        vault.created = data.get("created")
        vault.updated = data.get("updated")
        vault.entries = data.get("entries", [])

        return vault
PBKDF2_ITERATIONS = 150_000
SALT_LEN = 16
NONCE_LEN = 12
TAG_LEN = 16  # GCM-тег 128 біт


def _utc_now_iso() -> str:
    """Повертає ISO-8601 UTC у форматі, придатному для ZVAULT."""
    return datetime.utcnow().isoformat() + "Z"


def _derive_key(master_password: str, salt: bytes) -> bytes:
    """PBKDF2-HMAC-SHA256 з 150000 ітерацій, 32-байтовий ключ."""
    return pbkdf2_hmac(
        "sha256",
        master_password.encode("utf-8"),
        salt,
        PBKDF2_ITERATIONS,
        dklen=32,
    )


def encrypt_data_gcm(master_password: str, plaintext: str) -> Dict[str, str]:
    """
    Шифрує довільний текст (JSON рядок з entries) у формат crypto-об’єкта,
    сумісний з PowerShell (AES-256-GCM + PBKDF2).
    """
    salt = os.urandom(SALT_LEN)
    key = _derive_key(master_password, salt)

    nonce = os.urandom(NONCE_LEN)
    aesgcm = AESGCM(key)

    plain_bytes = plaintext.encode("utf-8")
    ct_and_tag = aesgcm.encrypt(nonce, plain_bytes, None)

    # cryptography повертає cipher || tag
    ciphertext = ct_and_tag[:-TAG_LEN]
    tag = ct_and_tag[-TAG_LEN:]

    return {
        "alg": "AES-256-GCM",
        "salt": base64.b64encode(salt).decode("ascii"),
        "nonce": base64.b64encode(nonce).decode("ascii"),
        "data": base64.b64encode(ciphertext).decode("ascii"),
        "tag": base64.b64encode(tag).decode("ascii"),
    }


def decrypt_data_gcm(master_password: str, encrypted: Dict[str, str]) -> str:
    """
    Розшифровує crypto-об’єкт (alg/salt/nonce/data/tag) у вихідний plaintext JSON.
    """
    if encrypted.get("alg") != "AES-256-GCM":
        raise ValueError(f"Unsupported algorithm: {encrypted.get('alg')}")

    salt = base64.b64decode(encrypted["salt"])
    nonce = base64.b64decode(encrypted["nonce"])
    ciphertext = base64.b64decode(encrypted["data"])
    tag = base64.b64decode(encrypted["tag"])

    key = _derive_key(master_password, salt)
    aesgcm = AESGCM(key)

    ct_and_tag = ciphertext + tag
    plain_bytes = aesgcm.decrypt(nonce, ct_and_tag, None)
    return plain_bytes.decode("utf-8")


def save_zvault(path: str, master_password: str, entries: List[Dict[str, Any]]) -> None:
    """
    Записує список entries у файл *.zvault у форматі Z-1080/ZVAULT v1
    з AES-256-GCM, PBKDF2 (SHA256, 150000).
    """
    # серіалізуємо список записів у JSON-рядок
    entries_json = json.dumps(entries, ensure_ascii=False)

    # шифруємо JSON у crypto-об’єкт
    crypto_obj = encrypt_data_gcm(master_password, entries_json)

    # часові мітки (UTC, ISO8601)
    now = _utc_now_iso()

    # об’єкт сейфа (обгортка над crypto)
    vault_obj = {
        "format": "Z-1080/ZVAULT",
        "version": 1,
        "created": now,
        "updated": now,
        "crypto": crypto_obj,
    }

    # запис у файл
    with open(path, "w", encoding="utf-8") as f:
        json.dump(vault_obj, f, ensure_ascii=False, indent=2)
    


def generate_passglyph_password(
    master_password: str,
    glyph: str,
    title: str,
    username: str,
    length: int = PASSGLYPH_DEFAULT_LEN,
) -> str:
    """
    Детермінований генератор паролів для режиму 'glyph'.

    Вхід:
      - master_password: майстер-пароль сейфа
      - glyph: рядок-гліф / мнемоніка
      - title, username: додатковий контекст, щоб різні записи з тим самим glyph були різними
      - length: довжина кінцевого пароля

    Алгоритм:
      1) Формуємо seed-рядок: master|glyph|title|username
      2) Гонуємо його через SHA256 багато разів (seed + лічильник)
      3) З отриманого потоку байтів вибираємо символи з алфавіту PASSGLYPH_ALPHABET
    """
    if length <= 0:
        raise ValueError("Password length must be positive")

    seed = f"{master_password}|{glyph}|{title}|{username}".encode("utf-8")
    alphabet = PASSGLYPH_ALPHABET
    n = len(alphabet)

    output_chars = []
    counter = 0
    buffer = b""

    while len(output_chars) < length:
        if not buffer:
            # Новий блок байтів з SHA256(seed + counter)
            counter_bytes = counter.to_bytes(4, "big")
            buffer = hashlib.sha256(seed + counter_bytes).digest()
            counter += 1

        b = buffer[0]
        buffer = buffer[1:]

        idx = b % n
        output_chars.append(alphabet[idx])

    return "".join(output_chars)

    
    

    with open(path, "w", encoding="utf-8") as f:
        json.dump(vault_obj, f, ensure_ascii=False, indent=2)


def load_zvault(path: str, master_password: str) -> List[Dict[str, Any]]:
    """
    Читає файл *.zvault, перевіряє формат/версію і повертає список entries.
    """
    with open(path, "r", encoding="utf-8") as f:
        vault_obj = json.load(f)

    if vault_obj.get("format") != "Z-1080/ZVAULT":
        raise ValueError(f"Unsupported vault format: {vault_obj.get('format')}")
    if vault_obj.get("version") != 1:
        raise ValueError(f"Unsupported vault version: {vault_obj.get('version')}")

    crypto_obj = vault_obj["crypto"]
    entries_json = decrypt_data_gcm(master_password, crypto_obj)
    entries = json.loads(entries_json)
    return entries


# --------- TEST BLOCK ---------
if __name__ == "__main__":
    vault = ZVault()
    vault.add_entry(
        title="Test Entry",
        username="user@test.com",
        password="ABC123!@#",
        url="https://example.com",
        notes="Prototype test record"
    )

    vault.save("test.zvault")
    print("Vault saved: test.zvault")

    loaded = ZVault.load("test.zvault")
    print("Loaded entries:", loaded.entries)
