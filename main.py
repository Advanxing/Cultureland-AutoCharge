import httpx
from mTransKey.transkey import mTransKey
from flask import Flask, request
from random import randrange
from time import time

app = Flask(__name__)


@app.route("/api/charge", methods=["POST"])
def charge():
    current_time = time()
    req_data = request.get_json()
    pin = req_data.get("pin").split("-")
    if len(pin) == 4 and len(pin[0]) == 4 and len(pin[1]) == 4 and len(pin[2]) == 4 and pin[0].isdigit() and pin[1].isdigit() and pin[2].isdigit() and pin[3].isdigit() and ((pin[0][:2] in ["20", "21", "22", "30", "31", "32", "40", "51", "52"] and len(pin[3]) == 6) or (pin[0][:2] == "41" and pin[0][2:3] not in ["6", "8"] and len(pin[3]) == 6) or (pin[0][:3] in ["416", "418", "916"] and len(pin[3]) == 4)):
        with httpx.Client() as client:
            mtk = mTransKey(client, "https://m.cultureland.co.kr/transkeyServlet")
            pw_encrypt = mtk.new_keypad("qwerty", "passwd", "passwd", "password").encrypt_password(req_data.get("pw"))

            login_result = client.post("https://m.cultureland.co.kr/mmb/loginProcess.do", data={"userId": req_data.get("id"), "transkeyUuid": mtk.get_uuid(), "transkey_passwd": pw_encrypt, "transkey_HM_passwd": mtk.hmac_digest(pw_encrypt.encode())})

            if "frmRedirect" in login_result.text:
                return {"result": False, "amount": 0, "reason": "아이디 또는 비밀번호 불일치", "timeout": round((time() - current_time) * 1000)}

            client.cookies.set("appInfoConfig", '"cookieClientType=IPHONE&cookieKeepLoginYN=F"')
            client.get("https://m.cultureland.co.kr/csh/cshGiftCard.do")
            client.post("https://m.cultureland.co.kr/csh/cshGiftCardProcess.do", data={"scr11": pin[0], "scr12": pin[1], "scr13": pin[2], "scr14": pin[3]})
            charge_result = client.get("https://m.cultureland.co.kr/csh/cshGiftCardCfrm.do")

            charge_amount = charge_result.text.split('walletChargeAmt" value="')[1].split("\n\n\n")[0]
            wallet_charge_amount = int(charge_amount.split('"')[0])
            charge_amount = wallet_charge_amount + int(charge_amount.split('value="')[1].split('"')[0])

            charge_result = charge_result.text.split("<b>")[1].split("</b>")[0]
            if wallet_charge_amount:
                charge_result = charge_result.split(">")[1].split("<")[0]

            return {"result": bool(charge_amount), "amount": charge_amount, "reason": charge_result, "timeout": round((time() - current_time) * 1000), "fake": False}
    else:
        return {"result": False, "amount": 0, "reason": "상품권 번호 불일치", "timeout": randrange(400, 600), "fake": True}


app.run(host="0.0.0.0", port=80)
