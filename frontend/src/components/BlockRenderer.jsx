/**
 * BlockRenderer - Renders structured message blocks
 * NO hardcoded parsing - only handles proper JSON blocks from backend
 */
import { useMemo } from 'react'
import { BlockMath, InlineMath } from 'react-katex'
import 'katex/dist/katex.min.css'

/**
 * Render a TextBlock - plain text
 */
const TextBlock = ({ content }) => {
    if (!content) return null
    return <p className="text-block">{content}</p>
}

/**
 * Render a MathBlock - KaTeX for math expressions
 * Accepts either 'latex' or 'content' prop for compatibility
 */
const MathBlockRenderer = ({ latex, content, display = 'block' }) => {
    // Support both 'latex' and 'content' field names
    const mathContent = latex || content
    if (!mathContent) return null

    try {
        if (display === 'inline') {
            return <InlineMath math={mathContent} />
        }
        return (
            <div className="math-block-container">
                <BlockMath math={mathContent} />
            </div>
        )
    } catch (error) {
        console.error('KaTeX render error:', error)
        return <code className="math-error">{mathContent}</code>
    }
}

/**
 * Render a ListBlock - ordered or unordered list
 */
const ListBlockRenderer = ({ items, ordered = false }) => {
    if (!items || !items.length) return null

    const ListTag = ordered ? 'ol' : 'ul'
    return (
        <ListTag className="list-block">
            {items.map((item, idx) => (
                <li key={idx}>{item}</li>
            ))}
        </ListTag>
    )
}

/**
 * Render a CodeBlock - syntax highlighted code
 */
const CodeBlockRenderer = ({ content, language = 'python' }) => {
    if (!content) return null
    return (
        <pre className="code-block">
            <code className={`language-${language}`}>{content}</code>
        </pre>
    )
}

/**
 * Render a StepBlock - solution step with nested blocks
 */
const StepBlockRenderer = ({ index, title, blocks }) => {
    return (
        <div className="step-block">
            <div className="step-header">
                <span className="step-number">{index}</span>
                <span className="step-title">{title}</span>
            </div>
            <div className="step-content">
                {blocks && blocks.map((block, idx) => (
                    <BlockRenderer key={idx} block={block} />
                ))}
            </div>
        </div>
    )
}

/**
 * Main BlockRenderer - dispatches to appropriate renderer based on block type
 */
const BlockRenderer = ({ block }) => {
    if (!block || !block.type) return null

    switch (block.type) {
        case 'text':
            return <TextBlock content={block.content} />

        case 'math':
            // Support both 'latex' and 'content' fields
            return <MathBlockRenderer latex={block.latex} content={block.content} display={block.display} />

        case 'list':
            return <ListBlockRenderer items={block.items} ordered={block.ordered} />

        case 'code':
            return <CodeBlockRenderer content={block.content} language={block.language} />

        case 'step':
            return <StepBlockRenderer index={block.index} title={block.title} blocks={block.blocks} />

        default:
            console.warn('Unknown block type:', block.type)
            return <p className="text-block">{JSON.stringify(block)}</p>
    }
}

/**
 * MessageBlocks - Renders an array of blocks for a message
 * Only parses JSON - no hardcoded fallback parsing
 */
export const MessageBlocks = ({ content }) => {
    const blocks = useMemo(() => {
        if (!content) return []

        try {
            // Parse JSON blocks from backend
            const parsed = typeof content === 'string' ? JSON.parse(content) : content
            if (parsed.blocks && Array.isArray(parsed.blocks)) {
                return parsed.blocks
            }
            // If no blocks array, wrap as single text block
            return [{ type: 'text', content: String(content) }]
        } catch {
            // JSON parse failed - backend didn't return proper format
            // Show as plain text (no regex processing)
            return [{ type: 'text', content: String(content) }]
        }
    }, [content])

    if (!blocks.length) return null

    return (
        <div className="message-blocks">
            {blocks.map((block, idx) => (
                <BlockRenderer key={idx} block={block} />
            ))}
        </div>
    )
}

export default BlockRenderer
