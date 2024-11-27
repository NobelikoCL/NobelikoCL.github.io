import hmac
import hashlib
import json
import requests
from typing import Dict, Optional
from django.conf import settings
from decimal import Decimal

class FlowPaymentService:
    def __init__(self):
        self.api_key = settings.FLOW_API_KEY
        self.secret_key = settings.FLOW_SECRET_KEY
        self.api_url = settings.FLOW_API_URL

    def create_payment(self, order) -> Optional[str]:
        try:
            # Datos mínimos requeridos según documentación Flow
            payment_data = {
                "apiKey": self.api_key,
                "commerceOrder": str(order.order_number),
                "subject": f"Pago Orden {order.order_number}",
                "currency": "CLP",
                "amount": int(order.total_amount),
                "email": order.customer_email,
                "urlConfirmation": settings.FLOW_CONFIRM_URL,
                "urlReturn": settings.FLOW_RETURN_URL
            }

            print("Datos de pago:", json.dumps(payment_data, indent=2))

            # Ordenar parámetros alfabéticamente para firma
            params = sorted(payment_data.items())
            
            # Concatenar para firma
            to_sign = "".join(f"{k}{v}" for k, v in params)
            print(f"String para firma: {to_sign}")
            
            # Generar firma
            signature = hmac.new(
                self.secret_key.encode(),
                to_sign.encode(),
                hashlib.sha256
            ).hexdigest()

            # Agregar firma a los datos
            payment_data["s"] = signature

            # Realizar petición a Flow
            response = requests.post(
                f"{self.api_url}/payment/create",
                data=payment_data,
                headers={
                    'Content-Type': 'application/x-www-form-urlencoded',
                    'Accept': 'application/json'
                }
            )

            print(f"Status Code: {response.status_code}")
            print(f"Respuesta de Flow: {response.text}")

            if response.status_code == 200:
                data = response.json()
                if 'url' in data and 'token' in data:
                    # Guardar token en la orden
                    order.flow_token = data['token']
                    order.save()
                    return f"{data['url']}?token={data['token']}"

            print(f"Error en respuesta de Flow: {response.status_code} - {response.text}")
            return None

        except Exception as e:
            print(f"Error al crear pago en Flow: {str(e)}")
            return None