import React, { useState, useEffect, useRef, useCallback, useLayoutEffect } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkMath from 'remark-math'
import remarkGfm from 'remark-gfm'
import rehypeKatex from 'rehype-katex'
import { Copy, Check, ChevronDown, ChevronUp, Bot, User, FileText, FileDown, FileCode, Download } from 'lucide-react'
import { jsPDF } from 'jspdf'
import html2canvas from 'html2canvas'
import { preprocessLaTeX, parseMessageContent } from '../utils/chatUtils'

import ErrorBoundary from './ErrorBoundary'

const MessageFooter = ({ role, onCopy, onToggleExpand, isExpanded, isOverflow, copiedId, idx, onExportMD, onExportPDF, onExportLaTeX }) => {
    const [showMenu, setShowMenu] = useState(false)

    return (
        <div className="message-footer">
            {isOverflow && (
                <button className="footer-btn expand-toggle" onClick={onToggleExpand} title={isExpanded ? "Thu gọn" : "Xem thêm"}>
                    {isExpanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
                </button>
            )}
            <div className="footer-actions-right">
                <button
                    onClick={onCopy}
                    title="Sao chép"
                    className={`footer-btn copy-btn ${copiedId === idx ? 'copied' : ''}`}
                >
                    {copiedId === idx ? <Check size={16} /> : <Copy size={16} />}
                    {copiedId === idx && <span className="copy-toast">Đã copy</span>}
                </button>

                {role === 'assistant' && (
                    <div className="export-dropdown-wrapper">
                        <button
                            className="footer-btn export-trigger"
                            onClick={() => setShowMenu(!showMenu)}
                            title="Tải về"
                        >
                            <Download size={16} />
                        </button>
                        {showMenu && (
                            <div className="export-menu" onMouseLeave={() => setShowMenu(false)}>
                                <button onClick={() => { onExportMD(); setShowMenu(false); }}>
                                    <FileText size={14} /> <span>Markdown (.md)</span>
                                </button>
                                <button onClick={() => { onExportLaTeX(); setShowMenu(false); }}>
                                    <FileCode size={14} /> <span>LaTeX (.tex)</span>
                                </button>
                                <button onClick={() => { onExportPDF(); setShowMenu(false); }}>
                                    <FileDown size={14} /> <span>PDF (.pdf)</span>
                                </button>
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    )
}

const CollapsibleContent = ({ content, messageId, maxLines = 12, isStreaming = false, children }) => {
    const [expanded, setExpanded] = useState(() => {
        if (!messageId) return false
        return localStorage.getItem(messageId) === 'true'
    })
    // Maintain expanded state after streaming finishes for the current session
    const [wasStreaming, setWasStreaming] = useState(false)

    useEffect(() => {
        if (isStreaming && !wasStreaming) {
            setWasStreaming(true)
            setExpanded(true)
        }
    }, [isStreaming, wasStreaming])

    const [isOverflow, setIsOverflow] = useState(false)
    const contentRef = useRef(null)

    useEffect(() => {
        if (contentRef.current) {
            const lineHeight = parseFloat(getComputedStyle(contentRef.current).lineHeight)
            const maxHeight = lineHeight * maxLines
            setIsOverflow(contentRef.current.scrollHeight > maxHeight + 10)
        }
    }, [content, maxLines])

    const toggleExpand = () => {
        const nextState = !expanded
        setExpanded(nextState)
        if (messageId) {
            localStorage.setItem(messageId, String(nextState))
        }
    }

    return (
        <div className={`collapsible-content ${expanded ? 'expanded' : ''} ${isOverflow && !expanded ? 'truncated' : ''}`}>
            <div
                ref={contentRef}
                className="content-inner message-content"
                style={(!expanded && isOverflow && !isStreaming) ? { maxHeight: `${maxLines * 1.7}em`, overflow: 'hidden' } : {}}
            >
                <ErrorBoundary>
                    <ReactMarkdown
                        remarkPlugins={[remarkMath, remarkGfm]}
                        rehypePlugins={[[rehypeKatex, { strict: false, trust: true, throwOnError: false }]]}
                        components={{
                            a: ({ node, ...props }) => <a {...props} target="_blank" rel="noopener noreferrer" />
                        }}
                    >
                        {preprocessLaTeX(parseMessageContent(content))}
                    </ReactMarkdown>
                </ErrorBoundary>
            </div>
            {children({ isOverflow, isExpanded: expanded, onToggleExpand: toggleExpand })}
        </div>
    )
}

const MessageList = ({
    messages,
    isLoading,
    conversationId,
    onExampleClick,
    onImageClick,
    userAvatar,
    userName = 'User'
}) => {
    const messagesEndRef = useRef(null)
    const containerRef = useRef(null)
    const [showScrollBtn, setShowScrollBtn] = useState(false)
    const [isRestored, setIsRestored] = useState(false)
    const [isTransitioning, setIsTransitioning] = useState(false)
    const scrollPositionsRef = useRef({}) // Persistent in-memory scroll storage

    const prevConversationId = useRef(conversationId)
    const prevMessagesLengthRef = useRef(0)
    const prevStreamingRef = useRef(false)
    const [copiedId, setCopiedId] = useState(null)
    const pdfExportRef = useRef(null)
    const [exportingIndex, setExportingIndex] = useState(null)

    const scrollToBottom = (behavior = 'smooth') => {
        if (containerRef.current) {
            const container = containerRef.current
            if (behavior === 'smooth') {
                // Use requestAnimationFrame to ensure React has rendered the new content
                requestAnimationFrame(() => {
                    container.scrollTo({
                        top: container.scrollHeight,
                        behavior: 'smooth'
                    })
                })
            } else {
                container.scrollTop = container.scrollHeight
            }
        }
    }

    const handleScroll = useCallback(() => {
        if (containerRef.current && conversationId && isRestored && !isTransitioning) {
            const { scrollTop, scrollHeight, clientHeight } = containerRef.current
            // Save to both Ref (instant access) and SessionStorage (persistence)
            scrollPositionsRef.current[conversationId] = scrollTop
            sessionStorage.setItem(`scroll_${conversationId}`, String(scrollTop))
            setShowScrollBtn(scrollHeight - scrollTop - clientHeight > 100)
        }
    }, [conversationId, isRestored, isTransitioning])

    // Detect Session Change
    useLayoutEffect(() => {
        if (prevConversationId.current !== conversationId) {
            // Store current position before switching
            if (containerRef.current && prevConversationId.current) {
                scrollPositionsRef.current[prevConversationId.current] = containerRef.current.scrollTop
            }

            setIsRestored(false)
            setIsTransitioning(true)
            prevConversationId.current = conversationId
            prevMessagesLengthRef.current = 0
        }
    }, [conversationId])

    // Restore Scroll Position
    useLayoutEffect(() => {
        if (!containerRef.current || messages.length === 0 || !conversationId) {
            if (messages.length === 0 && conversationId) {
                setIsTransitioning(false) // No messages, nothing to restore
                setIsRestored(true)
            }
            return
        }
        if (isRestored) return

        const container = containerRef.current

        // Priority: Ref -> SessionStorage -> Bottom
        const savedScroll = scrollPositionsRef.current[conversationId] ??
            sessionStorage.getItem(`scroll_${conversationId}`)

        // Use 'auto' behavior for instant restoration (no jump)
        if (savedScroll !== null) {
            container.scrollTo({
                top: parseInt(savedScroll, 10),
                behavior: 'auto'
            })
        } else {
            container.scrollTo({
                top: container.scrollHeight,
                behavior: 'auto'
            })
        }

        // Force a layout reflow to ensure scroll is applied before showing
        void container.offsetHeight

        // If it's a session switch (isTransitioning), we use a small delay to hide the "jump"
        if (isTransitioning) {
            const timer = setTimeout(() => {
                setIsRestored(true)
                setIsTransitioning(false)
                prevMessagesLengthRef.current = messages.length
            }, 50)
            return () => clearTimeout(timer)
        } else {
            // --- REFRESH CASE (INITIAL LOAD) ---
            // Set isRestored to true to start animations
            // Set prevMessagesLength to 0 to make ALL messages animate from the start
            setIsRestored(true)
            prevMessagesLengthRef.current = 0
        }
    }, [messages.length, conversationId, isRestored, isTransitioning])

    const isInitialLoadRef = useRef(true)

    // Handle New Messages
    useEffect(() => {
        if (!isRestored || isTransitioning || messages.length === 0) return

        const isNewMessage = messages.length > prevMessagesLengthRef.current

        // If it's the initial load (refresh), we want animations but NOT auto-scroll
        if (isInitialLoadRef.current) {
            isInitialLoadRef.current = false
            prevMessagesLengthRef.current = messages.length
            return
        }

        const lastMessage = messages[messages.length - 1]
        const isUserMessage = lastMessage?.role === 'user'

        if (isNewMessage) {
            // Always scroll to bottom for user messages
            // For bot messages, only scroll if already at bottom (sticky)
            if (isUserMessage || !showScrollBtn) {
                scrollToBottom('smooth')
            }
        }

        prevMessagesLengthRef.current = messages.length
    }, [messages.length, showScrollBtn, isRestored, isTransitioning])

    // Auto-scroll during streaming to keep user's view locked on new content
    const lastMessageContent = messages[messages.length - 1]?.content
    const isLastMessageStreaming = messages[messages.length - 1]?.isStreaming

    useEffect(() => {
        if (!containerRef.current) return

        if (isLastMessageStreaming) {
            // "Sticky Scroll": Only auto-scroll if user is already near the bottom
            // !showScrollBtn means distance to bottom < 100px
            if (!showScrollBtn) {
                containerRef.current.scrollTop = containerRef.current.scrollHeight
            }
        } else if (prevStreamingRef.current) {
            // Just finished streaming - do one final sync to be sure
            // but only if the user didn't scroll too far up
            if (!showScrollBtn) {
                scrollToBottom('smooth')
            }
        }

        prevStreamingRef.current = isLastMessageStreaming
    }, [lastMessageContent, isLastMessageStreaming, showScrollBtn])

    const copyToClipboard = (text, idx) => {
        navigator.clipboard.writeText(text)
        setCopiedId(idx)
        setTimeout(() => setCopiedId(null), 2000)
    }

    const exportToMarkdown = (content, idx) => {
        const blob = new Blob([content], { type: 'text/markdown' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `chat-answer-${idx + 1}.md`
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        URL.revokeObjectURL(url)
    }

    const exportToLaTeX = (content, idx) => {
        const texContent = `\\documentclass{article}\n\\usepackage[utf8]{inputenc}\n\\usepackage{amsmath}\n\n\\begin{document}\n${content}\n\\end{document}`
        const blob = new Blob([texContent], { type: 'text/x-tex' })
        const url = URL.createObjectURL(blob)
        const a = document.createElement('a')
        a.href = url
        a.download = `chat-answer-${idx + 1}.tex`
        document.body.appendChild(a)
        a.click()
        document.body.removeChild(a)
        URL.revokeObjectURL(url)
    }

    const exportToPDF = async (idx) => {
        setExportingIndex(idx)

        // Wait for DOM to update the hidden element
        setTimeout(async () => {
            if (!pdfExportRef.current) return

            try {
                const canvas = await html2canvas(pdfExportRef.current, {
                    scale: 3,
                    useCORS: true,
                    backgroundColor: '#ffffff',
                    logging: false,
                })

                const imgData = canvas.toDataURL('image/png')
                const pdfWidth = 595.28
                const pdfHeight = 841.89
                const pdf = new jsPDF('p', 'pt', 'a4')

                const margin = 0 // Container already has padding
                const innerWidth = pdfWidth
                const imgProps = pdf.getImageProperties(imgData)
                const imgHeight = (imgProps.height * innerWidth) / imgProps.width

                let heightLeft = imgHeight
                let position = 0

                pdf.addImage(imgData, 'PNG', 0, position, innerWidth, imgHeight)
                heightLeft -= pdfHeight

                while (heightLeft >= 0) {
                    pdf.addPage()
                    position = heightLeft - imgHeight
                    pdf.addImage(imgData, 'PNG', 0, position, innerWidth, imgHeight)
                    heightLeft -= pdfHeight
                }

                pdf.save(`chat-answer-${idx + 1}.pdf`)
                setExportingIndex(null)
            } catch (error) {
                console.error('PDF Export failed:', error)
                setExportingIndex(null)
            }
        }, 100)
    }

    if (messages.length === 0) {
        return (
            <div className="welcome-screen">
                <div id="tour-chat-interface" className="tour-chat-spotlight"></div>
                <div className="welcome-icon">
                    <img src="/calculus-icon.png" alt="Icon" onError={(e) => e.target.style.display = 'none'} />
                    <div className="p-4 bg-indigo-100 rounded-full dark:bg-indigo-900/30" style={{ display: 'none' }}>
                        <Bot size={48} className="text-indigo-600 dark:text-indigo-400" />
                    </div>
                </div>
                <h2>Xin chào, tôi có thể giúp gì?</h2>
                <p>Tôi là Pochi, bạn đồng hành của bạn trong việc chinh phục môn toán giải tích.<br />Hãy bắt đầu bằng việc đặt câu hỏi cho tôi nhé!</p>
                <div className="example-prompts">
                    <button onClick={() => onExampleClick('Tính đạo hàm của hàm số y = x³ - 3x + 2')}>Tính đạo hàm của hàm số y = x³ - 3x + 2</button>
                    <button onClick={() => onExampleClick('Tính tích phân của hàm số f(x) = sin(x) từ 0 đến π')}>Tính tích phân của hàm số f(x) = sin(x) từ 0 đến π</button>
                    <button onClick={() => onExampleClick('Tìm cực trị của hàm số y = x⁴ - 2x²')}>Tìm cực trị của hàm số y = x⁴ - 2x²</button>
                </div>
            </div>
        )
    }

    return (
        <div className="messages-section">
            <div id="tour-chat-interface" className="tour-chat-spotlight"></div>
            <div
                className={`messages-container ${isTransitioning ? 'transitioning' : ''}`}
                ref={containerRef}
                onScroll={handleScroll}
            >
                {messages.map((msg, idx) => (
                    <div
                        key={`${idx}-${msg.role}`}
                        className={`message ${msg.role} ${msg.isStreaming ? 'streaming' : ''} ${isRestored && idx >= prevMessagesLengthRef.current - 1 ? 'animate-msg-slide-up' : ''}`}
                        style={{ animationDelay: isRestored ? `${Math.min((idx - (prevMessagesLengthRef.current - 1)) * 0.05, 0.5)}s` : '0s' }}
                    >
                        {/* Avatar removed */}

                        <div className="message-body">
                            {msg.status && <div className="agent-status-badge">{msg.status}</div>}
                            {msg.images && msg.images.length > 0 && (
                                <div className="message-images-list">
                                    {msg.images.map((src, i) => (
                                        <div key={i} className="message-image-preview" onClick={() => onImageClick(msg.images, i)}>
                                            <img src={src} alt={`Attachment ${i}`} />
                                        </div>
                                    ))}
                                </div>
                            )}

                            {msg.content ? (
                                <CollapsibleContent
                                    content={msg.content}
                                    messageId={conversationId ? `expand_${conversationId}_${idx}` : null}
                                    isStreaming={msg.isStreaming}
                                >
                                    {({ isOverflow, isExpanded, onToggleExpand }) => (
                                        <MessageFooter
                                            role={msg.role}
                                            isOverflow={isOverflow}
                                            isExpanded={isExpanded}
                                            onToggleExpand={onToggleExpand}
                                            onCopy={() => copyToClipboard(msg.content, idx)}
                                            onExportMD={() => exportToMarkdown(msg.content, idx)}
                                            onExportPDF={() => exportToPDF(idx)}
                                            onExportLaTeX={() => exportToLaTeX(msg.content, idx)}
                                            copiedId={copiedId}
                                            idx={idx}
                                        />
                                    )}
                                </CollapsibleContent>
                            ) : msg.role === 'assistant' ? (
                                <div className="thinking-indicator"><span></span><span></span><span></span>Đang suy nghĩ...</div>
                            ) : (
                                <span className="text-gray-400 italic">...</span>
                            )}
                        </div>
                    </div>
                ))}
                <div ref={messagesEndRef} />
            </div>

            {/* Hidden Premium PDF Layout Component */}
            {exportingIndex !== null && (
                <div className="pdf-export-container" ref={pdfExportRef}>
                    {/* Background Watermark */}
                    <div className="pdf-watermark">POCHI</div>

                    <div className="pdf-header">
                        <div className="pdf-brand">POCHI</div>
                        <div className="pdf-meta">
                            <div>Assistant Export</div>
                            <div>{new Date().toLocaleDateString('vi-VN')}</div>
                        </div>
                    </div>
                    <div className="pdf-content">
                        <ReactMarkdown
                            remarkPlugins={[remarkMath, remarkGfm]}
                            rehypePlugins={[[rehypeKatex, { strict: false, trust: true, throwOnError: false }]]}
                        >
                            {preprocessLaTeX(parseMessageContent(messages[exportingIndex].content))}
                        </ReactMarkdown>
                    </div>
                    <div className="pdf-footer">
                        Tài liệu được tạo bởi Pochi
                    </div>
                </div>
            )}

            {showScrollBtn && (
                <button className="scroll-to-bottom" onClick={() => scrollToBottom('smooth')}>
                    <ChevronDown size={20} />
                </button>
            )}
        </div>
    )
}

export default MessageList
