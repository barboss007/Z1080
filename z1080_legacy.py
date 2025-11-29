import secrets
import sys
import argparse

# ~149 000 Unicode | базовий safe-мінімум виключає керуючі символи
UNICODE_RANGE = (0x20, 0x2FFF)  

def generate_secret(length: int = 16):
    return ''.join(chr(secrets.randbelow(UNICODE_RANGE[1] - UNICODE_RANGE[0]) + UNICODE_RANGE[0]) for _ in range(length))

def main():
    parser = argparse.ArgumentParser(
        prog="Z1080",
        description="Z1080 high-entropy Unicode password generator."
    )

    parser.add_argument(
        "-g", "--generate",
        action="store_true",
        help="Generate a new password"
    )

    parser.add_argument(
        "-l", "--length",
        type=int,
        default=16,
        help="Password length (default: 16)"
    )

    parser.add_argument(
        "-s", "--save",
        type=str,
        help="Save the generated password to a file"
    )

    args = parser.parse_args()

    if not args.generate and not args.save:
        parser.print_help()
        return

    secret = generate_secret(args.length)

    print("\nZ1080 Secret:\n", secret)

    if args.save:
        with open(args.save, "w", encoding="utf-8") as f:
            f.write(secret)
        print(f"\nSaved to: {args.save}")

if __name__ == "__main__":
    main()
