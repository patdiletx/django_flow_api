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
from django.http import HttpResponseRedirect
import urllib.parse

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
    Crea una orden en nuestra BD y genera la petición a Flow.
    La urlReturn ahora apunta a una página de estado final en esta misma app Django.
    """
    def post(self, request, *args, **kwargs):
        amount = request.data.get('amount')
        commerce_order = request.data.get('commerceOrder')
        subject = request.data.get('subject')

        # Validación: ya NO esperamos return_url desde el request.data
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
            # logger.error(f"Error al crear orden {commerce_order} en BD: {e}")
            print(f"ERROR al crear orden {commerce_order} en BD: {e}")
            return Response(
                {"error": f"La orden {commerce_order} ya existe o hubo un error al crearla en la BD."},
                status=status.HTTP_400_BAD_REQUEST
            )

        api_key = os.getenv('FLOW_API_KEY')
        secret_key = os.getenv('FLOW_SECRET_KEY')

        flow_api_base_url = os.getenv('FLOW_API_URL_PROD', 'https://sandbox.flow.cl/api') 
        flow_payment_create_endpoint_url = f"{flow_api_base_url}/payment/create"

        # URL pública base de NUESTRO backend (API) desde settings.py
        public_backend_url = settings.PUBLIC_URL_BASE

        params = {
            'apiKey': api_key,
            'commerceOrder': str(commerce_order),
            'amount': str(amount),
            'subject': subject,
            'email': "patricio.dilet@gmail.com", # Considera hacerlo dinámico
            'urlConfirmation': f"{public_backend_url}/api/confirm-payment/",
            # --- CAMBIO IMPORTANTE: urlReturn ahora apunta a nuestra nueva vista de estado final ---
            'urlReturn': f"{public_backend_url}/payment/flow-callback/" 
        }

        params['s'] = sign_params(params, secret_key) 

        # Mantenemos los prints de depuración por ahora
        print("---------------------------------------------------------")
        print("--- DEBUG: INICIANDO PETICIÓN A FLOW (urlReturn interna) ---")
        print(f"--- DEBUG: URL Flow: {flow_payment_create_endpoint_url}")
        params_para_imprimir = params.copy()
        print(f"--- DEBUG: Params a Flow: {params_para_imprimir}")
        print("--- DEBUG: FIN DE PETICIÓN A FLOW ---")
        print("---------------------------------------------------------")

        try:
            response_from_flow = requests.post(flow_payment_create_endpoint_url, data=params)
            response_from_flow.raise_for_status()
            flow_json_response = response_from_flow.json()

            if 'code' in flow_json_response: # Error estructurado de Flow
                new_order.status = 'REJECTED'; new_order.save()
                return Response({"error": f"Error por parte de Flow: {flow_json_response.get('message')}"}, status=status.HTTP_400_BAD_REQUEST)
            
            flow_token = flow_json_response.get('token')
            if flow_token:
                new_order.flow_token = flow_token; new_order.save()
            else: # Respuesta inesperada sin token
                new_order.status = 'REJECTED'; new_order.save()
                print(f"ERROR GRABE: Respuesta exitosa de Flow pero sin token: {flow_json_response} para orden {commerce_order}")
                return Response({"error": "Respuesta inesperada de Flow al crear el pago (sin token)."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            payment_redirect_url = f"{flow_json_response.get('url')}?token={flow_token}"
            return Response({"redirect_url": payment_redirect_url, "token": flow_token}, status=status.HTTP_201_CREATED)

        except requests.exceptions.HTTPError as http_err:
            new_order.status = 'REJECTED'
            new_order.save()
            error_content = "No se pudo obtener contenido del error de Flow."
            try: error_content = http_err.response.json()
            except ValueError: error_content = http_err.response.text[:500]
            print(f"ERROR HTTP de Flow: {http_err.response.status_code} - {error_content}")
            return Response({
                "error": f"Error directo de Flow: {http_err.response.status_code}",
                "flow_response_details": error_content
            }, status=status.HTTP_502_BAD_GATEWAY)
        except requests.exceptions.RequestException as e:
            new_order.status = 'REJECTED'
            new_order.save()
            print(f"ERROR de conexión con Flow: {e}")
            return Response({"error": f"Error de conexión al contactar a Flow: {e}"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

        if 'code' in flow_json_response:
            new_order.status = 'REJECTED'
            new_order.save()
            return Response(
                {"error": f"Error por parte de Flow: {flow_json_response.get('message')}"},
                status=status.HTTP_400_BAD_REQUEST
            )

        flow_token = flow_json_response.get('token')
        if flow_token:
            new_order.flow_token = flow_token
            new_order.save()
        else:
            new_order.status = 'REJECTED'
            new_order.save()
            print(f"ERROR GRABE: Respuesta exitosa de Flow pero sin token: {flow_json_response} para orden {commerce_order}")
            return Response(
                {"error": "Respuesta inesperada de Flow al crear el pago (sin token)."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        payment_redirect_url = f"{flow_json_response.get('url')}?token={flow_token}"

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





# payments/views.py

class GetOrderStatusByTokenView(APIView):
    """
    Permite al frontend consultar el estado de una orden usando el
    token de Flow, que es devuelto en la URL de retorno.
    """
    def get(self, request, flow_token, *args, **kwargs):
        try:
            # Buscamos la orden en nuestra base de datos usando el flow_token
            order = Order.objects.get(flow_token=flow_token)
            return Response({"status": order.status})
        except Order.DoesNotExist:
            return Response({"error": "Orden no encontrada con el token proporcionado"}, status=status.HTTP_404_NOT_FOUND)



class PaymentFinalStatusView(View):
    """
    Renderiza la página de estado final para el usuario, la cual luego lo redirigirá
    a la tienda principal (FungiFresh) con el estado del pago.
    """
    def get(self, request, commerce_order, *args, **kwargs):
        # Pasamos el commerce_order y la URL de la tienda FungiFresh al template
        context = {
            "commerce_order": commerce_order,
            "fungifresh_store_url": settings.FUNGIFRESH_STORE_URL 
        }
        return render(request, 'payment_final_status.html', context)

    def post(self, request, commerce_order, *args, **kwargs):
        # Manejamos POST igual que GET para esta página de retorno
        context = {
            "commerce_order": commerce_order,
            "fungifresh_store_url": settings.FUNGIFRESH_STORE_URL
        }
        return render(request, 'payment_final_status.html', context)



@method_decorator(csrf_exempt, name='dispatch') # Por si Flow decide hacer POST aquí alguna vez
class FlowReturnHandlerView(View):
    """
    Maneja el retorno del usuario desde Flow.
    Verifica el estado del pago con Flow usando el token y redirige
    al usuario al frontend de FungiFresh con el resultado.
    """
    def get(self, request, *args, **kwargs):
        flow_token = request.GET.get('token')

        if not flow_token:
            # Si no hay token, redirigir a FungiFresh con un error genérico
            error_url = f"{settings.FUNGIFRESH_STORE_URL}/checkout/confirmation?status=error&reason=missing_token"
            return HttpResponseRedirect(error_url)

        # Consultar el estado del pago en Flow usando el token
        api_key = os.getenv('FLOW_API_KEY')
        secret_key = os.getenv('FLOW_SECRET_KEY')
        flow_api_base_url = os.getenv('FLOW_API_URL_PROD', 'https://sandbox.flow.cl/api')
        flow_status_endpoint_url = f"{flow_api_base_url}/payment/getStatus"
        
        params_to_sign = {'apiKey': api_key, 'token': flow_token}
        signature = sign_params(params_to_sign, secret_key)
        
        params_for_get_status = {'apiKey': api_key, 'token': flow_token, 's': signature}

        order_in_db = None
        try:
            # Intentamos obtener nuestra orden local usando el flow_token para tener el commerceOrder
            # Si no la encontramos aún (podría ser una carrera con el webhook), no es crítico para la redirección
            order_in_db = Order.objects.filter(flow_token=flow_token).first()
        except Exception:
            pass # No bloqueamos la redirección si no encontramos la orden local inmediatamente

        final_redirect_url = ""
        try:
            response = requests.get(flow_status_endpoint_url, params=params_for_get_status)
            response.raise_for_status()
            payment_data = response.json()

            flow_status_code = payment_data.get('status') # 1=Pendiente, 2=Pagada, 3=Rechazada, 4=Anulada
            commerce_order_from_flow = payment_data.get('commerceOrder', 'unknown') # Tomamos el commerceOrder de Flow

            # Es buena idea actualizar nuestra BD aquí también, aunque el webhook es el principal
            if order_in_db and order_in_db.status == 'PENDING':
                if flow_status_code == 2: order_in_db.status = 'PAID'
                elif flow_status_code == 3 or flow_status_code == 4: order_in_db.status = 'REJECTED'
                order_in_db.save()
            
            # Construir la URL de FungiFresh
            fungifresh_base_redirect = f"{settings.FUNGIFRESH_STORE_URL}/checkout/confirmation"
            if flow_status_code == 2: # Pagada
                final_redirect_url = f"{fungifresh_base_redirect}?status=success&orderId={commerce_order_from_flow}&flowToken={flow_token}"
            elif flow_status_code == 3 or flow_status_code == 4: # Rechazada o Anulada
                final_redirect_url = f"{fungifresh_base_redirect}?status=failure&orderId={commerce_order_from_flow}&flowToken={flow_token}"
            else: # Pendiente u otro estado
                final_redirect_url = f"{fungifresh_base_redirect}?status=pending&orderId={commerce_order_from_flow}&flowToken={flow_token}"

        except requests.exceptions.RequestException as e:
            print(f"Error al consultar estado en Flow (ReturnHandler): {e}")
            # Si falla la consulta a Flow, redirigir a FungiFresh con un error
            commerce_order_for_error = order_in_db.commerce_order if order_in_db else "unknown_order"
            final_redirect_url = f"{settings.FUNGIFRESH_STORE_URL}/checkout/confirmation?status=error&reason=flow_status_check_failed&orderId={commerce_order_for_error}&flowToken={flow_token}"
        
        return HttpResponseRedirect(final_redirect_url)

    def post(self, request, *args, **kwargs):
        # Por si Flow alguna vez decide hacer POST a esta URL de retorno
        return self.get(request, *args, **kwargs)



@method_decorator(csrf_exempt, name='dispatch')
class FlowReturnHandlerView(View):
    """
    Maneja el retorno del usuario desde Flow.
    Verifica el estado del pago con Flow usando el token y redirige
    al usuario al frontend FungiFresh con el resultado.
    """
    def get(self, request, *args, **kwargs):
        flow_token = request.GET.get('token')
        
        # Preparamos los parámetros base para la redirección a FungiFresh
        fungifresh_base_url = settings.FUNGIFRESH_STORE_URL
        fungifresh_path = "/checkout/confirmation"
        redirect_params = {
            'status': 'error', # Por defecto, si algo falla
            'message': 'Error_desconocido_procesando_el_pago'
            # 'orderId' se añadirá si podemos obtenerlo
        }

        if not flow_token:
            redirect_params['message'] = 'Token_de_Flow_no_recibido'
            query_string = urllib.parse.urlencode(redirect_params)
            return HttpResponseRedirect(f"{fungifresh_base_url}{fungifresh_path}?{query_string}")

        # Intentamos obtener nuestra orden local para tener el commerceOrder
        order_in_db = Order.objects.filter(flow_token=flow_token).first()
        commerce_order_for_redirect = order_in_db.commerce_order if order_in_db else "desconocido"
        redirect_params['orderId'] = commerce_order_for_redirect

        # Consultar el estado del pago en Flow usando el token
        api_key = os.getenv('FLOW_API_KEY')
        secret_key = os.getenv('FLOW_SECRET_KEY')
        flow_api_base_url = os.getenv('FLOW_API_URL_PROD', 'https://sandbox.flow.cl/api')
        flow_status_endpoint_url = f"{flow_api_base_url}/payment/getStatus"
        
        params_to_sign = {'apiKey': api_key, 'token': flow_token}
        signature = sign_params(params_to_sign, secret_key) # Asumiendo que sign_params está disponible
        
        params_for_get_status = {'apiKey': api_key, 'token': flow_token, 's': signature}

        try:
            response = requests.get(flow_status_endpoint_url, params=params_for_get_status)
            response.raise_for_status()
            payment_data = response.json()

            flow_status_code = payment_data.get('status') # 1=Pendiente, 2=Pagada, 3=Rechazada, 4=Anulada
            
            # Actualizar nuestra BD (opcional aquí, pero bueno para consistencia rápida)
            # El webhook FlowConfirmationView es el principal para esto.
            if order_in_db and order_in_db.status == 'PENDING':
                if flow_status_code == 2: order_in_db.status = 'PAID'
                elif flow_status_code == 3 or flow_status_code == 4: order_in_db.status = 'REJECTED'
                order_in_db.save()
            
            if flow_status_code == 2: # Pagada
                redirect_params['status'] = 'success'
                redirect_params['message'] = 'Tu pago fue exitoso'
            elif flow_status_code == 3 or flow_status_code == 4: # Rechazada o Anulada
                redirect_params['status'] = 'failure'
                redirect_params['message'] = payment_data.get('paymentData', {}).get('user_message', 'Pago rechazado o anulado')
            elif flow_status_code == 1: # Pendiente
                redirect_params['status'] = 'pending'
                redirect_params['message'] = 'Tu pago esta pendiente'
            else: # Otro estado o error en la respuesta de Flow
                redirect_params['status'] = 'error'
                redirect_params['message'] = 'Estado de pago desconocido o invalido desde Flow'
        
        except requests.exceptions.RequestException as e:
            print(f"Error al consultar estado en Flow (ReturnHandler): {e}")
            redirect_params['status'] = 'error'
            redirect_params['message'] = 'Fallo en la verificacion del estado con Flow'
        
        query_string = urllib.parse.urlencode(redirect_params)
        return HttpResponseRedirect(f"{fungifresh_base_url}{fungifresh_path}?{query_string}")

    def post(self, request, *args, **kwargs):
        # Flow usualmente redirige con GET, pero por si acaso manejamos POST igual.
        return self.get(request, *args, **kwargs)        