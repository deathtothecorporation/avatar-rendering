import asyncio
from telegram import Bot
from web3 import Web3

CHAT_ID = -4094632978
ALERT_THRESHOLD_IN_BLOCKS = 15
LOG_FILE_PATH = "./equip_and_update.log"

def getBot():
    bot_token = open("./secrets/telegram_bot_token.txt", "r").read().strip()
    return Bot(token=bot_token)

def getLastBlockProcessed():
    try:
        with open('./data/last_block_processed.txt', 'r') as file:
            return int(file.read().strip())
    except FileNotFoundError:
        raise Exception('File last_block_processed.txt does not exist')

def getNumBlocksBehind(w3):
    lastBlockProcessed = getLastBlockProcessed()
    currentBlock = w3.eth.block_number
    return (currentBlock - lastBlockProcessed)

def getLogTextOfLastRun():
    lastStartLine = None
    with open(LOG_FILE_PATH, 'r') as file:
        lines = file.readlines()
        for i in range(len(lines)):
            if "INFO:Starting script" in lines[i]:
                lastStartLine = i

        if lastStartLine is not None:
            return "".join(lines[lastStartLine:])
        else:
            return "The script start line was not found in the log file."


async def main():
    print("running alert script")
    w3 = Web3(Web3.HTTPProvider(open("./secrets/eth_node_url.txt", "r").read().strip()))

    bot = getBot()
    numBlocksBehind = getNumBlocksBehind(w3)
    if numBlocksBehind < 0:
        await bot.send_message(chat_id=CHAT_ID, text="Uh oh. Script seems to be \"ahead\" of the blockchain by {0} blocks...".format(-numBlocksBehind))
    if numBlocksBehind > ALERT_THRESHOLD_IN_BLOCKS:
        await bot.send_message(chat_id=CHAT_ID, text="Script is behind by {0} blocks.\nLog of last run:\n\n{1}".format(numBlocksBehind, getLogTextOfLastRun()))

if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(main())