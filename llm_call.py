import requests


def gemma3(prompt, model='gemma3:27b'):
    print(prompt)
    api_url = "http://localhost:11434/api/generate"
    body = {
        "model": model,
        "prompt": prompt,
        "stream": False
    }
    response = requests.post(api_url, json=body)
    corrected = response.json()['response']
    return corrected.strip()
