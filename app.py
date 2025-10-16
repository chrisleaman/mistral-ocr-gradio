import os
import tempfile
from pathlib import Path
import gradio as gr
from mistralai import Mistral
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Mistral client
api_key = os.environ.get("MISTRAL_API_KEY")
if not api_key:
    raise ValueError("MISTRAL_API_KEY environment variable not set")

client = Mistral(api_key=api_key)


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


def process_pdf_ocr(pdf_file, progress=gr.Progress()):
    """Process PDF file with Mistral OCR and return markdown content."""
    try:
        progress(0, desc="Uploading PDF to Mistral...")

        # Upload PDF and get URL
        pdf_url = upload_pdf_to_mistral(pdf_file)

        progress(0.3, desc="Processing OCR...")

        # Process OCR
        ocr_response = client.ocr.process(
            model="mistral-ocr-latest",
            document={
                "type": "document_url",
                "document_url": pdf_url,
            },

        )

        progress(0.7, desc="Generating markdown...")

        # Combine all pages into a single markdown string
        markdown_content = ""
        for idx, page in enumerate(ocr_response.pages, 1):
            markdown_content += f"<!-- Page {idx} -->\n\n"
            markdown_content += page.markdown
            markdown_content += "\n\n"

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
        inputs=[pdf_input],
        outputs=[markdown_output, download_btn, status_text]
    )

    gr.Markdown("""
    ## Instructions
    1. Upload a PDF file using the file picker above
    2. Click "Convert to Markdown" to process the PDF
    3. View the extracted markdown in the output box
    4. Download the markdown file using the download button

    **Note:** Make sure you have set the `MISTRAL_API_KEY` environment variable with your Mistral API key.
    """)


if __name__ == "__main__":
    # Use environment variables for Docker compatibility
    # Default to localhost for local dev, but can be overridden to 0.0.0.0 for Docker
    server_name = os.environ.get("GRADIO_SERVER_NAME", "localhost")
    server_port = int(os.environ.get("GRADIO_SERVER_PORT", "7860"))
    demo.launch(server_name=server_name, server_port=server_port)
