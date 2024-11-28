from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import io
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class InvoiceGenerator:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self.title_style = ParagraphStyle(
            'CustomTitle',
            parent=self.styles['Heading1'],
            alignment=1,
            spaceAfter=30
        )

    def generate_invoice(self, order):
        """Genera la boleta en PDF"""
        try:
            buffer = io.BytesIO()
            doc = SimpleDocTemplate(
                buffer,
                pagesize=letter,
                rightMargin=72,
                leftMargin=72,
                topMargin=72,
                bottomMargin=72
            )
            
            elements = self._build_elements(order)
            doc.build(elements)
            
            buffer.seek(0)
            return buffer
            
        except Exception as e:
            logger.error(f"Error generando boleta: {str(e)}")
            raise

    def _build_elements(self, order):
        """Construye los elementos del PDF"""
        elements = []
        
        # Encabezado
        elements.extend(self._build_header(order))
        
        # Tabla de productos
        elements.append(self._build_products_table(order))
        
        return elements

    def _build_header(self, order):
        """Construye el encabezado de la boleta"""
        return [
            Paragraph("BOLETA ELECTRÓNICA", self.title_style),
            Paragraph(f"Orden #{order.order_number}", self.styles['Heading2']),
            Paragraph(f"Fecha: {datetime.now().strftime('%d/%m/%Y')}", self.styles['Normal']),
            Spacer(1, 20),
            Paragraph("Tu Empresa", self.styles['Heading3']),
            Paragraph("RUT: 76.XXX.XXX-X", self.styles['Normal']),
            Paragraph("Dirección de la empresa", self.styles['Normal']),
            Spacer(1, 20)
        ]

    def _build_products_table(self, order):
        """Construye la tabla de productos"""
        data = [['Producto', 'Cantidad', 'Precio', 'Total']]
        
        for item in order.orderitem_set.all():
            data.append([
                item.product.name,
                str(item.quantity),
                f"${item.price:,.0f}",
                f"${item.get_total():,.0f}"
            ])
        
        data.extend([
            ['', '', 'Subtotal:', f"${order.get_subtotal():,.0f}"],
            ['', '', 'IVA (19%):', f"${order.get_iva():,.0f}"],
            ['', '', 'Total:', f"${order.total_amount:,.0f}"]
        ])
        
        table = Table(data, colWidths=[4*inch, inch, 1.2*inch, 1.2*inch])
        table.setStyle(self._get_table_style())
        return table

    def _get_table_style(self):
        """Define el estilo de la tabla"""
        return TableStyle([
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
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ])
