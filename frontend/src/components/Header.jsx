import React, { useState, useRef, useEffect } from 'react'
import { Share2, User, MoreHorizontal, Sparkles, ChevronDown, Edit3, Pin, Archive, Trash2, Settings, LogOut, Moon, Sun, HelpCircle } from 'lucide-react'

const Header = ({ title, onOpenSidebar, isMobile, currentConversationId, onDeleteConversation, onRenameConversation, onRenameClick, onTogglePin, onToggleArchive, currentChat, onSettingsClick, onToggleTheme, darkMode, userProfile, onHelpClick }) => {
    const [showMenu, setShowMenu] = useState(() => {
        return sessionStorage.getItem('showHeaderMenu') === 'true'
    })
    const [showUserMenu, setShowUserMenu] = useState(() => {
        return sessionStorage.getItem('showUserMenu') === 'true'
    })
    const menuRef = useRef(null)
    const userMenuRef = useRef(null)

    useEffect(() => {
        sessionStorage.setItem('showHeaderMenu', showMenu)
    }, [showMenu])

    useEffect(() => {
        sessionStorage.setItem('showUserMenu', showUserMenu)
    }, [showUserMenu])

    // Close menus when clicking outside
    useEffect(() => {
        const handleClickOutside = (event) => {
            if (menuRef.current && !menuRef.current.contains(event.target)) {
                setShowMenu(false)
            }
            if (userMenuRef.current && !userMenuRef.current.contains(event.target)) {
                setShowUserMenu(false)
            }
        }
        if (showMenu || showUserMenu) {
            document.addEventListener('mousedown', handleClickOutside)
        }
        return () => document.removeEventListener('mousedown', handleClickOutside)
    }, [showMenu, showUserMenu])

    return (
        <header className="premium-header">
            <div className="header-left">
                <div className="brand-wrapper">
                    <span className="brand-name">Pochi <span className="brand-version">4.o</span></span>
                    <ChevronDown size={16} className="brand-dropdown-icon" />
                </div>
            </div>

            <div className="header-center">
                <button className="upgrade-pill" id="tour-upgrade">
                    <Sparkles size={14} className="sparkle-icon" />
                    <span>Nâng cấp lên Pro</span>
                </button>
            </div>

            <div className="header-right">
                <button
                    className="header-action-btn help-btn"
                    id="tour-help-btn"
                    title="Hướng dẫn sử dụng"
                    onClick={onHelpClick}
                    style={{ fontFamily: "'Outfit', sans-serif", fontWeight: 600 }}
                >
                    <HelpCircle size={18} />
                    <span className="btn-label" style={{ marginTop: '1px' }}>Hướng dẫn</span>
                </button>

                <div className="user-avatar-container" ref={userMenuRef}>
                    <div
                        className={`user-avatar-wrapper ${showUserMenu ? 'active' : ''}`}
                        onClick={() => setShowUserMenu(!showUserMenu)}
                        id="tour-profile-header"
                    >
                        <div className="user-avatar" id="tour-profile-header-avatar">
                            {userProfile.avatar ? (
                                <img src={userProfile.avatar} alt="Avatar" />
                            ) : (
                                <div className="avatar-circle small">{userProfile?.name?.charAt(0) || 'U'}</div>
                            )}
                        </div>
                    </div>

                    {showUserMenu && (
                        <div className="context-menu user-dropdown">
                            <div className="user-dropdown-header">
                                <div className="user-info">
                                    <span className="user-name">{userProfile.name}</span>
                                    <span className="user-email">{userProfile.email}</span>
                                </div>
                            </div>
                            <div className="divider" />
                            <button onClick={() => { onSettingsClick('account'); setShowUserMenu(false) }}>
                                <User size={14} />
                                <span>Tài khoản</span>
                                <div className="shortcut-hint">
                                    {navigator.platform.toUpperCase().indexOf('MAC') >= 0 ? '⌘I' : 'Ctrl I'}
                                </div>
                            </button>
                            <button onClick={() => { onSettingsClick('general'); setShowUserMenu(false) }}>
                                <Settings size={14} />
                                <span>Cài đặt</span>
                                <div className="shortcut-hint">
                                    {navigator.platform.toUpperCase().indexOf('MAC') >= 0 ? '⌘X' : 'Ctrl X'}
                                </div>
                            </button>
                            <button onClick={() => { onToggleTheme() }}>
                                {darkMode ? <Sun size={14} /> : <Moon size={14} />}
                                <span>{darkMode ? 'Chế độ sáng' : 'Chế độ tối'}</span>
                                <div className="shortcut-hint">
                                    {navigator.platform.toUpperCase().indexOf('MAC') >= 0 ? '⌘K' : 'Ctrl K'}
                                </div>
                            </button>
                            <div className="divider" />
                            <button className="danger" onClick={() => setShowUserMenu(false)}>
                                <LogOut size={14} /> Đăng xuất
                            </button>
                        </div>
                    )}
                </div>

                <div className="header-menu-container" ref={menuRef}>
                    <button
                        className={`header-icon-btn more-btn ${showMenu ? 'active' : ''}`}
                        onClick={() => setShowMenu(!showMenu)}
                        disabled={!currentConversationId}
                        id="tour-chat-features"
                    >
                        <MoreHorizontal size={20} />
                    </button>

                    {showMenu && currentConversationId && (
                        <div className="context-menu header-dropdown">
                            <button onClick={() => {
                                onRenameClick()
                                setShowMenu(false)
                            }}>
                                <Edit3 size={14} /> Đổi tên
                            </button>
                            <button onClick={() => { onTogglePin(currentConversationId); setShowMenu(false) }}>
                                <Pin size={14} className={currentChat?.isPinned ? 'fill-current' : ''} />
                                {currentChat?.isPinned ? 'Bỏ ghim' : 'Ghim'}
                            </button>
                            <button onClick={() => { onToggleArchive(currentConversationId); setShowMenu(false) }}>
                                <Archive size={14} />
                                {currentChat?.isArchived ? 'Bỏ lưu trữ' : 'Lưu trữ'}
                            </button>
                            <div className="divider" />
                            <button
                                onClick={() => { onDeleteConversation(currentConversationId); setShowMenu(false) }}
                                className="danger"
                            >
                                <Trash2 size={14} /> Xóa
                            </button>
                        </div>
                    )}
                </div>
            </div>
        </header>
    )
}

export default Header
