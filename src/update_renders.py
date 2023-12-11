import os
from render_avatar import renderAvatar
import json

# get list of filenames in directory rerenders_needed
rerendersNeeded = [int(id) for id in os.listdir('rerenders_needed')]
equipState = json.load(open('data/equip_state.json'))
staticComponentsPerMilady = json.load(open('data-in/static_components_per_milady.json'))
accessoryData = json.load(open('data-in/accessory_data.json'))

# sort rerendersNeeded so we can more easily see progress
rerendersNeeded.sort()

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
    image = renderAvatar(i, drawableComponents)
    image.save('avatar_renders/' + str(i) + '.png')

    os.remove('rerenders_needed/' + str(i))
    print('Rendered ' + str(i))