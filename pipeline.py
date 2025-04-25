from load import read_pkl, write_pkl, convert_to_json
import os


def pipeline_img(img_path):
    from extract import img_to_dataframes_paddle
    df = img_to_dataframes_paddle(img_path)
    write_pkl(df, 'temp/e_paddle_img.pkl')

    from transform import transform_pipeline_img, fuzzy_match_column
    df = read_pkl('temp/e_paddle_img.pkl')
    df = transform_pipeline_img(df)
    write_pkl(df, 'temp/t_paddle_img.pkl')

    df = read_pkl('temp/t_paddle_img.pkl')
    matched_df = fuzzy_match_column(df['品名'], threshold=80)
    convert_to_json({}, df, matched_df, f"./output/{os.path.basename(img_path).split('.')[0]}.json")
    print(matched_df)


def pipeline_pdf(pdf_path):
    from extract import pdf_to_dataframes_paddle
    orderinfo, df = pdf_to_dataframes_paddle(pdf_path)
    write_pkl(df, 'temp/e_paddle_pdf.pkl')

    from transform import transform_pipeline_pdf, fuzzy_match_column, fuzzy_match_ordermeta
    orderinfo = fuzzy_match_ordermeta(orderinfo)
    df = read_pkl('temp/e_paddle_pdf.pkl')
    df = transform_pipeline_pdf(df)
    write_pkl(df, 'temp/t_paddle_pdf.pkl')

    df = read_pkl('temp/t_paddle_pdf.pkl')
    matched_df = fuzzy_match_column(df['品名'], threshold=80)
    convert_to_json(orderinfo, df, matched_df, f"./output/{os.path.basename(pdf_path).split('.')[0]}.json")
    print(matched_df)


if __name__ == '__main__':
    pipeline_img('inputs/p1.png')
