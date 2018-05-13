import os
from pykoikatu import *

in_dir = 'tmp'
out_filename = 'out.png'


def test(in_filename):
    try:
        card = read_card(in_filename)
        face_body_params = parse_face_body_params(card)
        dump_face_body_params(card, face_body_params)
        last_name, first_name, nickname = parse_name(card)
        dump_name(card, last_name, first_name, nickname)
        write_card(out_filename, card)
        with open(in_filename, 'rb') as f:
            card_data_in = f.read()
        with open(out_filename, 'rb') as f:
            card_data_out = f.read()
        # card_data_in may have additional data at the end, such as eof and bepis
        assert card_data_in.startswith(card_data_out)
    except KeyboardInterrupt:
        exit()
    except Exception as e:
        print('Error', e)


if __name__ == '__main__':
    for root, dirs, files in os.walk(in_dir):
        for file in sorted(files):
            in_filename = os.path.join(root, file)
            print(in_filename)
            test(in_filename)
