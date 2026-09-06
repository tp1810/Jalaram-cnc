#!/usr/bin/env python3
"""
Set (or change) the admin password required to delete the database.

Run this ONCE during installation, then keep the password safe.

Usage:
    python scripts/set_db_password.py
"""
import getpass
import hashlib

from jalaram_cnc.runtime_paths import DATA_DIR, ensure_data_dirs

HASH_FILE = DATA_DIR / '.db_password_hash'


def main() -> None:
    ensure_data_dirs()
    print('=' * 45)
    print('  Set Database Delete Password')
    print('=' * 45)

    if HASH_FILE.exists():
        print('\nA password is already set.')
        old = getpass.getpass('Enter current password to change it: ')
        stored = HASH_FILE.read_text().strip()
        if hashlib.sha256(old.encode()).hexdigest() != stored:
            print('Incorrect current password.')
            return

    pw = getpass.getpass('\nNew password: ')
    if len(pw) < 6:
        print('Password must be at least 6 characters.')
        return

    pw2 = getpass.getpass('Confirm new password: ')
    if pw != pw2:
        print('Passwords do not match.')
        return

    HASH_FILE.write_text(hashlib.sha256(pw.encode()).hexdigest(), encoding='utf-8')
    print('\nPassword saved. Keep it safe — without it you cannot delete the database.')


if __name__ == '__main__':
    main()
