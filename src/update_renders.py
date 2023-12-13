import os
from render_avatar import renderAvatar
import json
import boto3
import logging

def setupS3Client():
    SPACES_KEY = "DO00VCRGC6EKX3EU7JZ9"
    SPACES_SECRET = open('secrets/spaces_secret.txt').read().strip()

    session = boto3.session.Session()
    return session.client('s3',
                            region_name='nyc3',
                            endpoint_url='https://nyc3.digitaloceanspaces.com',
                            aws_access_key_id=SPACES_KEY,
                            aws_secret_access_key=SPACES_SECRET)

def uploadFile(filepath, destName):
    return client.put_object(
        Bucket='avatar-renders',
        Key=destName,
        Body=open(filepath, 'rb'),
        CacheControl="public, no-cache",
        ACL='public-read',
        ContentType='image/png'
    )

logging.basicConfig(filename='equip_and_update.log', level=logging.INFO, format='%(asctime)s %(levelname)s:%(message)s')

logging.info("Starting render and upload script")

# get list of filenames in directory rerenders_needed
rerendersNeeded = [int(id) for id in os.listdir('rerenders_needed')]
if len(rerendersNeeded) == 0:
    logging.info('No rerenders needed')
    exit()

rerendersNeeded.sort()

equipState = json.load(open('data/equip_state.json'))
staticComponentsPerMilady = json.load(open('data-in/static_components_per_milady.json'))
accessoryData = json.load(open('data-in/accessory_data.json'))

client = setupS3Client()

# sort rerendersNeeded so we can more easily see progress

for i in rerendersNeeded:
    # get static components and equipped accessory ids
    staticComponents = staticComponentsPerMilady[str(i)]
    equippedAccessoryIds = equipState[str(i)]

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
    # print(f"uploading as {destName}")
    logging.info(uploadFile('render.png', destName))
    os.remove('render.png')

    os.remove('rerenders_needed/' + str(i))
    logging.info(f"done {i}")