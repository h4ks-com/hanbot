import re

# Mapping from ANSI color codes to IRC color codes
ansi_to_irc = {
    "0;30": "01",  # Black
    "0;31": "04",  # Red
    "0;32": "03",  # Green
    "0;33": "07",  # Yellow
    "0;34": "02",  # Blue
    "0;35": "06",  # Magenta
    "0;36": "10",  # Cyan
    "0;37": "00",  # White
    "1;30": "14",  # Bold Black (Grey)
    "1;31": "05",  # Bold Red
    "1;32": "09",  # Bold Green
    "1;33": "08",  # Bold Yellow
    "1;34": "12",  # Bold Blue
    "1;35": "13",  # Bold Magenta
    "1;36": "11",  # Bold Cyan
    "1;37": "15",  # Bold White
}

# General pattern to match any ANSI escape sequence
ansi_escape_pattern = re.compile(r"\x1b\[[0-9;?]*[a-zA-Z]")


def convert_ansi_to_irc(text):
    def ansi_to_irc_code(match):
        ansi_code = match.group(0)
        # Extract the actual color code (e.g., '0;31' from '\x1b[0;31m')
        code = re.findall(r"\d+(?:;\d+)?", ansi_code)
        if code:
            irc_code = ansi_to_irc.get(code[0], "")
            # Return the IRC color code format if found, else an empty string
            return f"\x03{irc_code}" if irc_code else ""
        return ""

    # Replace known ANSI color escape sequences with corresponding IRC color codes
    converted_text = ansi_escape_pattern.sub(ansi_to_irc_code, text)
    # Remove any remaining ANSI escape sequences
    converted_text = ansi_escape_pattern.sub("", converted_text)
    return converted_text
