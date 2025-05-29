# payments/emails.py
import os
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string # Para usar templates HTML en el futuro

def format_order_details_for_email(order):
    # Helper para formatear los detalles comunes
    details = f"ID de Orden FungiGrow: {order.commerce_order}\n"
    details += f"Monto Total: ${order.amount:,.0f} CLP\n" # Asumiendo CLP y formateando
    details += f"Fecha del Pedido: {order.created_at.strftime('%d-%m-%Y %H:%M')}\n\n"

    details += "Detalles de Envío:\n"
    details += f"  Nombre: {order.shipping_name or 'No especificado'}\n"
    details += f"  RUT: {order.shipping_rut or 'No especificado'}\n"
    details += f"  Dirección: {order.shipping_address or 'No especificado'}\n"
    details += f"  Comuna: {order.shipping_commune or 'No especificado'}\n"
    details += f"  Región: {order.shipping_region or 'No especificado'}\n"
    details += f"  Teléfono: {order.shipping_phone or 'No especificado'}\n"
    details += f"  Email Cliente: {order.customer_email or 'No especificado'}\n"
    return details

def send_new_sale_to_owner(order):
    subject = f"¡Nueva Venta en FungiGrow! Orden #{order.commerce_order}"

    message_body = "Hola Dueño de FungiGrow,\n\n"
    message_body += "¡Has recibido una nueva orden pagada! Por favor, prepara el pedido para el despacho.\n\n"
    message_body += format_order_details_for_email(order)
    message_body += "\nSaludos,\nTu Sistema de Pagos FungiGrow"

    from_email = settings.DEFAULT_FROM_EMAIL
    recipient_list = [settings.STORE_OWNER_EMAIL]

    try:
        send_mail(subject, message_body, from_email, recipient_list, fail_silently=False)
        print(f"Email de nueva venta enviado a {settings.STORE_OWNER_EMAIL} para orden {order.commerce_order}")
    except Exception as e:
        print(f"Error al enviar email de nueva venta al dueño: {e}")

def send_payment_confirmation_to_customer(order):
    if not order.customer_email:
        print(f"No se puede enviar email a cliente para orden {order.commerce_order}: email no proporcionado.")
        return

    subject = ""
    message_body = ""

    if order.status == 'PAID':
        subject = f"Confirmación de tu Pedido FungiGrow #{order.commerce_order}"
        message_body = f"Hola {order.shipping_name or 'Cliente'},\n\n"
        message_body += "¡Gracias por tu compra en FungiGrow!\n"
        message_body += "Hemos recibido tu pago y tu pedido está siendo procesado.\n\n"
        message_body += format_order_details_for_email(order)
        message_body += "\nPronto recibirás más información sobre el envío.\n\n"
        message_body += "Saludos,\nEl Equipo de FungiGrow"
    elif order.status == 'REJECTED':
        subject = f"Información sobre tu Pedido FungiGrow #{order.commerce_order}"
        message_body = f"Hola {order.shipping_name or 'Cliente'},\n\n"
        message_body += "Hubo un problema al procesar tu pago para la orden #{order.commerce_order} en FungiGrow.\n"
        message_body += "Por favor, intenta realizar el pago nuevamente o contacta a nuestro soporte si el problema persiste.\n\n"
        message_body += "Lamentamos cualquier inconveniente.\n\n"
        message_body += "Saludos,\nEl Equipo de FungiGrow"
    else: # Para PENDING u otros estados, podrías no enviar email o enviar uno diferente
        print(f"No se enviará email a cliente para orden {order.commerce_order} con estado {order.status}")
        return

    from_email = settings.DEFAULT_FROM_EMAIL
    recipient_list = [order.customer_email]

    try:
        send_mail(subject, message_body, from_email, recipient_list, fail_silently=False)
        print(f"Email de confirmación/estado enviado a {order.customer_email} para orden {order.commerce_order}")
    except Exception as e:
        print(f"Error al enviar email al cliente {order.customer_email}: {e}")