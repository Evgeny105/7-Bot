HELP_COMMANDS = """
/help - list of commands
/start - start working with bot
/stop - kill bot
"""

TZs = (
    [f"-{i:02}:00" for i in range(12, 0, -1)]
    + ["00:00"]
    + [f"+{i:02}:00" for i in range(1, 15)]
)
