import { useState, useEffect, useLayoutEffect, useRef } from 'react'
import Header from './components/Header'
import Sidebar from './components/Sidebar'
import MessageList from './components/MessageList'
import ChatInput from './components/ChatInput'
import { SearchModal, ImageViewer, SettingsModal } from './components/Modals'
import { Menu, MoreHorizontal } from 'lucide-react'
import './App.css'
import GuideTour from './components/GuideTour'
import defaultAvatar from './assets/pochi.jpeg'

const API_BASE = '/api'

function App() {
    // --- State Management ---
    const [darkMode, setDarkMode] = useState(() => {
        if (typeof window !== 'undefined') {
            const saved = localStorage.getItem('darkMode')
            if (saved !== null) return saved === 'true'
            return window.matchMedia('(prefers-color-scheme: dark)').matches
        }
        return false
    })

    const [conversations, setConversations] = useState([])
    const [currentConversation, setCurrentConversation] = useState(() => {
        const lastId = localStorage.getItem('lastConversationId')
        return (lastId === 'null' || !lastId) ? null : lastId
    })
    const [messages, setMessages] = useState([])
    const [isLoading, setIsLoading] = useState(false)
    const [isInitializing, setIsInitializing] = useState(true) // Prevents flash on refresh

    // User Profile State
    const [userProfile, setUserProfile] = useState(() => {
        const saved = localStorage.getItem('user_profile')
        if (saved) {
            try {
                const profile = JSON.parse(saved)
                // Migrate old static paths to new hashed assets
                if (profile.avatar === '/hnam.jpeg' || profile.avatar === '/pochi.jpeg' || profile.avatar.includes('hnam')) {
                    profile.avatar = defaultAvatar
                    localStorage.setItem('user_profile', JSON.stringify(profile))
                }
                return profile
            } catch (e) {
                console.error('Failed to parse user_profile', e)
            }
        }
        return {
            name: 'Guest',
            email: 'guest@example.com',
            avatar: defaultAvatar
        }
    })

    const handleUpdateProfile = (newProfile) => {
        const updated = { ...userProfile, ...newProfile }
        setUserProfile(updated)
        localStorage.setItem('user_profile', JSON.stringify(updated))
    }

    // UI State
    const [sidebarOpen, setSidebarOpen] = useState(() => {
        const saved = localStorage.getItem('sidebarOpen')
        return saved !== null ? saved === 'true' : true
    })
    const [showSearch, setShowSearch] = useState(() => {
        return sessionStorage.getItem('showSearch') === 'true'
    })
    const [tourVersion, setTourVersion] = useState(0)
    const [showTour, setShowTour] = useState(() => {
        const hasSeenTour = localStorage.getItem('hasSeenTour')
        const savedIndex = localStorage.getItem('tourStepIndex')
        // Auto-show if never seen or if interrupted (index exists and is not -1)
        return !hasSeenTour || (savedIndex !== null && savedIndex !== '-1')
    })
    const [showSettings, setShowSettings] = useState(() => {
        return sessionStorage.getItem('showSettings') === 'true'
    })
    const [settingsTab, setSettingsTab] = useState(() => {
        return localStorage.getItem('settingsTab') || 'general'
    })
    const [viewerData, setViewerData] = useState(() => {
        try {
            const saved = sessionStorage.getItem('viewerData')
            return saved ? JSON.parse(saved) : null
        } catch (e) {
            console.error('Failed to parse viewerData:', e)
            return null
        }
    }) // { images: [], index: 0 }
    const [memoryStatus, setMemoryStatus] = useState(null) // For future memory blocking features
    const [showPinLimitToast, setShowPinLimitToast] = useState(false)

    const [isMobile, setIsMobile] = useState(window.innerWidth < 768)
    const [showRenameModal, setShowRenameModal] = useState(() => {
        return sessionStorage.getItem('showRenameModal') === 'true'
    })
    const [modalTempTitle, setModalTempTitle] = useState(() => {
        return sessionStorage.getItem('modalTempTitle') || ''
    })
    const appRef = useRef(null)
    const isCreatingSessionRef = useRef(false)
    const isSendingMessageRef = useRef(false) // Track if we're currently sending a message
    const isInitialMountRef = useRef(true) // Track if this is the first mount after refresh

    // --- Effects ---

    // Note: Removed useLayoutEffect scroll reset - it caused more issues than it solved.
    // Scroll persistence is now handled in MessageList.


    // Dark Mode - Apply synchronously before paint to prevent flickering
    useLayoutEffect(() => {
        document.documentElement.classList.remove('light', 'dark')
        document.documentElement.classList.add(darkMode ? 'dark' : 'light')
        localStorage.setItem('darkMode', darkMode)
    }, [darkMode])

    useEffect(() => {
        localStorage.setItem('sidebarOpen', sidebarOpen)
    }, [sidebarOpen])

    useEffect(() => {
        sessionStorage.setItem('showSearch', showSearch)
    }, [showSearch])

    useEffect(() => {
        sessionStorage.setItem('showSettings', showSettings)
    }, [showSettings])

    useEffect(() => {
        localStorage.setItem('settingsTab', settingsTab)
    }, [settingsTab])

    useEffect(() => {
        sessionStorage.setItem('showRenameModal', showRenameModal)
        sessionStorage.setItem('modalTempTitle', modalTempTitle)
    }, [showRenameModal, modalTempTitle])

    useEffect(() => {
        if (viewerData) {
            sessionStorage.setItem('viewerData', JSON.stringify(viewerData))
        } else {
            sessionStorage.removeItem('viewerData')
        }
    }, [viewerData])

    // Scroll Restoration & Event Listeners
    useEffect(() => {
        // Disable native scroll restoration to prevent jump on refresh
        if ('scrollRestoration' in window.history) {
            window.history.scrollRestoration = 'manual'
        }

        const handleResize = () => setIsMobile(window.innerWidth < 768)
        const handleKeyDown = (e) => {
            // Cmd+F or Ctrl+F for Search
            if ((e.metaKey || e.ctrlKey) && e.key === 'f') {
                e.preventDefault()
                setShowSearch(true)
            }

            // Cmd+E or Ctrl+E for New Chat
            if ((e.metaKey || e.ctrlKey) && e.key === 'e') {
                e.preventDefault()
                createConversation()
            }

            // Cmd+X or Ctrl+X for General Settings
            if ((e.metaKey || e.ctrlKey) && e.key === 'x') {
                e.preventDefault()
                setSettingsTab('general')
                setShowSettings(true)
            }

            // Cmd+I or Ctrl+I for Account Settings
            if ((e.metaKey || e.ctrlKey) && e.key === 'i') {
                e.preventDefault()
                setSettingsTab('account')
                setShowSettings(true)
            }

            // Cmd+K or Ctrl+K for Dark Mode Toggle
            if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
                e.preventDefault()
                setDarkMode(prev => !prev)
            }
        }

        window.addEventListener('resize', handleResize)
        window.addEventListener('keydown', handleKeyDown)

        return () => {
            window.removeEventListener('resize', handleResize)
            window.removeEventListener('keydown', handleKeyDown)
        }
    }, [])

    // Load Conversations on Mount
    useEffect(() => {
        const initConversations = async () => {
            try {
                const res = await fetch(`${API_BASE}/conversations`)
                const data = await res.json()

                // Merge persisted metadata (Pin/Archive)
                const persistedMetadata = JSON.parse(localStorage.getItem('chat_metadata') || '{}')
                const mergedData = data.map(conv => ({
                    ...conv,
                    isPinned: persistedMetadata[conv.id]?.isPinned || false,
                    isArchived: persistedMetadata[conv.id]?.isArchived || false
                }))

                setConversations(mergedData)

                const savedId = localStorage.getItem('lastConversationId')
                if (savedId) {
                    const exists = data.find(c => c.id === savedId)
                    if (exists) {
                        // Load messages for saved conversation before showing UI
                        await loadMessagesSync(savedId)
                    } else {
                        localStorage.removeItem('lastConversationId')
                        setCurrentConversation(null)
                        setMessages([])
                    }
                }
            } catch (error) {
                console.error('Failed to fetch conversations:', error)
            } finally {
                // Always mark initialization as complete
                setIsInitializing(false)
            }
        }
        initConversations()
    }, [])

    // Mark initial mount as complete after first render cycle of the REAL UI
    useEffect(() => {
        if (!isInitializing) {
            const timer = setTimeout(() => {
                isInitialMountRef.current = false
            }, 300) // Slightly longer to be safe
            return () => clearTimeout(timer)
        }
    }, [isInitializing])

    // Load Messages when Conversation Changes
    useEffect(() => {
        if (currentConversation) {
            if (isCreatingSessionRef.current) {
                // If we JUST created this session, don't clear messages!
                // The current messages state already contains the optimistic user message.
                isCreatingSessionRef.current = false
                return
            }

            // Skip loading if we're currently sending a message (to prevent race condition)
            if (isSendingMessageRef.current) {
                return
            }

            loadMessages(currentConversation)
            localStorage.setItem('lastConversationId', currentConversation)
        } else {
            setMessages([])
        }
    }, [currentConversation])

    // Auto-refresh for pending messages (e.g., if user returns to a generating session)
    useEffect(() => {
        if (!currentConversation || isLoading || messages.length === 0) return

        const lastMsg = messages[messages.length - 1]
        const isPending = lastMsg.role === 'assistant' && !lastMsg.content

        if (isPending) {
            const pollInterval = setInterval(() => {
                loadMessagesSync(currentConversation)
            }, 3000) // Poll every 3s

            return () => clearInterval(pollInterval)
        }
    }, [messages, currentConversation, isLoading])

    // Simulation Engine for "Resume Streaming" experience
    useEffect(() => {
        if (messages.length === 0 || isLoading) return

        const lastIdx = messages.length - 1
        const lastMsg = messages[lastIdx]

        if (lastMsg.isSimulating && lastMsg._fullContent) {
            const simulationTimer = setTimeout(() => {
                setMessages(prev => {
                    const newMessages = [...prev]
                    const msg = newMessages[lastIdx]
                    if (!msg || !msg.isSimulating) return prev

                    const currentLen = msg.content.length
                    const fullContent = msg._fullContent

                    // Batch size for simulation (approx 24 chars for that "super fast" feel)
                    const batchSize = 24
                    const nextContent = fullContent.substring(0, currentLen + batchSize)

                    msg.content = nextContent

                    if (nextContent.length >= fullContent.length) {
                        msg.isStreaming = false
                        msg.isSimulating = false
                        delete msg._fullContent
                    }

                    return newMessages
                })
            }, 5) // Very fast update for simulation

            return () => clearTimeout(simulationTimer)
        }
    }, [messages, isLoading])

    // --- Actions ---

    const loadMessages = async (conversationId) => {
        try {
            const res = await fetch(`${API_BASE}/conversations/${conversationId}/messages`)
            const data = await res.json()
            setMessages(parseMessagesData(data))
        } catch (error) {
            console.error('Failed to load messages:', error)
        }
    }

    // Sync version for initial load (doesn't trigger effects that cause scroll)
    const loadMessagesSync = async (conversationId) => {
        try {
            const res = await fetch(`${API_BASE}/conversations/${conversationId}/messages`)
            const data = await res.json()
            setMessages(parseMessagesData(data))
        } catch (error) {
            console.error('Failed to load messages:', error)
        }
    }

    // Helper to parse messages data
    const parseMessagesData = (data) => {
        const TYPING_SPEED = 0.25 // chars/ms (approx 250 chars/sec)
        const now = new Date().getTime()

        return data.map((m, idx) => {
            let images = []
            if (m.image_data) {
                try {
                    const parsed = JSON.parse(m.image_data)
                    if (Array.isArray(parsed)) {
                        images = parsed.map(b64 => `data:image/jpeg;base64,${b64}`)
                    } else {
                        images = [`data:image/jpeg;base64,${m.image_data}`]
                    }
                } catch (e) {
                    images = [`data:image/jpeg;base64,${m.image_data}`]
                }
            }

            const createdAt = new Date(m.created_at).getTime()
            const elapsed = now - createdAt
            const fullContent = m.content || ''

            // Only simulate for the VERY LAST message if it's an assistant message
            const isLastMessage = idx === data.length - 1
            const shouldSimulate = isLastMessage && m.role === 'assistant' && fullContent.length > 0

            if (shouldSimulate) {
                const expectedVisibleLength = Math.floor(elapsed * TYPING_SPEED)
                if (expectedVisibleLength < fullContent.length) {
                    return {
                        role: m.role,
                        content: fullContent.substring(0, Math.max(0, expectedVisibleLength)),
                        _fullContent: fullContent, // Hidden property for simulation
                        images: images,
                        isStreaming: true,
                        isSimulating: true // Flag for simulation
                    }
                }
            }

            return {
                role: m.role,
                content: fullContent,
                images: images,
                // If assistant message is empty, it means it's still being generated in background
                isStreaming: m.role === 'assistant' && !fullContent
            }
        })
    }

    const createConversation = () => {
        setCurrentConversation(null)
        setMessages([])
        localStorage.removeItem('lastConversationId') // Clear instead of setting "null"
        if (window.innerWidth < 768) setSidebarOpen(false)
    }

    const deleteConversation = async (id) => {
        try {
            await fetch(`${API_BASE}/conversations/${id}`, { method: 'DELETE' })
            const remaining = conversations.filter(c => c.id !== id)
            setConversations(remaining)

            if (currentConversation === id) {
                setCurrentConversation(null)
                setMessages([])
                localStorage.removeItem('lastConversationId')
            }

            // Cleanup metadata
            const metadata = JSON.parse(localStorage.getItem('chat_metadata') || '{}')
            if (metadata[id]) {
                delete metadata[id]
                localStorage.setItem('chat_metadata', JSON.stringify(metadata))
            }

            // Cleanup message expansion states
            Object.keys(localStorage).forEach(key => {
                if (key.startsWith(`expand_${id}`)) {
                    localStorage.removeItem(key)
                }
            })
        } catch (error) {
            console.error('Failed to delete conversation:', error)
        }
    }

    const renameConversation = async (id, newTitle) => {
        // Optimistic UI update
        setConversations(prev => prev.map(c =>
            c.id === id ? { ...c, title: newTitle } : c
        ))

        try {
            const res = await fetch(`${API_BASE}/conversations/${id}`, {
                method: 'PATCH',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title: newTitle })
            })
            if (!res.ok) throw new Error('Failed to rename on server')
        } catch (error) {
            console.error('Failed to rename conversation:', error)
            // Revert on error? (Optional, maybe just notify)
        }
    }

    const handleSaveRename = () => {
        if (modalTempTitle.trim() && currentConversation) {
            renameConversation(currentConversation, modalTempTitle)
        }
        setShowRenameModal(false)
    }

    const togglePin = (id) => {
        setConversations(prev => {
            const isCurrentlyPinned = prev.find(c => c.id === id)?.isPinned
            const currentPinnedCount = prev.filter(c => c.isPinned).length

            // If we are pinning (not unpinning) and already at 5, stop and warn.
            if (!isCurrentlyPinned && currentPinnedCount >= 5) {
                setShowPinLimitToast(true)
                setTimeout(() => setShowPinLimitToast(false), 3000)
                return prev
            }

            const updated = prev.map(c => {
                if (c.id === id) {
                    const newPinned = !c.isPinned
                    return { ...c, isPinned: newPinned, isArchived: newPinned ? false : c.isArchived }
                }
                return c
            })
            // Persist metadata
            const metadata = JSON.parse(localStorage.getItem('chat_metadata') || '{}')
            const conv = updated.find(c => c.id === id)
            metadata[id] = { ...metadata[id], isPinned: conv.isPinned, isArchived: conv.isArchived }
            localStorage.setItem('chat_metadata', JSON.stringify(metadata))
            return updated
        })
    }

    const toggleArchive = (id) => {
        setConversations(prev => {
            const updated = prev.map(c => {
                if (c.id === id) {
                    const newArchived = !c.isArchived
                    return { ...c, isArchived: newArchived, isPinned: newArchived ? false : c.isPinned }
                }
                return c
            })
            // If the current conversation is archived, deselect it
            if (currentConversation === id) {
                const isArchiving = !prev.find(c => c.id === id)?.isArchived
                if (isArchiving) {
                    setCurrentConversation(null)
                    setMessages([])
                }
            }
            // Persist metadata
            const metadata = JSON.parse(localStorage.getItem('chat_metadata') || '{}')
            const conv = updated.find(c => c.id === id)
            metadata[id] = { ...metadata[id], isPinned: conv.isPinned, isArchived: conv.isArchived }
            localStorage.setItem('chat_metadata', JSON.stringify(metadata))
            return updated
        })
    }

    const sendMessage = async (text, uploadedImages) => {
        const userMessage = text.trim()
        const imagePreviews = uploadedImages.map(img => img.preview)
        // Set flag to prevent loadMessages from overwriting optimistic updates
        isSendingMessageRef.current = true

        // Optimistic UI update
        setMessages(prev => [...prev, {
            role: 'user',
            content: userMessage,
            images: imagePreviews
        }])

        setIsLoading(true)

        const formData = new FormData()
        formData.append('message', userMessage)
        if (currentConversation) formData.append('session_id', currentConversation)
        uploadedImages.forEach(img => {
            formData.append('images', img.file)
        })

        try {
            const res = await fetch(`${API_BASE}/chat`, { method: 'POST', body: formData })
            const sessionId = res.headers.get('X-Session-Id')

            // Handle New Session
            if (sessionId && !currentConversation) {
                isCreatingSessionRef.current = true
                setCurrentConversation(sessionId)
                localStorage.setItem('lastConversationId', sessionId)
                setConversations(prev => {
                    if (prev.find(c => c.id === sessionId)) return prev
                    return [{ id: sessionId, title: userMessage.slice(0, 50), created_at: new Date().toISOString() }, ...prev]
                })
            }

            // Stream Response
            const reader = res.body.getReader()
            const decoder = new TextDecoder()
            let assistantMessage = ''

            setMessages(prev => [...prev, { role: 'assistant', content: '', isStreaming: true }])

            while (true) {
                const { done, value } = await reader.read()
                if (done) break

                const chunk = decoder.decode(value, { stream: true })
                const lines = chunk.split('\n').filter(l => l.trim().length > 0)
                let batchTokens = 0
                const BATCH_SIZE = 8 // Update UI every 8 tokens if they arrive at once

                for (let i = 0; i < lines.length; i++) {
                    const line = lines[i]
                    if (line.startsWith('data: ')) {
                        const data = line.slice(6)
                        if (data === '[DONE]') break

                        let parsed = null
                        try { parsed = JSON.parse(data) }
                        catch { parsed = data } // Legacy fallback

                        if (typeof parsed === 'object' && parsed !== null && parsed.type) {
                            if (parsed.type === 'token') {
                                assistantMessage += parsed.content
                                batchTokens++
                            } else if (parsed.type === 'status') {
                                setMessages(prev => {
                                    const newMessages = [...prev]
                                    if (newMessages.length > 0) newMessages[newMessages.length - 1].status = parsed.status
                                    return newMessages
                                })
                            } else if (parsed.type === 'done') {
                                break;
                            }
                        } else if (typeof parsed === 'string') {
                            assistantMessage += parsed
                            batchTokens++
                        }

                        // Update UI either on batch size or end of chunk lines
                        if (batchTokens >= BATCH_SIZE || i === lines.length - 1) {
                            setMessages(prev => {
                                const newMessages = [...prev]
                                const lastMsg = newMessages[newMessages.length - 1]
                                if (lastMsg) lastMsg.content = assistantMessage
                                return newMessages
                            })
                            batchTokens = 0

                            // A very tiny delay between batches to keep the main thread breathing 
                            // and maintain the typewriter feel
                            await new Promise(resolve => setTimeout(resolve, 2))
                        }
                    }
                }
            }

            // Finish Streaming
            setMessages(prev => {
                const newMessages = [...prev]
                if (newMessages.length > 0) {
                    newMessages[newMessages.length - 1].isStreaming = false
                    newMessages[newMessages.length - 1].status = null // Clear any persistent "Thinking..." status
                }
                return newMessages
            })

        } catch (error) {
            console.error('Failed to send message:', error)
            setMessages(prev => {
                const newMessages = [...prev]
                // If the last message was the streaming one, mark it as finished/error
                if (newMessages.length > 0 && newMessages[newMessages.length - 1].role === 'assistant') {
                    newMessages[newMessages.length - 1].isStreaming = false
                    newMessages[newMessages.length - 1].status = null
                }
                return [...newMessages, { role: 'assistant', content: 'Xin lỗi, đã có lỗi xảy ra.' }]
            })
        } finally {
            setIsLoading(false)
            // Clear flag after message sending is complete
            isSendingMessageRef.current = false
        }
    }

    return (
        <div className="app-container" ref={appRef}>
            {isInitializing ? (
                // Only show loading if viewer is NOT active
                !viewerData && (
                    <div className="flex items-center justify-center h-screen w-screen bg-bg-primary">
                        <div className="animate-spin w-8 h-8 border-4 border-primary border-t-transparent rounded-full"></div>
                    </div>
                )
            ) : (
                <>
                    {showTour && (
                        <GuideTour
                            darkMode={darkMode}
                            tourVersion={tourVersion}
                            onTourEnd={() => {
                                setTourVersion(0)
                                setShowTour(false)
                            }}
                        />
                    )}
                    <Sidebar
                        isOpen={sidebarOpen}
                        toggleSidebar={() => setSidebarOpen(!sidebarOpen)}
                        conversations={[...conversations].sort((a, b) => {
                            if (a.isPinned && !b.isPinned) return -1
                            if (!a.isPinned && b.isPinned) return 1

                            const dateA = a.created_at ? new Date(a.created_at).getTime() : 0
                            const dateB = b.created_at ? new Date(b.created_at).getTime() : 0
                            return dateB - dateA
                        })}
                        currentConversationId={currentConversation}
                        onSelectConversation={(id) => {
                            setCurrentConversation(id)
                            if (window.innerWidth < 768) setSidebarOpen(false)
                        }}
                        onNewChat={createConversation}
                        onDeleteConversation={deleteConversation}
                        onRenameConversation={renameConversation}
                        onTogglePin={togglePin}
                        onToggleArchive={toggleArchive}
                        onSearchClick={() => setShowSearch(true)}
                        onSettingsClick={(tab = 'general') => {
                            setSettingsTab(tab)
                            setShowSettings(true)
                        }}
                        darkMode={darkMode}
                        toggleTheme={() => setDarkMode(!darkMode)}
                        userProfile={userProfile}
                    />

                    <main className="main-content">
                        <Header
                            onOpenSidebar={() => setSidebarOpen(true)}
                            isMobile={isMobile}
                            currentConversationId={currentConversation}
                            onDeleteConversation={deleteConversation}
                            onRenameConversation={renameConversation}
                            onTogglePin={togglePin}
                            onToggleArchive={toggleArchive}
                            currentChat={conversations.find(c => c.id === currentConversation)}
                            onRenameClick={() => {
                                const currentConv = conversations.find(c => c.id === currentConversation)
                                setModalTempTitle(currentConv?.title || '')
                                setShowRenameModal(true)
                                sessionStorage.setItem('isNewRenameModal', 'true')
                            }}
                            title={conversations.find(c => c.id === currentConversation)?.title}
                            onSettingsClick={(tab = 'general') => {
                                setSettingsTab(tab)
                                setShowSettings(true)
                            }}
                            onToggleTheme={() => setDarkMode(!darkMode)}
                            darkMode={darkMode}
                            userProfile={userProfile}
                            onHelpClick={() => {
                                setTourVersion(prev => prev + 1)
                                setShowTour(true)
                            }}
                        />

                        {showRenameModal && (
                            <div className="rename-modal-overlay" onClick={() => setShowRenameModal(false)}>
                                <div className="rename-modal-content" onClick={e => e.stopPropagation()}>
                                    <h3 className="rename-modal-title">Đổi tên đoạn chat</h3>
                                    <input
                                        className="premium-rename-input"
                                        value={modalTempTitle}
                                        onChange={(e) => setModalTempTitle(e.target.value)}
                                        onKeyDown={(e) => {
                                            if (e.key === 'Enter') handleSaveRename()
                                            if (e.key === 'Escape') setShowRenameModal(false)
                                        }}
                                        autoFocus
                                        onFocus={e => {
                                            const isRestored = !sessionStorage.getItem('isNewRenameModal');
                                            if (!isRestored) {
                                                e.target.select();
                                                sessionStorage.removeItem('isNewRenameModal');
                                            }
                                        }}
                                    />
                                    <div className="rename-modal-actions">
                                        <button className="modal-btn modal-btn-cancel" onClick={() => setShowRenameModal(false)}>Hủy</button>
                                        <button className="modal-btn modal-btn-save" onClick={handleSaveRename}>Lưu</button>
                                    </div>
                                </div>
                            </div>
                        )}

                        {isLoading && (
                            <div className="loading-bar">
                                <div className="loading-progress"></div>
                            </div>
                        )}

                        <MessageList
                            messages={messages}
                            isLoading={isLoading}
                            conversationId={currentConversation}
                            onExampleClick={(text) => sendMessage(text, [])}
                            onImageClick={(images, index) => setViewerData({ images, index })}
                            userAvatar={userProfile.avatar}
                            userName={userProfile.name}
                        />

                        <ChatInput
                            onSendMessage={sendMessage}
                            isLoading={isLoading}
                            onImageClick={(images, index) => setViewerData({ images, index })}
                        />
                    </main>

                    {showSearch && (
                        <SearchModal
                            conversations={conversations}
                            onSelect={(id) => setCurrentConversation(id)}
                            onClose={() => setShowSearch(false)}
                            isRestored={isInitialMountRef.current}
                        />
                    )}

                    {showSettings && (
                        <SettingsModal
                            onClose={() => setShowSettings(false)}
                            darkMode={darkMode}
                            onToggleTheme={() => setDarkMode(!darkMode)}
                            archivedSessions={conversations.filter(c => c.isArchived)}
                            onRestoreSession={(id) => toggleArchive(id)}
                            initialTab={settingsTab}
                            userProfile={userProfile}
                            onUpdateProfile={handleUpdateProfile}
                            isRestored={isInitialMountRef.current}
                            onTabChange={setSettingsTab}
                        />
                    )}

                    {showPinLimitToast && (
                        <div className="premium-toast warning">
                            <div className="toast-icon">⚠️</div>
                            <div className="toast-content">
                                <strong>Giới hạn ghim</strong>
                                <p>Bạn chỉ có thể ghim tối đa 5 đoạn chat.</p>
                            </div>
                        </div>
                    )}
                </>
            )}

            {/* Always render at fixed position to prevent DOM unmount/remount on isInitializing change */}
            {viewerData && (
                <ImageViewer
                    images={viewerData.images}
                    startIndex={viewerData.index}
                    onClose={() => setViewerData(null)}
                    onIndexChange={(newIndex) => {
                        setViewerData(prev => prev ? { ...prev, index: newIndex } : null)
                    }}
                    isRestored={isInitialMountRef.current || isInitializing}
                />
            )}
        </div>
    )
}

export default App
