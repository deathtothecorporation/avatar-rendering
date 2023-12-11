# This script iterates through web3 Avatar equip/unequip events and arrives at a "equip state" for all Avatars.
# this state is then written to a json file.
# It operates in 1000 block chunks, and runs once, expected to be run regularly on a cron job.

from web3 import Web3
import logging
import json

RPC_URL = open("secrets/eth_node_url.txt", "r").read().strip()

w3 = Web3(Web3.HTTPProvider(RPC_URL))

AVATAR_ADDRESS = "0x0Ef38aE5B7Ba0B8641cf34C2B9bAC3694B92EeFF"

EQUIP_EVENT_SIGNATURE = w3.keccak(text="AccessoryEquipped(uint256,uint256)").hex()
print(EQUIP_EVENT_SIGNATURE)
UNEQUIP_EVENT_SIGNATURE = w3.keccak(text="AccessoryUnequipped(uint256,uint256)").hex()

# Load last processed block or fail if the file does not exist
def getLastBlockProcessed():
    try:
        with open('./data/last_block_processed.txt', 'r') as file:
            return int(file.read().strip())
    except FileNotFoundError:
        raise Exception('File last_block_processed.txt does not exist')

def updateLastBlockProcessed(blockNumber):
    with open('./data/last_block_processed.txt', 'w') as file:
        file.write(str(blockNumber))

def main():
    logging.basicConfig(filename='equip_state_update.log', level=logging.INFO, format='%(asctime)s %(levelname)s:%(message)s')

    logging.info("Starting Avatar equip/unequip event processing")

    # Get last block processed
    lastBlockProcessed = getLastBlockProcessed()

    # Get latest block
    latestBlock = int(w3.eth.block_number)

    # If last block processed is the latest block, there is nothing to do
    print(lastBlockProcessed, latestBlock)
    if lastBlockProcessed >= latestBlock:
        logging.info("No new blocks to process")
        return

    # create filter for equip/unequip events
    fromBlock = lastBlockProcessed + 1

    toBlock = min(fromBlock + 1000, latestBlock)
    logging.info(f"Processing blocks {fromBlock} to {toBlock}")
    
    filter = w3.eth.filter({
        "address": AVATAR_ADDRESS,
        "fromBlock": fromBlock,
        "toBlock": toBlock,
        # a list of a list of topics means we are looking for either of these event signatures
        # (in contrast to looking for an event with arg 1 in position 1 and arg 2 in position 2)
        # https://web3py.readthedocs.io/en/stable/filters.html#web3.eth.Eth.filter
        "topics": [[EQUIP_EVENT_SIGNATURE, UNEQUIP_EVENT_SIGNATURE]]
    })

    # Get all events
    events = filter.get_all_entries()

    if len(events) == 0:
        logging.info("No events to process")
        updateLastBlockProcessed(toBlock)
        return
    
    # get current equip state from json file
    equipState = json.load(open("./data/equip_state.json", "r"))

    # first, order events by block number and then by index
    events.sort(key=lambda x: (x["blockNumber"], x["logIndex"]))

    # finally, iterate through events and update equip state
    for event in events:
        hexlifiedTopic = event["topics"][0].hex()
        # get tokenId and accessoryId from event
        miladyId = int(event["topics"][1].hex(), 16)
        accessoryId = int(event["topics"][2].hex(), 16)

        # if this is an equip event, add the accessoryId to the equip state for this miladyId
        if hexlifiedTopic == EQUIP_EVENT_SIGNATURE:
            print(f"equipping {accessoryId} to {miladyId}")
            equipState[str(miladyId)].append(accessoryId)
        # if this is an unequip event, remove the accessoryId from the equip state for this miladyId
        elif hexlifiedTopic == UNEQUIP_EVENT_SIGNATURE:
            print(f"unequipping {accessoryId} from {miladyId}")
            try:
                equipState[str(miladyId)].remove(accessoryId)
            except ValueError:
                raise Exception("Unequip event for accessory that was not equipped")
        else:
            raise Exception("Event signature not recognized")
    
    # write equip state to json file
    json.dump(equipState, open("./data/equip_state.json", "w"))

    logging.info(f"Finished processing {len(events)} events for blocks {fromBlock} to {toBlock}")
    # update last block processed
    updateLastBlockProcessed(toBlock)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.exception(f'Unexpected error occurred: {e}')
        raise e