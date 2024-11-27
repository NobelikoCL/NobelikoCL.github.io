import hmac
import hashlib
import requests
from typing import Dict
from django.conf import settings
from ..models import FlowCredentials, Order

class FlowPaymentService:
    def __init__(self):
        self.credentials = FlowCredentials.objects.filter(is_active=True).first()
        if not self.credentials:
            raise ValueError("No hay credenciales de Flow configuradas")
        
        self.api_key = self.credentials.api_key
        self.secret_key = self.credentials.secret_key
        self.api_url = "https://sandbox.flow.cl/api" if self.credentials.is_sandbox else "https://www.flow.cl/api"

    def create_signature(self, data: Dict) -> str:
        sorted_params = dict(sorted(data.items()))
        to_sign = ''.join(f"{k}{v}" for k, v in sorted_params.items())
        
        signature = hmac.new(
            self.secret_key.encode(),
            to_sign.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return signature

    def create_payment(self, order: Order) -> Dict:
        payment_data = {
            "commerceOrder": order.flow_order_id,
            "subject": f"Orden #{order.flow_order_id}",
            "currency": "CLP",
            "amount": order.total_amount,
            "email": order.customer_email,
            "urlConfirmation": f"{settings.SITE_URL}/api/payments/confirmation/",
            "urlReturn": f"{settings.SITE_URL}/payments/return/"
        }
        
        signature = self.create_signature(payment_data)
        payment_data.update({
            "apiKey": self.api_key,
            "s": signature
        })
        
        response = requests.post(
            f"{self.api_url}/payment/create",
            data=payment_data
        )
        
        return response.json()

    def verify_payment(self, token: str) -> Dict:
        payment_data = {
            "apiKey": self.api_key,
            "token": token
        }
        
        signature = self.create_signature(payment_data)
        payment_data["s"] = signature
        
        response = requests.post(
            f"{self.api_url}/payment/getStatus",
            data=payment_data
        )
        
        return response.json()