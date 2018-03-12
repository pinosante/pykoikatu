import os
from pykoikatu import *

in_folder = 'test'


def get_body(filename):
    img1, img2, chara_data = read_card(filename)
    tokens = parse_tokens(chara_data)
    token_idx_seg = read_token_idx_seg(tokens)
    body = read_tokens(tokens, token_idx_seg, token_dspl_body)
    return body


if __name__ == '__main__':
    body_data = []
    for root, dirs, files in os.walk(in_folder):
        for file in sorted(files):
            in_filename = os.path.join(root, file)
            print(in_filename)
            body_data.append(get_body(in_filename))

    body_data = np.array(body_data, dtype=float)
    body_data = body_data.T
    body_mean = np.mean(body_data, axis=1)
    body_cov = np.cov(body_data)

    with h5py.File('data/body.hdf5', 'w') as g:
        g.create_dataset('mean', data=body_mean)
        g.create_dataset('cov', data=body_cov)
