"""
Z1080 Secure Vault package.

High-level API:

- z1080.crypto   – шифрування та формат сейфу
- z1080.cli      – командний інтерфейс
- z1080.gui      – графічний інтерфейс
"""

from .crypto import (
    save_zvault,
    load_zvault,
    generate_passglyph_password,
)