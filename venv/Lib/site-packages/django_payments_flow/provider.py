from dataclasses import asdict
from typing import Any, Optional

from django.http import HttpResponseBadRequest, JsonResponse
from payments import PaymentError, PaymentStatus, RedirectNeeded
from payments.core import BasicProvider, get_base_url
from payments.forms import PaymentForm as BasePaymentForm
from pyflowcl import Payment as FlowPayment
from pyflowcl import Refund as FlowRefund
from pyflowcl.Clients import ApiClient


class FlowProvider(BasicProvider):
    """
    FlowProvider es una clase que proporciona integración con Flow para procesar pagos.
    Inicializa una instancia de FlowProvider con el key y el secreto de Flow.

    Args:
        api_key (str): ApiKey entregada por Flow.
        api_secret (str): ApiSecret entregada por Flow.
        api_medio (int | None): Versión de la API de notificaciones a utilizar (Valor por defecto: 9).
        api_endpoint (str): Ambiente flow, puede ser "live" o "sandbox" (Valor por defecto: live).
        **kwargs: Argumentos adicionales.
    """

    form_class = BasePaymentForm
    api_endpoint: str
    api_key: str = None
    api_secret: str = None
    api_medio: int
    _client: Any = None

    def __init__(
        self,
        api_endpoint: str,
        api_key: str,
        api_secret: str,
        api_medio: int = 9,
        **kwargs: int,
    ):
        super().__init__(**kwargs)
        self.api_endpoint = api_endpoint
        self.api_key = api_key
        self.api_secret = api_secret
        self.api_medio = api_medio
        if self.api_endpoint == "live":
            self.api_endpoint = "https://www.flow.cl/api"
        elif self.api_endpoint == "sandbox":
            self.api_endpoint = "https://sandbox.flow.cl/api"
        self._client = ApiClient(self.api_endpoint, self.api_key, self.api_secret)

    def get_form(self, payment, data: Optional[dict] = None) -> Any:
        """
        Genera el formulario de pago para redirigir a la página de pago de Flow.

        Args:
            payment ("Payment"): Objeto de pago Django Payments.
            data (dict | None): Datos del formulario (opcional).

        Returns:
            Any: Formulario de pago redirigido a la página de pago de Flow.

        Raises:
            RedirectNeeded: Redirige a la página de pago de Flow.

        """
        if not payment.transaction_id:
            datos_para_flow = {
                "apiKey": self.api_key,
                "commerceOrder": payment.token,
                "urlReturn": payment.get_success_url(),
                "urlConfirmation": f"{get_base_url()}{payment.get_process_url()}",
                "subject": payment.description,
                "amount": int(payment.total),
                "paymentMethod": self.api_medio,
                "currency": payment.currency,
            }

            if payment.billing_email:
                datos_para_flow.update({"email": payment.billing_email})

            datos_para_flow.update(**self._extra_data(payment.attrs))

            try:
                payment.attrs.datos_payment_create_flow = datos_para_flow
                payment.save()
            except Exception as e:
                raise PaymentError(f"Ocurrió un error al guardar attrs.datos_flow: {e}")

            try:
                pago = FlowPayment.create(self._client, datos_para_flow)

            except Exception as pe:
                payment.change_status(PaymentStatus.ERROR, str(pe))
                raise PaymentError(pe)
            else:
                payment.transaction_id = pago.token
                payment.attrs.respuesta_flow = {
                    "url": pago.url,
                    "token": pago.token,
                    "flowOrder": pago.flowOrder,
                }
                payment.save()
                payment.change_status(PaymentStatus.WAITING)

            raise RedirectNeeded(f"{pago.url}?token={pago.token}")

    def process_data(self, payment, request) -> JsonResponse:
        """
        Procesa los datos del pago recibidos desde Flow.

        Args:
            payment ("Payment"): Objeto de pago Django Payments.
            request ("HttpRequest"): Objeto de solicitud HTTP de Django.

        Returns:
            JsonResponse: Respuesta JSON que indica el procesamiento de los datos del pago.

        """
        if "token" not in request.POST:
            raise HttpResponseBadRequest("token no está en post")

        data = {"status": "ok"}
        if payment.status in [PaymentStatus.WAITING, PaymentStatus.PREAUTH]:
            self.actualiza_estado(payment=payment)

        return JsonResponse(data)

    def actualiza_estado(self, payment) -> dict:
        """Actualiza el estado del pago con Flow

        Args:
            payment ("Payment): Objeto de pago Django Payments.

        Returns:
            dict: Diccionario con valores del objeto `PaymentStatus`.
        """
        try:
            status = FlowPayment.getStatus(self._client, payment.transaction_id)
        except Exception as e:
            raise e
        else:
            if status.status == 2:
                payment.change_status(PaymentStatus.CONFIRMED)
            elif status.status == 3:
                payment.change_status(PaymentStatus.REJECTED)
            elif status.status == 4:
                payment.change_status(PaymentStatus.ERROR)
        return asdict(status)

    def _extra_data(self, attrs) -> dict:
        """Busca los datos que son enviandos por django-payments y los saca del diccionario

        Args:
            attrs ("PaymentAttributeProxy"): Obtenido desde PaymentModel.extra_data

        Returns:
            dict: Diccionario con valores permitidos.
        """
        try:
            data = attrs.datos_extra
        except AttributeError:
            return {}

        prohibidos = [
            "commerceOrder",
            "urlReturn",
            "urlConfirmation",
            "amount",
            "subject",
            "paymentMethod",
            "currency",
        ]
        for valor in prohibidos:
            if valor in data:
                del data[valor]

        return data

    def refund(self, payment, amount: Optional[int] = None) -> int:
        """
        Realiza un reembolso del pago.
        El seguimiendo se debe hacer directamente en Flow

        Args:
            payment ("Payment"): Objeto de pago Django Payments.
            amount (int | None): Monto a reembolsar (opcional).

        Returns:
            int: Monto de reembolso solicitado.

        Raises:
            PaymentError: Error al crear el reembolso.

        """
        if payment.status != PaymentStatus.CONFIRMED:
            raise PaymentError("El pago debe estar confirmado para reversarse.")

        to_refund = amount or payment.total
        try:
            datos_reembolso = {
                "apiKey": self.api_key,
                "refundCommerceOrder": payment.token,
                "receiverEmail": payment.billing_email,
                "amount": to_refund,
                "urlCallBack": f"{get_base_url()}{payment.get_process_url()}",
                "commerceTrxId": payment.token,
                "flowTrxId": payment.attrs.respuesta_flow["flowOrder"],
            }
            refund = FlowRefund.create(self._client, datos_reembolso)
        except Exception as pe:
            raise PaymentError(pe)
        else:
            payment.attrs.solicitud_reembolso = refund
            payment.save()
            payment.change_status(PaymentStatus.REFUNDED)
            return to_refund

    def capture(self):
        """
        Captura el pago (no implementado).

        Note:
            Método no soportado por Flow.
        Raises:
            NotImplementedError: Método no implementado.
        """
        raise NotImplementedError()

    def release(self):
        """
        Libera el pago (no implementado).

        Note:
            Método no soportado por Flow.

        Raises:
            NotImplementedError: Método no implementado.

        """
        raise NotImplementedError()
