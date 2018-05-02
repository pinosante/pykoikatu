# Generate a random character

from pykoikatu import *

in_filename = 'in.png'
out_filename = 'out_{}.png'

if __name__ == '__main__':
    card = read_card(in_filename)

    face_body_mean, face_body_cov = read_face_body_data()
    face_body_params = generate_face_body_params(face_body_mean, face_body_cov)
    dump_face_body_params(card, face_body_params)

    last_name_list, male_name_list, female_name_list = read_name_data()
    last_name, first_name, nickname = generate_name(
        last_name_list, male_name_list, female_name_list)
    dump_name(card, last_name, first_name, nickname)


    card['img1'], card['img2'] = generate_img12(last_name[0])

    write_card(out_filename.format(last_name + first_name), card)
