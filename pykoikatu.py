# Guessed file structure:
# The chara card contains two png (full, head) and chara data.
# The chara data contains several segments. Each segment begins with b'\xa7version'.
# A segment contains several tokens. Each token has a start byte and several following bytes.
# Start bytes:
# 81: ?
# 84: ?
# 87: ?
# 90~94: list
# a0~bf: string
# c2: False
# c3: True
# c4, x: bool array
# ca: float4
# cd: uint2
# dc, 0, x: list?
# de, 0, x: list?
# Single char: uint1?

# TODO:
# Generate random name and nickname, re-calculate segment length
# Guess full file structure
# Edit clothes
# Edit floats

import codecs
import h5py
import io
import numpy as np
import struct
from PIL import Image


def read_png(data, idx):
    # PNG magic number
    assert data[idx:idx + 8] == b'\x89\x50\x4e\x47\x0d\x0a\x1a\x0a'

    idx += 8
    while True:
        chunk_len = struct.unpack('>I', data[idx:idx + 4])[0]
        chunk_type = data[idx + 4:idx + 8].decode()
        idx += chunk_len + 12
        if chunk_type == 'IEND':
            break
    return idx


# img1: full, 252x352
# img2: head, 240x320
def read_card(filename):
    with open(filename, 'rb') as f:
        card_data = f.read()
    idx = 0
    idx_new = read_png(card_data, idx)
    img1 = card_data[idx:idx_new]
    idx = idx_new + 33
    idx_new = read_png(card_data, idx)
    img2 = card_data[idx:idx_new]
    idx = idx_new + 4
    chara_data = card_data[idx:]
    return img1, img2, chara_data


def write_card(filename, img1, img2, chara_data):
    with open(filename, 'wb') as g:
        g.write(img1)
        g.write(b''.join([
            b'\x64\x00\x00\x00',
            b'\x12',
            '【KoiKatuChara】'.encode(),
            b'\x05',
            '0.0.0'.encode(),
            struct.pack('<I', len(img2)),
        ]))
        g.write(img2)
        g.write(b'\xb7\x00\x00\x00')
        g.write(chara_data)


SIGN_STR = 0xa0
SIGN_STR_MAX = 0xc0
SIGN_FLOAT4 = 0xca
SIGN_UINT2 = 0xcd


def append_tuple(tokens, now_tuple):
    if tokens and isinstance(tokens[-1], tuple):
        tokens[-1] = tokens[-1] + now_tuple
    else:
        tokens.append(now_tuple)

    # Peek backward to recover 'version'
    delta_idx = 0
    for idx in range(len(tokens[-1])):
        if tokens[-1][idx:idx + 8] == tuple(b'\xa7version'):
            delta_idx = idx - len(tokens[-1])
            tokens[-1] = tokens[-1][:idx]
            break

    return delta_idx


def parse_tokens(data):
    STATE_META = 0
    STATE_STR = 1
    STATE_FLOAT4 = 2
    STATE_UINT2 = 3

    tokens = []
    state = STATE_META
    now_chunk = []
    now_count = 0
    idx = 0
    while idx < len(data):
        if state == STATE_META:
            if SIGN_STR <= data[idx] <= SIGN_STR_MAX:
                if now_chunk:
                    idx += append_tuple(tokens, tuple(now_chunk))
                    now_chunk = []
                state = STATE_STR
                now_count = data[idx] - SIGN_STR
                if now_count <= 0:
                    tokens.append('')
                    state = STATE_META
            elif data[idx] == SIGN_FLOAT4:
                if now_chunk:
                    idx += append_tuple(tokens, tuple(now_chunk))
                    now_chunk = []
                state = STATE_FLOAT4
                now_count = 4
            elif data[idx] == SIGN_UINT2:
                if now_chunk:
                    idx += append_tuple(tokens, tuple(now_chunk))
                    now_chunk = []
                state = STATE_UINT2
                now_count = 2
            else:
                now_chunk.append(data[idx])
        elif state == STATE_STR:
            now_chunk.append(data[idx])
            now_count -= 1
            if now_count <= 0:
                try:
                    tokens.append(bytes(now_chunk).decode())
                except:
                    now_tuple = (
                        tuple([SIGN_STR + len(now_chunk)]) + tuple(now_chunk))
                    idx += append_tuple(tokens, now_tuple)
                now_chunk = []
                state = STATE_META
        elif state == STATE_FLOAT4:
            now_chunk.append(data[idx])
            now_count -= 1
            if now_count <= 0:
                tokens.append(struct.unpack('>f', bytes(now_chunk))[0])
                now_chunk = []
                state = STATE_META
        elif state == STATE_UINT2:
            now_chunk.append(data[idx])
            now_count -= 1
            if now_count <= 0:
                tokens.append(struct.unpack('>H', bytes(now_chunk))[0])
                now_chunk = []
                state = STATE_META
        else:
            raise Exception('Unknown state: {}'.format(state))
        idx += 1

    return tokens


def commit_tokens(tokens):
    data_list = []
    for token in tokens:
        if isinstance(token, tuple):
            data_list.append(bytes(token))
        elif isinstance(token, str):
            b = token.encode()
            data_list.append(bytes([SIGN_STR + len(b)]) + b)
        elif isinstance(token, float):
            data_list.append(bytes([SIGN_FLOAT4]) + struct.pack('>f', token))
        elif isinstance(token, int):
            data_list.append(bytes([SIGN_UINT2]) + struct.pack('>H', token))
        else:
            raise Exception('Unknown token: {} {}'.format(type(token), token))
    data = b''.join(data_list)
    return data


def read_token_idx_seg(tokens):
    return [idx for idx in range(len(tokens)) if tokens[idx] == 'version']


token_dspl_body = [
    x for y in [
        [(4, z) for z in range(4, 56)],
        [(4, 63), (4, 65)],
        [(6, z) for z in range(4, 48)],
        [(6, 49), (6, 51), (6, 117)],
    ] for x in y
]

token_dspl_name = [(29, 5), (29, 7), (29, 9)]


def read_tokens(tokens, token_idx_seg, token_dspl_list):
    return [
        tokens[token_idx_seg[seg_idx] + token_dspl]
        for seg_idx, token_dspl in token_dspl_list
    ]


def write_tokens(tokens, token_idx_seg, token_dspl_list, item_list):
    for item_idx, (seg_idx, token_dspl) in enumerate(token_dspl_list):
        tokens[token_idx_seg[seg_idx] + token_dspl] = item_list[item_idx]


def generate_img_pure(width, height, color):
    img = Image.new('RGB', (width, height), color)
    bytes_io = io.BytesIO()
    img.save(bytes_io, format='PNG', optimize=True, compress_level=9)
    img_bytes = bytes_io.getvalue()
    return img_bytes


def generate_random_img():
    color = tuple(np.random.randint(256) for i in range(3))
    img1 = generate_img_pure(252, 352, color)
    img2 = generate_img_pure(240, 320, color)
    return img1, img2


def read_extern_img():
    img = Image.open('test.png').convert('RGB')
    bytes_io = io.BytesIO()
    img.save(bytes_io, format='PNG', optimize=True, compress_level=9)
    img_bytes = bytes_io.getvalue()
    return img_bytes


def read_body_data():
    with h5py.File('data/body.hdf5', 'r') as f:
        body_mean = np.array(f['mean'], dtype=float)
        body_cov = np.array(f['cov'], dtype=float)
    return body_mean, body_cov


# Sample body parameters from a multivariate normal distribution
def generate_random_body(body_mean, body_cov):
    body = np.random.multivariate_normal(body_mean, body_cov)
    body = np.clip(body, 0, 1)
    return body


def read_name_data():
    with codecs.open('data/last_name.txt', 'r', 'utf-8') as f:
        last_name_list = [line.strip() for line in f]
    with codecs.open('data/male_name.txt', 'r', 'utf-8') as f:
        male_name_list = [line.strip() for line in f]
    with codecs.open('data/female_name.txt', 'r', 'utf-8') as f:
        female_name_list = [line.strip() for line in f]
    return last_name_list, male_name_list, female_name_list


GENDER_MALE = 0
GENDER_FEMALE = 1


def generate_random_name(last_name_list,
                         male_name_list,
                         female_name_list,
                         gender=GENDER_FEMALE):
    last_name = np.random.choice(last_name_list)

    if gender == GENDER_MALE:
        first_name = np.random.choice(male_name_list)
    elif gender == GENDER_FEMALE:
        first_name = np.random.choice(female_name_list)
    else:
        raise Exception('Unknown gender: {}'.format(gender))
    hiragana, first_name = first_name.split()

    if len(hiragana) == 1:
        nickname = hiragana
    else:
        choice = np.random.randint(5)
        if choice == 0:
            nickname = hiragana[0]
        elif choice == 1:
            nickname = hiragana[-1]
        elif choice == 2:
            nickname = hiragana[:2]
        elif choice == 3:
            nickname = hiragana[-2:]
        else:  # choice == 4
            nickname = hiragana

    suffix = np.random.choice(['ちゃん', 'たん', 'りん', 'じん'])
    nickname += suffix

    return [last_name, first_name, nickname]
