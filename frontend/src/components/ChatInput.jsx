import React, { useRef, useState, useCallback, useEffect } from 'react'
import { useDropzone } from 'react-dropzone'
import { Send, Plus, X, ImageIcon, Paperclip, UploadCloud } from 'lucide-react'

const MAX_IMAGES = 5

const ChatInput = ({ onSendMessage, isLoading, onImageClick }) => {
    const [input, setInput] = useState(() => sessionStorage.getItem('chat_draft') || '')
    const [uploadedImages, setUploadedImages] = useState([])
    const [showAttachMenu, setShowAttachMenu] = useState(false)
    const [uploadError, setUploadError] = useState('')
    const textareaRef = useRef(null)

    // Draft persistence
    useEffect(() => {
        sessionStorage.setItem('chat_draft', input)
    }, [input])

    // Initial image restoration
    useEffect(() => {
        const savedImages = sessionStorage.getItem('chat_images')
        if (savedImages) {
            try {
                const parsed = JSON.parse(savedImages)
                const restored = parsed.map(img => {
                    // Convert base64 back to Blob/File if needed, or just use data URL as preview
                    return {
                        file: null, // Original file is lost on refresh, but we have the data
                        preview: img.data,
                        name: img.name,
                        type: img.type
                    }
                })
                setUploadedImages(restored)
            } catch (e) {
                console.error('Failed to restore images:', e)
            }
        }
    }, [])

    // Image persistence (Base64)
    useEffect(() => {
        if (uploadedImages.length === 0) {
            sessionStorage.removeItem('chat_images')
            return
        }

        // Only save images that have a preview (base64 or blob URL)
        // If it's a blob URL, it won't survive refresh, so we need to ensure they are base64 when adding
        const persistImages = async () => {
            const dataToSave = await Promise.all(uploadedImages.map(async (img) => {
                if (img.preview.startsWith('data:')) {
                    return { name: img.name, type: img.type, data: img.preview }
                }
                // If it's a blob URL, we should have converted it already on drop
                return { name: img.name, type: img.type, data: img.preview }
            }))
            sessionStorage.setItem('chat_images', JSON.stringify(dataToSave))
        }
        persistImages()
    }, [uploadedImages])

    // Auto-resize textarea
    useEffect(() => {
        if (textareaRef.current) {
            textareaRef.current.style.height = 'auto'
            textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 200) + 'px'
        }
    }, [input])

    // Clear error after 3 seconds
    useEffect(() => {
        if (uploadError) {
            const timer = setTimeout(() => setUploadError(''), 3000)
            return () => clearTimeout(timer)
        }
    }, [uploadError])

    // Close menu when clicking outside
    useEffect(() => {
        const handleClickOutside = (e) => {
            if (showAttachMenu && !e.target.closest('.attach-btn-wrapper')) {
                setShowAttachMenu(false)
            }
        }
        document.addEventListener('mousedown', handleClickOutside)
        return () => document.removeEventListener('mousedown', handleClickOutside)
    }, [showAttachMenu])

    const handleKeyDown = (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault()
            handleSubmit()
        }
    }

    const onDrop = useCallback((acceptedFiles) => {
        const processFiles = async () => {
            const newImagesPromises = acceptedFiles.map(file => {
                return new Promise((resolve) => {
                    const reader = new FileReader()
                    reader.onloadend = () => {
                        resolve({
                            file,
                            preview: reader.result,
                            name: file.name,
                            type: file.type
                        })
                    }
                    reader.readAsDataURL(file)
                })
            })

            const newImages = await Promise.all(newImagesPromises)

            setUploadedImages(prev => {
                const remaining = MAX_IMAGES - prev.length
                if (remaining <= 0) {
                    setUploadError(`Bạn chỉ được tải tối đa ${MAX_IMAGES} ảnh`)
                    return prev
                }
                if (newImages.length > remaining) {
                    setUploadError(`Chỉ nhận thêm ${remaining} ảnh cuối cùng`)
                }
                return [...prev, ...newImages.slice(0, remaining)]
            })
        }

        processFiles()
        setShowAttachMenu(false)
    }, [])

    const { getRootProps, getInputProps, isDragActive, open: openFilePicker } = useDropzone({
        onDrop,
        accept: { 'image/*': ['.png', '.jpg', '.jpeg', '.gif', '.webp'] },
        maxFiles: MAX_IMAGES,
        noClick: true,
        noKeyboard: true,
        disabled: uploadedImages.length >= MAX_IMAGES,
    })

    const removeImage = (index) => {
        setUploadedImages(prev => prev.filter((_, i) => i !== index))
    }

    const clearAllImages = () => {
        setUploadedImages([])
    }

    const handleSubmit = () => {
        if ((!input.trim() && uploadedImages.length === 0) || isLoading) return

        onSendMessage(input, uploadedImages)

        // Clear persistence
        setInput('')
        setUploadedImages([])
        sessionStorage.removeItem('chat_draft')
        sessionStorage.removeItem('chat_images')

        if (textareaRef.current) textareaRef.current.style.height = 'auto'
    }

    return (
        <div className="input-container">
            {/* Image Previews & Counter */}
            {uploadedImages.length > 0 && (
                <div className="image-attachment-area">
                    <div className="attachment-header">
                        <span className="attachment-counter">
                            Đã đính kèm: <strong>{uploadedImages.length}/{MAX_IMAGES}</strong> ảnh
                        </span>
                        <button type="button" className="clear-all-btn" onClick={clearAllImages}>
                            Xóa hết
                        </button>
                    </div>
                    <div className="uploaded-images-preview">
                        {uploadedImages.map((img, idx) => (
                            <div
                                key={idx}
                                className="preview-item clickable"
                                onClick={() => onImageClick?.(uploadedImages.map(img => img.preview), idx)}
                                title="Xem ảnh lớn"
                            >
                                <img src={img.preview} alt={`Preview ${idx + 1}`} />
                                <button
                                    type="button"
                                    className="remove-img-btn"
                                    onClick={(e) => {
                                        e.stopPropagation()
                                        removeImage(idx)
                                    }}
                                    title="Xóa ảnh"
                                >
                                    <X size={12} />
                                </button>
                            </div>
                        ))}
                    </div>
                </div>
            )}

            {/* Upload Error Message */}
            {uploadError && (
                <div className="upload-error-toast">
                    {uploadError}
                </div>
            )}

            <div className={`input-wrapper ${isLoading ? 'opacity-50' : ''}`} {...getRootProps()} id="tour-chat-input-area">
                <input {...getInputProps()} />

                {/* Drag Overlay - Compact & Premium */}
                {isDragActive && (
                    <div className="drag-overlay">
                        <div className="drag-content">
                            <UploadCloud size={24} className="drag-icon" />
                            <span className="drag-text">Thả ảnh vào đây</span>
                        </div>
                    </div>
                )}

                <div className="attach-btn-wrapper">
                    <button
                        type="button"
                        className="attach-btn"
                        onClick={(e) => {
                            e.stopPropagation();
                            setShowAttachMenu(!showAttachMenu);
                        }}
                        title="Đính kèm"
                        id="tour-attach"
                    >
                        <Plus size={20} className={showAttachMenu ? 'rotate-45 transition-transform' : 'transition-transform'} />
                    </button>

                    {showAttachMenu && (
                        <div className="attachment-menu">
                            <button type="button" onClick={(e) => { e.stopPropagation(); openFilePicker(); setShowAttachMenu(false) }}>
                                <ImageIcon size={18} /> Ảnh/Video
                            </button>
                            <button type="button" onClick={(e) => { e.stopPropagation(); setShowAttachMenu(false) }} className="opacity-50 cursor-not-allowed">
                                <Paperclip size={18} /> Tài liệu (Sắp ra mắt)
                            </button>
                        </div>
                    )}
                </div>

                <textarea
                    ref={textareaRef}
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    onKeyDown={handleKeyDown}
                    placeholder="Nhập tin nhắn..."
                    rows={1}
                    disabled={isLoading}
                    id="tour-chat-input"
                />

                <button
                    type="button"
                    className="send-btn"
                    onClick={(e) => {
                        e.stopPropagation(); // Prevent bubbling to dropzone
                        handleSubmit();
                    }}
                    disabled={isLoading || (!input.trim() && uploadedImages.length === 0)}
                    title="Gửi"
                    id="tour-send"
                >
                    <Send size={18} />
                </button>
            </div>

            <p className="input-hint">
                Pochi không phải lúc nào cũng đúng. Hãy tập thói quen double check nhé!
            </p>
        </div>
    )
}

export default ChatInput
