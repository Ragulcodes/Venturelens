import os
import json
import logging
import re
import sys
import time
from datetime import datetime
from typing import Dict, List, Any
import uuid
import tempfile
import shutil
from pathlib import Path

# Add src path for imports
# sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'src'))

from google.adk.agents import Agent
from google.cloud import bigquery, vision, storage

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
PROJECT_ID = os.getenv('GOOGLE_CLOUD_PROJECT', 'your-project-id')
BUCKET_NAME = os.getenv('BUCKET_NAME', 'pitch-deck-analysis-bucket')
BIGQUERY_DATASET = os.getenv('BIGQUERY_DATASET', 'pitch_deck_analysis')
BIGQUERY_TABLE = 'startup_analysis'

def convert_pdf_to_images_and_extract(local_file_path: str, gcs_uri: str) -> dict:
    """
    Convert PDF pages to images and use Vision API image text detection
    This is useful when async PDF detection fails but the PDF has readable content
    """
    try:
        # Try to import pdf2image
        try:
            from pdf2image import convert_from_path
        except ImportError:
            return {
                "success": False, 
                "error": "pdf2image library not installed. Run: pip install pdf2image"
            }
        
        logger.info("🖼️ Converting PDF to images for Vision API processing...")
        
        # Convert PDF to images
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                # Convert PDF pages to images
                images = convert_from_path(
                    local_file_path,
                    dpi=200,  # Good balance of quality and file size
                    first_page=1,
                    last_page=10,  # Limit to first 10 pages to avoid timeouts
                    output_folder=temp_dir,
                    fmt='jpeg'
                )
                
                if not images:
                    return {"success": False, "error": "No images generated from PDF"}
                
                # Process each image with Vision API
                client = vision.ImageAnnotatorClient()
                all_text = []
                total_confidence = 0
                successful_pages = 0
                
                for i, image in enumerate(images):
                    try:
                        # Save image temporarily
                        image_path = os.path.join(temp_dir, f"page_{i+1}.jpg")
                        image.save(image_path, 'JPEG', quality=85)
                        
                        # Upload image to GCS temporarily
                        temp_gcs_path = upload_temp_image_to_gcs(image_path, i+1)
                        if not temp_gcs_path:
                            continue
                        
                        # Extract text from image
                        image_vision = vision.Image()
                        image_vision.source.image_uri = temp_gcs_path
                        
                        response = client.annotate_image(request=vision.AnnotateImageRequest(
                            image=image_vision,
                            features=[vision.Feature(type_=vision.Feature.Type.DOCUMENT_TEXT_DETECTION)]
                        ))
                        
                        if response.full_text_annotation:
                            page_text = response.full_text_annotation.text
                            all_text.append(f"--- Page {i+1} ---\n{page_text}")
                            
                            # Calculate confidence
                            confidences = []
                            for page in response.full_text_annotation.pages:
                                for block in page.blocks:
                                    for paragraph in block.paragraphs:
                                        for word in paragraph.words:
                                            confidences.append(word.confidence)
                            
                            if confidences:
                                page_confidence = sum(confidences) / len(confidences)
                                total_confidence += page_confidence
                                successful_pages += 1
                        
                        # Clean up temporary GCS file
                        cleanup_temp_gcs_file(temp_gcs_path)
                        
                    except Exception as e:
                        logger.warning(f"Failed to process page {i+1}: {e}")
                        continue
                
                if not all_text:
                    return {"success": False, "error": "No text extracted from any PDF page"}
                
                full_text = '\n\n'.join(all_text)
                avg_confidence = total_confidence / successful_pages if successful_pages > 0 else 0.0
                
                return {
                    "success": True,
                    "extracted_text": full_text,
                    "word_count": len(full_text.split()),
                    "confidence_score": avg_confidence,
                    "page_count": successful_pages,
                    "method": "pdf_to_images_vision"
                }
                
            except Exception as e:
                return {"success": False, "error": f"PDF to image conversion failed: {str(e)}"}
            
    except Exception as e:
        return {"success": False, "error": f"PDF image extraction failed: {str(e)}"}
    
def upload_temp_image_to_gcs(image_path: str, page_num: int) -> str:
    """Upload temporary image to GCS for Vision API processing"""
    try:
        client = storage.Client(project=PROJECT_ID)
        bucket = client.bucket(BUCKET_NAME)
        
        temp_blob_name = f"temp/page_{page_num}_{uuid.uuid4().hex[:8]}.jpg"
        blob = bucket.blob(temp_blob_name)
        
        blob.upload_from_filename(image_path)
        return f"gs://{BUCKET_NAME}/{temp_blob_name}"
        
    except Exception as e:
        logger.error(f"Failed to upload temp image: {e}")
        return None
    
def cleanup_temp_gcs_file(gcs_uri: str):
    """Clean up temporary files from GCS"""
    try:
        client = storage.Client(project=PROJECT_ID)
        bucket_name = gcs_uri.split('/')[2]
        file_path = '/'.join(gcs_uri.split('/')[3:])
        
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(file_path)
        blob.delete()
        
    except Exception as e:
        logger.warning(f"Failed to cleanup temp file {gcs_uri}: {e}")

def extract_text_with_pymupdf(local_file_path: str) -> dict:
    """
    Extract text using PyMuPDF (fitz) - often more reliable than PyPDF2
    Install with: pip install PyMuPDF
    """
    try:
        import fitz  # PyMuPDF
        
        logger.info("📚 Attempting PyMuPDF text extraction...")
        
        doc = fitz.open(local_file_path)
        text_parts = []
        
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            page_text = page.get_text()
            
            if page_text.strip():
                text_parts.append(f"--- Page {page_num + 1} ---\n{page_text}")
        
        doc.close()
        
        if not text_parts:
            return {"success": False, "error": "No text extracted with PyMuPDF"}
        
        full_text = '\n\n'.join(text_parts)
        
        return {
            "success": True,
            "extracted_text": full_text,
            "word_count": len(full_text.split()),
            "confidence_score": 0.85,  # PyMuPDF is generally quite reliable
            "page_count": len(text_parts),
            "method": "direct_pdf_pymupdf"
        }
        
    except ImportError:
        return {
            "success": False, 
            "error": "PyMuPDF not installed. Run: pip install PyMuPDF"
        }
    except Exception as e:
        return {"success": False, "error": f"PyMuPDF extraction failed: {str(e)}"}
    

def extract_text_with_pdfplumber(local_file_path: str) -> dict:
    """
    Extract text using pdfplumber - excellent for tables and structured data
    Install with: pip install pdfplumber
    """
    try:
        import pdfplumber
        
        logger.info("🔧 Attempting pdfplumber text extraction...")
        
        text_parts = []
        
        with pdfplumber.open(local_file_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                try:
                    # Extract text
                    page_text = page.extract_text()
                    
                    # Extract tables if any
                    tables = page.extract_tables()
                    
                    if page_text or tables:
                        page_content = f"--- Page {page_num + 1} ---\n"
                        
                        if page_text:
                            page_content += page_text + "\n"
                        
                        # Add table content
                        for table_num, table in enumerate(tables):
                            page_content += f"\n[Table {table_num + 1}]\n"
                            for row in table:
                                if row:
                                    page_content += " | ".join([cell or "" for cell in row]) + "\n"
                        
                        text_parts.append(page_content)
                        
                except Exception as e:
                    logger.warning(f"Failed to extract page {page_num + 1} with pdfplumber: {e}")
                    continue
        
        if not text_parts:
            return {"success": False, "error": "No text extracted with pdfplumber"}
        
        full_text = '\n\n'.join(text_parts)
        
        return {
            "success": True,
            "extracted_text": full_text,
            "word_count": len(full_text.split()),
            "confidence_score": 0.9,  # pdfplumber is excellent for structured content
            "page_count": len(text_parts),
            "method": "direct_pdf_pdfplumber"
        }
        
    except ImportError:
        return {
            "success": False, 
            "error": "pdfplumber not installed. Run: pip install pdfplumber"
        }
    except Exception as e:
        return {"success": False, "error": f"pdfplumber extraction failed: {str(e)}"}
    
def enhanced_pdf_extraction_pipeline(local_file_path: str, gcs_uri: str) -> dict:
    """
    Comprehensive PDF extraction pipeline trying multiple methods in order of reliability
    """
    logger.info("🔄 Starting enhanced PDF extraction pipeline...")
    
    # Method 1: Try async Vision API first (best for scanned PDFs)
    result = extract_text_from_pdf_async(gcs_uri)
    if result["success"] and result["word_count"] > 50:
        logger.info("✅ Async Vision API successful")
        return result
    
    # Method 2: Try pdfplumber (best for structured PDFs with tables)
    result = extract_text_with_pdfplumber(local_file_path)
    if result["success"] and result["word_count"] > 50:
        logger.info("✅ pdfplumber extraction successful")
        return result
    
    # Method 3: Try PyMuPDF (good general-purpose PDF reader)
    result = extract_text_with_pymupdf(local_file_path)
    if result["success"] and result["word_count"] > 50:
        logger.info("✅ PyMuPDF extraction successful")
        return result
    
    # Method 4: Try PDF to images + Vision API (for complex layouts)
    result = convert_pdf_to_images_and_extract(local_file_path, gcs_uri)
    if result["success"] and result["word_count"] > 50:
        logger.info("✅ PDF to images extraction successful")
        return result
    
    # Method 5: Try PyPDF2 as final fallback
    result = extract_text_from_pdf_directly(local_file_path)
    if result["success"]:
        logger.info("✅ PyPDF2 extraction successful (final fallback)")
        return result
    
    return {
        "success": False,
        "error": "All PDF extraction methods failed",
        "suggestions": [
            "PDF may be password-protected or corrupted",
            "Try manually converting PDF to text or images first",
            "Check if PDF contains only images without OCR text layer",
            "Consider using a different file format (DOCX, PPTX, TXT)"
        ]
    }


def upload_and_analyze_pitch_deck(local_file_path: str) -> dict:
    """
    Complete pipeline: upload file to GCS, extract text with Vision API, analyze content, save to BigQuery
    
    Args:
        local_file_path: Path to local pitch deck file (PDF, PPTX, DOCX, TXT)
        
    Returns:
        Complete analysis results with structured business insights
    """
    session_id = str(uuid.uuid4())
    
    try:
        logger.info(f"🚀 Starting pitch deck analysis for: {local_file_path}")
        
        # Validate file exists
        if not os.path.exists(local_file_path):
            return {
                "success": False,
                "error": f"File not found: {local_file_path}",
                "session_id": session_id
            }
        # Step 0: Preprocess PDF if it's likely problematic
        if local_file_path.lower().endswith('.pdf'):
            file_size = os.path.getsize(local_file_path)
            if file_size > 5 * 1024 * 1024:  # Files larger than 5MB
                logger.info("📦 Large PDF detected, preprocessing...")
                local_file_path = preprocess_problematic_pdf(local_file_path)
        
        # Step 1: Upload to GCS
        logger.info("📁 Step 1: Uploading file to Google Cloud Storage...")
        gcs_result = upload_file_to_gcs(local_file_path)
        if not gcs_result["success"]:
            return {
                "success": False,
                "error": f"Upload failed: {gcs_result['error']}",
                "session_id": session_id
            }
        
        gcs_uri = gcs_result["gcs_uri"]
        logger.info(f"✅ Uploaded to: {gcs_uri}")
        
        # Step 2: Smart text extraction with proper PDF handling
        logger.info("Step 2: Extracting text (trying multiple methods)...")
        
        # Check file type and use appropriate extraction method
        if local_file_path.lower().endswith('.pdf'):
            logger.info("PDF detected, using enhanced extraction pipeline...")
            vision_result = enhanced_pdf_extraction_pipeline(local_file_path, gcs_uri)
            
            # If all PDF methods fail, provide detailed error
            if not vision_result["success"]:
                return {
                    "success": False,
                    "error": f"All PDF extraction methods failed: {vision_result.get('error', 'Unknown error')}",
                    "session_id": session_id,
                    "gcs_uri": gcs_uri,
                    "suggestions": vision_result.get('suggestions', [
                        "PDF may have complex formatting, corrupted content, or unsupported features",
                        "Try converting PDF to images first using pdf2image",
                        "Consider using a different PDF processing tool",
                        "Check if PDF is password-protected or has restrictions"
                    ])
                }
        else:
            # For non-PDF files, use regular image-based text detection
            vision_result = extract_text_with_vision(gcs_uri)
            
        extracted_text = vision_result["extracted_text"]
        logger.info(f"✅ Extracted {vision_result['word_count']} words using {vision_result.get('method', 'unknown')} method")
        
        # Step 3: Analyze startup content
        logger.info("🧠 Step 3: Analyzing startup business content...")
        analysis = analyze_startup_content(extracted_text)
        
        # Add metadata
        analysis.update({
            "session_id": session_id,
            "gcs_uri": gcs_uri,
            "original_filename": os.path.basename(local_file_path),
            "vision_api_confidence": vision_result.get("confidence_score", 0.0),
            "file_size_bytes": gcs_result.get("file_size", 0),
            "extraction_method": vision_result.get("method", "unknown")
        })
        
        # Step 4: Save to BigQuery
        logger.info("💾 Step 4: Saving analysis to BigQuery...")
        bigquery_success = save_to_bigquery(analysis)
        analysis["bigquery_saved"] = bigquery_success
        
        logger.info(f"🎉 Analysis completed for: {analysis.get('company_name', 'Unknown Company')}")
        return analysis
        
    except Exception as e:
        logger.error(f"❌ Pipeline failed: {str(e)}")
        return {
            "success": False,
            "error": str(e),
            "session_id": session_id
        }

def upload_file_to_gcs(local_file_path: str) -> dict:
    """Upload local file to Google Cloud Storage"""
    try:
        # Initialize GCS client
        client = storage.Client(project=PROJECT_ID)
        bucket = client.bucket(BUCKET_NAME)
        
        # Get file info
        file_name = os.path.basename(local_file_path)
        file_size = os.path.getsize(local_file_path)
        
        # Create GCS path with timestamp to avoid conflicts
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        gcs_path = f"pitch-decks/{timestamp}_{file_name}"
        blob = bucket.blob(gcs_path)
        
        # Upload file
        blob.upload_from_filename(local_file_path)
        gcs_uri = f"gs://{BUCKET_NAME}/{gcs_path}"
        
        return {
            "success": True,
            "gcs_uri": gcs_uri,
            "file_size": file_size,
            "gcs_path": gcs_path
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}

def extract_text_from_pdf_async(gcs_uri: str) -> dict:
    """
    Extract text from PDF using async document text detection - the proper way for PDFs
    This is the correct method for PDF files according to Vision API documentation
    """
    try:
        client = vision.ImageAnnotatorClient()
        
        # Configure input for PDF
        gcs_source = vision.GcsSource(uri=gcs_uri)
        input_config = vision.InputConfig(
            gcs_source=gcs_source,
            mime_type='application/pdf'  # Specify PDF MIME type
        )
        
        # Configure output (results will be saved to GCS)
        output_uri_prefix = gcs_uri.replace('.pdf', '_output')
        gcs_destination = vision.GcsDestination(uri=output_uri_prefix)
        output_config = vision.OutputConfig(
            gcs_destination=gcs_destination,
            batch_size=1
        )
        
        # Create async request
        async_request = vision.AsyncAnnotateFileRequest(
            features=[vision.Feature(type_=vision.Feature.Type.DOCUMENT_TEXT_DETECTION)],
            input_config=input_config,
            output_config=output_config
        )
        
        # Start async operation
        operation = client.async_batch_annotate_files(
            requests=[async_request]
        )
        
        logger.info("📄 Async PDF processing started, waiting for completion...")
        
        # Wait for operation to complete (with timeout)
        result = operation.result(timeout=300)  # 5 minutes timeout
        
        # Read results from GCS
        storage_client = storage.Client(project=PROJECT_ID)
        bucket_name = gcs_uri.split('/')[2]
        bucket = storage_client.bucket(bucket_name)
        
        # List output files
        output_prefix = output_uri_prefix.split('/')[-1]
        blobs = list(bucket.list_blobs(prefix=output_prefix))
        
        if not blobs:
            return {"success": False, "error": "No output files generated"}
        
        # Read the first output file (usually output-1-to-1.json)
        for blob in blobs:
            if blob.name.endswith('.json'):
                result_json = json.loads(blob.download_as_text())
                
                # Extract text from the response
                extracted_text = ""
                page_count = 0
                
                if 'responses' in result_json:
                    for response in result_json['responses']:
                        if 'fullTextAnnotation' in response:
                            extracted_text += response['fullTextAnnotation']['text'] + "\n"
                            if 'pages' in response['fullTextAnnotation']:
                                page_count += len(response['fullTextAnnotation']['pages'])
                
                if extracted_text.strip():
                    return {
                        "success": True,
                        "extracted_text": extracted_text.strip(),
                        "word_count": len(extracted_text.split()),
                        "confidence_score": 0.9,  # Async method is generally more accurate
                        "page_count": page_count,
                        "method": "async_pdf_document_detection"
                    }
        
        return {"success": False, "error": "No valid text found in output files"}
        
    except Exception as e:
        logger.error(f"Async PDF extraction failed: {str(e)}")
        return {"success": False, "error": f"Async PDF extraction failed: {str(e)}"}

def extract_text_with_vision(gcs_uri: str) -> dict:
    """Enhanced text extraction for non-PDF files with multiple fallback methods"""
    try:
        # Method 1: Try Cloud Vision API first for images/documents
        logger.info("🔍 Attempting Cloud Vision API extraction...")
        vision_result = extract_text_vision_api(gcs_uri)
        
        if vision_result["success"]:
            logger.info("✅ Cloud Vision API successful")
            return vision_result

        # Check if it's a format error that we can work around
        if vision_result.get("error") == "bad_image_format" or "Bad image data" in str(vision_result.get("error", "")):
            logger.warning(f"⚠️ Cloud Vision image format issue: {vision_result['error']}")
        else:
            logger.warning(f"⚠️ Cloud Vision failed: {vision_result['error']}")
        
        # Method 2: Try with different Vision API settings
        logger.info("🔄 Trying Vision API with different settings...")
        vision_simple_result = extract_text_vision_simple(gcs_uri)
        
        if vision_simple_result["success"]:
            logger.info("✅ Simple Vision API successful")
            return vision_simple_result
            
        return {
            "success": False,
            "error": "All Vision API methods failed for this file format",
            "vision_error": vision_result.get("error", "Unknown"),
            "simple_vision_error": vision_simple_result.get("error", "Unknown")
        }
        
    except Exception as e:
        logger.error(f"❌ Text extraction completely failed: {str(e)}")
        return {"success": False, "error": str(e)}

def extract_text_vision_api(gcs_uri: str) -> dict:
    """Original Vision API method for images and non-PDF documents"""
    try:
        client = vision.ImageAnnotatorClient()
        image = vision.Image()
        image.source.image_uri = gcs_uri
        
        feature = vision.Feature(type_=vision.Feature.Type.DOCUMENT_TEXT_DETECTION)
        request = vision.AnnotateImageRequest(image=image, features=[feature])
        
        response = client.annotate_image(request=request)
        
        if response.error.message:
            # Check if it's the "Bad image data" error specifically
            if "Bad image data" in response.error.message or "invalid" in response.error.message.lower():
                logger.warning(f"Vision API image format error: {response.error.message}")
                return {"success": False, "error": "bad_image_format", "original_error": response.error.message}
            else:
                return {"success": False, "error": response.error.message}
        
        if not response.full_text_annotation:
            return {"success": False, "error": "No text found in document"}
        
        extracted_text = response.full_text_annotation.text
        word_count = len(extracted_text.split())
        
        confidences = []
        for page in response.full_text_annotation.pages:
            for block in page.blocks:
                for paragraph in block.paragraphs:
                    for word in paragraph.words:
                        confidences.append(word.confidence)
        
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        
        return {
            "success": True,
            "extracted_text": extracted_text,
            "word_count": word_count,
            "confidence_score": avg_confidence,
            "page_count": len(response.full_text_annotation.pages),
            "method": "cloud_vision_document"
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}

def extract_text_vision_simple(gcs_uri: str) -> dict:
    """Try Vision API with simpler TEXT_DETECTION instead of DOCUMENT_TEXT_DETECTION"""
    try:
        client = vision.ImageAnnotatorClient()
        image = vision.Image()
        image.source.image_uri = gcs_uri
        
        # Use simpler text detection
        feature = vision.Feature(type_=vision.Feature.Type.TEXT_DETECTION)
        request = vision.AnnotateImageRequest(image=image, features=[feature])
        
        response = client.annotate_image(request=request)
        
        if response.error.message:
            return {"success": False, "error": response.error.message}
        
        if not response.text_annotations:
            return {"success": False, "error": "No text found with simple detection"}
        
        # Get the first annotation which contains all text
        extracted_text = response.text_annotations[0].description
        word_count = len(extracted_text.split())
        
        return {
            "success": True,
            "extracted_text": extracted_text,
            "word_count": word_count,
            "confidence_score": 0.8,  # Assume good quality
            "page_count": 1,
            "method": "cloud_vision_simple"
        }
        
    except Exception as e:
        return {"success": False, "error": str(e)}

def analyze_startup_content(text: str) -> dict:
    """Analyze extracted text for startup business elements"""
    if not text or len(text.strip()) < 50:
        return {
            "success": False,
            "error": "Insufficient text content for analysis",
            "company_name": "Unknown",
            "confidence_score": 0.0
        }
    
    # Extract business information using pattern matching
    analysis = {
        "success": True,
        "company_name": extract_company_name(text),
        "problem_statement": extract_section_content(text, ["problem", "pain point", "challenge"]),
        "solution_description": extract_section_content(text, ["solution", "our solution", "product"]),
        "target_market": extract_section_content(text, ["market", "target market", "customers", "tam"]),
        "team_info": extract_section_content(text, ["team", "founder", "leadership", "about us"]),
        "traction_metrics": extract_section_content(text, ["traction", "growth", "metrics", "users", "revenue"]),
        "financial_projections": extract_section_content(text, ["financial", "funding", "investment", "revenue"]),
        "key_metrics": extract_numerical_metrics(text),
        "risk_flags": identify_risk_factors(text)
    }
    
    # Calculate confidence based on completeness
    required_fields = ["company_name", "problem_statement", "solution_description", "target_market"]
    fields_found = sum(1 for field in required_fields if analysis[field] and len(analysis[field]) > 10)
    analysis["confidence_score"] = round(fields_found / len(required_fields), 2)
    
    return analysis

def extract_company_name(text: str) -> str:
    """Extract company name from text"""
    lines = text.split('\n')[:15]  # Check first 15 lines
    
    for line in lines:
        line = line.strip()
        # Look for company name patterns
        if len(line) > 2 and len(line) < 50 and not line.lower().startswith(('the ', 'a ', 'an ')):
            # Check if line looks like a company name (title case, short)
            if line[0].isupper() and ' ' in line and line.count(' ') <= 3:
                return line
    
    return "Unknown Company"

def extract_section_content(text: str, keywords: List[str]) -> str:
    """Extract content from sections matching keywords"""
    lines = text.split('\n')
    content_lines = []
    capturing = False
    
    for i, line in enumerate(lines):
        line_clean = line.strip().lower()
        
        # Check if line contains section keywords
        if any(keyword in line_clean for keyword in keywords):
            capturing = True
            content_lines.append(line.strip())
            # Add next few lines
            for j in range(i+1, min(i+5, len(lines))):
                next_line = lines[j].strip()
                if next_line and not next_line.lower().startswith(('slide', 'next', 'thank')):
                    content_lines.append(next_line)
                else:
                    break
            break
    
    return '\n'.join(content_lines[:200])  # Limit content length

def extract_numerical_metrics(text: str) -> str:
    """Extract key numerical metrics from text"""
    import re
    
    patterns = [
        r'\$[\d,]+[kmb]?',  # Money: $100k, $1.5M
        r'\d+%',  # Percentages: 25%
        r'\d+[kmb]?\s*(?:users?|customers?|clients?)',  # Users/customers
        r'\d+x\s*(?:growth|increase)',  # Growth multipliers
        r'\d+(?:\.\d+)?[kmb]?\s*(?:arr|mrr|revenue)',  # Revenue metrics
    ]
    
    metrics = []
    for pattern in patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        metrics.extend(matches)
    
    return ', '.join(set(metrics[:10]))  # Return unique metrics, limit to 10

def identify_risk_factors(text: str) -> List[str]:
    """Identify potential investment risk factors"""
    text_lower = text.lower()
    risks = []
    
    risk_indicators = {
        'Limited traction': ['no revenue', 'pre-revenue', 'just launched', 'prototype'],
        'High competition': ['competitive market', 'many competitors', 'saturated market'],
        'Team concerns': ['solo founder', 'no experience', 'first-time', 'learning'],
        'Funding risk': ['need funding', 'running out', 'cash flow', 'burn rate'],
        'Product risk': ['not built', 'early stage', 'beta', 'mvp']
    }
    
    for risk_type, indicators in risk_indicators.items():
        if any(indicator in text_lower for indicator in indicators):
            risks.append(risk_type)
    
    return risks

def save_to_bigquery(analysis: Dict[str, Any]) -> bool:
    """Save analysis results to BigQuery"""
    try:
        client = bigquery.Client(project=PROJECT_ID)
        
        # Prepare row data
        row_data = {
            'company_name': analysis.get('company_name', 'Unknown'),
            'source_gcs_uri': analysis.get('gcs_uri', ''),
            'original_filename': analysis.get('original_filename', ''),
            'file_type': os.path.splitext(analysis.get('original_filename', ''))[-1].upper().replace('.', ''),
            'ingested_at': datetime.utcnow().isoformat(),
            'agent_session_id': analysis.get('session_id', ''),
            'structured_data': json.dumps(analysis),
            'problem_statement': analysis.get('problem_statement', ''),
            'solution_description': analysis.get('solution_description', ''),
            'target_market': analysis.get('target_market', ''),
            'team_info': analysis.get('team_info', ''),
            'traction_metrics': analysis.get('traction_metrics', ''),
            'financial_projections': analysis.get('financial_projections', ''),
            'key_metrics': analysis.get('key_metrics', ''),
            'risk_flags': analysis.get('risk_flags', []),
            'confidence_score': analysis.get('confidence_score', 0.0),
            'processing_status': 'SUCCESS' if analysis.get('success') else 'ERROR',
            'vision_api_confidence': analysis.get('vision_api_confidence', 0.0),
            'extraction_method': analysis.get('extraction_method', 'unknown')
        }
        
        # Insert to BigQuery
        table_ref = client.dataset(BIGQUERY_DATASET).table(BIGQUERY_TABLE)
        table = client.get_table(table_ref)
        errors = client.insert_rows_json(table, [row_data])
        
        if errors:
            logger.error(f"BigQuery errors: {errors}")
            return False
        
        logger.info(f"✅ Saved to BigQuery: {analysis.get('company_name')}")
        return True
        
    except Exception as e:
        logger.error(f"❌ BigQuery save failed: {str(e)}")
        return False

def query_recent_analyses(limit: int = 10) -> dict:
    """Query recent pitch deck analyses from BigQuery"""
    try:
        client = bigquery.Client(project=PROJECT_ID)
        
        query = f"""
        SELECT 
            company_name,
            confidence_score,
            ARRAY_LENGTH(risk_flags) as risk_count,
            extraction_method,
            ingested_at,
            agent_session_id
        FROM `{PROJECT_ID}.{BIGQUERY_DATASET}.{BIGQUERY_TABLE}`
        WHERE processing_status = 'SUCCESS'
        ORDER BY ingested_at DESC
        LIMIT {limit}
        """
        
        results = client.query(query)
        
        analyses = []
        for row in results:
            analyses.append({
                "company_name": row.company_name,
                "confidence_score": row.confidence_score,
                "risk_count": row.risk_count,
                "extraction_method": row.extraction_method,
                "ingested_at": row.ingested_at.isoformat(),
                "session_id": row.agent_session_id
            })
        
        return {
            "success": True,
            "count": len(analyses),
            "analyses": analyses
        }
        
    except Exception as e:
        logger.error(f"Query failed: {str(e)}")
        return {"success": False, "error": str(e)}

def preprocess_problematic_pdf(local_file_path: str) -> str:
    """Clean problematic PDF before processing"""
    try:
        import subprocess
        import os
        
        # Create cleaned filename
        base_name = os.path.splitext(local_file_path)[0]
        cleaned_path = f"{base_name}_cleaned.pdf"
        
        # Try to clean PDF using ghostscript
        cmd = [
            'gs', '-sDEVICE=pdfwrite', '-dCompatibilityLevel=1.4',
            '-dPDFSETTINGS=/screen', '-dNOPAUSE', '-dQUIET', '-dBATCH',
            '-dColorImageResolution=150', '-dGrayImageResolution=150',
            f'-sOutputFile={cleaned_path}', local_file_path
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
        
        if result.returncode == 0 and os.path.exists(cleaned_path):
            file_size = os.path.getsize(cleaned_path)
            if file_size > 1000:  # At least 1KB
                logger.info(f"✅ PDF cleaned successfully: {file_size} bytes")
                return cleaned_path
        
        logger.warning("PDF cleaning failed, using original file")
        return local_file_path
        
    except Exception as e:
        logger.warning(f"PDF preprocessing failed: {e}")
        return local_file_path
    
def extract_text_from_pdf_directly(local_file_path: str) -> dict:
    """Extract text directly from local PDF file bypassing Vision API completely"""
    try:
        import PyPDF2
        import subprocess
        
        logger.info("📄 Attempting direct PDF text extraction...")
        
        # Method 1: Try PyPDF2 first
        try:
            with open(local_file_path, 'rb') as pdf_file:
                pdf_reader = PyPDF2.PdfReader(pdf_file)
                text_parts = []
                
                for page_num, page in enumerate(pdf_reader.pages):
                    try:
                        page_text = page.extract_text()
                        if page_text.strip():
                            text_parts.append(f"--- Page {page_num + 1} ---\n{page_text}")
                    except Exception as e:
                        logger.warning(f"Failed to extract page {page_num + 1}: {e}")
                        continue
                
                if text_parts:
                    full_text = '\n\n'.join(text_parts)
                    return {
                        "success": True,
                        "extracted_text": full_text,
                        "word_count": len(full_text.split()),
                        "confidence_score": 0.8,
                        "page_count": len(text_parts),
                        "method": "direct_pdf_pypdf2"
                    }
        except Exception as e:
            logger.warning(f"PyPDF2 extraction failed: {e}")
        
        # Method 2: Try pdftotext command
        try:
            result = subprocess.run(
                ['pdftotext', local_file_path, '-'], 
                capture_output=True, 
                text=True, 
                timeout=30
            )
            
            if result.returncode == 0 and result.stdout.strip():
                text = result.stdout.strip()
                return {
                    "success": True,
                    "extracted_text": text,
                    "word_count": len(text.split()),
                    "confidence_score": 0.9,
                    "page_count": 1,
                    "method": "direct_pdf_pdftotext"
                }
        except Exception as e:
            logger.warning(f"pdftotext extraction failed: {e}")
        
        return {"success": False, "error": "All direct PDF extraction methods failed"}
        
    except Exception as e:
        return {"success": False, "error": f"Direct PDF extraction failed: {str(e)}"}

# Create the ADK agent
document_preprocessing_agent = Agent(
    name="pitch_deck_analyzer",
    model="gemini-2.0-flash",
    description="AI agent that analyzes startup pitch decks and extracts key business insights for investor evaluation",
    instruction="""I am a startup pitch deck analysis expert. I help investors and entrepreneurs by:

    🔍 WHAT I ANALYZE:
    - Company information and value proposition
    - Problem statement and market opportunity  
    - Solution description and competitive advantages
    - Team background and expertise
    - Traction metrics and growth indicators
    - Financial projections and funding needs
    - Key business metrics and KPIs
    - Risk factors and potential concerns

    📋 HOW TO USE ME:
    1. Provide the local file path to your pitch deck (PDF, PPTX, DOCX, TXT)
    2. I'll upload it to Google Cloud Storage
    3. Extract all text using appropriate Vision API methods (async for PDFs)
    4. Analyze content for key business elements
    5. Store structured results in BigQuery
    6. Provide detailed analysis with confidence scores

    💡 EXAMPLE USAGE:
    - "Analyze the pitch deck at /path/to/startup-deck.pdf"
    - "Show me recent analysis results"
    - "What are the key risk factors for tech startups?"

    🔧 IMPROVED PDF HANDLING:
    - Uses async document text detection for PDFs (proper Vision API method)
    - Falls back to direct PDF text extraction if Vision API fails
    - Handles large files with preprocessing
    - Supports multiple file formats with appropriate extraction methods

    I provide comprehensive analysis that helps investors make informed decisions and helps startups improve their pitches.""",
        tools=[upload_and_analyze_pitch_deck, query_recent_analyses]
)
