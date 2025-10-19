import os
import re
import json
import tempfile
from pathlib import Path
import gradio as gr
from mistralai import Mistral
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from mistralai.extra import response_format_from_pydantic_model
from google import genai

# Load environment variables
load_dotenv()

# Initialize Mistral client
api_key = os.environ.get("MISTRAL_API_KEY")
if not api_key:
    raise ValueError("MISTRAL_API_KEY environment variable not set")

client = Mistral(api_key=api_key)

# Initialize Gemini client (optional)
# New SDK automatically picks up GEMINI_API_KEY or GOOGLE_API_KEY from environment
gemini_available = False
google_client = None
google_api_key = os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")
if google_api_key:
    try:
        google_client = genai.Client(api_key=google_api_key)
        gemini_available = True
    except Exception:
        gemini_available = False


# Define Pydantic model for image descriptions
class ImageDescription(BaseModel):
    description: str = Field(..., description="A detailed description of the image content")


def upload_pdf_to_mistral(pdf_file):
    """Upload a PDF file to Mistral and return the signed URL."""
    # Read the file content
    with open(pdf_file, "rb") as f:
        file_content = f.read()

    # Get the filename
    filename = Path(pdf_file).name

    # Upload to Mistral
    uploaded_pdf = client.files.upload(
        file={
            "file_name": filename,
            "content": file_content,
        },
        purpose="ocr"
    )

    # Get signed URL
    signed_url = client.files.get_signed_url(file_id=uploaded_pdf.id)
    return signed_url.url


def cleanup_markdown_with_gemini(markdown_content):
    """Use Gemini to clean up and format the markdown content."""
    if not gemini_available or not google_client:
        return markdown_content

    prompt = """You are a markdown formatting expert. Your task is to clean up and improve the formatting of OCR-extracted markdown content from a PDF document.

Please perform the following cleanup tasks:

1. **Remove page markers**: Delete all `<!-- Page X -->` comment tags
2. **Fix paragraph spacing**: If text appears to run from one page to another mid-sentence or mid-paragraph, merge them together properly without extra line breaks
3. **Format Tables of Contents**: Convert any table of contents sections (with dots/periods like "Section Name ..... Page Number") into proper markdown tables with columns for "Section" and "Page"
4. **Format Lists of Tables/Figures**: Convert any "List of Tables" or "List of Figures" sections (with dots/periods) into proper markdown tables
5. **Improve table formatting**: Ensure all markdown tables have proper spacing and are human-readable
6. **Preserve structure**: Keep all headings, lists, and other formatting intact
7. **Preserve content**: Do not remove, summarize, or change any actual content - only improve formatting
8. **Format Abbreviations**: If there is a section for abbreviations, it is most likely this should be presented as a table
9. **Format Tables**: Tables should have human readable spacing.

Return ONLY the cleaned markdown content without any explanations or commentary. 

You do not need to wrap the entire text in ```markdown tags.

Here is the markdown to clean up:

"""

    try:
        response = google_client.models.generate_content(
            model='gemini-2.0-flash-exp',
            contents=prompt + markdown_content
        )
        return response.text
    except Exception:
        # If Gemini fails, return original markdown
        return markdown_content


def process_pdf_ocr(pdf_file, include_image_descriptions=True, cleanup_with_gemini=False, progress=gr.Progress()):
    """Process PDF file with Mistral OCR and return markdown content."""
    try:
        progress(0, desc="Uploading PDF to Mistral...")

        # Upload PDF and get URL
        pdf_url = upload_pdf_to_mistral(pdf_file)

        progress(0.3, desc="Processing OCR...")

        # Process OCR with optional image descriptions
        ocr_params = {
            "model": "mistral-ocr-latest",
            "document": {
                "type": "document_url",
                "document_url": pdf_url,
            },
        }

        # Add bbox annotation format if image descriptions are enabled
        if include_image_descriptions:
            ocr_params["bbox_annotation_format"] = response_format_from_pydantic_model(ImageDescription)

        ocr_response = client.ocr.process(**ocr_params)

        progress(0.7, desc="Generating markdown...")

        # Combine all pages into a single markdown string
        markdown_content = ""
        for idx, page in enumerate(ocr_response.pages, 1):
            markdown_content += f"<!-- Page {idx} -->\n\n"
            page_markdown = page.markdown

            # Replace ![image] markers with descriptions if image annotations are available
            if include_image_descriptions and hasattr(page, 'images') and page.images:
                for image in page.images:
                    # The image_annotation is a JSON string, parse it
                    if hasattr(image, 'image_annotation') and image.image_annotation:
                        try:
                            annotation_dict = json.loads(image.image_annotation)
                            description = annotation_dict.get('description', '')
                            if description:
                                # Find and replace the first ![...] pattern with the description
                                page_markdown = re.sub(
                                    r'!\[.*?\]\(.*?\)',
                                    description,
                                    page_markdown,
                                    count=1
                                )
                        except json.JSONDecodeError:
                            # Skip this image if annotation parsing fails
                            continue

            markdown_content += page_markdown
            markdown_content += "\n\n"

        # Clean up markdown with Gemini if enabled
        if cleanup_with_gemini and gemini_available:
            progress(0.9, desc="Cleaning up markdown with Gemini...")
            markdown_content = cleanup_markdown_with_gemini(markdown_content)

        progress(1.0, desc="Complete!")

        # Save to a temporary markdown file for download
        with tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False, encoding='utf-8') as f:
            f.write(markdown_content)
            temp_path = f.name

        return markdown_content, temp_path, f"✓ Successfully processed {len(ocr_response.pages)} page(s)"

    except Exception as e:
        error_msg = f"✗ Error processing PDF: {str(e)}"
        return "", None, error_msg


# Create Gradio interface
with gr.Blocks(title="Mistral OCR - PDF to Markdown") as demo:
    gr.Markdown("# Mistral OCR: PDF to Markdown Converter")
    gr.Markdown("Upload a PDF file to convert it to Markdown using Mistral's OCR API.")

    with gr.Row():
        with gr.Column():
            pdf_input = gr.File(
                label="Upload PDF",
                file_types=[".pdf"],
                type="filepath"
            )
            image_desc_toggle = gr.Checkbox(
                label="Include image descriptions",
                value=True,
                info="Replace image markers with AI-generated descriptions"
            )
            gemini_cleanup_toggle = gr.Checkbox(
                label="Clean markdown with Gemini",
                value=True,
                info="Use Gemini to format tables of contents, fix spacing, and improve formatting",
                interactive=gemini_available
            )
            if not gemini_available:
                gr.Markdown("⚠️ **Gemini cleanup unavailable**: Set GOOGLE_API_KEY in .env to enable")
            process_btn = gr.Button("Convert to Markdown", variant="primary")
            status_text = gr.Textbox(label="Status", interactive=False)

        with gr.Column():
            markdown_output = gr.Textbox(
                label="Markdown Output",
                lines=20,
                max_lines=30,
                interactive=False
            )
            download_btn = gr.File(label="Download Markdown File")

    # Set up event handlers
    process_btn.click(
        fn=process_pdf_ocr,
        inputs=[pdf_input, image_desc_toggle, gemini_cleanup_toggle],
        outputs=[markdown_output, download_btn, status_text]
    )

    gr.Markdown("""
    ## Instructions
    1. Upload a PDF file using the file picker above
    2. Toggle "Include image descriptions" to enable/disable AI-generated descriptions for figures and charts
    3. Toggle "Clean markdown with Gemini" to automatically format tables of contents, fix spacing, and improve formatting 
    4. Click "Convert to Markdown" to process the PDF
    5. View the extracted markdown in the output box
    6. Download the markdown file using the download button

    **Note:** Make sure you have set the `MISTRAL_API_KEY` environment variable with your Mistral API key.
    For Gemini cleanup, also set `GOOGLE_API_KEY` in your .env file.
    """)


if __name__ == "__main__":
    # Use environment variables for Docker compatibility
    # Default to localhost for local dev, but can be overridden to 0.0.0.0 for Docker
    server_name = os.environ.get("GRADIO_SERVER_NAME", "localhost")
    server_port = int(os.environ.get("GRADIO_SERVER_PORT", "7860"))
    demo.launch(server_name=server_name, server_port=server_port)
