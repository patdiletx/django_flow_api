import os
import requests
import hmac
import hashlib
from collections import OrderedDict
import logging

from django.db import transaction
from django.shortcuts import render
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.views import View
from .models import Order
from django.conf import settings
from django.http import HttpResponse

# Configura el logger para este módulo
logger = logging.getLogger(__name__)


# --- Función Auxiliar para firmar los parámetros ---
def sign_params(params, secret_key):
    """
    Firma los parámetros para la API de Flow usando HMAC-SHA256.
    """
    sorted_params = OrderedDict(sorted(params.items()))
    param_string = "".join([f"{k}{v}" for k, v in sorted_params.items()])
    signature = hmac.new(
        secret_key.encode('utf-8'),
        param_string.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()
    return signature


# --- Vistas del API ---

class CreatePaymentView(APIView):
    """
    Crea una orden en nuestra base de datos y luego genera la petición
    de pago en Flow.
    """
    def post(self, request, *args, **kwargs):
        amount = request.data.get('amount')
        commerce_order = request.data.get('commerceOrder')
        subject = request.data.get('subject')

        if not all([amount, commerce_order, subject]):
            return Response(
                {"error": "Faltan parámetros requeridos: amount, commerceOrder, subject"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            new_order = Order.objects.create(
                commerce_order=commerce_order,
                amount=amount,
                status='PENDING'
            )
        except Exception as e:
            # Aquí podrías querer loguear el error 'e' también
            return Response(
                {"error": f"La orden {commerce_order} ya existe o hubo un error al crearla en la BD."},
                status=status.HTTP_400_BAD_REQUEST
            )

        api_key = os.getenv('FLOW_API_KEY')
        secret_key = os.getenv('FLOW_SECRET_KEY')
        
        # Obtiene la URL base de Flow desde las variables de entorno de Render/EasyPanel
        # El segundo argumento es un valor por defecto si la variable no está seteada (útil para desarrollo local)
        flow_api_base_url = os.getenv('FLOW_API_URL_PROD', 'https://sandbox.flow.cl/api') 
        
        # Construye la URL completa para el endpoint específico de creación de pago
        flow_payment_create_endpoint_url = f"{flow_api_base_url}/payment/create"

        # Obtiene la URL pública base de tu aplicación desde settings.py
        # Esta variable (PUBLIC_URL_BASE) la debes haber configurado en Render/EasyPanel
        public_url_base_from_settings = settings.PUBLIC_URL_BASE

        params = {
            'apiKey': api_key,
            'commerceOrder': str(commerce_order),
            'amount': str(amount),
            'subject': subject,
            'email': "patricio.dilet@gmail.com", # En un caso real, obtendrías esto del request
            'urlConfirmation': f"{public_url_base_from_settings}/api/confirm-payment/",
            'urlReturn': f"{public_url_base_from_settings}/payment/result/{commerce_order}/"
        }
        
        params['s'] = sign_params(params, secret_key)
        
        # =============================================================
        # === INICIO DE CÓDIGO DE DEPURACIÓN ==========================
        # =============================================================
        print("---------------------------------------------------------")
        print("--- INICIANDO DEPURACIÓN DE PETICIÓN A FLOW ---")
        # Imprime la URL que REALMENTE se usará para la petición a Flow
        print(f"URL de Flow (endpoint create): {flow_payment_create_endpoint_url}")
        
        params_para_imprimir = params.copy()
        # No es necesario borrar secret_key de params_para_imprimir porque no está allí,
        # pero es buena práctica si alguna vez la incluyeras temporalmente.
        
        print(f"Parámetros enviados a Flow: {params_para_imprimir}")
        print("--- FIN DE DEPURACIÓN ---")
        print("---------------------------------------------------------")
        # =============================================================
        # === FIN DE CÓDIGO DE DEPURACIÓN ============================
        # =============================================================

        try:
            # Usa la URL COMPLETA del endpoint para la petición
            response = requests.post(flow_payment_create_endpoint_url, data=params)
            response.raise_for_status() # Lanza un error para respuestas 4xx/5xx
            flow_response = response.json()
        except requests.exceptions.RequestException as e:
            new_order.status = 'REJECTED' # Marcar la orden como fallida si no se pudo conectar
            new_order.save()
            # Aquí también es bueno loguear el error 'e'
            return Response({"error": f"Error al conectar con Flow: {e}"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        
        if 'code' in flow_response: # Flow a veces devuelve errores con una estructura {"code": ..., "message": ...}
            new_order.status = 'REJECTED' # Marcar la orden como fallida
            new_order.save()
            return Response(
                {"error": f"Error por parte de Flow: {flow_response.get('message')}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        flow_token = flow_response.get('token')
        if flow_token: # Asegurarse de que el token exista
            new_order.flow_token = flow_token
            new_order.save()
        else:
            # Si Flow no devuelve un token pero tampoco un error con 'code', es una respuesta inesperada.
            new_order.status = 'REJECTED'
            new_order.save()
            logger.error(f"Respuesta inesperada de Flow sin token ni código de error: {flow_response} para orden {commerce_order}")
            return Response(
                {"error": "Respuesta inesperada de Flow al crear el pago."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        payment_redirect_url = f"{flow_response.get('url')}?token={flow_token}"
        
        return Response({
            "redirect_url": payment_redirect_url,
            "token": flow_token
        }, status=status.HTTP_201_CREATED)


@method_decorator(csrf_exempt, name='dispatch')
class FlowConfirmationView(APIView):
    """
    Vista que recibe la confirmación de pago por parte de Flow (Webhook).
    """
    def post(self, request, *args, **kwargs):
        token = request.POST.get('token')
        if not token:
            logger.warning("Recibida confirmación de Flow sin token.")
            return Response(status=status.HTTP_400_BAD_REQUEST)

        try:
            api_key = os.getenv('FLOW_API_KEY')
            secret_key = os.getenv('FLOW_SECRET_KEY')
            flow_status_url = f"https://sandbox.flow.cl/api/payment/getStatus?apiKey={api_key}&token={token}"
            signature = sign_params({'apiKey': api_key, 'token': token}, secret_key)
            flow_status_url += f"&s={signature}"
            
            response = requests.get(flow_status_url)
            response.raise_for_status()
            payment_data = response.json()
            
            commerce_order_id = payment_data.get('commerceOrder')
            flow_status = payment_data.get('status')

            with transaction.atomic():
                try:
                    order_to_update = Order.objects.select_for_update().get(commerce_order=commerce_order_id)
                except Order.DoesNotExist:
                    logger.error(f"Flow confirmó la orden {commerce_order_id}, pero no fue encontrada en la BD.")
                    return Response(status=status.HTTP_200_OK)

                if order_to_update.status != 'PENDING':
                    logger.warning(f"Recibida confirmación para orden {commerce_order_id} que ya fue procesada (Estado: {order_to_update.status}).")
                    return Response(status=status.HTTP_200_OK)

                if flow_status == 2: # Pagada
                    order_to_update.status = 'PAID'
                    logger.info(f"✅ Orden {commerce_order_id} actualizada a PAGADA.")
                elif flow_status == 3: # Rechazada
                    order_to_update.status = 'REJECTED'
                    logger.info(f"❌ Orden {commerce_order_id} actualizada a RECHAZADA.")
                
                order_to_update.save()

        except requests.exceptions.RequestException as e:
            logger.error(f"Error de conexión al consultar estado en Flow para token {token}: {e}")
            return Response(status=status.HTTP_503_SERVICE_UNAVAILABLE)
        except Exception as e:
            logger.critical(f"Error crítico no esperado en confirmación de Flow para token {token}: {e}")
            return Response(status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response(status=status.HTTP_200_OK)


class OrderStatusView(APIView):
    """
    API para consultar el estado de una orden específica (usado por el frontend).
    """
    def get(self, request, commerce_order, *args, **kwargs):
        try:
            order = Order.objects.get(commerce_order=commerce_order)
            return Response({"status": order.status})
        except Order.DoesNotExist:
            return Response({"error": "Orden no encontrada"}, status=status.HTTP_404_NOT_FOUND)


# payments/views.py

@method_decorator(csrf_exempt, name='dispatch')
class PaymentResultView(View):
    """
    Renderiza la página de resultados para el usuario.
    Acepta tanto GET como POST para manejar el retorno desde Flow.
    """
    def get(self, request, commerce_order, *args, **kwargs):
        # Renderiza el template si el usuario llega con GET
        return render(request, 'payment_result.html', {"commerce_order": commerce_order})

    def post(self, request, commerce_order, *args, **kwargs):
        # Renderiza el mismo template si Flow redirige con POST
        return render(request, 'payment_result.html', {"commerce_order": commerce_order})



def health_check_view(request):
    return HttpResponse("OK", status=200)