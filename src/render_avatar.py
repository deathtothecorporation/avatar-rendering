import json
from PIL import Image

def getComponentPath(components, typeStr):
    return f"./components/{typeStr}/{components[typeStr]}.png"

def renderAvatar(miladyId, componentsToRender):
    # make a copy of the components dict so we can modify it
    componentsToRender = componentsToRender.copy()

    # Background
    image = Image.open(getComponentPath(componentsToRender, "Background")).convert("RGBA")

    # order of rendering
    typesToDraw = ["Race", "Neck", "Necklace", "Shirt", "Blush", "Mouth", "Eyes", "Face Tattoo", "Face Piercing", "Hair", "Earring", "Eyebrow", "Glasses", "Hat"]

    for t in typesToDraw:
        if t in componentsToRender:
            # combine "Eyes" and "Eye Color" into a single string to find the correct image asset.
            if t == "Eyes":
                componentsToRender[t] = "_".join([componentsToRender[t], componentsToRender["Eye Color"]])
            
            try:
                componentImage = Image.open(getComponentPath(componentsToRender, t)).convert("RGBA")
            except FileNotFoundError:
                raise FileNotFoundError(f"{miladyId}\tCould not find {t} {componentsToRender[t]}")

            try:
                image = Image.alpha_composite(image, componentImage)
            except ValueError as e:
                raise ValueError(f"{miladyId}\tCould not composite {t} {componentsToRender[t]}: {e}")
    
    return image

