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

# Load environment variables
load_dotenv()

# Initialize Mistral client
api_key = os.environ.get("MISTRAL_API_KEY")
if not api_key:
    raise ValueError("MISTRAL_API_KEY environment variable not set")

client = Mistral(api_key=api_key)


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


def process_pdf_ocr(pdf_file, include_image_descriptions=True, progress=gr.Progress()):
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

        # Debug: Print summary of image annotations
        if include_image_descriptions:
            total_images = sum(len(page.images) if hasattr(page, 'images') else 0 for page in ocr_response.pages)
            print(f"=== Image Descriptions Processing ===")
            print(f"Total images with annotations: {total_images}")

        # Combine all pages into a single markdown string
        markdown_content = ""
        for idx, page in enumerate(ocr_response.pages, 1):
            markdown_content += f"<!-- Page {idx} -->\n\n"
            page_markdown = page.markdown

            # Replace ![image] markers with descriptions if image annotations are available
            if include_image_descriptions and hasattr(page, 'images') and page.images:
                for img_idx, image in enumerate(page.images):
                    # The image_annotation is a JSON string, parse it
                    if hasattr(image, 'image_annotation') and image.image_annotation:
                        try:
                            annotation_dict = json.loads(image.image_annotation)
                            description = annotation_dict.get('description', '')
                            if description:
                                print(f"  Page {idx}, Image {img_idx}: Replacing image marker with description ({len(description)} chars)")
                                # Find and replace the first ![...] pattern with the description
                                page_markdown = re.sub(
                                    r'!\[.*?\]\(.*?\)',
                                    description,
                                    page_markdown,
                                    count=1
                                )
                        except json.JSONDecodeError as e:
                            print(f"Error parsing image annotation: {e}")
                            continue

            markdown_content += page_markdown
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
            image_desc_toggle = gr.Checkbox(
                label="Include image descriptions",
                value=True,
                info="Replace image markers with AI-generated descriptions"
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
        inputs=[pdf_input, image_desc_toggle],
        outputs=[markdown_output, download_btn, status_text]
    )

    gr.Markdown("""
    ## Instructions
    1. Upload a PDF file using the file picker above
    2. Toggle "Include image descriptions" to enable/disable AI-generated descriptions for figures and charts
    3. Click "Convert to Markdown" to process the PDF
    4. View the extracted markdown in the output box
    5. Download the markdown file using the download button

    **Note:** Make sure you have set the `MISTRAL_API_KEY` environment variable with your Mistral API key.
    """)


if __name__ == "__main__":
    # Use environment variables for Docker compatibility
    # Default to localhost for local dev, but can be overridden to 0.0.0.0 for Docker
    server_name = os.environ.get("GRADIO_SERVER_NAME", "localhost")
    server_port = int(os.environ.get("GRADIO_SERVER_PORT", "7860"))
    demo.launch(server_name=server_name, server_port=server_port)
