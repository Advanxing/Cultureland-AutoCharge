import httpx
import logging
from mTransKey.transkey import mTransKey
from colorama import init, Fore, Style
from datetime import datetime
from flask import Flask, request
from json import load
from random import randrange
from time import time
from urllib import parse

accounts = {}
with open("./accounts.json", "r") as f:
    accounts = load(f)

logging.getLogger("werkzeug").disabled = True

init()

app = Flask(__name__)

@app.route("/api/charge", methods=["POST"])
def charge():
    current_date = datetime.now().strftime("%B %d, %Y %H:%M:%S")
    current_time = time()
    req_data = request.get_json()
    id = req_data.get("id")
    pw = req_data.get("pw")
    account = accounts.get(id)

    if not account or account.get("pw") != pw:
        print(f"{Fore.RED}{Style.BRIGHT}[UNKNOWN] {id}:{pw} | {current_date}{Style.RESET_ALL}")
        return {"result": False, "amount": 0, "reason": "아이디 등록 필요", "timeout": round((time() - current_time) * 1000), "fake": False}

    pin = req_data.get("pin").split("-")
    if len(pin) == 4 and len(pin[0]) == 4 and len(pin[1]) == 4 and len(pin[2]) == 4 and pin[0].isdigit() and pin[1].isdigit() and pin[2].isdigit() and pin[3].isdigit() and ((pin[0][:2] in ["20", "21", "22", "30", "31", "32", "40", "51", "52"] and len(pin[3]) == 6) or (pin[0][:2] == "41" and pin[0][2:3] not in ["6", "8"] and len(pin[3]) == 6) or (pin[0][:3] in ["416", "418", "916"] and len(pin[3]) == 4)):
        with httpx.Client() as client:
            #mtk = mTransKey(client, "https://m.cultureland.co.kr/transkeyServlet")
            #pw_encrypt = mtk.new_keypad("qwerty", "passwd", "passwd", "password").encrypt_password(pw)

            #login_result = client.post("https://m.cultureland.co.kr/mmb/loginProcess.do", data={"userId": req_data.get("id"), "transkeyUuid": mtk.get_uuid(), "transkey_passwd": pw_encrypt, "transkey_HM_passwd": mtk.hmac_digest(pw_encrypt.encode())})

            keepLoginInfo = account.get("keepLoginInfo")
            client.cookies.set("KeepLoginConfig", parse.quote(keepLoginInfo))
            login_result = client.post("https://m.cultureland.co.kr/mmb/loginProcess.do", data={"keepLoginInfo": keepLoginInfo})

            if "frmRedirect" in login_result.text:
                print(f"{Fore.RED}{Style.BRIGHT}[LOGIN FAILED] {id} | {current_date}{Style.RESET_ALL}")
                return {"result": False, "amount": 0, "reason": "아이디 또는 비밀번호 불일치", "timeout": round((time() - current_time) * 1000), "fake": False}

            client.get("https://m.cultureland.co.kr/csh/cshGiftCard.do")

            mtk = mTransKey(client, "https://m.cultureland.co.kr/transkeyServlet")
            pin_encrypt = mtk.new_keypad("number", "txtScr14", "scr14", "password").encrypt_password(pin[3])

            client.post("https://m.cultureland.co.kr/csh/cshGiftCardProcess.do", data={"scr11": pin[0], "scr12": pin[1], "scr13": pin[2], "transkeyUuid": mtk.get_uuid(), "transkey_txtScr14": pin_encrypt, "transkey_HM_txtScr14": mtk.hmac_digest(pin_encrypt.encode())})
            charge_result = client.get("https://m.cultureland.co.kr/csh/cshGiftCardCfrm.do")

            charge_amount = charge_result.text.split('walletChargeAmt" value="')[1].split("\n\n\n")[0]
            wallet_charge_amount = int(charge_amount.split('"')[0])
            charge_amount = wallet_charge_amount + int(charge_amount.split('value="')[1].split('"')[0])

            charge_result = charge_result.text.split("<b>")[1].split("</b>")[0]
            if wallet_charge_amount:
                charge_result = charge_result.split(">")[1].split("<")[0]

            charge_time = round((time() - current_time) * 1000)
            if bool(charge_amount):
                print(f"{Fore.GREEN}{Style.BRIGHT}[SUCCESS] {id} | {'-'.join(pin)} | {charge_amount}원 | {charge_result} | {charge_time}ms | {current_date}{Style.RESET_ALL}")
            else:
                print(f"{Fore.CYAN}{Style.BRIGHT}[FAILED] {id} | {'-'.join(pin)} | {charge_amount}원 | {charge_result} | {charge_time}ms | {current_date}{Style.RESET_ALL}")
            return {"result": bool(charge_amount), "amount": charge_amount, "reason": charge_result, "timeout": charge_time, "fake": False}
    else:
        print(f"{Fore.CYAN}{Style.BRIGHT}[FAKE] {id} | {'-'.join(pin)} | {current_date}{Style.RESET_ALL}")
        return {"result": False, "amount": 0, "reason": "상품권 번호 불일치", "timeout": randrange(400, 500), "fake": True}

app.run(host="0.0.0.0", port=9999)
