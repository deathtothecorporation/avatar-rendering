# This script iterates through web3 Avatar equip/unequip events and arrives at a "equip state" for all Avatars.
# this state is then written to a json file.
# It operates in 1000 block chunks, and runs once, expected to be run regularly on a cron job.

from render_avatar import renderAvatar
import os
from web3 import Web3
import logging
import json
from pathlib import Path
import boto3

RPC_URL = open("secrets/eth_node_url.txt", "r").read().strip()

w3 = Web3(Web3.HTTPProvider(RPC_URL))

AVATAR_ADDRESS = "0x0Ef38aE5B7Ba0B8641cf34C2B9bAC3694B92EeFF"

EQUIP_EVENT_SIGNATURE = w3.keccak(text="AccessoryEquipped(uint256,uint256)").hex()
UNEQUIP_EVENT_SIGNATURE = w3.keccak(text="AccessoryUnequipped(uint256,uint256)").hex()

def setupS3Client():
    SPACES_KEY = "DO00VCRGC6EKX3EU7JZ9"
    SPACES_SECRET = open('secrets/spaces_secret.txt').read().strip()

    session = boto3.session.Session()
    return session.client('s3',
                            region_name='nyc3',
                            endpoint_url='https://nyc3.digitaloceanspaces.com',
                            aws_access_key_id=SPACES_KEY,
                            aws_secret_access_key=SPACES_SECRET)

def uploadFile(s3Client, filepath, destName):
    return s3Client.put_object(
        Bucket='avatar-renders',
        Key=destName,
        Body=open(filepath, 'rb'),
        CacheControl="public, no-cache",
        ACL='public-read',
        ContentType='image/png'
    )

staticComponentsPerMilady = json.load(open('data-in/static_components_per_milady.json'))
accessoryData = json.load(open('data-in/accessory_data.json'))

def renderAndUploadAvatar(i, equippedAccessoryIds, s3Client):
    # get static components and equipped accessory ids
    staticComponents = staticComponentsPerMilady[str(i)]

    # get accessory type and variant names and form dictionary with same format as staticComponents
    equippedComponents = {}
    for id in equippedAccessoryIds:
        equippedComponents[accessoryData[str(id)]["typeName"]] = accessoryData[str(id)]["variantName"]

    # combine into one dictionary
    drawableComponents = staticComponents.copy()
    drawableComponents.update(equippedComponents)

    # render avatar and save
    logging.info(f"rendering {i}")
    image = renderAvatar(i, drawableComponents)
    logging.info(f"saving {i}")
    image.save('render.png')
    destName = str(i) + '.png'
    response = uploadFile(s3Client, 'render.png', destName)
    if response['ResponseMetadata']['HTTPStatusCode'] != 200:
        raise Exception(f"Failed to upload {i} to s3 with status code {response['ResponseMetadata']['HTTPStatusCode']}")
    os.remove('render.png')
    logging.info(f"done {i}")

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
    logging.basicConfig(filename='equip_and_update.log', level=logging.INFO, format='%(asctime)s %(levelname)s:%(message)s')

    logging.info("Starting script")

    s3Client = setupS3Client()

    # Get last block processed
    lastBlockProcessed = getLastBlockProcessed()

    # Get latest block
    latestBlock = int(w3.eth.block_number)

    # If last block processed is the latest block, there is nothing to do
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

    rerendersNeeded = []

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
            logging.info(f"equipping {accessoryId} to {miladyId}")
            equipState[str(miladyId)].append(accessoryId)
        # if this is an unequip event, remove the accessoryId from the equip state for this miladyId
        elif hexlifiedTopic == UNEQUIP_EVENT_SIGNATURE:
            logging.info(f"unequipping {accessoryId} from {miladyId}")
            try:
                equipState[str(miladyId)].remove(accessoryId)
            except ValueError:
                raise Exception("Unequip event for accessory that was not equipped")
        else:
            raise Exception("Event signature not recognized")

        if miladyId not in rerendersNeeded:
            rerendersNeeded.append(miladyId)

    for miladyId in rerendersNeeded:
        renderAndUploadAvatar(miladyId, equipState[str(miladyId)], s3Client)
    
    # now that we've gotten here without failing, let's save state

    # write equip state to json file
    json.dump(equipState, open("./data/equip_state.json", "w"))

    # update last block processed
    updateLastBlockProcessed(toBlock)

    logging.info(f"Finished processing {len(events)} events for blocks {fromBlock} to {toBlock}")

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logging.exception(f'Unexpected error occurred: {e}')
        raise e