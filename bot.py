import asyncio
import json
import logging
import os
import re
import tempfile
from pathlib import Path

import requests
from dotenv import load_dotenv
from ircbot import IrcBot, utils
from ircbot.message import Message
from pexpect import replwrap

from shell_convert import convert_ansi_to_irc

load_dotenv()


def remove_surrounding_quotes(text: str) -> str:
    text = text.strip()
    if (text.startswith('"') and text.endswith('"')) or (text.startswith("'") and text.endswith("'")):
        return text[1:-1]
    return text


HOST = os.getenv("HOST")
assert HOST, "HOST is required"
PORT = int(os.getenv("PORT") or 6667)
SSL = os.getenv("SSL", "").lower() == "true"
NICK = os.getenv("NICK") or "caibot"
PREFIX = os.getenv("PREFIX", ">")
CHANNELS = remove_surrounding_quotes(os.getenv("CHANNELS", "")).split(",")
HANB_CMD = os.getenv("HANB_CMD") or "hanb"
HANB_CMD = os.environ.get("HANB_CMD", HANB_CMD)

utils.set_loglevel(logging.INFO)

info = utils.log

OUTPUT_DIR = "./output/"

# If export dir for coq doesn't exist, create it
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# Change working directory to the directory of OUTPUT_DIR
os.chdir(OUTPUT_DIR)

shell = replwrap.REPLWrapper(HANB_CMD, "hanb>", None)

bot = IrcBot(HOST, PORT, NICK, use_ssl=SSL, disable_automatic_help=True)

bot.set_prefix(PREFIX)
bot.set_parser_order(False)


def paste(file):
    """Paste text to s.h4ks.com"""
    filebin = "http://s.h4ks.com"
    response = requests.post(
        f"{filebin}/api/",
        files={"file": open(file, "rb")},
    )
    try:
        obj = response.json()
    except json.JSONDecodeError:
        response.raise_for_status()
        return response.text

    if "url" in obj:
        return obj["url"]
    if "error" in obj:
        return f"error: {obj['error']}"
    return f"error: {obj}"


def read_paste(url):
    """Read text from s.h4ks.com"""
    response = requests.request("GET", url)
    return response.text


def run_command(text: str):
    return [convert_ansi_to_irc(m) for m in list(shell.run_command(text, timeout=10).split("\n"))]


@bot.arg_command("load", "Populates your environment code with code from url")
async def readurl(args: re.Match, msg: Message):
    if not args[1]:
        return "Please provide a url"
    try:
        with tempfile.NamedTemporaryFile(delete=False) as f:
            f.write(read_paste(args[1]).encode())
        output = run_command(f"load {f.name}")
        os.unlink(f.name)
        return output
    except Exception as e:
        return f"Error: {e}"


@bot.arg_command("reset", "Resets the environment")
async def reset(args: re.Match, msg: Message):
    global shell
    shell.child.close()
    shell = replwrap.REPLWrapper(HANB_CMD, "hanb>", None)
    return "Environment has been reset"


@bot.regex_cmd_with_message(rf"^{PREFIX}(.+)$")
async def run(match: re.Match, message: Message):
    text = match.group(1).strip()
    return run_command(text)


@bot.regex_cmd_with_message(rf"^{PREFIX}\s*h(?:elp)?( .*)?$")
async def run_help(match: re.Match, message: Message):
    text = "help " + (match.group(1) or "").strip()
    help = run_command(text)
    help = [line for line in help if line.strip()]
    if match.group(1):
        return help
    help.extend(
        [
            f"read <url> {bot.commands_help['load'] or ''}",
            f"reset {bot.commands_help['reset'] or ''}",
        ]
    )
    return help


async def on_connect():
    for channel in CHANNELS:
        await bot.join(channel)

    # Send pexpect hanb output to channels
    for channel in CHANNELS:
        await bot.send_message(channel=channel, message=list(shell.child.before.split("\n")))

    # Update cache to eliminate invalid keys and monitor
    while True:
        for file in Path("./").glob("*"):
            info(f"Found {file=}")
            if not file.is_file():
                continue
            name = file.name
            url = paste(file)

            # TODO what channel should we send this to?
            for channel in CHANNELS:
                await bot.send_message(f"{name}: {url}", channel)
            file.unlink()

        await asyncio.sleep(2)


if __name__ == "__main__":
    bot.run_with_callback(on_connect)
