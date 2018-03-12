from pykoikatu import *

if __name__ == '__main__':
    in_filename = 'in.png'
    out_filename = 'out.png'

    img1, img2, chara_data = read_card(in_filename)
    # with open('in_img1.png', 'wb') as g:
    #     g.write(img1)
    # with open('in_img2.png', 'wb') as g:
    #     g.write(img2)

    tokens = parse_tokens(chara_data)
    # with codecs.open('in_tokens.txt', 'w', 'utf-8') as g:
    #     for token in tokens:
    #         g.write(str(token) + '\n')

    token_idx_seg = read_token_idx_seg(tokens)
    # for seg_idx, token_idx in enumerate(token_idx_seg):
    #     print(seg_idx, token_idx)

    # str_set = {x for x in tokens if isinstance(x, str)}
    # print(sorted(str_set))

    body = read_tokens(tokens, token_idx_seg, token_dspl_body)
    name = read_tokens(tokens, token_idx_seg, token_dspl_name)
    print(name)

    # body_mean, body_cov = read_body_data()
    # body = generate_random_body(body_mean, body_cov)

    # last_name_list, male_name_list, female_name_list = read_name_data()
    # name = generate_random_name(last_name_list, male_name_list,
    #                             female_name_list)
    # print(name)

    write_tokens(tokens, token_idx_seg, token_dspl_body, body)
    write_tokens(tokens, token_idx_seg, token_dspl_name, name)

    chara_data = commit_tokens(tokens)

    # img1, img2 = generate_random_img()

    write_card(out_filename, img1, img2, chara_data)

    with open(in_filename, 'rb') as f:
        card_data_in = f.read()
    with open(out_filename, 'rb') as f:
        card_data_out = f.read()
    # card_data_in and card_data_out may differ in eof bytes
    assert (card_data_in.startswith(card_data_out)
            and len(card_data_in) - len(card_data_out) < 8)
