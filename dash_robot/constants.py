import binascii
from uuid import UUID

# BLE service and characteristics
ROBOT_SERVICE_UUID = UUID("AF237777-879D-6186-1F49-DECA0E85D9C1")
COMMAND_CHAR_UUID = UUID("AF230002-879D-6186-1F49-DECA0E85D9C1")
DASH_SENSOR_CHAR_UUID = UUID("AF230006-879D-6186-1F49-DECA0E85D9C1")
DOT_SENSOR_CHAR_UUID = UUID("AF230003-879D-6186-1F49-DECA0E85D9C1")

# Command IDs — first byte of every GATT write
COMMANDS = {
    "drive": 0x02,
    "neck_color": 0x03,
    "tail_brightness": 0x04,
    "head_yaw": 0x06,
    "head_pitch": 0x07,
    "eye_brightness": 0x08,
    "eye": 0x09,
    "left_ear_color": 0x0B,
    "right_ear_color": 0x0C,
    "head_color": 0x0D,
    "say": 0x18,
    "move": 0x23,
    "reset": 0xC8,
}

# Built-in sound bank — hex-encoded BLE payloads
NOISES: dict[str, bytes] = {
    k: binascii.unhexlify(v)
    for k, v in {
        # Voices
        "hi": "53595354444153485f48495f564f0b00c900",
        "bragging": "535953544252414747494e4731410b232300",
        "ohno": "5359535456375f4f484e4f5f30390b000000",
        "ayayay": "53595354434f4e46555345445f310b000000",
        "confused": "53595354434f4e46555345445f320b000000",
        "huh": "53595354435552494f55535f30340b000000",
        "okay": "53595354424f5f4f4b41595f30330b000000",
        "yawn": "53595354424f5f56375f5941574e0b000000",
        "tada": "535953545441485f4441485f30310b000000",
        "wee": "53595354455843495445445f30310b000000",
        "bye": "53595354424f5f56375f564152490b000000",
        "charge": "535953544348415247455f3033000b000000",
        # Animals
        "elephant": "53595354454c455048414e545f300e460000",
        "horse": "53595354484f5253455748494e320b000000",
        "cat": "5359535446585f4341545f3031000b000000",
        "dog": "5359535446585f444f475f3032000b000000",
        "dino": "5359535444494e4f534155525f330b000000",
        "lion": "5359535446585f4c494f4e5f30310b000000",
        "goat": "5359535446585f30335f474f41540b000000",
        "croc": "5359535443524f434f44494c45000b000000",
        # Vehicles
        "siren": "53595354545255434b484f524e000b000000",
        "horn": "53595354454e47494e455f5245560b000000",
        "engine": "535953545449524553515545414c0b000000",
        "tires": "53595354424f5f4f4b41595f30330b000000",
        "helicopter": "5359535448454c49434f505445520b000000",
        "jet": "53595354414952504f52544a45540b000000",
        "boat": "53595354545547424f41545f30310b000000",
        "train": "53595354545241494e5f574849530b000000",
        # Effects
        "beep": "53595354424f545f435554455f300b000000",
        "laser": "535953544f545f435554455f30330b000000",
        "gobble": "53595354474f42424c455f3030310b000000",
        "buzz": "5359535455535f4c495042555a5a0b000000",
        "squeek": "535953544f545f435554455f30340b000000",
    }.items()
}
