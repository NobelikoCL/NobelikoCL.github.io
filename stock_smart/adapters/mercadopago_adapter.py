import mercadopago
import logging
from django.conf import settings
from django.urls import reverse
from urllib.parse import urljoin
from ..models import OrderItem

logger = logging.getLogger(__name__)

class MercadoPagoAdapter:
    def __init__(self):
        logger.info("="*50)
        logger.info("Inicializando MercadoPago SDK")
        try:
            self.sdk = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)
            logger.info("SDK inicializado correctamente")
        except Exception as e:
            logger.error(f"Error al inicializar SDK: {str(e)}")
            raise

    def create_preference(self, order):
        try:
            logger.info("="*50)
            logger.info(f"Creando preferencia para orden: {order.id}")
            
            # Obtener el item de la orden
            order_item = OrderItem.objects.filter(order=order).first()
            if not order_item:
                logger.error("No se encontraron items en la orden")
                return None

            # Obtener el dominio base desde settings
            base_url = settings.SITE_URL  # Necesitamos agregar esto en settings.py
            
            # Construir URLs completas
            success_url = urljoin(base_url, reverse('payment_success'))
            failure_url = urljoin(base_url, reverse('payment_failure'))
            pending_url = urljoin(base_url, reverse('payment_pending'))
            
            logger.info(f"URL base: {base_url}")
            logger.info(f"URL success: {success_url}")

            # Crear preferencia básica según documentación de MercadoPago Chile
            preference_data = {
                "items": [
                    {
                        "title": order_item.product.name,
                        "quantity": 1,
                        "currency_id": "CLP",
                        "unit_price": float(order_item.price)
                    }
                ],
                "back_urls": {
                    "success": success_url,
                    "failure": failure_url,
                    "pending": pending_url
                },
                "auto_return": "approved",
                "external_reference": str(order.id)
            }
            
            logger.info("Datos de preferencia a enviar:")
            logger.info(preference_data)
            
            # Crear preferencia
            try:
                preference_response = self.sdk.preference().create(preference_data)
                logger.info("Respuesta raw de MercadoPago:")
                logger.info(preference_response)
                
                if preference_response.get('status') == 201:
                    response_data = preference_response.get('response', {})
                    logger.info(f"Preferencia creada exitosamente. ID: {response_data.get('id')}")
                    
                    return {
                        "id": response_data.get("id"),
                        "init_point": response_data.get("init_point"),
                        "sandbox_init_point": response_data.get("sandbox_init_point")
                    }
                else:
                    logger.error("La respuesta de MercadoPago no tiene el formato esperado")
                    logger.error(f"Respuesta completa: {preference_response}")
                    return None
                    
            except Exception as mp_error:
                logger.error(f"Error al crear preferencia en MercadoPago: {str(mp_error)}")
                logger.error(f"Tipo de error: {type(mp_error)}")
                return None

        except Exception as e:
            logger.error(f"Error general en create_preference: {str(e)}")
            logger.error(f"Tipo de error: {type(e)}")
            return None 