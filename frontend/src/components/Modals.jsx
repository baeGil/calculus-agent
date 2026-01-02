import React, { useState, useEffect, useMemo } from 'react'
import { Search, X, MessageSquare, Clock, ChevronLeft, ChevronRight, ZoomIn, ZoomOut, Maximize, Download, RotateCcw, Settings, User, Sun, Edit, Archive } from 'lucide-react'

export const SearchModal = ({ onSelect, onClose, conversations = [], isRestored = false }) => {
    // Lock in the initial isRestored value to prevent re-triggering animations if App re-renders
    const [wasRestored] = useState(isRestored)

    const [query, setQuery] = useState(() => {
        return sessionStorage.getItem('searchQuery') || ''
    })
    const [results, setResults] = useState([])
    const [isLoading, setIsLoading] = useState(false)
    const [debouncedQuery, setDebouncedQuery] = useState('')

    useEffect(() => {
        sessionStorage.setItem('searchQuery', query)
        const timer = setTimeout(() => setDebouncedQuery(query), 300)
        return () => clearTimeout(timer)
    }, [query])

    useEffect(() => {
        if (!debouncedQuery || debouncedQuery.trim().length < 1) {
            setResults([])
            return
        }
        const fetchResults = async () => {
            setIsLoading(true)
            try {
                const res = await fetch(`/api/search?q=${encodeURIComponent(debouncedQuery)}`)
                if (res.ok) {
                    const data = await res.json()
                    setResults(data)
                }
            } catch (error) {
                console.error("Search failed", error)
            } finally {
                setIsLoading(false)
            }
        }
        fetchResults()
    }, [debouncedQuery])

    const groupedConversations = React.useMemo(() => {
        if (query.trim().length >= 1) return null;
        const groups = { today: [], yesterday: [], last7Days: [], older: [] }
        const now = new Date()
        const today = new Date(now.getFullYear(), now.getMonth(), now.getDate())
        const yesterday = new Date(today)
        yesterday.setDate(yesterday.getDate() - 1)
        const last7Days = new Date(today)
        last7Days.setDate(last7Days.getDate() - 7)

        conversations.forEach(conv => {
            const dateStr = conv.updated_at || conv.created_at
            if (!dateStr) { groups.older.push(conv); return; }
            const date = new Date(dateStr)
            if (date >= today) groups.today.push(conv)
            else if (date >= yesterday) groups.yesterday.push(conv)
            else if (date >= last7Days) groups.last7Days.push(conv)
            else groups.older.push(conv)
        })
        return groups
    }, [conversations, query])

    useEffect(() => {
        const handleEsc = (e) => { if (e.key === 'Escape') onClose() }
        window.addEventListener('keydown', handleEsc)
        return () => window.removeEventListener('keydown', handleEsc)
    }, [onClose])

    const highlightText = (text, highlight) => {
        if (!highlight) return text

        // Function to strip Vietnamese accents for matching
        const stripAccents = (str) => {
            return str.normalize('NFD')
                .replace(/[\u0300-\u036f]/g, "")
                .replace(/đ/g, "d")
                .replace(/Đ/g, "D");
        }

        const normalizedText = stripAccents(text.toLowerCase())
        const normalizedQuery = stripAccents(highlight.toLowerCase())

        if (!normalizedText.includes(normalizedQuery)) return text

        const parts = []
        let lastIdx = 0
        let idx = normalizedText.indexOf(normalizedQuery)

        while (idx !== -1) {
            // Push non-matching part
            parts.push(text.substring(lastIdx, idx))
            // Push matching part with original formatting
            const matchedContent = text.substring(idx, idx + highlight.length)
            parts.push(
                <span key={idx} className="bg-brand-primary/20 text-brand-primary rounded px-0.5">
                    {text.substring(idx, idx + highlight.length)}
                </span>
            )
            lastIdx = idx + highlight.length
            idx = normalizedText.indexOf(normalizedQuery, lastIdx)
        }
        parts.push(text.substring(lastIdx))

        return parts
    }

    const renderGroup = (title, items) => {
        if (!items || items.length === 0) return null
        return (
            <div className="search-group">
                <h3 className="group-title">{title}</h3>
                <div className="group-items">
                    {items.map(conv => (
                        <button
                            key={conv.id}
                            onClick={() => { onSelect(conv.id); onClose(); }}
                            className="search-result-item"
                        >
                            <div className="item-icon">
                                <MessageSquare size={14} />
                            </div>
                            <span className="item-title truncate">{conv.title || 'Đoạn chat mới'}</span>
                        </button>
                    ))}
                </div>
            </div>
        )
    }

    return (
        <div className={`modal-overlay centered ${wasRestored ? 'no-animation' : ''}`} onClick={onClose}>
            <div className={`search-modal-container glass ${wasRestored ? 'no-animation' : ''}`} onClick={e => e.stopPropagation()}>
                <div className="search-modal-header">
                    <Search className="w-5 h-5 text-text-tertiary" />
                    <input
                        type="text"
                        placeholder="Tìm kiếm tin nhắn, hội thoại..."
                        className="search-input"
                        value={query}
                        onChange={e => setQuery(e.target.value)}
                        autoFocus
                    />
                    <div className="search-shortcut">ESC</div>
                </div>

                <div className="search-modal-content custom-scrollbar">
                    {query.trim().length >= 1 ? (
                        <div className="p-2">
                            {results.length > 0 ? (
                                <div className="flex flex-col gap-1">
                                    {results.map((item) => (
                                        <button
                                            key={`${item.type}-${item.id}`}
                                            onClick={() => { onSelect(item.conversation_id || item.id); onClose(); }}
                                            className="search-result-item"
                                        >
                                            <div className="item-icon">
                                                {item.type === 'conversation' ? <MessageSquare size={14} /> : <Search size={14} />}
                                            </div>
                                            <div className="flex-1 min-w-0">
                                                <div className="flex items-center justify-between gap-2">
                                                    <span className="item-title font-medium text-sm truncate">{highlightText(item.title, debouncedQuery)}</span>
                                                    <span className="item-date text-[10px] opacity-40 uppercase">{new Date(item.created_at).toLocaleDateString()}</span>
                                                </div>
                                                {item.content && (
                                                    <p className="text-xs opacity-60 line-clamp-1 mt-0.5">{highlightText(item.content, debouncedQuery)}</p>
                                                )}
                                            </div>
                                        </button>
                                    ))}
                                </div>
                            ) : (!isLoading && query.trim() === debouncedQuery.trim()) ? (
                                <div className="empty-state">Không tìm thấy kết quả nào cho "{query}"</div>
                            ) : null}
                        </div>
                    ) : (
                        <div className="py-2">
                            {groupedConversations && Object.entries(groupedConversations).map(([key, items]) => {
                                const labels = { today: 'Hôm nay', yesterday: 'Hôm qua', last7Days: '7 ngày qua', older: 'Cũ hơn' }
                                return renderGroup(labels[key], items)
                            })}
                        </div>
                    )}
                </div>
            </div>
        </div>
    )
}

export const SettingsModal = ({
    onClose,
    darkMode,
    onToggleTheme,
    archivedSessions = [],
    onRestoreSession,
    onUpdateProfile,
    userProfile,
    initialTab = 'general',
    isRestored = false,
    onTabChange
}) => {
    // Lock in the initial isRestored value to prevent re-triggering animations if App re-renders
    const [wasRestored] = useState(isRestored)

    const [activeTab, setActiveTab] = useState(initialTab)
    const [editName, setEditName] = useState(userProfile.name)
    const [editEmail, setEditEmail] = useState(userProfile.email)
    const [editAvatar, setEditAvatar] = useState(userProfile.avatar)
    const [isSaving, setIsSaving] = useState(false)
    const [showUnsavedWarning, setShowUnsavedWarning] = useState(false)
    const [pendingAction, setPendingAction] = useState(null) // { type: 'tab', value: '...' } or { type: 'close' }

    const tabs = [
        { id: 'general', label: 'Chung', icon: Settings },
        { id: 'account', label: 'Tài khoản', icon: User },
        { id: 'appearance', label: 'Giao diện', icon: Sun },
        { id: 'archived', label: 'Lưu trữ', icon: Archive }
    ]

    const hasUnsavedChanges = useMemo(() => {
        return editName !== userProfile.name ||
            editEmail !== userProfile.email ||
            editAvatar !== userProfile.avatar
    }, [editName, editEmail, editAvatar, userProfile])

    const handleTabClick = (tabId) => {
        if (activeTab === 'account' && hasUnsavedChanges) {
            setPendingAction({ type: 'tab', value: tabId })
            setShowUnsavedWarning(true)
        } else {
            setActiveTab(tabId)
            if (onTabChange) onTabChange(tabId)
        }
    }

    const handleCloseClick = () => {
        if (activeTab === 'account' && hasUnsavedChanges) {
            setPendingAction({ type: 'close' })
            setShowUnsavedWarning(true)
        } else {
            onClose()
        }
    }

    const handleDiscard = () => {
        // Reset local state to original
        setEditName(userProfile.name)
        setEditEmail(userProfile.email)
        setEditAvatar(userProfile.avatar)
        setShowUnsavedWarning(false)

        if (pendingAction.type === 'tab') {
            setActiveTab(pendingAction.value)
            if (onTabChange) onTabChange(pendingAction.value)
        } else if (pendingAction.type === 'close') {
            onClose()
        }
    }

    const handleSaveAndContinue = async () => {
        setIsSaving(true)
        await onUpdateProfile({ name: editName, email: editEmail, avatar: editAvatar })
        setIsSaving(false)
        setShowUnsavedWarning(false)

        if (pendingAction.type === 'tab') {
            setActiveTab(pendingAction.value)
        } else if (pendingAction.type === 'close') {
            onClose()
        }
    }

    return (
        <div className={`modal-overlay centered ${wasRestored ? 'no-animation' : ''}`} onClick={handleCloseClick}>
            <div className={`settings-container glass ${wasRestored ? 'no-animation' : ''}`} onClick={e => e.stopPropagation()}>
                {/* Sidebar Tabs */}
                <div className="settings-nav">
                    <div className="nav-title">Cài đặt</div>
                    <div className="nav-items">
                        {tabs.map(tab => (
                            <button
                                key={tab.id}
                                className={`nav-tab ${activeTab === tab.id ? 'active' : ''}`}
                                onClick={() => handleTabClick(tab.id)}
                            >
                                <tab.icon size={18} />
                                <span>{tab.label}</span>
                            </button>
                        ))}
                    </div>
                </div>

                <button className="body-close" onClick={handleCloseClick}><X size={20} /></button>

                {/* Main Content */}
                <div className="settings-body">

                    <div className="body-content custom-scrollbar">
                        <header className="content-header">
                            <h2>{tabs.find(t => t.id === activeTab).label}</h2>
                        </header>

                        {activeTab === 'general' && (
                            <div className="content-section">
                                <section className="setting-group">
                                    <div className="group-info">
                                        <h3>Dữ liệu huấn luyện</h3>
                                        <p>Đóng góp các cuộc hội thoại để cải thiện mô hình AI cho mọi người.</p>
                                    </div>
                                    <div className="group-action">
                                        <button className="toggle-pill on">Bật</button>
                                    </div>
                                </section>
                                <section className="setting-group">
                                    <div className="group-info">
                                        <h3>Lưu trữ hội thoại</h3>
                                        <p>Tự động lưu lịch sử chat vào tài khoản của bạn.</p>
                                    </div>
                                    <div className="group-action">
                                        <button className="toggle-pill on">Bật</button>
                                    </div>
                                </section>
                            </div>
                        )}

                        {activeTab === 'account' && (
                            <div className="content-section">
                                <div className="user-profile-card editing">
                                    <div className="card-avatar large">
                                        {editAvatar ? <img src={editAvatar} alt="Avatar" /> : <div className="avatar-placeholder large">{editName.charAt(0)}</div>}
                                        <label className="avatar-edit-overlay">
                                            <Edit size={16} />
                                            <span>Thay đổi</span>
                                            <input type="file" hidden accept="image/*" onChange={e => {
                                                const file = e.target.files[0]
                                                if (file) {
                                                    const reader = new FileReader()
                                                    reader.onloadend = () => {
                                                        setEditAvatar(reader.result)
                                                    }
                                                    reader.readAsDataURL(file)
                                                }
                                            }} />
                                        </label>
                                    </div>
                                    <div className="card-form">
                                        <div className="form-group">
                                            <label>Họ và tên</label>
                                            <input
                                                type="text"
                                                value={editName}
                                                onChange={e => setEditName(e.target.value)}
                                                placeholder="Nhập tên của bạn"
                                            />
                                        </div>
                                        <div className="form-group">
                                            <label>Email</label>
                                            <input
                                                type="email"
                                                value={editEmail}
                                                onChange={e => setEditEmail(e.target.value)}
                                                placeholder="social@example.com"
                                            />
                                        </div>
                                        <button
                                            className={`save-profile-btn ${hasUnsavedChanges ? 'active' : ''}`}
                                            disabled={isSaving || !hasUnsavedChanges}
                                            onClick={() => {
                                                setIsSaving(true)
                                                onUpdateProfile({ name: editName, email: editEmail, avatar: editAvatar })
                                                setTimeout(() => setIsSaving(false), 500)
                                            }}
                                        >
                                            {isSaving ? 'Đang lưu...' : 'Lưu thay đổi'}
                                        </button>
                                    </div>
                                </div>
                                <div className="account-danger-zone">
                                    <button className="danger-btn-outline">Đăng xuất khỏi tất cả các thiết bị</button>
                                    <button className="danger-text">Xóa tài khoản</button>
                                </div>
                            </div>
                        )}

                        {activeTab === 'appearance' && (
                            <div className="content-section">
                                <div className="appearance-grid">
                                    <button
                                        className={`theme-card ${!darkMode ? 'active' : ''}`}
                                        onClick={() => !darkMode || onToggleTheme()}
                                    >
                                        <div className="theme-preview light" />
                                        <span>Giao diện sáng</span>
                                    </button>
                                    <button
                                        className={`theme-card ${darkMode ? 'active' : ''}`}
                                        onClick={() => darkMode || onToggleTheme()}
                                    >
                                        <div className="theme-preview dark" />
                                        <span>Giao diện tối</span>
                                    </button>
                                </div>
                            </div>
                        )}

                        {activeTab === 'archived' && (
                            <div className="content-section">
                                {archivedSessions.length > 0 ? (
                                    <div className="archived-list">
                                        {archivedSessions.map(session => (
                                            <div key={session.id} className="archived-row">
                                                <div className="row-info">
                                                    <span className="row-title">{session.title || 'Không có tiêu đề'}</span>
                                                    <span className="row-date">{new Date(session.created_at).toLocaleDateString()}</span>
                                                </div>
                                                <button
                                                    className="restore-btn"
                                                    onClick={() => onRestoreSession(session.id)}
                                                    title="Khôi phục"
                                                >
                                                    <Archive size={14} />
                                                    Khôi phục
                                                </button>
                                            </div>
                                        ))}
                                    </div>
                                ) : (
                                    <div className="empty-state">
                                        <Clock size={40} className="mb-4 opacity-20" />
                                        <p>Không có hội thoại nào được lưu trữ</p>
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                </div>

                {/* Unsaved Changes Warning Overlay */}
                {showUnsavedWarning && (
                    <div className="unsaved-warning-overlay glass">
                        <div className="warning-content">
                            <div className="warning-icon-wrapper">
                                <Clock size={28} className="text-amber-500 animate-pulse" />
                            </div>
                            <h3>Bạn chưa lưu thay đổi</h3>
                            <p>Các chỉnh sửa trong phần tài khoản của bạn chưa được lưu lại. Bạn muốn làm gì tiếp theo?</p>
                            <div className="warning-actions">
                                <button className="warning-btn discard" onClick={handleDiscard}>Bỏ qua</button>
                                <button className="warning-btn cancel" onClick={() => setShowUnsavedWarning(false)}>Quay lại</button>
                                <button className="warning-btn save" onClick={handleSaveAndContinue}>Lưu & Tiếp tục</button>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    )
}

// Helper needed for the above
const renderedGroups = (groups, renderer) => {
    if (!groups) return null;
    return (
        <>
            {renderer("Hôm nay", groups.today)}
            {renderer("Hôm qua", groups.yesterday)}
            {renderer("7 ngày trước", groups.last7Days)}
            {renderer("Cũ hơn", groups.older)}
        </>
    )
}



export const ImageViewer = ({ images = [], startIndex = 0, onClose, onIndexChange, isRestored = false }) => {
    // Lock in the initial isRestored value to prevent re-triggering animations if App re-renders
    const [wasRestored] = useState(isRestored)

    const [currentIndex, setCurrentIndex] = useState(startIndex)
    const [zoom, setZoom] = useState(1)
    const [rotation, setRotation] = useState(0)

    // Sync current index to parent for persistence
    useEffect(() => {
        if (onIndexChange) onIndexChange(currentIndex)
    }, [currentIndex, onIndexChange])

    useEffect(() => {
        const handleKeyDown = (e) => {
            if (e.key === 'Escape') onClose()
            if (e.key === 'ArrowLeft') handlePrev()
            if (e.key === 'ArrowRight') handleNext()
        }
        window.addEventListener('keydown', handleKeyDown)
        return () => window.removeEventListener('keydown', handleKeyDown)
    }, [currentIndex, images.length])

    const handleNext = () => {
        setCurrentIndex((prev) => (prev + 1) % images.length)
        setZoom(1)
        setRotation(0)
    }

    const handlePrev = () => {
        setCurrentIndex((prev) => (prev - 1 + images.length) % images.length)
        setZoom(1)
        setRotation(0)
    }

    const handleZoomIn = () => setZoom(prev => Math.min(prev + 0.25, 3))
    const handleZoomOut = () => setZoom(prev => Math.max(prev - 0.25, 0.5))
    const handleReset = () => {
        setZoom(1)
        setRotation(0)
    }

    const handleDownload = () => {
        const link = document.createElement('a')
        link.href = images[currentIndex]
        link.download = `image-${currentIndex + 1}.png`
        link.click()
    }

    if (!images || images.length === 0) return null

    return (
        <div className={`premium-viewer-overlay ${wasRestored ? 'is-restored' : ''}`} onClick={onClose}>
            {/* Top Controls */}
            <div className="viewer-top-bar" onClick={e => e.stopPropagation()}>
                <div className="viewer-info">
                    {currentIndex + 1} / {images.length}
                </div>
                <div className="viewer-actions">
                    <button onClick={handleZoomOut} title="Thu nhỏ"><ZoomOut size={20} /></button>
                    <button onClick={handleZoomIn} title="Phóng to"><ZoomIn size={20} /></button>
                    <button onClick={handleReset} title="Đặt lại"><RotateCcw size={20} /></button>
                    <div className="viewer-divider"></div>
                    <button onClick={handleDownload} title="Tải về"><Download size={20} /></button>
                    <button onClick={onClose} className="viewer-close-btn" title="Đóng (Esc)"><X size={20} /></button>
                </div>
            </div>

            {/* Navigation Arrows */}
            {images.length > 1 && (
                <>
                    <button
                        className="viewer-nav-btn prev"
                        onClick={(e) => { e.stopPropagation(); handlePrev(); }}
                    >
                        <ChevronLeft size={32} />
                    </button>
                    <button
                        className="viewer-nav-btn next"
                        onClick={(e) => { e.stopPropagation(); handleNext(); }}
                    >
                        <ChevronRight size={32} />
                    </button>
                </>
            )}

            {/* Image Container */}
            <div className="viewer-image-container" onClick={e => e.stopPropagation()}>
                <img
                    src={images[currentIndex]}
                    alt={`Preview ${currentIndex + 1}`}
                    style={{
                        transform: `scale(${zoom}) rotate(${rotation}deg)`,
                        transition: zoom === 1 ? 'transform 0.3s cubic-bezier(0.16, 1, 0.3, 1)' : 'none'
                    }}
                    className="viewer-main-image"
                />
            </div>

            {/* Thumbnails Strip */}
            {images.length > 1 && (
                <div className="viewer-thumbnails-strip" onClick={e => e.stopPropagation()}>
                    {images.map((img, idx) => (
                        <div
                            key={idx}
                            className={`viewer-thumb-item ${idx === currentIndex ? 'active' : ''}`}
                            onClick={() => {
                                setCurrentIndex(idx)
                                setZoom(1)
                                setRotation(0)
                            }}
                        >
                            <img src={img} alt={`Thumb ${idx}`} />
                        </div>
                    ))}
                </div>
            )}
        </div>
    )
}
