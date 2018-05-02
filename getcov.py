# Get mean and covariance of face and body parameters from dataset

import os
from pykoikatu import *

in_dir = 'test_booru'

if __name__ == '__main__':
    face_body_data = []
    for root, dirs, files in os.walk(in_dir):
        for file in sorted(files):
            in_filename = os.path.join(root, file)
            print(in_filename)
            card = read_card(in_filename)
            face_body_params = parse_face_body_params(card)
            face_body_data.append(face_body_params)

    face_body_data = np.array(face_body_data, dtype=float)
    face_body_data = face_body_data.T
    body_mean = np.mean(face_body_data, axis=1)
    body_cov = np.cov(face_body_data)

    with h5py.File('data/face_body.hdf5', 'w') as g:
        g.create_dataset('mean', data=body_mean)
        g.create_dataset('cov', data=body_cov)
