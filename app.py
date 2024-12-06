from fastapi import FastAPI, HTTPException, Request
import requests
import time

app = FastAPI()

# Configurações
MERCADO_PAGO_TOKEN = "seu_token_mercado_pago"  # Token do Mercado Pago
MIKROTIK_API_URL = "http://seu_mikrotik_api"  # Endereço do Mikrotik API
MIKROTIK_USER = "admin"
MIKROTIK_PASSWORD = "senha"

def generate_pix_payment(plan, amount):
    """Gera um QR Code PIX no Mercado Pago"""
    url = "https://api.mercadopago.com/v1/payments"
    headers = {"Authorization": f"Bearer {MERCADO_PAGO_TOKEN}"}
    data = {
        "transaction_amount": amount,
        "description": f"Pagamento WiFi - Plano {plan}",
        "payment_method_id": "pix",
        "payer": {"email": "cliente@example.com"}  # Opcional
    }
    response = requests.post(url, json=data, headers=headers)
    if response.status_code != 201:
        raise HTTPException(status_code=500, detail="Erro ao criar pagamento PIX")
    return response.json()

@app.get("/generate_qr")
async def generate_qr(plan: str):
    """Endpoint para gerar QR Code baseado no plano"""
    plans = {"1hora": 2.00, "5horas": 8.00, "10horas": 10.00}
    if plan not in plans:
        raise HTTPException(status_code=400, detail="Plano inválido")
    payment = generate_pix_payment(plan, plans[plan])
    return {
        "qr_code_url": payment["point_of_interaction"]["transaction_data"]["qr_code_base64"],
        "payment_id": payment["id"]
    }

@app.post("/webhook")
async def webhook(request: Request):
    """Recebe notificações de pagamento do Mercado Pago"""
    body = await request.json()
    if body.get("type") == "payment" and body.get("data", {}).get("status") == "approved":
        # Extrair informações relevantes
        plan = body["data"]["description"].split()[-1]
        mac = body["data"]["metadata"]["mac_address"]  # Enviado do cliente
        time_limit = {"1hora": "1h", "5horas": "5h", "10horas": "10h"}[plan]

        # Adicionar usuário ao Mikrotik
        add_user_to_mikrotik(mac, time_limit)
    return {"status": "ok"}

def add_user_to_mikrotik(mac, time_limit):
    """Adiciona o cliente ao Mikrotik para liberar acesso"""
    payload = {
        "command": f"/ip/hotspot/active/add",
        "mac": mac,
        "time": time_limit
    }
    response = requests.post(
        MIKROTIK_API_URL,
        json=payload,
        auth=(MIKROTIK_USER, MIKROTIK_PASSWORD)
    )
    if response.status_code != 200:
        raise Exception("Erro ao adicionar usuário ao Mikrotik")

# Inicializar o servidor: uvicorn main:app --reload
