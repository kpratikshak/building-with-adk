import os
import random
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field

# Core Google ADK & GenAI elements
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

# ReportLab Engine Layout components
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.graphics.shapes import Drawing, RoundRect

# Google Design Token Palette
GOOGLE_BLUE = colors.Color(0.259, 0.522, 0.957)   # #4285F4
GOOGLE_GREEN = colors.Color(0.208, 0.682, 0.325)  # #34A853
GOOGLE_GREY = colors.Color(0.376, 0.376, 0.376)   # #606060

APP_NAME = "invoice_app"
USER_ID = "1234"
SESSION_ID = "session1234"

# --- PYDANTIC SCHEMAS FOR STRUCTURED FUNCTION CALLING ---
class InvoiceItem(BaseModel):
    description: str = Field(description="The description of services rendered or goods sold")
    quantity: int = Field(default=1, description="Quantity of items")
    rate: float = Field(description="Unit cost/rate per item hour")

class BillingInfo(BaseModel):
    name: str = Field(description="Customer or business legal name")
    address: str = Field(description="Street address details")
    city: str = Field(description="City identifier")
    state: str = Field(description="State code abbreviation")
    zip: str = Field(description="Postal zip code")
    email: Optional[str] = Field(default=None, description="Optional customer communication email address")

class InvoiceSchema(BaseModel):
    bill_to: BillingInfo
    items: List[InvoiceItem]
    notes: Optional[str] = Field(default=None, description="Optional annotations, terms or bank details")


# --- OPTIMIZED GENERATION TOOL ---
def generate_invoice_pdf(invoice_payload: dict) -> str:
    """Generates a professional, branded invoice PDF using the captured customer schema parameters.

    Args:
        invoice_payload: Clean mapping matching the structure of InvoiceSchema.
    """
    try:
        # File management setup
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"invoice_{timestamp}.pdf"
        filepath = os.path.join(os.getcwd(), filename)
        
        # Setup document frame geometry
        margin = 36 # 0.5 inch margins
        doc = SimpleDocTemplate(
            filepath, 
            pagesize=letter,
            leftMargin=margin,
            rightMargin=margin,
            topMargin=margin,
            bottomMargin=margin
        )
        printable_width = letter[0] - (2 * margin)
        story = []
        styles = getSampleStyleSheet()
        
        # Header banner layout
        header_drawing = Drawing(printable_width, 60)
        header_rect = RoundRect(0, 0, printable_width, 60, 10, 10)
        header_rect.fillColor = GOOGLE_BLUE
        header_rect.strokeColor = None
        header_drawing.add(header_rect)
        story.append(header_drawing)
        story.append(Spacer(1, 15))
        
        # Corporate branding text
        company_style = ParagraphStyle(
            'CompanyHeader',
            parent=styles['Normal'],
            fontSize=22,
            textColor=GOOGLE_BLUE,
            fontName='Helvetica-Bold',
            spaceAfter=5
        )
        story.append(Paragraph("Easy AI Labs", company_style))
        
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=14,
            textColor=GOOGLE_GREY,
            fontName='Helvetica',
            spaceAfter=20
        )
        story.append(Paragraph("OFFICIAL RECORD INVOICE", title_style))
        
        # Handle generation fallback values cleanly on runtime level
        invoice_num = ''.join([str(random.randint(0, 9)) for _ in range(16)])
        invoice_date = datetime.now().strftime("%Y-%m-%d")
        
        # Meta Info Meta Table Block
        invoice_info = [
            ["Invoice ID Reference:", invoice_num],
            ["Issue Timestamp Date:", invoice_date]
        ]
        
        meta_table = Table(invoice_info, colWidths=[2*inch, 4*inch])
        meta_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TEXTCOLOR', (0, 0), (-1, -1), GOOGLE_GREY),
            ('ALIGN', (0, 0), (0, -1), 'LEFT'),
            ('BACKGROUND', (0, 0), (-1, -1), colors.Color(0.96, 0.96, 0.96)),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('TOPPADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(meta_table)
        story.append(Spacer(1, 20))
        
        # Client Billing Presentation Panel
        bill_to = invoice_payload.get('bill_to', {})
        billing_text = f"""
        <b>CLIENT ENTITY BILL TO:</b><br/>
        {bill_to.get('name', '')}<br/>
        {bill_to.get('address', '')}<br/>
        {bill_to.get('city', '')}, {bill_to.get('state', '')} {bill_to.get('zip', '')}
        """
        if bill_to.get('email'):
            billing_text += f"<br/>Contact: {bill_to.get('email')}"
            
        story.append(Paragraph(billing_text, styles['Normal']))
        story.append(Spacer(1, 25))
        
        # Process and map item lists
        table_data = [["Line Item Description", "Qty", "Unit Rate", "Gross Amount"]]
        total_accrued = 0.0
        
        items_list = invoice_payload.get('items', [])
        for item in items_list:
            qty = int(item.get('quantity', 1))
            rate = float(item.get('rate', 0.0))
            gross = qty * rate
            total_accrued += gross
            
            table_data.append([
                item.get('description', 'Services Rendered'),
                str(qty),
                f"${rate:.2f}",
                f"${gross:.2f}"
            ])
            
        table_data.append(["", "", "AGGREGATE TOTAL:", f"${total_accrued:.2f}"])
        
        # Items and ledger layout configuration
        col_widths = [printable_width * 0.55, printable_width * 0.12, printable_width * 0.15, printable_width * 0.18]
        items_table = Table(table_data, colWidths=col_widths)
        items_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), GOOGLE_BLUE),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (1, 0), (-1, -1), 'RIGHT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('LINEBELOW', (0, 0), (-1, -2), 0.5, colors.Color(0.9, 0.9, 0.9)),
            ('BACKGROUND', (0, -1), (-1, -1), GOOGLE_GREEN),
            ('TEXTCOLOR', (0, -1), (-1, -1), colors.white),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ]))
        story.append(items_table)
        story.append(Spacer(1, 20))
        
        # Optional metadata annotations handling
        if invoice_payload.get('notes'):
            notes_header = Paragraph("<b>MEMORANDUM & SYSTEM NOTES:</b>", styles['Normal'])
            notes_body = Paragraph(str(invoice_payload['notes']), styles['Normal'])
            story.extend([notes_header, Spacer(1, 5), notes_body])
            
        # Complete rendering pipeline orchestration
        doc.build(story)
        return f"Invoice PDF generated successfully at local filesystem target location: {filepath}"
        
    except Exception as error_context:
        return f"Error executing native PDF transformation layers: {str(error_context)}"


# --- AGENT WRAPPING DEFINITIONS ---
MODEL_NAME = "gemini-2.5-flash"

invoice_generator_agent = Agent(
    model=MODEL_NAME,
    name='invoice_generator_agent',
    instruction=(
        "You are an specialized billing operational assistant agent framework. When users prompt you "
        "to synthesize an invoice ledger, cross-examine incoming user data attributes to parse details "
        "into strict schema models. Do not prompt for random token identifiers like an invoice reference index number or dates "
        "manually, as these components construct systematically on system execution runtime layers. "
        "Once required information parameters map cleanly, trigger the `generate_invoice_pdf` function."
    ),
    description="Captures structural client data parameters via contextual parsing streams to generate invoice sheets.",
    tools=[generate_invoice_pdf],
)

# Session tracking initialization block setup 
session_service = InMemorySessionService()
session = session_service.create_session(app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID)
runner = Runner(agent=invoice_generator_agent, app_name=APP_NAME, session_service=session_service)

def call_agent(query: str):
    content = types.Content(role='user', parts=[types.Part(text=query)])
    events = runner.run(user_id=USER_ID, session_id=SESSION_ID, new_message=content)

    for event in events:
        if event.is_final_response():
            final_response = event.content.parts[0].text
            print("Agent Execution Flow Output Layer: \n", final_response)

# Execute verification task run loop
call_agent(
    "Create an invoice for ABC Company with the following details: Customer: John Smith, "
    "Address: 456 Oak Street, City: Springfield, State: IL, Zip: 62701, Email: john.smith@email.com. "
    "Invoice payload specifications: Web Development Services, 20 hours at $85/unit hour rate."
)
root_agent = invoice_generator_agent
