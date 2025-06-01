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
from .emails import send_new_sale_to_owner, send_payment_confirmation_to_customer

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
    Recibe detalles del pedido y envío de FungiGrow, crea una orden local,
    genera la petición de pago en Flow, y devuelve la URL de Flow para el pago.
    """
    def post(self, request, *args, **kwargs):
        amount = request.data.get('amount')
        commerce_order = request.data.get('commerceOrder')
        subject = request.data.get('subject')
        # Nuevos campos del payload
        currency = request.data.get('currency', 'CLP') # Moneda, con CLP por defecto
        fungigrow_return_url_from_frontend = request.data.get('return_url')
        shipping_details = request.data.get('shippingDetails', {}) # Objeto, default a dict vacío
        customer_email_from_frontend = request.data.get('customer_email') 

        # Validación más completa
        if not all([amount, commerce_order, subject, fungigrow_return_url_from_frontend, customer_email_from_frontend]):
            missing_params = []
            if not amount: missing_params.append("amount")
            if not commerce_order: missing_params.append("commerceOrder")
            if not subject: missing_params.append("subject")
            if not fungigrow_return_url_from_frontend: missing_params.append("return_url")
            return Response(
                {"error": f"Faltan parámetros requeridos: {', '.join(missing_params)}"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            new_order = Order.objects.create(
                commerce_order=commerce_order,
                amount=amount,
                status='PENDING',
                fungigrow_return_url=fungigrow_return_url_from_frontend, # Guardamos la URL de FungiGrow
                shipping_name=shipping_details.get('nombreCompleto'),
                shipping_rut=shipping_details.get('rut'),
                shipping_address=shipping_details.get('direccion'),
                shipping_commune=shipping_details.get('comuna'),
                shipping_region=shipping_details.get('region'),
                shipping_phone=shipping_details.get('telefono'),
                customer_email=customer_email_from_frontend 
            )
        except Exception as e:
            print(f"ERROR al crear orden {commerce_order} en BD: {e}")
            return Response(
                {"error": f"La orden {commerce_order} ya existe o hubo un error al crearla en la BD."},
                status=status.HTTP_400_BAD_REQUEST
            )

        api_key = os.getenv('FLOW_API_KEY')
        secret_key = os.getenv('FLOW_SECRET_KEY')
        flow_api_base_url = os.getenv('FLOW_API_URL_PROD', 'https://flow.cl/api')
        flow_payment_create_endpoint_url = f"{flow_api_base_url}/payment/create"

        public_backend_url = settings.PUBLIC_URL_BASE # Nuestra URL base de la API Django

        params = {
            'apiKey': api_key,
            'commerceOrder': str(commerce_order),
            'amount': str(amount),
            'subject': subject,
            'email': "patricio.dilet@gmail.com", # Considera obtenerlo de shippingDetails o request.data
            # El webhook de confirmación servidor-a-servidor sigue siendo nuestro
            'urlConfirmation': f"{public_backend_url}/api/confirm-payment/",
            # urlReturn para Flow AHORA apunta a nuestro endpoint de callback
            'urlReturn': f"{public_backend_url}/payment/flow-callback/"
        }
        
        params['s'] = sign_params(params, secret_key)
        
        # (Los prints de depuración pueden quedarse o quitarse según prefieras)
        print("---------------------------------------------------------")
        print("--- DEBUG: CREATE_PAYMENT PETICIÓN A FLOW ---")
        print(f"--- DEBUG: URL Flow: {flow_payment_create_endpoint_url}")
        params_para_imprimir = params.copy(); params_para_imprimir.pop('apiKey', None) # No imprimir apiKey
        print(f"--- DEBUG: Params a Flow (sin apiKey): {params_para_imprimir}")
        print("---------------------------------------------------------")

        try:
            response_from_flow = requests.post(flow_payment_create_endpoint_url, data=params)
            response_from_flow.raise_for_status()
            flow_json_response = response_from_flow.json()
            
            if 'code' in flow_json_response:
                new_order.status = 'REJECTED'; new_order.save()
                return Response({"error": f"Error por parte de Flow: {flow_json_response.get('message')}"}, status=status.HTTP_400_BAD_REQUEST)
            
            flow_token = flow_json_response.get('token')
            if flow_token:
                new_order.flow_token = flow_token; new_order.save()
            else:
                new_order.status = 'REJECTED'; new_order.save()
                print(f"ERROR GRABE: Respuesta de Flow sin token: {flow_json_response} para orden {commerce_order}")
                return Response({"error": "Respuesta inesperada de Flow (sin token)."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

            payment_redirect_url = f"{flow_json_response.get('url')}?token={flow_token}"
            return Response({"redirect_url": payment_redirect_url, "token": flow_token}, status=status.HTTP_201_CREATED)

        except requests.exceptions.HTTPError as http_err:
            new_order.status = 'REJECTED'; new_order.save()
            error_content = "No se pudo obtener contenido del error de Flow."
            try: error_content = http_err.response.json()
            except ValueError: error_content = http_err.response.text[:500]
            print(f"ERROR HTTP de Flow: {http_err.response.status_code} - {error_content}")
            return Response({"error": f"Error directo de Flow: {http_err.response.status_code}", "flow_response_details": error_content}, status=status.HTTP_502_BAD_GATEWAY)
        except requests.exceptions.RequestException as e:
            new_order.status = 'REJECTED'; new_order.save()
            print(f"ERROR de conexión con Flow: {e}")
            return Response({"error": f"Error de conexión al contactar a Flow: {e}"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)


# @method_decorator(csrf_exempt, name='dispatch')
# class FlowConfirmationView(APIView):
#     """
#     Webhook endpoint que Flow llama para confirmar el estado de un pago.
#     Esta vista es crucial y debe ser robusta e idempotente.
#     """
#     def post(self, request, *args, **kwargs):
#         # Flow envía los datos como form-data (request.POST) para el webhook de confirmación
#         flow_token = request.POST.get('token')

#         if not flow_token:
#             logger.warning("FlowConfirmationView: Recibida confirmación de Flow SIN token.")
#             return Response({"error": "Token no proporcionado por Flow"}, status=status.HTTP_400_BAD_REQUEST)

#         logger.info(f"FlowConfirmationView: Recibido token de confirmación de Flow: {flow_token}")

#         try:
#             api_key = os.getenv('FLOW_API_KEY')
#             secret_key = os.getenv('FLOW_SECRET_KEY')
#             flow_api_base_url = os.getenv('FLOW_API_URL_PROD', 'https://sandbox.flow.cl/api')
#             flow_status_endpoint_url = f"{flow_api_base_url}/payment/getStatus"
            
#             params_to_sign_for_get_status = {'apiKey': api_key, 'token': flow_token}
#             signature_for_get_status = sign_params(params_to_sign_for_get_status, secret_key)
            
#             params_for_get_status_call = {
#                 'apiKey': api_key,
#                 'token': flow_token,
#                 's': signature_for_get_status
#             }

#             # Llamada a Flow para obtener el estado REAL y AUTORITATIVO del pago
#             response_flow_status = requests.get(flow_status_endpoint_url, params=params_for_get_status_call)
#             response_flow_status.raise_for_status() # Lanza HTTPError para respuestas 4xx/5xx de Flow
#             payment_data_from_flow = response_flow_status.json()

#             commerce_order_id = payment_data_from_flow.get('commerceOrder')
#             flow_status_code = payment_data_from_flow.get('status') # 1=Pendiente, 2=Pagada, 3=Rechazada, 4=Anulada
            
#             # El token que Flow devuelve en getStatus es el mismo que usamos para consultar
#             # flow_payment_token_from_getstatus = payment_data_from_flow.get('token') 

#             if not commerce_order_id:
#                 logger.error(f"FlowConfirmationView: Flow no devolvió commerceOrder para el token {flow_token}. Respuesta de Flow: {payment_data_from_flow}")
#                 # Respondemos OK a Flow para que no reintente, pero logueamos el error severo.
#                 return Response(status=status.HTTP_200_OK) 

#             logger.info(f"FlowConfirmationView: Estado de Flow para orden {commerce_order_id} (token {flow_token}): Código {flow_status_code}")

#             with transaction.atomic():
#                 order_to_update = None
#                 try:
#                     # Buscamos la orden por commerceOrder, que es nuestro ID principal.
#                     order_to_update = Order.objects.select_for_update().get(commerce_order=commerce_order_id)
#                 except Order.DoesNotExist:
#                     # Si no la encontramos por commerceOrder (raro, pero podría pasar si Flow envía un commerceOrder diferente al que creamos)
#                     # podríamos intentar buscarla por flow_token si lo guardamos en la creación.
#                     # Esto asume que el flow_token guardado en la creación es el mismo que llega por el webhook.
#                     logger.warning(f"FlowConfirmationView: Orden {commerce_order_id} no encontrada por commerce_order. Intentando buscar por flow_token {flow_token} (si está disponible en el modelo).")
#                     # order_to_update = Order.objects.select_for_update().filter(flow_token=flow_token).first() # Descomentar si guardas token en creación
#                     if not order_to_update:
#                         logger.error(f"FlowConfirmationView: Orden {commerce_order_id} (token {flow_token}) confirmada por Flow NO FUE ENCONTRADA en la BD por ningún medio.")
#                         return Response(status=status.HTTP_200_OK) # OK para Flow, pero problema interno grave.

#                 previous_status = order_to_update.status

#                 # Guardar/Actualizar el token de Flow en nuestra orden por si no lo teníamos
#                 if not order_to_update.flow_token or order_to_update.flow_token != flow_token:
#                     order_to_update.flow_token = flow_token
                
#                 # Lógica de Idempotencia: Solo procesar si el estado realmente necesita actualizarse.
#                 if order_to_update.status == 'PAID' and flow_status_code == 2:
#                     logger.info(f"FlowConfirmationView: Orden {commerce_order_id} ya está PAGADA. No se realizan acciones adicionales.")
#                 elif order_to_update.status == 'REJECTED' and (flow_status_code == 3 or flow_status_code == 4):
#                     logger.info(f"FlowConfirmationView: Orden {commerce_order_id} ya está RECHAZADA. No se realizan acciones adicionales.")
#                 else:
#                     # El estado actual de la orden no es final o no coincide con el de Flow, procedemos a actualizar.
#                     if flow_status_code == 2: # Pagada
#                         order_to_update.status = 'PAID'
#                         logger.info(f"FlowConfirmationView: ✅ Orden {commerce_order_id} actualizada a PAGADA en BD.")
#                     elif flow_status_code == 3 or flow_status_code == 4: # Rechazada o Anulada
#                         order_to_update.status = 'REJECTED'
#                         logger.info(f"FlowConfirmationView: ❌ Orden {commerce_order_id} actualizada a RECHAZADA en BD.")
#                     elif flow_status_code == 1: # Pendiente
#                         # Si ya estaba PENDING, no hacemos nada. Si estaba en otro estado (ej. ERROR)
#                         # y Flow dice PENDING, podríamos querer registrarlo o actualizarlo.
#                         # Por ahora, si es PENDING y ya estaba PENDING, no hay cambio.
#                         if order_to_update.status != 'PENDING':
#                            # order_to_update.status = 'PENDING' # Decide si quieres actualizar a PENDING
#                            logger.info(f"FlowConfirmationView: ⏳ Orden {commerce_order_id} está PENDIENTE según Flow. Estado actual: {previous_status}.")
#                         else:
#                            logger.info(f"FlowConfirmationView: ⏳ Orden {commerce_order_id} ya estaba PENDIENTE.")
#                     else:
#                         logger.warning(f"FlowConfirmationView: Estado desconocido {flow_status_code} de Flow para orden {commerce_order_id}. Se marcará como ERROR.")
#                         order_to_update.status = 'ERROR' # Usando el estado 'ERROR' que definimos en el modelo

#                     order_to_update.save()

#                     # Envío de emails si el estado cambió a PAID (y no lo estaba antes)
#                     if order_to_update.status == 'PAID' and previous_status != 'PAID':
#                         logger.info(f"FlowConfirmationView: Enviando emails para orden PAGADA {commerce_order_id}...")
#                         send_new_sale_to_owner(order_to_update)
#                         send_payment_confirmation_to_customer(order_to_update)
#                     # O si cambió a REJECTED y antes estaba PENDING
#                     elif order_to_update.status == 'REJECTED' and previous_status == 'PENDING':
#                         logger.info(f"FlowConfirmationView: Enviando email de rechazo para orden {commerce_order_id}...")
#                         send_payment_confirmation_to_customer(order_to_update) 

#         except requests.exceptions.HTTPError as http_err:
#             error_text = http_err.response.text[:200] if http_err.response else str(http_err)
#             logger.error(f"FlowConfirmationView: HTTPError al contactar Flow para getStatus (token {flow_token}): {http_err.response.status_code if http_err.response else 'N/A'} - {error_text}")
#             if http_err.response and http_err.response.status_code == 400:
#                 return Response({"error": "Token inválido para Flow getStatus o petición malformada"}, status=status.HTTP_400_BAD_REQUEST)
#             return Response({"error": "Error comunicándose con Flow"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
#         except requests.exceptions.RequestException as e:
#             logger.error(f"FlowConfirmationView: RequestException al contactar Flow para getStatus (token {flow_token}): {e}")
#             return Response({"error": "Error de red comunicándose con Flow"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
#         except Exception as e:
#             logger.critical(f"FlowConfirmationView: Error crítico inesperado procesando confirmación (token {flow_token}): {e}", exc_info=True)
#             return Response({"error": "Error interno del servidor"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

#         # Flow espera un 200 OK para saber que recibimos y procesamos la notificación.
#         return Response(status=status.HTTP_200_OK)

@method_decorator(csrf_exempt, name='dispatch')
class FlowConfirmationView(APIView):
    """
    Webhook endpoint que Flow llama para confirmar el estado de un pago.
    Verifica el estado, actualiza la BD, y si el pago es exitoso,
    llama a un webhook de n8n para manejar notificaciones y otros flujos.
    """
    def post(self, request, *args, **kwargs):
        flow_token = request.POST.get('token')

        if not flow_token:
            logger.warning("FlowConfirmationView: Recibida confirmación de Flow SIN token.")
            return Response({"error": "Token no proporcionado por Flow"}, status=status.HTTP_400_BAD_REQUEST)

        logger.info(f"FlowConfirmationView: Recibido token de confirmación de Flow: {flow_token}")

        try:
            api_key = os.getenv('FLOW_API_KEY')
            secret_key = os.getenv('FLOW_SECRET_KEY')
            flow_api_base_url = os.getenv('FLOW_API_URL_PROD', 'https://flow.cl/api')
            flow_status_endpoint_url = f"{flow_api_base_url}/payment/getStatus"
            
            params_to_sign_for_get_status = {'apiKey': api_key, 'token': flow_token}
            signature_for_get_status = sign_params(params_to_sign_for_get_status, secret_key)
            
            params_for_get_status_call = {
                'apiKey': api_key,
                'token': flow_token,
                's': signature_for_get_status
            }

            response_flow_status = requests.get(flow_status_endpoint_url, params=params_for_get_status_call)
            response_flow_status.raise_for_status()
            payment_data_from_flow = response_flow_status.json()

            commerce_order_id = payment_data_from_flow.get('commerceOrder')
            flow_status_code = payment_data_from_flow.get('status')

            if not commerce_order_id:
                logger.error(f"FlowConfirmationView: Flow no devolvió commerceOrder para token {flow_token}. Respuesta: {payment_data_from_flow}")
                return Response(status=status.HTTP_200_OK) 

            logger.info(f"FlowConfirmationView: Estado de Flow para orden {commerce_order_id} (token {flow_token}): Código {flow_status_code}")

            with transaction.atomic():
                order_to_update = None
                try:
                    order_to_update = Order.objects.select_for_update().get(commerce_order=commerce_order_id)
                except Order.DoesNotExist:
                    logger.error(f"FlowConfirmationView: Orden {commerce_order_id} (token {flow_token}) confirmada por Flow NO ENCONTRADA en BD.")
                    return Response(status=status.HTTP_200_OK)

                previous_status = order_to_update.status
                if not order_to_update.flow_token or order_to_update.flow_token != flow_token:
                    order_to_update.flow_token = flow_token
                
                should_trigger_n8n = False
                
                if order_to_update.status == 'PAID' and flow_status_code == 2:
                    logger.info(f"FlowConfirmationView: Orden {commerce_order_id} ya está PAGADA. No se realizan acciones adicionales de BD ni n8n.")
                elif order_to_update.status == 'REJECTED' and (flow_status_code == 3 or flow_status_code == 4):
                    logger.info(f"FlowConfirmationView: Orden {commerce_order_id} ya está RECHAZADA. No se realizan acciones adicionales de BD.")
                else:
                    if flow_status_code == 2: # Pagada
                        order_to_update.status = 'PAID'
                        logger.info(f"FlowConfirmationView: ✅ Orden {commerce_order_id} actualizada a PAGADA en BD.")
                    elif flow_status_code == 3 or flow_status_code == 4: # Rechazada o Anulada
                        order_to_update.status = 'REJECTED'
                        logger.info(f"FlowConfirmationView: ❌ Orden {commerce_order_id} actualizada a RECHAZADA en BD.")
                    elif flow_status_code == 1: # Pendiente
                        logger.info(f"FlowConfirmationView: ⏳ Orden {commerce_order_id} PENDIENTE según Flow. Estado actual BD: {previous_status}.")
                    else:
                        logger.warning(f"FlowConfirmationView: Estado desconocido {flow_status_code} de Flow para orden {commerce_order_id}. Se marca como ERROR.")
                        order_to_update.status = 'ERROR'

                    order_to_update.save()

                    if order_to_update.status == 'PAID' and previous_status != 'PAID':
                        should_trigger_n8n = True
                    # Podrías decidir si también quieres notificar a n8n para pagos RECHAZADOS
                    # elif order_to_update.status == 'REJECTED' and previous_status == 'PENDING':
                    #     should_trigger_n8n = True # O un webhook diferente para fallos

                if should_trigger_n8n:
                    n8n_webhook_url = os.getenv('N8N_SALE_WEBHOOK_URL')
                    if n8n_webhook_url:
                        payload_to_n8n = {
                            "commerceOrder": order_to_update.commerce_order,
                            "amount": str(order_to_update.amount),
                            "customer_email": order_to_update.customer_email,
                            "flow_token": order_to_update.flow_token,
                            "payment_status_flow_code": flow_status_code,
                            "payment_status_internal": order_to_update.status,
                            "shipping_details": {
                                "nombreCompleto": order_to_update.shipping_name,
                                "rut": order_to_update.shipping_rut,
                                "direccion": order_to_update.shipping_address,
                                "comuna": order_to_update.shipping_commune,
                                "region": order_to_update.shipping_region,
                                "telefono": order_to_update.shipping_phone,
                            },
                            "fungigrow_return_url": order_to_update.fungigrow_return_url,
                            "order_created_at": order_to_update.created_at.isoformat() if order_to_update.created_at else None,
                            "order_updated_at": order_to_update.updated_at.isoformat() if order_to_update.updated_at else None,
                            "store_owner_email_recipient": settings.STORE_OWNER_EMAIL,
                        }
                        try:
                            logger.info(f"FlowConfirmationView: Enviando datos a n8n para orden {commerce_order_id}...")
                            requests.post(n8n_webhook_url, json=payload_to_n8n, timeout=10) 
                            logger.info(f"FlowConfirmationView: Datos enviados a n8n para orden {commerce_order_id}.")
                        except requests.exceptions.RequestException as n8n_error:
                            logger.error(f"FlowConfirmationView: Error al enviar datos a n8n para orden {commerce_order_id}: {n8n_error}")
                    else:
                        logger.warning(f"FlowConfirmationView: N8N_SALE_WEBHOOK_URL no está configurada. No se puede notificar a n8n para orden {commerce_order_id}.")

        except requests.exceptions.HTTPError as http_err:
            error_text = http_err.response.text[:200] if http_err.response else str(http_err)
            logger.error(f"FlowConfirmationView: HTTPError al contactar Flow para getStatus (token {flow_token}): {http_err.response.status_code if http_err.response else 'N/A'} - {error_text}")
            # Determinar si es un error que Flow debería reintentar o un error de nuestra parte
            if http_err.response and http_err.response.status_code == 400: # Error del cliente (ej. token inválido)
                return Response({"error": "Token inválido para Flow getStatus o petición malformada"}, status=status.HTTP_400_BAD_REQUEST)
            return Response({"error": "Error comunicándose con Flow"}, status=status.HTTP_503_SERVICE_UNAVAILABLE) # Error del servidor o red
        
        except requests.exceptions.RequestException as e: # Errores de conexión, DNS, etc.
            logger.error(f"FlowConfirmationView: RequestException al contactar Flow para getStatus (token {flow_token}): {e}")
            return Response({"error": "Error de red comunicándose con Flow"}, status=status.HTTP_503_SERVICE_UNAVAILABLE)
        
        except Order.DoesNotExist: # Esto no debería pasar si la lógica de búsqueda es correcta.
            logger.error(f"FlowConfirmationView: CRÍTICO - Orden no encontrada después de getStatus exitoso para commerceOrder {commerce_order_id if 'commerce_order_id' in locals() else 'desconocido'} (token {flow_token}).")
            return Response(status=status.HTTP_200_OK) # OK a Flow para evitar reintentos, pero es un error grave nuestro.

        except Exception as e:
            logger.critical(f"FlowConfirmationView: Error crítico inesperado procesando confirmación (token {flow_token}): {e}", exc_info=True)
            return Response({"error": "Error interno del servidor"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Siempre respondemos 200 OK a Flow si llegamos hasta aquí sin errores graves que requieran reintento de Flow.
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
        flow_api_base_url = os.getenv('FLOW_API_URL_PROD', 'https://flow.cl/api')
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
class FlowCallbackView(View): # Renombrada para claridad y usando View base de Django
    """
    Maneja el retorno del usuario desde Flow (configurada como urlReturn para Flow).
    Verifica el estado del pago con Flow usando el token y luego redirige
    al usuario al frontend FungiGrow (usando la fungigrow_return_url guardada).
    """
    def handle_callback(self, request):
        # Nivel de indentación 2 (dentro del método handle_callback)
        flow_token = request.POST.get('token') or request.GET.get('token')

        fungifresh_base_url = settings.FUNGIFRESH_STORE_URL
        fungifresh_path = "/checkout/confirmation" # Path estándar de FungiGrow
        
        redirect_params = {
            'orderId': 'desconocido', # Lo actualizaremos si encontramos la orden
            'status': 'error',        # Por defecto, si algo falla
            'message': 'Error_procesando_pago_interno' # Mensaje por defecto
        }

        if not flow_token:
            redirect_params['message'] = 'Token_de_Flow_no_recibido_en_callback'
            query_string = urllib.parse.urlencode(redirect_params)
            return HttpResponseRedirect(f"{fungifresh_base_url}{fungifresh_path}?{query_string}")

        # Intentamos obtener nuestra orden local para tener el commerceOrder
        # y la fungigrow_return_url específica si se guardó
        order_in_db = Order.objects.filter(flow_token=flow_token).first()
        if order_in_db:
            redirect_params['orderId'] = order_in_db.commerce_order
            # Si la URL de FungiGrow se guardó por orden, podríamos usarla,
            # pero el plan actual es usar una URL base y un path fijo.
        else:
            # Si no encontramos la orden por token, es un problema.
            # El webhook /api/confirm-payment/ debería haber guardado el token.
            print(f"ALERTA: No se encontró orden con flow_token {flow_token} en el callback. Se intentará buscar por commerceOrder si Flow lo devuelve.")
            # No asignamos un mensaje de error aquí todavía, esperaremos a la respuesta de Flow.

        # Consultar el estado REAL del pago en Flow usando el token
        api_key = os.getenv('FLOW_API_KEY')
        secret_key = os.getenv('FLOW_SECRET_KEY')
        flow_api_base_url = os.getenv('FLOW_API_URL_PROD', 'https://flow.cl/api')
        flow_status_endpoint_url = f"{flow_api_base_url}/payment/getStatus"
        
        params_to_sign = {'apiKey': api_key, 'token': flow_token}
        # Asegúrate que la función sign_params esté disponible en este scope
        signature = sign_params(params_to_sign, secret_key) 
        params_for_get_status = {'apiKey': api_key, 'token': flow_token, 's': signature}

        try:
            response = requests.get(flow_status_endpoint_url, params=params_for_get_status)
            response.raise_for_status() # Lanza HTTPError para respuestas 4xx/5xx
            payment_data = response.json()

            flow_status_code = payment_data.get('status') # 1=Pendiente, 2=Pagada, 3=Rechazada, 4=Anulada
            commerce_order_from_flow = payment_data.get('commerceOrder')

            if commerce_order_from_flow: # Usamos el commerceOrder de Flow como la fuente más fiable
                 redirect_params['orderId'] = commerce_order_from_flow

            # Intentar actualizar nuestra BD
            # Buscamos la orden por commerceOrder devuelto por Flow, ya que es más fiable que el token solo
            order_to_update = None
            if commerce_order_from_flow:
                order_to_update = Order.objects.filter(commerce_order=commerce_order_from_flow).first()
            
            if order_to_update:
                if not order_to_update.flow_token: # Si no tenía el token, lo guardamos
                    order_to_update.flow_token = flow_token
                
                # Solo actualizamos si está PENDING para no sobrescribir un estado final del webhook
                if order_to_update.status == 'PENDING':
                    if flow_status_code == 2:
                        order_to_update.status = 'PAID'
                    elif flow_status_code == 3 or flow_status_code == 4:
                        order_to_update.status = 'REJECTED'
                    # No cambiamos a PENDING aquí, solo a estados finales.
                    order_to_update.save()
            else:
                print(f"ALERTA: No se encontró orden local para commerceOrder {commerce_order_from_flow} devuelto por Flow en callback.")


            # Definir status y message para FungiGrow
            if flow_status_code == 2: # Pagada
                redirect_params['status'] = 'success'
                redirect_params['message'] = 'Tu pago fue exitoso'
            elif flow_status_code == 3 or flow_status_code == 4: # Rechazada o Anulada
                redirect_params['status'] = 'failure'
                # Usar el mensaje de Flow si está disponible, sino uno genérico
                flow_payment_message = payment_data.get('paymentData', {}).get('user_message', 'Pago rechazado o anulado')
                redirect_params['message'] = flow_payment_message if flow_payment_message else 'Pago rechazado o anulado'
            elif flow_status_code == 1: # Pendiente
                redirect_params['status'] = 'pending'
                redirect_params['message'] = 'Tu pago esta pendiente'
            else: # Otro estado o error en la respuesta de Flow
                redirect_params['status'] = 'error'
                # Esta es la línea 442 original, asegúrate que la indentación de este 'else'
                # y su contenido sea correcta, alineada con el 'if' y 'elif' anteriores.
                redirect_params['message'] = 'Estado de pago desconocido desde Flow' 
        
        except requests.exceptions.RequestException as e:
            print(f"Error al consultar estado en Flow (FlowCallbackView): {e}")
            redirect_params['status'] = 'error'
            redirect_params['message'] = 'Fallo en la verificacion del estado con Flow'
        
        # Limpiar y codificar espacios en el mensaje para la URL
        if 'message' in redirect_params and redirect_params['message']:
            redirect_params['message'] = urllib.parse.quote_plus(str(redirect_params['message']))

        query_string = urllib.parse.urlencode(redirect_params)
        final_url_to_fungigrow = f"{fungifresh_base_url}{fungifresh_path}?{query_string}"
        print(f"--- DEBUG CALLBACK: Redirigiendo a FungiGrow: {final_url_to_fungigrow} ---")
        return HttpResponseRedirect(final_url_to_fungigrow)

    def get(self, request, *args, **kwargs):
        # Nivel de indentación 1 (dentro de la clase)
        return self.handle_callback(request) # Nivel 2

    def post(self, request, *args, **kwargs):
        # Nivel de indentación 1 (dentro de la clase)
        # Flow usualmente redirige con GET, pero por si acaso manejamos POST igual.
        return self.handle_callback(request) # Nivel 2



class QueryOrderStatusView(APIView):
    """
    Permite consultar el estado de una o más órdenes usando
    commerce_order, customer_email o shipping_phone como parámetro query.
    """
    def get(self, request, *args, **kwargs):
        commerce_order = request.query_params.get('commerce_order', None)
        email = request.query_params.get('email', None)
        phone = request.query_params.get('phone', None)

        orders_query = None

        if commerce_order:
            orders_query = Order.objects.filter(commerce_order__iexact=commerce_order)
        elif email:
            orders_query = Order.objects.filter(customer_email__iexact=email).order_by('-created_at')
        elif phone:
            # Considerar normalizar el 'phone' si los formatos pueden variar mucho.
            # Por ahora, búsqueda exacta (ignorando mayúsculas/minúsculas si es relevante, aunque para teléfonos no tanto).
            # Si guardas teléfonos con '+569...' el usuario debe proveerlo así.
            orders_query = Order.objects.filter(shipping_phone=phone).order_by('-created_at')
        else:
            return Response(
                {"error": "Debes proporcionar un parámetro de búsqueda: commerce_order, email, o phone."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if not orders_query: # Si el filtro no arrojó nada (aunque el query en sí era válido)
            return Response([], status=status.HTTP_200_OK) # Devolver lista vacía en lugar de 404

        # Preparamos una lista simplificada de los resultados
        results = []
        for order in orders_query:
            results.append({
                "commerce_order": order.commerce_order,
                "status": order.status,
                "created_at": order.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                "amount": str(order.amount), # Convertir Decimal a string
                "subject": order.shipping_name # O un resumen de productos si lo tuvieras
                                               # Por ahora, el nombre del destinatario podría servir
            })

        if not results: # Si después de procesar, la lista sigue vacía (ej. por un error interno no capturado)
             return Response([], status=status.HTTP_200_OK)


        return Response(results, status=status.HTTP_200_OK)