# Email Document Assistant - MCP Server

Automatically fills PDF forms from incoming emails using AI. Built with [FastMCP](https://gofastmcp.com) for Model Context Protocol integration.

## Overview

This MCP server automates the complete workflow of:
1. **Parsing emails** with PDF attachments
2. **Downloading PDFs** from attachment URLs
3. **Extracting form fields** from PDF forms
4. **Generating realistic data** with OpenAI GPT-4o-mini
5. **Filling PDF forms** with smart date/year handling
6. **Returning filled PDFs** with base64 encoding

Perfect for integration with AI assistants like Claude (via Poke, Claude Desktop, or custom MCP clients).

## Features

- **End-to-end automation**: Single tool call processes entire workflow
- **Smart form filling**: Handles split year fields, month name conversion, duplicate seller detection
- **AI-powered data generation**: Uses OpenAI to generate realistic form values
- **Langfuse observability**: Tracks all AI calls for monitoring and debugging
- **Base64 PDF encoding**: Returns filled PDFs that can be downloaded by clients
- **Generic form support**: Works with any PDF form type, not just Bill of Sale

## Quick Start

### 1. Install Dependencies

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configure Environment Variables

Create a `.env` file:

```bash
# OpenAI API (required for form data generation)
OPENAI_API_KEY=sk-...

# Langfuse Observability (optional but recommended)
LANGFUSE_SECRET_KEY=sk-lf-...
LANGFUSE_PUBLIC_KEY=pk-lf-...
LANGFUSE_BASE_URL=https://us.cloud.langfuse.com
```

### 3. Run the Server

```bash
python src/server.py
```

The server will start on `http://0.0.0.0:8000/mcp`

### 4. Connect with Poke or Claude Desktop

See [Integration](#integration-with-poke--claude-desktop) section below for setup instructions.

## MCP Tools

The server exposes 6 MCP tools:

### `process_email_automation(email_json_url: str)`
**Complete end-to-end automation** - recommended for most use cases.

```json
{
  "email_json_url": "https://interaction.co/assets/easy-pdf.json"
}
```

Returns:
- `status`: "success" or "error"
- `email_subject`: Email subject line
- `filled_pdf`: Path to filled PDF
- `fields_filled`: Number of fields filled
- `pdf_base64`: Base64-encoded PDF for download
- `message`: Success message

### Individual Tools

For more granular control, use these tools separately:

1. **`parse_email(email_json_url)`** - Extract PDF URLs from email JSON
2. **`download_pdf(url)`** - Download PDF from URL
3. **`extract_form_fields(pdf_path)`** - Get all form fields from PDF
4. **`generate_form_values(field_names)`** - Generate realistic data with AI
5. **`fill_pdf_form(pdf_path, field_values)`** - Fill PDF with provided values

## Integration with Poke / Claude Desktop

### Option 1: Local Connection (Claude Desktop)

Add to `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "email-document-assistant": {
      "url": "http://localhost:8000/mcp"
    }
  }
}
```

### Option 2: Remote Connection (Poke via Localtunnel)

```bash
# Terminal 1: Start the server
python src/server.py

# Terminal 2: Create tunnel
lt --port 8000 --subdomain your-subdomain
```

Then add `https://your-subdomain.loca.lt/mcp` to Poke's integrations page.

### Example Prompts for AI Assistants

```
"Process the email at https://interaction.co/assets/easy-pdf.json and fill the PDF form"

"Using the email-document-assistant, parse the email, download the PDF, and fill it with realistic data"
```

## How It Works

### Smart Form Filling Logic

1. **Month Normalization**: Converts month names ("January") to 2-digit format ("01")
2. **Year Splitting**: Splits 4-digit years into individual digit fields (2025 → |2|0|2|5|)
3. **Duplicate Seller Detection**: Clears second seller row if same as first seller
4. **Comprehensive Defaults**: Provides fallback values for commonly missed fields
5. **Base64 Encoding**: Returns PDF as base64 for easy client-side download

### AI Prompt Engineering

The system uses detailed prompts to ensure the AI:
- Uses **exact field names** (preserves spacing, capitalization)
- Fills **every single field** without skipping
- Generates **realistic but fake** data
- Follows **specific formats** for dates, states, zip codes
- Intelligently handles **multi-entity fields** (e.g., multiple sellers)

## Langfuse Observability

All OpenAI API calls are automatically tracked in Langfuse:

1. Visit https://us.cloud.langfuse.com
2. Log in with your Langfuse account
3. View traces, latencies, token usage, and costs
4. Debug AI generation issues with full prompt/response logs

## Project Structure

```
mcp-server-template/
├── src/
│   └── server.py          # Main MCP server with all tools
├── requirements.txt       # Python dependencies
├── .env                   # API keys (create this)
└── README.md             # This file
```

## Sample Data

Two test emails are available:

- **Easy PDF**: `https://interaction.co/assets/easy-pdf.json` - Fillable form with 35 fields
- **Hard PDF**: `https://interaction.co/assets/hard-pdf.json` - Scanned image (no fillable fields)

The server handles fillable PDFs. Scanned PDFs would require OCR/vision AI (future enhancement).

## Technical Details

### Dependencies

- **FastMCP**: MCP server framework with HTTP transport
- **PyMuPDF**: PDF manipulation and form field extraction
- **OpenAI**: AI-powered form data generation
- **Langfuse**: LLM observability and tracing
- **httpx**: Async HTTP client for downloads

### Performance

- **Local execution**: ~15-20 seconds end-to-end
- **Remote (Poke + localtunnel)**: ~4 minutes due to network overhead and MCP protocol
- **Optimization**: Use `process_email_automation` for single-call execution

### Limitations

- **Scanned PDFs**: Only works with fillable PDF forms, not scanned images
- **Network latency**: Remote integrations have overhead from multiple HTTP roundtrips
- **Base64 size**: Large PDFs may hit response size limits in some MCP clients

## Future Enhancements

- [ ] OCR + Vision AI for scanned PDFs
- [ ] Direct file upload/download endpoints
- [ ] Support for user-provided context (integrate with AI assistant knowledge)
- [ ] Multi-language form support
- [ ] Batch processing multiple emails
- [ ] Custom validation rules

## License

MIT

## Credits

Built for The Interaction Company technical challenge.

## Support

For issues or questions, check the [FastMCP documentation](https://gofastmcp.com) or [Langfuse docs](https://langfuse.com/docs).
