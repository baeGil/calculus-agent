"""
Simplified block-based message schemas for structured LLM output.
Only TextBlock and MathBlock for maximum reliability.
"""
from typing import Literal, Optional
from pydantic import BaseModel, Field
import re


class SimpleBlock(BaseModel):
    """A content block - either text or math."""
    type: Literal["text", "math"]
    content: str = Field(description="Text content or LaTeX formula (without $ delimiters)")
    display: Optional[Literal["inline", "block"]] = Field(
        default="block",
        description="For math: 'block' for display math, 'inline' for inline math"
    )


class SimpleResponse(BaseModel):
    """
    Simplified agent response schema.
    Much easier for LLM to follow than complex nested types.
    """
    thinking: Optional[str] = Field(None, description="Agent's reasoning process")
    
    # Tool call fields
    tool: Optional[Literal["wolfram", "code"]] = Field(None, description="Tool to use")
    tool_input: Optional[str] = Field(None, description="Input for the tool")
    
    # Direct answer as simple blocks
    blocks: Optional[list[SimpleBlock]] = Field(
        None, 
        description="List of content blocks. Each block is either 'text' (plain Vietnamese) or 'math' (LaTeX formula)"
    )


class SimpleMessageBlocks(BaseModel):
    """Container for message blocks."""
    blocks: list[SimpleBlock] = Field(default_factory=list)


def parse_text_to_blocks(text: str) -> list[dict]:
    """
    General parser: Convert raw text with LaTeX markers into blocks.
    This is NOT hardcoded for specific cases - it handles any text with:
    - $$...$$ for block math
    - $...$ for inline math
    - \\[...\\] for display math
    - \\(...\\) for inline math
    - Plain text for everything else
    
    Returns list of block dicts ready for JSON serialization.
    """
    if not text or not text.strip():
        return [{"type": "text", "content": text or "", "display": None}]
    
    # Normalize LaTeX display math notations to $$...$$
    processed = text
    processed = re.sub(r'\\\[([\s\S]*?)\\\]', r'$$\1$$', processed)
    processed = re.sub(r'\\\(([\s\S]*?)\\\)', r'$\1$', processed)
    
    # Handle \begin{...}\end{...} environments - convert to display math
    processed = re.sub(
        r'\\begin\{(equation|aligned|align|cases|gather)\}([\s\S]*?)\\end\{\1\}',
        lambda m: f'$${m.group(2)}$$',
        processed
    )
    
    blocks = []
    
    # Split by block math first ($$...$$)
    # This regex captures both the math and the surrounding text
    pattern_block = r'(\$\$[\s\S]*?\$\$)'
    parts = re.split(pattern_block, processed)
    
    for part in parts:
        if not part.strip():
            continue
            
        # Check if this is block math
        if part.startswith('$$') and part.endswith('$$'):
            latex = part[2:-2].strip()
            if latex:
                blocks.append({
                    "type": "math",
                    "content": latex,
                    "display": "block"
                })
        else:
            # Process text with potential inline math ($...$)
            # Split by inline math
            pattern_inline = r'(\$[^$\n]+\$)'
            inline_parts = re.split(pattern_inline, part)
            
            current_text = ""
            for inline_part in inline_parts:
                if not inline_part:
                    continue
                    
                # Check if inline math
                if inline_part.startswith('$') and inline_part.endswith('$') and len(inline_part) > 2:
                    # First, add accumulated text
                    if current_text.strip():
                        blocks.append({
                            "type": "text",
                            "content": current_text.strip(),
                            "display": None
                        })
                        current_text = ""
                    
                    # Add inline math
                    latex = inline_part[1:-1].strip()
                    if latex:
                        blocks.append({
                            "type": "math",
                            "content": latex,
                            "display": "inline"
                        })
                else:
                    current_text += inline_part
            
            # Add remaining text
            if current_text.strip():
                blocks.append({
                    "type": "text",
                    "content": current_text.strip(),
                    "display": None
                })
    
    return blocks if blocks else [{"type": "text", "content": text, "display": None}]


def ensure_valid_blocks(response_blocks: list[SimpleBlock] | None, raw_content: str = "") -> list[dict]:
    """
    Ensure we have valid blocks.
    Parse any text block that contains LaTeX markers.
    """
    if not response_blocks:
        return parse_text_to_blocks(raw_content) if raw_content else []
    
    result_blocks = []
    
    for block in response_blocks:
        block_data = block.model_dump()
        
        # If it's a text block with LaTeX markers, parse it
        if block_data["type"] == "text":
            content = block_data.get("content", "")
            # Check for LaTeX markers
            if '$' in content or '\\[' in content or '\\begin' in content:
                # Parse this text block into multiple blocks
                parsed = parse_text_to_blocks(content)
                result_blocks.extend(parsed)
            else:
                result_blocks.append(block_data)
        else:
            result_blocks.append(block_data)
    
    return result_blocks if result_blocks else [{"type": "text", "content": raw_content or "", "display": None}]

