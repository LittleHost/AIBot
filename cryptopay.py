# cryptopay.py
import aiohttp
from config import CRYPTO_PAY_TOKEN, CRYPTO_BASE_URL


async def cb_create_invoice(amount: float, user_id: int):
    if not CRYPTO_PAY_TOKEN or amount < 0.05:
        return None
    url = f"{CRYPTO_BASE_URL}/createInvoice"
    headers = {"Crypto-Pay-API-Token": CRYPTO_PAY_TOKEN}
    payload = {"asset": "USDT", "amount": f"{amount:.2f}", "description": f"Пополнение #{user_id}", "payload": str(user_id)}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers, timeout=10) as resp:
                data = await resp.json()
                if data.get("ok"):
                    return data.get("result")
                print(f"CryptoBot createInvoice error: {data}")
                return None
    except Exception as e:
        print(f"CryptoBot createInvoice exception: {e}")
        return None


async def cb_check_stat(invoice_id: int):
    if not CRYPTO_PAY_TOKEN:
        return None
    url = f"{CRYPTO_BASE_URL}/getInvoices"
    headers = {"Crypto-Pay-API-Token": CRYPTO_PAY_TOKEN}
    params = {"invoice_ids": str(invoice_id)}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, headers=headers, timeout=10) as resp:
                data = await resp.json()
                if data.get("ok") and data["result"]["items"]:
                    return data["result"]["items"][0]["status"]
                return None
    except Exception as e:
        print(f"CryptoBot checkInvoice exception: {e}")
        return None


async def cb_create_check(amount: float):
    if not CRYPTO_PAY_TOKEN:
        return None
    if amount < 0.10:
        return None
    url = f"{CRYPTO_BASE_URL}/createCheck"
    headers = {"Crypto-Pay-API-Token": CRYPTO_PAY_TOKEN}
    payload = {"asset": "USDT", "amount": f"{amount:.2f}"}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers, timeout=15) as resp:
                data = await resp.json()
                if data.get("ok"):
                    result = data.get("result")
                    if result and result.get("bot_check_url"):
                        return result
                return None
    except Exception as e:
        print(f"CryptoBot createCheck exception: {e}")
        return None
