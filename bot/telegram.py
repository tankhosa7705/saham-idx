import requests


def send_message(token: str, chat_id: str, text: str) -> bool:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    try:
        r = requests.post(url, json={
            'chat_id': chat_id,
            'text': text,
            'parse_mode': 'HTML',
        }, timeout=10)
        return r.status_code == 200
    except Exception as e:
        print(f"[Telegram] Error: {e}")
        return False


def get_updates(token: str) -> list:
    url = f"https://api.telegram.org/bot{token}/getUpdates"
    try:
        r = requests.get(url, timeout=10)
        return r.json().get('result', [])
    except Exception:
        return []
