# Test read + write is identity

from pykoikatu import *

in_filename = 'in2.png'
out_filename = 'out.png'

if __name__ == '__main__':
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
