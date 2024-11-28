import uuid
from django.utils.deprecation import MiddlewareMixin
from django.middleware.csrf import CsrfViewMiddleware
import logging

logger = logging.getLogger(__name__)

class VisitorMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # Intentar obtener el visitor_id de la cookie
        visitor_id = request.COOKIES.get('visitor_id')
        
        if not visitor_id:
            # Si no existe, crear uno nuevo
            visitor_id = str(uuid.uuid4())
            # Lo guardamos en el request para usarlo en la respuesta
            request.visitor_id_new = visitor_id
        
        # Guardar el visitor_id en el request para uso en las vistas
        request.visitor_id = visitor_id

    def process_response(self, request, response):
        # Si hay un nuevo visitor_id, establecerlo como cookie
        if hasattr(request, 'visitor_id_new'):
            # Cookie que dura 1 año
            response.set_cookie('visitor_id', request.visitor_id_new, 
                              max_age=365*24*60*60, 
                              httponly=True, 
                              samesite='Lax')
        return response

class FlowCsrfMiddleware(CsrfViewMiddleware):
    def process_view(self, request, callback, callback_args, callback_kwargs):
        try:
            # Verificar si es una solicitud de Flow
            if request.path == '/checkout/payment-success/' and request.method == 'POST':
                logger.info("="*50)
                logger.info("FLOW CSRF MIDDLEWARE")
                logger.info(f"Path: {request.path}")
                logger.info(f"Method: {request.method}")
                logger.info(f"Headers: {dict(request.headers)}")
                
                # Permitir solicitudes con Origin: null (común en redirects de Flow)
                if request.headers.get('Origin') == 'null':
                    logger.info("Permitiendo solicitud con Origin: null")
                    return None
                
                # Verificar si hay token de Flow
                flow_token = request.POST.get('token')
                if flow_token:
                    logger.info(f"Flow token encontrado: {flow_token}")
                    return None
                
                logger.warning("No se encontró token de Flow")
            
            # Para otras solicitudes, usar el comportamiento normal de CSRF
            return super().process_view(request, callback, callback_args, callback_kwargs)
            
        except Exception as e:
            logger.error(f"Error en FlowCsrfMiddleware: {str(e)}")
            # En caso de error, mantener la protección CSRF
            return super().process_view(request, callback, callback_args, callback_kwargs)

    def process_response(self, request, response):
        """Procesar la respuesta para permitir Origin: null"""
        if request.path == '/checkout/payment-success/':
            return response
        return super().process_response(request, response)