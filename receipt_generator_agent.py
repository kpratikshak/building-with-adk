"""
Invoice Generator Agent
============================
Generates a polished PDF invoice from user-supplied billing and item data.
  - Actually collects user input (name, address, date, order items, etc.)
    instead of firing a single hardcoded `call_agent(...)` on import.
  - Validates input (missing name, non-numeric quantity/rate, empty items)
    and returns clear errors instead of crashing or silently defaulting.
  - Respects a user-supplied invoice number / date / due date instead of
    always overwriting them.
  - Removes hardcoded personal branding (GitHub/LinkedIn links) in favor of
    environment-configurable company name and footer text.
  - Writes PDFs to a dedicated `invoices/` output folder instead of cwd.
  - Adds logging and type hints for maintainability.
"""

import json
import logging
import os
import random
from datetime import datetime, timedelta

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("invoice_agent")

# ---------------------------------------------------------------------------
# Branding / configuration (override via environment variables, no more
# hardcoded personal links baked into every invoice)
# ---------------------------------------------------------------------------
COMPANY_NAME = os.environ.get("INVOICE_COMPANY_NAME", "Your Company")
COMPANY_FOOTER_LINES = [
    line.strip() for line in os.environ.get("INVOICE_FOOTER", "").split("|") if line.strip()
] or ["Thank you for your business."]

BRAND_BLUE = colors.Color(0.259, 0.522, 0.957)
BRAND_GREEN = colors.Color(0.208, 0.682, 0.325)
BRAND_GREY = colors.Color(0.376, 0.376, 0.376)
LIGHT_GREY = colors.Color(0.97, 0.97, 0.97)
BORDER_GREY = colors.Color(0.90, 0.90, 0.90)

OUTPUT_DIR = os.environ.get("INVOICE_OUTPUT_DIR", os.path.join(os.getcwd(), "invoices"))
os.makedirs(OUTPUT_DIR, exist_ok=True)

APP_NAME = "invoice_app"
USER_ID = "1234"
SESSION_ID = "session1234"


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------
class InvoiceDataError(ValueError):
    """Raised when invoice input data is missing or malformed."""


def _generate_invoice_number() -> str:
    return "".join(str(random.randint(0, 9)) for _ in range(10))


def _validate_bill_to(bill_to: dict) -> dict:
    name = str(bill_to.get("name", "")).strip()
    if not name:
        raise InvoiceDataError("Customer name is required.")
    return {
        "name": name,
        "address": str(bill_to.get("address", "")).strip(),
        "city": str(bill_to.get("city", "")).strip(),
        "state": str(bill_to.get("state", "")).strip(),
        "zip": str(bill_to.get("zip", "")).strip(),
        "email": str(bill_to.get("email", "")).strip(),
    }


def _parse_items(raw_items: list) -> list:
    if not raw_items:
        raise InvoiceDataError("At least one item is required to generate an invoice.")

    parsed = []
    for idx, item in enumerate(raw_items, start=1):
        description = str(item.get("description", "")).strip()
        if not description:
            raise InvoiceDataError(f"Item {idx} is missing a description.")
        try:
            quantity = float(item.get("quantity", 1))
            rate = float(item.get("rate", 0))
        except (TypeError, ValueError):
            raise InvoiceDataError(f"Item {idx} has a non-numeric quantity or rate.")
        if quantity <= 0 or rate < 0:
            raise InvoiceDataError(f"Item {idx} has an invalid quantity or rate.")
        parsed.append({
            "description": description,
            "quantity": quantity,
            "rate": rate,
            "amount": round(quantity * rate, 2),
        })
    return parsed


def _parse_date(value: str, fallback: datetime) -> tuple[str, datetime]:
    if not value:
        return fallback.strftime("%Y-%m-%d"), fallback
    try:
        parsed = datetime.strptime(value, "%Y-%m-%d")
        return value, parsed
    except ValueError:
        logger.warning("Could not parse date %r, falling back to %s", value, fallback.date())
        return fallback.strftime("%Y-%m-%d"), fallback


# ---------------------------------------------------------------------------
# Header / footer drawn directly on the canvas (replaces the old
# Drawing + negative-Spacer overlay hack)
# ---------------------------------------------------------------------------
def _draw_header_footer(canvas, doc):
    canvas.saveState()
    width, height = letter

    canvas.setFillColor(BRAND_BLUE)
    canvas.roundRect(0, height - 90, width, 90, 12, fill=1, stroke=0)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica-Bold", 20)
    canvas.drawCentredString(width / 2, height - 42, COMPANY_NAME)
    canvas.setFont("Helvetica-Bold", 15)
    canvas.drawCentredString(width / 2, height - 68, "INVOICE")

    canvas.setFillColor(BRAND_GREY)
    canvas.roundRect(0, 0, width, 50, 12, fill=1, stroke=0)
    canvas.setFillColor(colors.white)
    canvas.setFont("Helvetica", 9)
    y = 32
    for line in COMPANY_FOOTER_LINES[:2]:
        canvas.drawCentredString(width / 2, y, line)
        y -= 12

    canvas.restoreState()


# ---------------------------------------------------------------------------
# Core PDF generation (this is the ADK tool function)
# ---------------------------------------------------------------------------
def generate_invoice_pdf(invoice_data: str) -> str:
    """
    Generates an invoice PDF from the provided invoice data.

    Args:
        invoice_data (str): JSON string with the shape:
            {
              "bill_to": {"name", "address", "city", "state", "zip", "email"?},
              "items": [{"description", "quantity", "rate"}, ...],
              "invoice_number"?: str,   # auto-generated if omitted
              "date"?: "YYYY-MM-DD",    # defaults to today
              "due_date"?: "YYYY-MM-DD",# defaults to date + 30 days
              "notes"?: str
            }

    Returns:
        str: Path to the generated PDF, or an "Error ..." message.
    """
    try:
        data = json.loads(invoice_data) if isinstance(invoice_data, str) else invoice_data
    except json.JSONDecodeError as exc:
        return f"Error generating invoice PDF: invalid JSON ({exc})"

    try:
        bill_to = _validate_bill_to(data.get("bill_to", {}))
        items = _parse_items(data.get("items", []))
    except InvoiceDataError as exc:
        return f"Error generating invoice PDF: {exc}"

    invoice_number = str(data.get("invoice_number") or _generate_invoice_number())
    date_str, invoice_date = _parse_date(data.get("date"), datetime.now())
    due_date_str, _ = _parse_date(data.get("due_date"), invoice_date + timedelta(days=30))
    notes = str(data.get("notes", "")).strip()

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"invoice_{invoice_number}_{timestamp}.pdf"
    filepath = os.path.join(OUTPUT_DIR, filename)

    styles = getSampleStyleSheet()
    story = [Spacer(1, 70)]  # clears the fixed header band

    meta_table = Table(
        [
            ["Invoice Number:", invoice_number, "Date:", date_str],
            ["Due Date:", due_date_str, "", ""],
        ],
        colWidths=[1.2 * inch, 1.8 * inch, 1 * inch, 1.5 * inch],
    )
    meta_table.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("TEXTCOLOR", (0, 0), (-1, -1), BRAND_GREY),
        ("ALIGN", (0, 0), (0, -1), "RIGHT"),
        ("ALIGN", (2, 0), (2, -1), "RIGHT"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 16))

    section_style = ParagraphStyle(
        "Section", parent=styles["Heading2"], textColor=BRAND_BLUE, fontSize=13,
    )

    story.append(Paragraph("BILL TO", section_style))
    address_lines = [bill_to["name"]]
    if bill_to["address"]:
        address_lines.append(bill_to["address"])
    city_line = ", ".join(p for p in [bill_to["city"], bill_to["state"]] if p)
    if bill_to["zip"]:
        city_line = f"{city_line} {bill_to['zip']}".strip()
    if city_line:
        address_lines.append(city_line)
    if bill_to["email"]:
        address_lines.append(bill_to["email"])
    story.append(Paragraph("<br/>".join(address_lines), styles["Normal"]))
    story.append(Spacer(1, 16))

    story.append(Paragraph("ITEMS", section_style))
    table_data = [["Description", "Quantity", "Rate", "Amount"]]
    total = 0.0
    for item in items:
        total += item["amount"]
        table_data.append([
            item["description"],
            f"{item['quantity']:g}",
            f"${item['rate']:.2f}",
            f"${item['amount']:.2f}",
        ])
    table_data.append(["", "", "TOTAL", f"${total:.2f}"])

    items_table = Table(table_data, colWidths=[3 * inch, 1 * inch, 1.2 * inch, 1.2 * inch])
    items_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), BRAND_BLUE),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("ALIGN", (0, 0), (0, -1), "LEFT"),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 10),
        ("TOPPADDING", (0, 1), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 6),
        ("ROWBACKGROUNDS", (0, 1), (-1, -2), [LIGHT_GREY, colors.white]),
        ("BACKGROUND", (0, -1), (-1, -1), BRAND_GREEN),
        ("TEXTCOLOR", (0, -1), (-1, -1), colors.white),
        ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.5, BORDER_GREY),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 16))

    if notes:
        story.append(Paragraph("NOTES", section_style))
        story.append(Paragraph(notes, styles["Normal"]))

    doc = SimpleDocTemplate(
        filepath,
        pagesize=letter,
        topMargin=1 * inch,
        bottomMargin=0.8 * inch,
        leftMargin=0.75 * inch,
        rightMargin=0.75 * inch,
    )
    doc.build(story, onFirstPage=_draw_header_footer, onLaterPages=_draw_header_footer)

    logger.info("Invoice %s generated at %s", invoice_number, filepath)
    return f"Invoice PDF generated successfully: {filepath}"


# ---------------------------------------------------------------------------
# ADK Agent definition
# ---------------------------------------------------------------------------
invoice_generator_agent = Agent(
    model="gemini-2.0-flash",
    name="invoice_generator_agent",
    instruction="""You are an invoice generator agent. When a user requests to create an invoice, collect:

1. Billing information: customer name (required), address, city, state, zip.
   Email is optional - only include it if the user provides it.
2. Line items: description, quantity, and rate for each item (at least one item is required).
3. Optional: a custom invoice number, invoice date, due date, and notes.
   - If the user doesn't give an invoice number, one is auto-generated.
   - If the user doesn't give a date, today's date is used.
   - If the user doesn't give a due date, it defaults to 30 days after the invoice date.

Once you have the required billing and item information, format everything as a single JSON
string matching this shape and call generate_invoice_pdf with it:

{
    "bill_to": {
        "name": "John Doe",
        "address": "123 Main St",
        "city": "Anytown",
        "state": "ST",
        "zip": "12345",
        "email": "optional@example.com"
    },
    "items": [
        {"description": "Web Development Services", "quantity": 10, "rate": 75.00}
    ],
    "invoice_number": "optional custom number",
    "date": "optional YYYY-MM-DD",
    "due_date": "optional YYYY-MM-DD",
    "notes": "optional notes"
}

If required information (customer name, or at least one item) is missing, ask the user for it
before calling the tool. Report the resulting file path back to the user, or relay any error
message returned by the tool so the user knows what to fix.""",
    description=(
        "This agent specializes in generating professional invoices in PDF format. "
        "It collects invoice details, billing information, and line items to create "
        "formatted PDF invoices saved locally."
    ),
    tools=[generate_invoice_pdf],
)

root_agent = invoice_generator_agent


# ---------------------------------------------------------------------------
# Direct interactive CLI path (no LLM round-trip required) — prompts the
# user for Name, Address, Date, Order Items, etc. and builds the PDF.
# ---------------------------------------------------------------------------
def _prompt(label: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    value = input(f"{label}{suffix}: ").strip()
    return value or default


def collect_invoice_data_interactively() -> dict:
    print("\n=== New Invoice ===")
    bill_to = {
        "name": _prompt("Customer name"),
        "address": _prompt("Address"),
        "city": _prompt("City"),
        "state": _prompt("State"),
        "zip": _prompt("ZIP"),
        "email": _prompt("Email (optional)"),
    }

    items = []
    print("\nEnter order items (leave description blank to stop):")
    while True:
        description = _prompt(f"  Item {len(items) + 1} description")
        if not description:
            break
        quantity = _prompt("    Quantity", "1")
        rate = _prompt("    Rate", "0")
        items.append({"description": description, "quantity": quantity, "rate": rate})

    invoice_number = _prompt("\nInvoice number (blank = auto-generate)")
    date = _prompt("Invoice date YYYY-MM-DD (blank = today)")
    due_date = _prompt("Due date YYYY-MM-DD (blank = date + 30 days)")
    notes = _prompt("Notes (optional)")

    return {
        "bill_to": bill_to,
        "items": items,
        "invoice_number": invoice_number,
        "date": date,
        "due_date": due_date,
        "notes": notes,
    }


def run_cli() -> None:
    data = collect_invoice_data_interactively()
    result = generate_invoice_pdf(json.dumps(data))
    print(f"\n{result}")


# ---------------------------------------------------------------------------
# Optional: drive the agent conversationally instead of the direct CLI path
# ---------------------------------------------------------------------------
def run_agent_query(query: str) -> None:
    session_service = InMemorySessionService()
    session_service.create_session(app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID)
    runner = Runner(agent=invoice_generator_agent, app_name=APP_NAME, session_service=session_service)

    content = types.Content(role="user", parts=[types.Part(text=query)])
    for event in runner.run(user_id=USER_ID, session_id=SESSION_ID, new_message=content):
        if event.is_final_response():
            print("Agent Response:", event.content.parts[0].text)


if __name__ == "__main__":
    # Direct, dependency-free path: prompts for Name/Address/Date/Items and
    # writes the PDF immediately. Swap this for run_agent_query(...) if you
    # want the LLM to drive the conversation instead.
    run_cli()
