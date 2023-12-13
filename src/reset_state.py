import json

START_BLOCK = 18577827

equipState = {}
for i in range(10000):
    equipState[str(i)] = []

json.dump(equipState, open('data/equip_state.json', 'w'))

json.dump(START_BLOCK-1, open('data/last_block_processed.txt', 'w'))