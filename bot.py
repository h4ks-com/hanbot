import os
import re
from pathlib import Path
from pexpect import replwrap

import requests
import trio
from IrcBot.bot import IrcBot, Message, utils

from conf import CHANNELS, NICK, PORT, PREFIX, SERVER, SSL, HANB_CMD

HANB_CMD = os.environ.get("HANB_CMD", HANB_CMD)

utils.setLogging(10)
utils.setParseOrderTopBottom(True)
utils.setPrefix(PREFIX)

info = utils.log

OUTPUT_DIR = "./output/"

# If export dir for coq doesn't exist, create it
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# Change working directory to the directory of OUTPUT_DIR
os.chdir(OUTPUT_DIR)

oldterm = os.environ['TERM']
os.environ['TERM'] = 'dummy'
shell = replwrap.REPLWrapper(HANB_CMD, "hanb>", None)


def paste(text):
    """Paste text to ix.io."""
    info(f"Pasting {text=}")
    try:
        url = "http://ix.io"
        payload = {"f:1=<-": text}
        response = requests.request("POST", url, data=payload)
        return response.text
    except Exception as e:
        info(f"Error {e=}")
        return "Failed to paste"


def read_paste(url):
    """Read text from ix.io."""
    response = requests.request("GET", url)
    return response.text


def run_command(text: str):
    return list(shell.run_command(text, timeout=10).split("\n"))

@utils.regex_cmd_with_messsage(fr"^{PREFIX}(.+)$")
async def run(bot: IrcBot, match: re.Match, message: Message):
    text = match.group(1).strip()
    return run_command(text)

@utils.regex_cmd_with_messsage(fr"^{PREFIX}\s*help(.*)$")
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
        return(msg, "Failed to read paste: " + str(e))


async def onConnect(bot: IrcBot):
    for channel in CHANNELS:
        await bot.join(channel)

    # Send pexpect hanb output to channels
    for channel in CHANNELS:
        await bot.send_message(channel=channel, message=list(shell.child.before.split("\n")))

    async def update_loop():
        """Update cache to eliminate invalid keys and monitor
        COQ_EXPORT_DIR."""
        while True:
            for file in Path("./").glob("*"):
                info(f"Found {file=}")
                if not file.is_file():
                    continue
                name = file.name
                url = paste(file.read_text())

                # TODO what channel should we send this to?
                for channel in CHANNELS:
                    await bot.send_message(f"{name}: {url}", channel)
                file.unlink()

            await trio.sleep(3)

    async with trio.open_nursery() as nursery:
        nursery.start_soon(update_loop)


if __name__ == "__main__":
    bot = IrcBot(SERVER, PORT, NICK, use_ssl=SSL)
    bot.runWithCallback(onConnect)


os.environ['TERM'] = oldterm
