import uuid
from django.utils.deprecation import MiddlewareMixin

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