from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from io import BytesIO
from datetime import datetime
from decimal import Decimal

class InvoiceGenerator:
    def __init__(self, order, cart_items):
        self.order = order
        self.cart_items = cart_items
        self.buffer = BytesIO()
        self.styles = getSampleStyleSheet()
        self.width, self.height = letter

    def _header(self):
        elements = []
        header_style = ParagraphStyle(
            'CustomHeader',
            parent=self.styles['Heading1'],
            alignment=1,
            spaceAfter=30
        )
        elements.append(Paragraph("BOLETA ELECTRÓNICA", header_style))
        elements.append(Paragraph(f"N° {self.order.order_number}", header_style))
        elements.append(Spacer(1, 20))
        return elements

    def _company_info(self):
        elements = []
        elements.append(Paragraph("STOCK SMART", self.styles['Heading2']))
        company_info = [
            "RUT: XX.XXX.XXX-X",
            "Dirección: Tu Dirección Comercial",
            "Email: contacto@stocksmart.cl",
            "Teléfono: +56 9 XXXX XXXX"
        ]
        for info in company_info:
            elements.append(Paragraph(info, self.styles['Normal']))
        elements.append(Spacer(1, 20))
        return elements

    def _customer_info(self):
        elements = []
        elements.append(Paragraph("DATOS DEL CLIENTE", self.styles['Heading2']))
        customer_info = [
            f"Nombre: {self.order.guest_name}",
            f"Email: {self.order.guest_email}",
            f"Teléfono: {self.order.phone}",
            f"Dirección: {self.order.shipping_address}",
            f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
        ]
        for info in customer_info:
            elements.append(Paragraph(info, self.styles['Normal']))
        elements.append(Spacer(1, 20))
        return elements

    def _items_table(self):
        data = [['Producto', 'Cantidad', 'Precio Unitario', 'Subtotal']]
        
        for item in self.cart_items:
            data.append([
                item.product.name,
                str(item.quantity),
                f"${int(item.product.price):,}",
                f"${int(item.subtotal):,}"
            ])
        
        table = Table(data, colWidths=[4*inch, 1*inch, 1.5*inch, 1.5*inch])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 14),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 12),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        return table

    def _totals(self):
        elements = []
        elements.append(Spacer(1, 20))
        
        # Calcular totales usando Decimal
        subtotal = sum(item.subtotal for item in self.cart_items)
        iva = subtotal * Decimal('0.19')
        shipping = Decimal('5990') if self.order.shipping_method == 'express' else Decimal('0')
        total = subtotal + iva + shipping

        data = [
            ['Subtotal:', f"${int(subtotal):,}"],
            ['IVA (19%):', f"${int(iva):,}"],
            ['Envío:', f"${int(shipping):,}" if shipping else "Gratis"],
            ['TOTAL:', f"${int(total):,}"]
        ]
        
        table = Table(data, colWidths=[2*inch, 1.5*inch])
        table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('LINEABOVE', (0, -1), (-1, -1), 1, colors.black),
            ('GRID', (0, -1), (-1, -1), 1, colors.black)
        ]))
        elements.append(table)
        return elements

    def _footer(self):
        elements = []
        elements.append(Spacer(1, 30))
        footer_style = ParagraphStyle(
            'Footer',
            parent=self.styles['Normal'],
            alignment=1,
            textColor=colors.grey
        )
        elements.append(Paragraph("Gracias por tu compra", footer_style))
        elements.append(Paragraph("Este documento es una representación impresa de tu boleta electrónica", footer_style))
        elements.append(Paragraph("Para cualquier consulta, contáctanos al +56 9 XXXX XXXX o escríbenos a contacto@stocksmart.cl", footer_style))
        return elements

    def generate(self):
        doc = SimpleDocTemplate(
            self.buffer,
            pagesize=letter,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )

        elements = []
        elements.extend(self._header())
        elements.extend(self._company_info())
        elements.extend(self._customer_info())
        elements.append(self._items_table())
        elements.extend(self._totals())
        elements.extend(self._footer())

        doc.build(elements)
        pdf = self.buffer.getvalue()
        self.buffer.close()
        return pdf