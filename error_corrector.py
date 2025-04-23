
def pycorrect_spell_correct():
    from opencc import OpenCC
    import pycorrector
    corr = pycorrector.Corrector()

    # 1. 繁体转简体
    text_trad = '這是一個繁體錯誤的範例，粽子好吃。'
    cc = OpenCC('t2s')
    text_simp = cc.convert(text_trad)

    # 2. 简体纠错
    cor, details = corr.correct(text_simp)

    # 3. 可选：再转回繁体
    text_trad_fix = OpenCC('s2t').convert(cor)
    print('纠错前：', text_trad)
    print('简体：', text_simp)
    print('纠错后（简体）：', cor)
    print('纠错后（转回繁体）：', text_trad_fix)
    print('修正详情：', details)


def ollama_spell_correct(text, model='gemma3:27b'):
    import requests
    api_url = "http://localhost:11434/api/generate"
    body = {
        "model": model,
        "prompt": f"你是一名文本校对专家。请找出并纠正输入中的错别字，返回纠正后的文本。输出内容仅为纠正后的文本：\n{text}",
        "stream": False
    }
    response = requests.post(api_url, json=body)
    corrected = response.json()['response']
    return corrected.strip()


ollama_spell_correct('  - 提供 n8n JSON 設定檔或匯出流程挡案。')
# tra_to_sim()
