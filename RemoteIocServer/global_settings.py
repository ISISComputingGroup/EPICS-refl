import os


GLOBALS_PATH = os.path.normpath(os.path.join(os.environ.get("ICPCONFIGROOT"), "globals.txt"))


def read_globals_file():
    try:
        with open(GLOBALS_PATH) as f:
            return "\n".join(f.readlines())
    except (OSError, IOError):
        return ""


def write_globals_file(new_contents):
    with open(GLOBALS_PATH, "w") as f:
        f.write(new_contents)
