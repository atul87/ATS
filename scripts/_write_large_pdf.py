from pathlib import Path

p = Path("tests/fixtures/generated/too_large.pdf")
size = 6 * 1024 * 1024
p.write_bytes(b"%PDF" + b"A" * size)
print(p.stat().st_size)
