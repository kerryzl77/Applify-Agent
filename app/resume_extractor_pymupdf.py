"""
Resume Extractor using PyMuPDF (Tier 1)
=======================================

Layout-aware PDF extraction that produces:
- Structured blocks with text, bounding boxes, and font statistics
- Reading-order linear text
- Page images (first page by default) as base64 for VLM input

This is deterministic and fast - no LLM calls here.
"""

import base64
import io
import logging
import os
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

import fitz  # PyMuPDF
from PIL import Image

logger = logging.getLogger(__name__)


@dataclass
class FontStats:
    """Font statistics for a text block."""
    size: float
    flags: int  # bold=16, italic=2, etc.
    font_name: str
    
    @property
    def is_bold(self) -> bool:
        return bool(self.flags & 16)
    
    @property
    def is_italic(self) -> bool:
        return bool(self.flags & 2)


@dataclass
class TextBlock:
    """A text block extracted from the PDF."""
    text: str
    bbox: tuple  # (x0, y0, x1, y1)
    font_stats: FontStats
    is_heading_candidate: bool = False
    block_type: str = "text"  # "text" or "image"
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "bbox": self.bbox,
            "font_stats": {
                "size": self.font_stats.size,
                "flags": self.font_stats.flags,
                "font_name": self.font_stats.font_name,
                "is_bold": self.font_stats.is_bold,
                "is_italic": self.font_stats.is_italic,
            },
            "is_heading_candidate": self.is_heading_candidate,
            "block_type": self.block_type,
        }


@dataclass
class PageExtraction:
    """Extraction result for a single page."""
    page_number: int
    blocks: List[TextBlock] = field(default_factory=list)
    width: float = 0
    height: float = 0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "page_number": self.page_number,
            "blocks": [b.to_dict() for b in self.blocks],
            "width": self.width,
            "height": self.height,
        }


@dataclass
class ExtractionResult:
    """Complete extraction result from a resume PDF."""
    pages: List[PageExtraction] = field(default_factory=list)
    fulltext_linear: str = ""
    page_images: List[str] = field(default_factory=list)  # base64 data URLs
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "pages": [p.to_dict() for p in self.pages],
            "fulltext_linear": self.fulltext_linear,
            "page_images": self.page_images,
            "metadata": self.metadata,
        }


class ResumeExtractorPyMuPDF:
    """
    Tier 1: Layout-aware resume extraction using PyMuPDF.
    
    Extracts structured blocks with font information and renders
    page images for VLM processing.
    """
    
    def __init__(self, image_dpi: int = 150, max_image_pages: int = 1):
        """
        Initialize the extractor.
        
        Args:
            image_dpi: DPI for rendering page images (default 150 for balance of quality/size)
            max_image_pages: Maximum number of pages to render as images (default 1)
        """
        self.image_dpi = image_dpi
        self.max_image_pages = max_image_pages
    
    def extract(self, file_path: str) -> ExtractionResult:
        """
        Extract structured content from a PDF resume.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            ExtractionResult with blocks, linear text, and page images
        """
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")
        
        result = ExtractionResult()
        all_text_lines = []
        
        try:
            doc = fitz.open(file_path)
            result.metadata = {
                "page_count": len(doc),
                "title": doc.metadata.get("title", ""),
                "author": doc.metadata.get("author", ""),
            }
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                page_extraction = self._extract_page(page, page_num)
                result.pages.append(page_extraction)
                
                # Collect text for linear fulltext
                for block in page_extraction.blocks:
                    if block.text.strip():
                        all_text_lines.append(block.text.strip())
                
                # Render page image (only for first N pages)
                if page_num < self.max_image_pages:
                    image_b64 = self._render_page_image(page)
                    if image_b64:
                        result.page_images.append(image_b64)
            
            doc.close()
            
            # Build linear fulltext in reading order
            result.fulltext_linear = "\n".join(all_text_lines)
            
            logger.info(f"Extracted {len(result.pages)} pages, "
                       f"{sum(len(p.blocks) for p in result.pages)} blocks, "
                       f"{len(result.fulltext_linear)} chars")
            
        except Exception as e:
            logger.error(f"Error extracting PDF: {str(e)}")
            raise
        
        return result
    
    def _extract_page(self, page: fitz.Page, page_num: int) -> PageExtraction:
        """Extract blocks from a single page."""
        extraction = PageExtraction(
            page_number=page_num,
            width=page.rect.width,
            height=page.rect.height,
        )
        
        # Get text blocks with detailed information
        # Using "dict" extraction for full font info
        page_dict = page.get_text("dict", flags=fitz.TEXT_PRESERVE_WHITESPACE)
        
        for block in page_dict.get("blocks", []):
            if block["type"] == 0:  # Text block
                text_block = self._process_text_block(block)
                if text_block and text_block.text.strip():
                    extraction.blocks.append(text_block)
            elif block["type"] == 1:  # Image block
                # Note image presence but don't extract content
                extraction.blocks.append(TextBlock(
                    text="[IMAGE]",
                    bbox=tuple(block["bbox"]),
                    font_stats=FontStats(size=0, flags=0, font_name=""),
                    block_type="image",
                ))
        
        # Sort blocks by reading order (top-to-bottom, left-to-right)
        extraction.blocks.sort(key=lambda b: (b.bbox[1], b.bbox[0]))
        
        return extraction
    
    def _process_text_block(self, block: Dict) -> Optional[TextBlock]:
        """Process a text block and extract font statistics."""
        lines = block.get("lines", [])
        if not lines:
            return None
        
        # Collect all text and find dominant font
        all_text = []
        font_sizes = []
        font_flags = []
        font_names = []
        
        for line in lines:
            for span in line.get("spans", []):
                text = span.get("text", "")
                if text:
                    all_text.append(text)
                    font_sizes.append(span.get("size", 11))
                    font_flags.append(span.get("flags", 0))
                    font_names.append(span.get("font", ""))
        
        if not all_text:
            return None
        
        # Use the most common/first font as representative
        combined_text = " ".join(all_text)
        avg_size = sum(font_sizes) / len(font_sizes) if font_sizes else 11
        dominant_flags = max(set(font_flags), key=font_flags.count) if font_flags else 0
        dominant_font = font_names[0] if font_names else ""
        
        font_stats = FontStats(
            size=avg_size,
            flags=dominant_flags,
            font_name=dominant_font,
        )
        
        # Heuristic: heading candidate if larger font or bold
        is_heading = avg_size >= 12 or font_stats.is_bold
        
        return TextBlock(
            text=combined_text,
            bbox=tuple(block["bbox"]),
            font_stats=font_stats,
            is_heading_candidate=is_heading,
            block_type="text",
        )
    
    def _render_page_image(self, page: fitz.Page) -> Optional[str]:
        """Render a page as a base64-encoded PNG data URL."""
        try:
            # Render at specified DPI
            mat = fitz.Matrix(self.image_dpi / 72, self.image_dpi / 72)
            pix = page.get_pixmap(matrix=mat)
            
            # Convert to PIL Image
            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            
            # Compress to JPEG for smaller size
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=85)
            buffer.seek(0)
            
            # Encode as base64 data URL
            b64_data = base64.b64encode(buffer.read()).decode("utf-8")
            return f"data:image/jpeg;base64,{b64_data}"
            
        except Exception as e:
            logger.error(f"Error rendering page image: {str(e)}")
            return None
    
    def extract_from_bytes(self, pdf_bytes: bytes) -> ExtractionResult:
        """
        Extract from PDF bytes instead of file path.
        
        Args:
            pdf_bytes: Raw PDF file bytes
            
        Returns:
            ExtractionResult with blocks, linear text, and page images
        """
        result = ExtractionResult()
        all_text_lines = []
        
        try:
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            result.metadata = {
                "page_count": len(doc),
                "title": doc.metadata.get("title", ""),
                "author": doc.metadata.get("author", ""),
            }
            
            for page_num in range(len(doc)):
                page = doc[page_num]
                page_extraction = self._extract_page(page, page_num)
                result.pages.append(page_extraction)
                
                for block in page_extraction.blocks:
                    if block.text.strip():
                        all_text_lines.append(block.text.strip())
                
                if page_num < self.max_image_pages:
                    image_b64 = self._render_page_image(page)
                    if image_b64:
                        result.page_images.append(image_b64)
            
            doc.close()
            result.fulltext_linear = "\n".join(all_text_lines)
            
        except Exception as e:
            logger.error(f"Error extracting PDF from bytes: {str(e)}")
            raise
        
        return result


# Module-level instance for convenience
resume_extractor = ResumeExtractorPyMuPDF()
