from pathlib import Path

# touch files 0..9999 in rerenders_needed
for i in range(10000):
    Path(f"rerenders_needed/{i}").touch()