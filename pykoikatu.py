# A chara card contains two pngs (cover, head) and chara data.
# The chara data contains lstInfo and four lists (custom, coordinate, parameter, status).
# The custom list contains three lists (face, body, hair).
# Each list contains several tokens. Data types of tokens are shown below.
# The file structure is really awful... Why don't they use a common pickler?

# TODO:
# Generate random hair and eye
# Generate random coordinates and floats
# Better model of parameter space

import codecs
import h5py
import hsluv
import io
import numpy as np
import struct
from PIL import Image, ImageDraw, ImageFont
from collections import OrderedDict
from pprint import pprint

DEBUG = False


def debug_print(*args):
    if DEBUG:
        print(*args)


# MAX is inclusive
SIGN_UINT1_MAX = 0x7f
SIGN_PAIRS = 0x80
SIGN_PAIRS_MAX = 0x8f
SIGN_LIST = 0x90
SIGN_LIST_MAX = 0x9f
SIGN_STR = 0xa0
SIGN_STR_MAX = 0xbf
SIGN_FALSE = 0xc2
SIGN_TRUE = 0xc3
SIGN_LIST_ALTER = 0xc4
SIGN_FIXED_SIZE_LIST = 0xc5
SIGN_FLOAT4 = 0xca
SIGN_UINT1_ALTER = 0xcc
SIGN_UINT2 = 0xcd
SIGN_UINT4 = 0xce
SIGN_LONG_STR = 0xd9
SIGN_LONG_LIST = 0xdc
SIGN_LONG_PAIRS = 0xde


def parse_token(data, idx0):
    idx = idx0
    if idx >= len(data):
        return None, 0

    if data[idx] <= SIGN_UINT1_MAX:
        token = data[idx]
        idx += 1

    elif SIGN_PAIRS <= data[idx] <= SIGN_PAIRS_MAX:
        token_len = data[idx] - SIGN_PAIRS
        token = OrderedDict()
        idx += 1
        for i in range(token_len):
            key, delta_idx = parse_token(data, idx)
            idx += delta_idx
            value, delta_idx = parse_token(data, idx)
            idx += delta_idx
            token[key] = value

    elif SIGN_LIST <= data[idx] <= SIGN_LIST_MAX:
        token_len = data[idx] - SIGN_LIST
        token = []
        idx += 1
        for i in range(token_len):
            value, delta_idx = parse_token(data, idx)
            idx += delta_idx
            token.append(value)

    elif SIGN_STR <= data[idx] <= SIGN_STR_MAX:
        token_len = data[idx] - SIGN_STR
        try:
            token = data[idx + 1:idx + token_len + 1].decode()
        except:
            debug_print('STR', idx, data[idx:idx + token_len + 1])
            token = data[idx + 1:idx + token_len + 1]
        idx += token_len + 1

    elif data[idx] == SIGN_FALSE:
        token = False
        idx += 1

    elif data[idx] == SIGN_TRUE:
        token = True
        idx += 1

    elif data[idx] == SIGN_LIST_ALTER:
        token_len = data[idx + 1]
        token = []
        idx += 2
        for i in range(token_len):
            value, delta_idx = parse_token(data, idx)
            idx += delta_idx
            token.append(value)
        token = ('LIST_ALTER', token)

    elif data[idx] == SIGN_FIXED_SIZE_LIST:
        token_len = struct.unpack('>H', data[idx + 1:idx + 3])[0]
        token = []
        idx += 3
        max_idx = idx + token_len
        while idx < max_idx:
            # There may be an additional 0
            if data[idx + 4] == 0:
                token.append(0)
                idx += 1
            idx += 4  # Size of data chunk
            value, delta_idx = parse_token(data, idx)
            idx += delta_idx
            token.append(value)
        token = ('FIXED_SIZE_LIST', token)

    elif data[idx] == SIGN_FLOAT4:
        token = struct.unpack('>f', data[idx + 1:idx + 5])[0]
        idx += 5

    elif data[idx] == SIGN_UINT1_ALTER:
        debug_print('UINT1', idx, data[idx], data[idx + 1])
        token = data[idx + 1]
        idx += 2

    elif data[idx] == SIGN_UINT2:
        token = struct.unpack('>H', data[idx + 1:idx + 3])[0]
        idx += 3

    elif data[idx] == SIGN_UINT4:
        token = struct.unpack('>I', data[idx + 1:idx + 5])[0]
        idx += 5

    elif data[idx] == SIGN_LONG_STR:
        token_len = data[idx + 1]
        try:
            token = data[idx + 2:idx + token_len + 2].decode()
        except:
            debug_print('LONG_STR', idx, data[idx:idx + token_len + 2])
            token = data[idx + 2:idx + token_len + 2]
        idx += token_len + 2

    elif data[idx] == SIGN_LONG_LIST:
        token_len = struct.unpack('>H', data[idx + 1:idx + 3])[0]
        token = []
        idx += 3
        for i in range(token_len):
            value, delta_idx = parse_token(data, idx)
            idx += delta_idx
            token.append(value)

    elif data[idx] == SIGN_LONG_PAIRS:
        token_len = struct.unpack('>H', data[idx + 1:idx + 3])[0]
        token = OrderedDict()
        idx += 3
        for i in range(token_len):
            key, delta_idx = parse_token(data, idx)
            idx += delta_idx
            value, delta_idx = parse_token(data, idx)
            idx += delta_idx
            token[key] = value

    else:
        debug_print('?', idx, data[idx])
        token = ('?', data[idx])
        idx += 1

    delta_idx = idx - idx0
    return token, delta_idx


def parse_token_list(data):
    tokens = []
    idx = 0
    while idx < len(data):
        token, delta_idx = parse_token(data, idx)
        idx += delta_idx
        tokens.append(token)
    return tokens


def dump_token_with_len(token):
    data = dump_token(token)
    data = struct.pack('<I', len(data)) + data
    return data


def dump_token(token):
    if type(token) == tuple:
        if len(token) == 2:
            if token[0] == '?':
                debug_print('?', token[1])
                data = bytes([token[1]])
            elif token[0] == 'LIST_ALTER':
                data = (bytes([SIGN_LIST_ALTER, len(token[1])]) +
                        b''.join([dump_token(x) for x in token[1]]))
            elif token[0] == 'FIXED_SIZE_LIST':
                data_list = []
                for x in token[1]:
                    if x == 0:
                        data_list.append(b'\x00')
                    else:
                        data_list.append(dump_token_with_len(x))
                data = b''.join(data_list)
                data = (bytes([SIGN_FIXED_SIZE_LIST]) +
                        struct.pack('>H', len(data)) + data)
            else:
                raise Exception('Unknown token <{}>: {}'.format(
                    type(token), token))
        else:
            raise Exception('Unknown token <{}>: {}'.format(
                type(token), token))

    elif type(token) == list:
        if len(token) < 16:
            data = (bytes([SIGN_LIST + len(token)]) +
                    b''.join([dump_token(x) for x in token]))
        else:
            data = (bytes([SIGN_LONG_LIST]) + struct.pack('>H', len(token)) +
                    b''.join([dump_token(x) for x in token]))

    elif type(token) == OrderedDict:
        if len(token) < 16:
            data = (bytes([SIGN_PAIRS + len(token)]) + b''.join(
                [dump_token(k) + dump_token(v) for k, v in token.items()]))
        else:
            data = (bytes([SIGN_LONG_PAIRS]) + struct.pack(
                '>H', len(token)) + b''.join(
                    [dump_token(k) + dump_token(v) for k, v in token.items()]))

    elif type(token) == str:
        data = token.encode()
        if len(data) < 32:
            data = bytes([SIGN_STR + len(data)]) + data
        else:
            data = bytes([SIGN_LONG_STR, len(data)]) + data

    elif type(token) == int:
        if token <= SIGN_UINT1_MAX:
            data = bytes([token])
        elif token < 2**8:
            data = bytes([SIGN_UINT1_ALTER]) + bytes([token])
        elif token < 2**16:
            data = bytes([SIGN_UINT2]) + struct.pack('>H', token)
        else:
            data = bytes([SIGN_UINT4]) + struct.pack('>I', token)

    elif type(token) == float:
        data = bytes([SIGN_FLOAT4]) + struct.pack('>f', token)

    elif type(token) == bool:
        data = bytes([SIGN_TRUE if token else SIGN_FALSE])

    else:
        raise Exception('Unknown token <{}>: {}'.format(type(token), token))

    return data


def read_png(data, idx0):
    idx = idx0

    # PNG magic number
    assert data[idx:idx + 8] == b'\x89\x50\x4e\x47\x0d\x0a\x1a\x0a'

    idx += 8
    while True:
        chunk_len = struct.unpack('>I', data[idx:idx + 4])[0]
        chunk_type = data[idx + 4:idx + 8].decode()
        idx += chunk_len + 12
        if chunk_type == 'IEND':
            break

    img = data[idx0:idx]
    delta_idx = idx - idx0
    return img, delta_idx


def read_card(filename):
    with open(filename, 'rb') as f:
        card_data = f.read()

    # img1: cover, 252x352
    idx = 0
    img1, delta_idx = read_png(card_data, idx)
    idx += delta_idx

    # img2: head, 240x320
    idx += 33  # \x64\x00\x00\x00 【KoiKatuChara】 0.0.0
    img2, delta_idx = read_png(card_data, idx)
    idx += delta_idx

    # unknown_data is usually \xb7\x00\x00\x00
    unknown_data = card_data[idx:idx + 4]
    idx += 4

    lstinfo_token, delta_idx = parse_token(card_data, idx)
    idx += delta_idx

    idx += 8  # Size of lists
    idx += 4  # Size of face
    face_token, delta_idx = parse_token(card_data, idx)
    idx += delta_idx
    idx += 4  # Size of body
    body_token, delta_idx = parse_token(card_data, idx)
    idx += delta_idx
    idx += 4  # Size of hair
    hair_token, delta_idx = parse_token(card_data, idx)
    idx += delta_idx

    coordinate_token, delta_idx = parse_token(card_data, idx)
    idx += delta_idx
    parameter_token, delta_idx = parse_token(card_data, idx)
    idx += delta_idx
    status_token, delta_idx = parse_token(card_data, idx)

    card = {
        'img1': img1,
        'img2': img2,
        'unknown_data': unknown_data,
        'lstInfo': lstinfo_token,
        'face': face_token,
        'body': body_token,
        'hair': hair_token,
        'coordinate': coordinate_token,
        'parameter': parameter_token,
        'status': status_token,
    }
    return card


def write_card(filename, card):
    face_data = dump_token_with_len(card['face'])
    body_data = dump_token_with_len(card['body'])
    hair_data = dump_token_with_len(card['hair'])
    coordinate_data = dump_token(card['coordinate'])
    parameter_data = dump_token(card['parameter'])
    status_data = dump_token(card['status'])

    idx = 0
    card['lstInfo']['lstInfo'][0]['pos'] = idx
    card['lstInfo']['lstInfo'][0]['size'] = (
        len(face_data) + len(body_data) + len(hair_data))
    idx += len(face_data) + len(body_data) + len(hair_data)
    card['lstInfo']['lstInfo'][1]['pos'] = idx
    card['lstInfo']['lstInfo'][1]['size'] = len(coordinate_data)
    idx += len(coordinate_data)
    card['lstInfo']['lstInfo'][2]['pos'] = idx
    card['lstInfo']['lstInfo'][2]['size'] = len(parameter_data)
    idx += len(parameter_data)
    card['lstInfo']['lstInfo'][3]['pos'] = idx
    card['lstInfo']['lstInfo'][3]['size'] = len(status_data)
    idx += len(status_data)
    lstinfo_data = dump_token(card['lstInfo'])

    with open(filename, 'wb') as g:
        g.write(card['img1'])

        g.write(b''.join([
            b'\x64\x00\x00\x00',
            b'\x12',
            '【KoiKatuChara】'.encode(),
            b'\x05',
            '0.0.0'.encode(),
            struct.pack('<I', len(card['img2'])),
        ]))
        g.write(card['img2'])

        g.write(card['unknown_data'])

        g.write(lstinfo_data)

        g.write(
            struct.pack(
                '<Q',
                len(face_data) + len(body_data) + len(hair_data) +
                len(coordinate_data) + len(parameter_data) + len(status_data)))
        g.write(face_data)
        g.write(body_data)
        g.write(hair_data)

        g.write(coordinate_data)
        g.write(parameter_data)
        g.write(status_data)


def generate_img_text(width, height, bg_color, text, text_color):
    font_name = 'simhei.ttf'
    font_size = 120

    img = Image.new('RGB', (width, height), bg_color)
    draw = ImageDraw.Draw(img)
    font = ImageFont.truetype(font_name, font_size)
    draw.text(((width - font_size) // 2, (height - font_size) // 2), text,
              text_color, font)

    bytes_io = io.BytesIO()
    img.save(bytes_io, format='PNG', optimize=True, compress_level=9)
    img_data = bytes_io.getvalue()

    return img_data


def generate_img12(name):
    hue = np.random.random() * 360
    bg_color = hsluv.hsluv_to_rgb([
        hue,
        50 + np.random.random() * 50,
        50 + np.random.random() * 50,
    ])
    bg_color = tuple(int(x * 256) for x in bg_color)
    text_color = hsluv.hsluv_to_rgb([
        (hue + 120 + np.random.random() * 120) % 360,
        50 + np.random.random() * 50,
        np.random.random() * 100,
    ])
    text_color = tuple(int(x * 256) for x in text_color)
    img1 = generate_img_text(252, 352, bg_color, name, text_color)
    img2 = generate_img_text(240, 320, bg_color, name, text_color)
    return img1, img2


def read_extern_img(filename):
    with open(filename, 'rb') as f:
        img_data = f.read()
    return img_data


def read_face_body_data():
    with h5py.File('data/face_body.hdf5', 'r') as f:
        face_body_mean = np.array(f['mean'], dtype=float)
        face_body_cov = np.array(f['cov'], dtype=float)
    return face_body_mean, face_body_cov


# Sample face and body parameters from multivariate normal distribution
def generate_face_body_params(face_body_mean, face_body_cov):
    face_body_params = np.random.multivariate_normal(face_body_mean,
                                                     face_body_cov)
    face_body_params = np.clip(face_body_params, 0, 1)
    return face_body_params


def parse_face_body_params(card):
    return np.array(
        card['face']['shapeValueFace'] + card['body']['shapeValueBody'] + [
            card['body']['bustSoftness'], card['body']['bustWeight']
        ] + card['body']['skinMainColor'] + card['body']['skinSubColor'] +
        [card['body']['skinGlossPower']] + card['body']['nipColor'] +
        [card['body']['nipGlossPower']],
        dtype=float)


def dump_face_body_params(card, face_body_params):
    card['face']['shapeValueFace'] = face_body_params[0:52].tolist()
    card['body']['shapeValueBody'] = face_body_params[52:96].tolist()
    card['body']['bustSoftness'] = float(face_body_params[96])
    card['body']['bustWeight'] = float(face_body_params[97])
    card['body']['skinMainColor'] = face_body_params[98:102].tolist()
    card['body']['skinSubColor'] = face_body_params[102:106].tolist()
    card['body']['skinGlossPower'] = float(face_body_params[106])
    card['body']['nipColor'] = face_body_params[107:111].tolist()
    card['body']['nipGlossPower'] = float(face_body_params[111])


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


def generate_name(last_name_list,
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

    # np.str to builtin str
    return str(last_name), str(first_name), str(nickname)


def parse_name(card):
    return (card['parameter']['lastname'], card['parameter']['firstname'],
            card['parameter']['nickname'])


def dump_name(card, last_name, first_name, nickname):
    card['parameter']['lastname'] = last_name
    card['parameter']['firstname'] = first_name
    card['parameter']['nickname'] = nickname
