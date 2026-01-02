import React, { useState, useEffect, useRef } from 'react'
import {
    ChevronLeft,
    ChevronDown,
    ChevronRight,
    Search,
    MessageSquare,
    Edit,
    Image,
    LayoutGrid,
    Folder,
    Settings,
    User,
    Pin,
    MoreHorizontal,
    Archive,
    Trash2,
    PanelLeft,
    PanelRight
} from 'lucide-react'
const pochiLogo = '/pochi.jpeg'

const Sidebar = ({
    isOpen,
    toggleSidebar,
    conversations = [],
    currentConversationId,
    onSelectConversation,
    onNewChat,
    onDeleteConversation,
    onRenameConversation,
    onTogglePin,
    onToggleArchive,
    onSearchClick,
    onSettingsClick,
    darkMode,
    userProfile
}) => {
    const sidebarRef = useRef(null)
    const [activeMenuId, setActiveMenuId] = React.useState(() => {
        return sessionStorage.getItem('activeMenuId') || null
    })
    const [isHistoryCollapsed, setIsHistoryCollapsed] = useState(() => {
        return localStorage.getItem('isHistoryCollapsed') === 'true'
    })
    const [editingId, setEditingId] = useState(() => {
        return sessionStorage.getItem('editingId') || null
    })
    const [editTitle, setEditTitle] = useState(() => {
        return sessionStorage.getItem('editTitle') || ''
    })
    const [menuPlacement, setMenuPlacement] = useState(() => {
        return sessionStorage.getItem('menuPlacement') || 'bottom'
    })

    const pinnedChats = conversations.filter(c => c.isPinned && !c.isArchived)
    const activeChats = conversations.filter(c => !c.isPinned && !c.isArchived)

    const handleStartRename = (conv) => {
        setEditingId(conv.id)
        setEditTitle(conv.title || 'Đoạn chat mới')
        setActiveMenuId(null)
        sessionStorage.setItem('isNewRename', 'true')
    }

    const handleSaveRename = (id) => {
        if (editTitle.trim()) {
            onRenameConversation(id, editTitle.trim())
        }
        setEditingId(null)
    }

    const handleCancelRename = () => {
        setEditingId(null)
    }

    // Close menu when clicking outside
    React.useEffect(() => {
        const handleClickOutside = () => setActiveMenuId(null)
        window.addEventListener('click', handleClickOutside)
        return () => window.removeEventListener('click', handleClickOutside)
    }, [])

    useEffect(() => {
        localStorage.setItem('isHistoryCollapsed', isHistoryCollapsed)
    }, [isHistoryCollapsed])

    useEffect(() => {
        if (activeMenuId) {
            sessionStorage.setItem('activeMenuId', activeMenuId)
            sessionStorage.setItem('menuPlacement', menuPlacement)
        } else {
            sessionStorage.removeItem('activeMenuId')
            sessionStorage.removeItem('menuPlacement')
        }
    }, [activeMenuId, menuPlacement])

    useEffect(() => {
        if (editingId) {
            sessionStorage.setItem('editingId', editingId)
            sessionStorage.setItem('editTitle', editTitle)
        } else {
            sessionStorage.removeItem('editingId')
            sessionStorage.removeItem('editTitle')
        }
    }, [editingId, editTitle])

    const historyScrollRef = useRef(null)

    // Handle history scroll persistence
    const handleHistoryScroll = (e) => {
        if (!isOpen) return // Only save if open
        sessionStorage.setItem('sidebarScrollTop', e.target.scrollTop)
    }

    React.useLayoutEffect(() => {
        if (!isHistoryCollapsed && historyScrollRef.current) {
            const savedScroll = sessionStorage.getItem('sidebarScrollTop')
            if (savedScroll) {
                historyScrollRef.current.scrollTop = parseInt(savedScroll, 10)
            }
        }
    }, [isHistoryCollapsed, conversations]) // Restore when expanded or conversations change

    const renderChatItem = (conv) => (
        <div
            key={conv.id}
            className={`sidebar-chat-item group ${conv.id === currentConversationId ? 'active' : ''} ${activeMenuId === conv.id ? 'menu-open' : ''} ${editingId === conv.id ? 'editing' : ''}`}
            onClick={() => onSelectConversation(conv.id)}
        >
            <div className="active-indicator" />

            {editingId === conv.id ? (
                <div className="chat-item-text editing" onClick={e => e.stopPropagation()}>
                    <input
                        className="inline-rename-input"
                        value={editTitle}
                        onChange={(e) => setEditTitle(e.target.value)}
                        onBlur={() => handleSaveRename(conv.id)}
                        onKeyDown={(e) => {
                            if (e.key === 'Enter') handleSaveRename(conv.id)
                            if (e.key === 'Escape') handleCancelRename()
                        }}
                        autoFocus
                        spellCheck="false"
                        autoComplete="off"
                        onFocus={e => {
                            // Only select all if this is NOT a restored state from refresh
                            const isRestored = !sessionStorage.getItem('isNewRename');
                            if (!isRestored) {
                                e.target.select();
                                sessionStorage.removeItem('isNewRename');
                            }
                        }}
                    />
                </div>
            ) : (
                <div className="chat-item-text truncate">
                    {conv.isPinned && <Pin size={12} className="chat-pin-icon" fill="currentColor" />}
                    <span>{conv.title || 'Đoạn chat mới'}</span>
                </div>
            )}

            {/* Chat Actions Menu */}
            {!editingId && (
                <div className="chat-item-actions">
                    <button
                        onClick={(e) => {
                            e.stopPropagation();
                            const rect = e.currentTarget.getBoundingClientRect();
                            const spaceBelow = window.innerHeight - rect.bottom;
                            const newPlacement = spaceBelow < 200 ? 'top' : 'bottom';
                            setMenuPlacement(newPlacement);
                            setActiveMenuId(activeMenuId === conv.id ? null : conv.id)
                        }}
                        className="menu-trigger-btn"
                    >
                        <MoreHorizontal size={15.5} />
                    </button>

                    {activeMenuId === conv.id && (
                        <div className={`chat-menu-dropdown glass placement-${menuPlacement}`} onClick={e => e.stopPropagation()}>
                            <button className="menu-item" onClick={() => handleStartRename(conv)}>
                                <Edit size={15} />
                                <span>Đổi tên</span>
                            </button>
                            <button className="menu-item" onClick={() => { onTogglePin(conv.id); setActiveMenuId(null); }}>
                                <Pin size={15} fill={conv.isPinned ? "currentColor" : "none"} />
                                <span>{conv.isPinned ? "Bỏ ghim" : "Ghim"}</span>
                            </button>
                            <button className="menu-item" onClick={() => { onToggleArchive(conv.id); setActiveMenuId(null); }}>
                                <Archive size={15} />
                                <span>Lưu trữ</span>
                            </button>
                            <div className="menu-separator" />
                            <button className="menu-item delete" onClick={() => { onDeleteConversation(conv.id); setActiveMenuId(null); }}>
                                <Trash2 size={15} />
                                <span>Xóa</span>
                            </button>
                        </div>
                    )}
                </div>
            )}
        </div>
    )

    return (
        <div className={`sidebar-container ${isOpen ? 'open' : 'closed'}`}>
            <div className="sidebar-inner">
                {/* Header Actions */}
                <div className="sidebar-top-nav">
                    <div className="nav-header">
                        <div className="sidebar-brand">
                            <img src={pochiLogo} alt="Pochi Logo" className="brand-logo" id="tour-logo" />
                        </div>
                        {isOpen && (
                            <button
                                className="toggle-sidebar-trigger"
                                onClick={toggleSidebar}
                                title="Đóng sidebar"
                                id="tour-toggle-sidebar"
                            >
                                <PanelLeft size={20} />
                            </button>
                        )}
                    </div>

                    <div className="nav-list">
                        <button className="nav-item new-chat-btn" onClick={onNewChat} id="tour-new-chat">
                            <div className="nav-item-icon">
                                <Edit size={18} />
                            </div>
                            <span>Đoạn chat mới</span>
                            {isOpen && (
                                <div className="shortcut-hint">
                                    {navigator.platform.toUpperCase().indexOf('MAC') >= 0 ? '⌘E' : 'Ctrl E'}
                                </div>
                            )}
                        </button>

                        <button className="nav-item search-btn" onClick={onSearchClick} id="tour-search">
                            <div className="nav-item-icon">
                                <Search size={18} />
                            </div>
                            <span>Tìm kiếm đoạn chat</span>
                            {isOpen && (
                                <div className="shortcut-hint">
                                    {navigator.platform.toUpperCase().indexOf('MAC') >= 0 ? '⌘F' : 'Ctrl F'}
                                </div>
                            )}
                        </button>

                        <div className="nav-item-pill disabled">
                            <div className="nav-item-icon">
                                <Image size={18} />
                            </div>
                            <span>Ảnh <span className="badge-new">MỚI</span></span>
                        </div>

                        <div className="nav-item-pill disabled">
                            <div className="nav-item-icon">
                                <LayoutGrid size={18} />
                            </div>
                            <span>Ứng dụng</span>
                        </div>

                        <div className="nav-item-pill disabled">
                            <div className="nav-item-icon">
                                <Folder size={18} />
                            </div>
                            <span>Dự án</span>
                        </div>
                    </div>
                </div>

                <div className="sidebar-history" id="tour-history-section">
                    {/* Clickable area when sidebar is closed - from "Dự án" down to footer (but not including footer) */}
                    {!isOpen && (
                        <div
                            className="sidebar-clickable-area"
                            onClick={toggleSidebar}
                        />
                    )}
                    <div
                        className="history-label collapsible"
                        onClick={() => setIsHistoryCollapsed(!isHistoryCollapsed)}
                        id="tour-history-label"
                    >
                        <span>Các đoạn chat của bạn</span>
                        {isHistoryCollapsed ? <ChevronRight size={15} /> : <ChevronDown size={15} />}
                    </div>

                    {!isHistoryCollapsed && (
                        <div
                            className="history-scroll-area custom-scrollbar"
                            ref={historyScrollRef}
                            onScroll={handleHistoryScroll}
                        >
                            {pinnedChats.length > 0 && (
                                <div className="history-section">
                                    {pinnedChats.map(renderChatItem)}
                                </div>
                            )}

                            <div className="history-section">
                                {activeChats.length > 0 ? (
                                    activeChats.map(renderChatItem)
                                ) : (
                                    <div className="history-empty">Chưa có cuộc trò chuyện nào</div>
                                )}
                            </div>
                        </div>
                    )}
                </div>

                <div className="sidebar-footer" id="tour-profile">
                    <div className="profile-section" onClick={() => onSettingsClick('account')}>
                        <div className="profile-avatar" id="tour-profile-sidebar-avatar">
                            {userProfile?.avatar ? (
                                <img src={userProfile.avatar} alt="Avatar" className="sidebar-avatar-img" />
                            ) : (
                                <div className="avatar-circle">{userProfile?.name?.charAt(0) || 'U'}</div>
                            )}
                        </div>
                        <div className="profile-info">
                            <div className="profile-name">{userProfile?.name || 'Vô danh'}</div>
                            <div className="profile-plan">Free</div>
                        </div>
                        <button className="upgrade-btn" onClick={(e) => { e.stopPropagation(); /* handle upgrade */ }}>
                            Nâng cấp
                        </button>
                    </div>
                </div>
            </div>
        </div>
    )
}

export default Sidebar
