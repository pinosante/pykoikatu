import os
from pykoikatu import *

in_folder = 'test'
out_filename = 'out.png'


def test(in_filename):
    try:
        img1, img2, chara_data = read_card(in_filename)
        tokens = parse_tokens(chara_data)
        token_idx_seg = read_token_idx_seg(tokens)
        body = read_tokens(tokens, token_idx_seg, token_dspl_body)
        name = read_tokens(tokens, token_idx_seg, token_dspl_name)
        write_tokens(tokens, token_idx_seg, token_dspl_body, body)
        write_tokens(tokens, token_idx_seg, token_dspl_name, name)
        chara_data = commit_tokens(tokens)
        write_card(out_filename, img1, img2, chara_data)
        with open(in_filename, 'rb') as f:
            card_data_in = f.read()
        with open(out_filename, 'rb') as f:
            card_data_out = f.read()
        # card_data_in and card_data_out may differ in eof bytes
        assert (card_data_in.startswith(card_data_out)
                and len(card_data_in) - len(card_data_out) < 8)
    except:
        print('Error', in_filename)


if __name__ == '__main__':
    for root, dirs, files in os.walk(in_folder):
        for file in sorted(files):
            in_filename = os.path.join(root, file)
            print(in_filename)
            test(in_filename)
