import re

DENY_LIST = [
    "rd /s",
    "rmdir /s",
    "del /f /s /q",
    "format ",
    "diskpart",
    "shutdown",
    "runas",
    "reg delete",
    "vssadmin delete",
    "cipher /w",
]


def check_deny_list(command):
    lowered = command.lower()
    for pattern in DENY_LIST:
        if pattern in lowered:
            return f"Blocked: '{pattern}' is on the deny list"
    return None


DESTRUCTIVE = re.compile(r"(?i)(?:^|[;&|()\n])\s*(?:del|erase|rd|rmdir)(?=\s|$|[;&|()])")


def contains_destructive_command(command):
    return bool(DESTRUCTIVE.search(command))


tests = [
    "rd /s /q C:\\temp",
    "rmdir /s /q temp",
    "del /f /s /q *.tmp",
    "dir",
    "echo hello",
    "shutdown /s /t 0",
    "model.rd_something",
    "erase file.txt",
]
for t in tests:
    print(repr(t), "-> deny:", check_deny_list(t), "| destructive:", contains_destructive_command(t))
