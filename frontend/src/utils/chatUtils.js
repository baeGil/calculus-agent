/**
 * Preprocess LaTeX content to ensure proper rendering
 * Convert \[...\] to $$...$$ and \(...\) to $...$
 */
export const preprocessLaTeX = (content) => {
    if (!content) return ''
    let processed = content

    // Convert \[...\] to $$...$$ (display math)
    processed = processed.replace(/\\\[([\s\S]*?)\\\]/g, (match, math) => `$$${math}$$`)

    // Convert \(...\) to $...$ (inline math)
    processed = processed.replace(/\\\(([\s\S]*?)\\\)/g, (match, math) => `$${math}$`)

    return processed
}

/**
 * Parse message content - handles both legacy JSON blocks and new plain markdown
 */
export const parseMessageContent = (content) => {
    if (!content) return ''
    if (content.trim().startsWith('{') && content.includes('"blocks"')) {
        try {
            const parsed = JSON.parse(content)
            if (parsed.blocks && Array.isArray(parsed.blocks)) {
                return parsed.blocks.map(block => {
                    if (block.type === 'text') return block.content || ''
                    else if (block.type === 'math') {
                        const latex = block.latex || block.content || ''
                        const display = block.display === 'inline' ? '$' : '$$'
                        return `${display}${latex}${display}`
                    } else if (block.type === 'list') {
                        const items = block.items || []
                        return items.map((item, i) => `${block.ordered ? `${i + 1}.` : '-'} ${item}`).join('\n')
                    }
                    return ''
                }).join('\n\n')
            }
        } catch { /* Not valid JSON */ }
    }
    return content.replace(/\\n/g, '\n')
}
