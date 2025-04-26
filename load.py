import pickle


def read_pkl(filename):
    with open(filename, 'rb') as f:
        dfs = pickle.load(f)
    return dfs


def write_pkl(dfs, filename):
    with open(filename, 'wb') as f:
        pickle.dump(dfs, f)
        print("已缓存到：", filename)


def convert_to_json(ordermeta, df, matched_df):
    """
    参数说明:
    customer_name:  str, 客户名
    order_date:     str, 订单时间，格式如 '2025-03-25'
    items_df:       pd.DataFrame, 必须含有 product_id, matched_name, original_input, quantity, match_score (0~1)
    status:         str, 订单状态
    filepath:       str, 保存文件路径
    """
    # 转 list[dict]，且 json 能正确序列化 float
    total_price = df["price"].astype(float).sum()
    json_dict = {
        "prices": float(total_price),
        "items": [],
    }
    json_dict.update(ordermeta)
    # 组合items
    # 若数量与matched_df顺序与df一致，可以直接zip，否则用索引对齐
    for idx, row in matched_df.iterrows():
        item = {
            "product_id": row["product_id"],
            "matched_name": row["matched_name"],
            "original_input": row["original_input"],
            "quantity": float(df.loc[idx, "quantity"]),
            "match_score": row["match_score"]
        }
        json_dict["items"].append(item)

    return json_dict
