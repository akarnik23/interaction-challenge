#!/usr/bin/env python3
"""
Email Document Assistant - MCP Server
Automatically fills PDF forms from incoming emails
"""
import os
import httpx
import pymupdf  # PyMuPDF
from fastmcp import FastMCP
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
load_dotenv()

# Initialize Langfuse for observability
os.environ["LANGFUSE_SECRET_KEY"] = os.getenv("LANGFUSE_SECRET_KEY", "")
os.environ["LANGFUSE_PUBLIC_KEY"] = os.getenv("LANGFUSE_PUBLIC_KEY", "")
os.environ["LANGFUSE_HOST"] = os.getenv("LANGFUSE_BASE_URL", "https://us.cloud.langfuse.com")

# Initialize MCP server
mcp = FastMCP("Email Document Assistant")

# Simple working directory
WORK_DIR = Path("/tmp/mcp_pdfs")
WORK_DIR.mkdir(exist_ok=True)


def _download_pdf(url: str) -> dict:
    """Download a PDF file from a URL."""
    try:
        response = httpx.get(url, follow_redirects=True, timeout=30.0)
        response.raise_for_status()

        filename = url.split("/")[-1] or "downloaded.pdf"
        if not filename.endswith(".pdf"):
            filename += ".pdf"

        filepath = WORK_DIR / filename
        filepath.write_bytes(response.content)

        return {
            "status": "success",
            "message": f"Downloaded PDF to {filepath}",
            "filepath": str(filepath),
            "size_bytes": len(response.content)
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to download PDF: {str(e)}"}


def _parse_email(email_json_url: str) -> dict:
    """Parse an email JSON file and extract PDF attachment URLs."""
    try:
        import re
        response = httpx.get(email_json_url, timeout=30.0)
        response.raise_for_status()
        email_data = response.json()

        sender = email_data.get("sender", {})
        subject = email_data.get("subject", "")

        pdf_urls = []
        payload = email_data.get("payload", {})
        parts = payload.get("parts", [])

        for part in parts:
            filename = part.get("filename", "")
            if filename.endswith(".pdf"):
                if "drive.google.com" in str(part):
                    part_str = str(part)
                    drive_links = re.findall(r'https://drive\.google\.com/[^\s\'"]+', part_str)
                    pdf_urls.extend(drive_links)

        return {
            "status": "success",
            "sender": sender.get("email", ""),
            "subject": subject,
            "pdf_count": len(pdf_urls),
            "pdf_urls": pdf_urls
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to parse email: {str(e)}"}


def _extract_form_fields(pdf_path: str) -> dict:
    """Extract all form fields from a PDF."""
    try:
        doc = pymupdf.open(pdf_path)
        fields = {}

        for page_num in range(len(doc)):
            page = doc[page_num]
            widgets = page.widgets()
            if widgets:
                for widget in widgets:
                    fields[widget.field_name] = {
                        "type": widget.field_type_string,
                        "value": widget.field_value or "",
                        "page": page_num
                    }
        doc.close()

        return {
            "status": "success",
            "filepath": pdf_path,
            "num_fields": len(fields),
            "fields": fields
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to extract form fields: {str(e)}"}


def _generate_form_values(field_names: list) -> dict:
    """Use OpenAI to generate realistic fill values for form fields."""
    import json
    try:
        from openai import OpenAI
        from langfuse.openai import openai as langfuse_openai

        # Initialize OpenAI client with Langfuse observability
        client = langfuse_openai.OpenAI(
            api_key=os.getenv("OPENAI_API_KEY")
        )

        prompt = f"""Generate realistic sample data for a form with the following fields.

IMPORTANT: Use these EXACT field names as JSON keys (preserve spacing, capitalization):
{chr(10).join(f'"{name}"' for name in field_names)}

CRITICAL RULES:
- Fill EVERY SINGLE field in the list above - do not skip any
- For date fields (Month, Day, Year): use 2-digit format (01-12, 01-31, 20-25)
- For dates with full format (like "Sell date 1"): use MM/DD/YYYY format
- For State fields: use 2-letter codes like "CA", "NY", "TX"
- For zip codes: use 5-digit format like "90210" or "12345"
- Use realistic but fake names, addresses, phone numbers
- For fields ending with " 2": Only fill if there are genuinely 2 different people/items, otherwise leave empty ("")

Return ONLY a JSON object with ALL the field names above filled.
Example: {{"Name": "John Smith", "State": "CA", "Month": "03", "Day": "15", "Zip": "90210", "Date": "03/15/2025"}}"""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            timeout=20.0
        )

        values = json.loads(response.choices[0].message.content)
        return {"status": "success", "generated_values": values, "fields_filled": len(values)}
    except Exception as e:
        return {"status": "error", "message": f"Failed to generate values: {str(e)}"}


def _fill_pdf_form(pdf_path: str, field_values: dict) -> dict:
    """Fill a PDF form with the provided field values."""
    import base64
    try:
        doc = pymupdf.open(pdf_path)
        processed_values = {}

        month_map = {
            "january": "01", "february": "02", "march": "03", "april": "04",
            "may": "05", "june": "06", "july": "07", "august": "08",
            "september": "09", "october": "10", "november": "11", "december": "12"
        }

        for key, value in field_values.items():
            if "month" in key.lower() and str(value).lower() in month_map:
                processed_values[key] = month_map[str(value).lower()]
            else:
                processed_values[key] = value

        # Handle year split
        current_year = "2025"
        for key, value in processed_values.items():
            if "yr" in key.lower() or "year" in key.lower():
                if len(str(value)) == 4 and str(value).isdigit():
                    current_year = str(value)
                    break

        processed_values["Year-1"] = current_year[0]
        processed_values["Year-2"] = current_year[1]
        processed_values["Year-3"] = current_year[2]
        processed_values["Year-4"] = current_year[3]

        # Defaults
        defaults = {
            "Month": "03", "Day": "15",
            "Seller State": "CA", "Buyer State": "CA",
            "Sell zip": "90210", "Buyer zip": "90210",
            "Sell date 1": "03/15/2025", "Sell date 2": "",
        }
        for field, default_value in defaults.items():
            if field not in processed_values or not processed_values.get(field):
                processed_values[field] = default_value

        # Clear duplicate seller row
        first_seller = processed_values.get("Print seller's name", "") or processed_values.get("Seller print name 1", "")
        second_seller = processed_values.get("Seller print name 2", "")
        if not second_seller or second_seller == first_seller:
            for key in list(processed_values.keys()):
                if key.endswith(" 2"):
                    processed_values[key] = ""

        # Fill form
        fields_filled = 0
        for page_num in range(len(doc)):
            page = doc[page_num]
            for widget in page.widgets():
                if widget.field_name in processed_values:
                    widget.field_value = str(processed_values[widget.field_name])
                    widget.update()
                    fields_filled += 1

        output_path = str(Path(pdf_path).with_stem(Path(pdf_path).stem + "_filled"))
        doc.save(output_path)
        doc.close()

        # Encode as base64
        with open(output_path, 'rb') as f:
            pdf_base64 = base64.b64encode(f.read()).decode('utf-8')

        return {
            "status": "success",
            "message": f"Filled {fields_filled} fields",
            "output_path": output_path,
            "fields_filled": fields_filled,
            "pdf_base64": pdf_base64,
            "download_instructions": "Decode pdf_base64 from base64 and save as .pdf"
        }
    except Exception as e:
        return {"status": "error", "message": f"Failed to fill PDF: {str(e)}"}


def _process_email_automation(email_json_url: str) -> dict:
    """Complete end-to-end: Parse email, download PDF, fill forms with AI, return filled PDF."""
    try:
        # Step 1: Parse email
        email_result = _parse_email(email_json_url)
        if email_result["status"] != "success" or not email_result.get("pdf_urls"):
            return {"status": "error", "message": "No PDF found in email"}

        pdf_url = email_result["pdf_urls"][0]

        # Step 2: Download PDF
        download_result = _download_pdf(pdf_url)
        if download_result["status"] != "success":
            return download_result

        pdf_path = download_result["filepath"]

        # Step 3: Extract form fields
        extract_result = _extract_form_fields(pdf_path)
        if extract_result["status"] != "success":
            return extract_result

        if extract_result["num_fields"] == 0:
            return {"status": "info", "message": "PDF has no fillable form fields"}

        # Step 4: Generate values with AI
        excluded_patterns = ["Year-1", "Year-2", "Year-3", "Year-4"]
        field_names = [name for name in extract_result["fields"].keys()
                       if extract_result["fields"][name]["type"] != "Button"
                       and name not in excluded_patterns]

        gen_result = _generate_form_values(field_names)
        if gen_result["status"] != "success":
            return gen_result

        # Step 5: Fill PDF
        fill_result = _fill_pdf_form(pdf_path, gen_result["generated_values"])

        return {
            "status": "success",
            "email_subject": email_result["subject"],
            "original_pdf": pdf_path,
            "filled_pdf": fill_result["output_path"],
            "fields_filled": fill_result["fields_filled"],
            "pdf_base64": fill_result.get("pdf_base64", ""),
            "download_instructions": fill_result.get("download_instructions", ""),
            "message": f"✅ Successfully filled {fill_result['fields_filled']} fields!"
        }
    except Exception as e:
        return {"status": "error", "message": f"Processing failed: {str(e)}"}


@mcp.tool(description="Download a PDF from a URL and save it locally")
def download_pdf(url: str) -> dict:
    """Download a PDF file from a URL."""
    return _download_pdf(url)


@mcp.tool(description="Parse email JSON and extract PDF attachment URLs")
def parse_email(email_json_url: str) -> dict:
    """Parse an email JSON file and extract PDF attachment URLs."""
    return _parse_email(email_json_url)


@mcp.tool(description="Extract form fields from a PDF file")
def extract_form_fields(pdf_path: str) -> dict:
    """Extract all form fields from a PDF."""
    return _extract_form_fields(pdf_path)


@mcp.tool(description="Use AI to generate realistic values for PDF form fields")
def generate_form_values(field_names: list) -> dict:
    """Use OpenAI to generate realistic fill values for form fields."""
    return _generate_form_values(field_names)


@mcp.tool(description="Fill a PDF form with provided values and save result")
def fill_pdf_form(pdf_path: str, field_values: dict) -> dict:
    """Fill a PDF form with the provided field values."""
    return _fill_pdf_form(pdf_path, field_values)


@mcp.tool(description="Process email with PDF form - complete automation from email to filled PDF")
def process_email_automation(email_json_url: str) -> dict:
    """Complete end-to-end: Parse email, download PDF, fill forms with AI, return filled PDF."""
    return _process_email_automation(email_json_url)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    host = "0.0.0.0"

    print(f"Starting Email Document Assistant MCP server on {host}:{port}")
    print(f"Working directory: {WORK_DIR}")

    mcp.run(
        transport="http",
        host=host,
        port=port,
        stateless_http=True
    )
