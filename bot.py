import json
import logging
import os
import re
from pathlib import Path

import requests
import trio
from dotenv import load_dotenv
from IrcBot.bot import IrcBot, Message, utils
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

utils.setLogging(logging.INFO)
utils.setParseOrderTopBottom(False)
utils.setPrefix(PREFIX)

info = utils.log

OUTPUT_DIR = "./output/"

# If export dir for coq doesn't exist, create it
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# Change working directory to the directory of OUTPUT_DIR
os.chdir(OUTPUT_DIR)

shell = replwrap.REPLWrapper(HANB_CMD, "hanb>", None)


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


@utils.regex_cmd_with_messsage(rf"^{PREFIX}(.+)$")
async def run(bot: IrcBot, match: re.Match, message: Message):
    text = match.group(1).strip()
    return run_command(text)


@utils.regex_cmd_with_messsage(rf"^{PREFIX}\s*help(.*)$")
async def run_help(bot: IrcBot, match: re.Match, message: Message):
    text = "help" + (match.group(1).strip() or "")
    return run_command(text)


@utils.arg_command("read", "Populates your environment code with code from url")
async def readurl(bot: IrcBot, args: re.Match, msg: Message):
    if not args[1]:
        return "Please provide a url"
    try:
        run_command(read_paste(args[1]))
        return "Code has been evaluated but i am not going to spam the channel"
    except Exception as e:
        return (msg, "Failed to read paste: " + str(e))


@utils.arg_command("reset", "Resets the environment")
async def reset(bot: IrcBot, args: re.Match, msg: Message):
    global shell
    shell.child.close()
    shell = replwrap.REPLWrapper(HANB_CMD, "hanb>", None)
    return "Environment has been reset"


async def onConnect(bot: IrcBot):
    for channel in CHANNELS:
        await bot.join(channel)

    # Send pexpect hanb output to channels
    for channel in CHANNELS:
        await bot.send_message(channel=channel, message=list(shell.child.before.split("\n")))

    async def update_loop():
        """Update cache to eliminate invalid keys and monitor"""
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

            await trio.sleep(3)

    async with trio.open_nursery() as nursery:
        nursery.start_soon(update_loop)


if __name__ == "__main__":
    bot = IrcBot(HOST, PORT, NICK, use_ssl=SSL)
    bot.runWithCallback(onConnect)
