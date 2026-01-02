import React, { useState, useEffect, useMemo } from 'react';
import Joyride, { STATUS } from 'react-joyride';


const GuideTour = ({ darkMode, tourVersion, onTourEnd }) => {
    const steps = useMemo(() => [
        {
            target: 'body',
            title: 'Xin chào, tôi là Pochi',
            content: 'Cùng bắt đầu khám phá không gian làm việc của bạn nhé!',
            placement: 'center',
            disableBeacon: true,
        },
        {
            target: 'body',
            title: 'Thao tác nhanh',
            content: (
                <div className="tour-shortcuts-container">
                    <div className="shortcuts-intro">Sử dụng bàn phím để điều khiển linh hoạt:</div>
                    <div className="shortcuts-grid">
                        <span className="kbd-bullet">•</span>
                        <div className="kbd-center">
                            <span className="kbd-key">←</span>
                            <span className="kbd-key">→</span>
                        </div>
                        <span className="kbd-colon">:</span>
                        <span className="kbd-text">Điều hướng các bước.</span>

                        <span className="kbd-bullet">•</span>
                        <div className="kbd-center">
                            <span className="kbd-key">Esc</span>
                        </div>
                        <span className="kbd-colon">:</span>
                        <span className="kbd-text">Bỏ qua hướng dẫn nhanh.</span>

                        <span className="kbd-bullet">•</span>
                        <div className="kbd-center">
                            <span className="kbd-key">Enter</span>
                        </div>
                        <span className="kbd-colon">:</span>
                        <span className="kbd-text">Hoàn tất hướng dẫn.</span>
                    </div>
                </div>
            ),
            placement: 'center',
            disableBeacon: true,
        },
        {
            target: '#tour-new-chat',
            title: 'Đoạn chat mới',
            content: 'Nơi bạn bắt đầu những cuộc trò chuyện mới với Pochi linh hoạt và nhanh chóng.',
            disableBeacon: true,
        },
        {
            target: '#tour-chat-input-area',
            title: 'Khung gửi tin nhắn',
            content: 'Nhập nội dung câu hỏi, đính kèm hình ảnh để trò chuyện cùng Pochi.',
            disableBeacon: true,
        },
        {
            target: '#tour-chat-interface',
            title: 'Giao diện trò chuyện',
            content: 'Khu vực hiển thị nội dung trao đổi giữa bạn và Pochi một cách trực quan.',
            disableBeacon: true,
        },
        {
            target: '#tour-history-section',
            title: 'Lịch sử trò chuyện',
            content: 'Toàn bộ các cuộc trò chuyện của bạn đều được lưu trữ an toàn tại đây.',
            spotlightPadding: 5,
            disableBeacon: true,
        },
        {
            target: '#tour-chat-features',
            title: 'Tính năng nâng cao',
            content: 'Bạn có thể ghim, đổi tên, lưu trữ hoặc xóa các cuộc trò chuyện thông qua menu này.',
            spotlightPadding: 5,
            disableBeacon: true,
        },
        {
            target: '#tour-profile-header-avatar',
            title: 'Cài đặt cá nhân (Header)',
            content: 'Bạn có thể truy cập cài đặt, quản lý tài khoản hoặc đăng xuất nhanh tại logo góc trên này.',
            spotlightPadding: 5,
            disableBeacon: true,
        },
        {
            target: '#tour-profile-sidebar-avatar',
            title: 'Cài đặt cá nhân (Sidebar)',
            content: 'Hoặc bạn cũng có thể thay đổi chế độ tối / sáng và xem tin nhắn lưu trữ tại logo phía dưới này.',
            spotlightPadding: 5,
            disableBeacon: true,
        },
        {
            target: '#tour-search',
            title: 'Tìm kiếm đoạn chat',
            content: 'Giúp bạn tìm lại những thông tin cũ trong lịch sử trò chuyện chỉ với vài phím gõ.',
            spotlightPadding: 5,
            disableBeacon: true,
        },
        {
            target: '#tour-toggle-sidebar',
            title: 'Thu gọn thanh bên',
            content: 'Tối ưu không gian làm việc bằng cách thu gọn thanh bên khi cần thiết.',
            spotlightPadding: 5,
            disableBeacon: true,
        },
        {
            target: '#tour-help-btn',
            title: 'Trợ giúp & Hướng dẫn',
            content: 'Bất cứ lúc nào bạn cần, hãy nhấn vào đây để xem lại hướng dẫn sử dụng nhé!',
            disableBeacon: true,
        },
        {
            target: 'body',
            title: 'Tổng hợp phím tắt',
            content: (
                <div className="tour-shortcuts-container">
                    <div className="shortcuts-intro">Làm chủ ứng dụng qua các phím tắt nhanh:</div>
                    <div className="shortcuts-grid">
                        <span className="kbd-bullet">•</span>
                        <div className="kbd-center">
                            <span className="kbd-key">{navigator.platform.toUpperCase().indexOf('MAC') >= 0 ? '⌘' : 'Ctrl'}</span>
                            <span className="kbd-key">F</span>
                        </div>
                        <span className="kbd-colon">:</span>
                        <span className="kbd-text">Tìm kiếm trò chuyện.</span>

                        <span className="kbd-bullet">•</span>
                        <div className="kbd-center">
                            <span className="kbd-key">{navigator.platform.toUpperCase().indexOf('MAC') >= 0 ? '⌘' : 'Ctrl'}</span>
                            <span className="kbd-key">E</span>
                        </div>
                        <span className="kbd-colon">:</span>
                        <span className="kbd-text">Tạo đoạn chat mới.</span>

                        <span className="kbd-bullet">•</span>
                        <div className="kbd-center">
                            <span className="kbd-key">{navigator.platform.toUpperCase().indexOf('MAC') >= 0 ? '⌘' : 'Ctrl'}</span>
                            <span className="kbd-key">K</span>
                        </div>
                        <span className="kbd-colon">:</span>
                        <span className="kbd-text">Bật/tắt chế độ tối.</span>

                        <span className="kbd-bullet">•</span>
                        <div className="kbd-center">
                            <span className="kbd-key">{navigator.platform.toUpperCase().indexOf('MAC') >= 0 ? '⌘' : 'Ctrl'}</span>
                            <span className="kbd-key">X</span>
                        </div>
                        <span className="kbd-colon">:</span>
                        <span className="kbd-text">Mở cài đặt chung.</span>

                        <span className="kbd-bullet">•</span>
                        <div className="kbd-center">
                            <span className="kbd-key">{navigator.platform.toUpperCase().indexOf('MAC') >= 0 ? '⌘' : 'Ctrl'}</span>
                            <span className="kbd-key">I</span>
                        </div>
                        <span className="kbd-colon">:</span>
                        <span className="kbd-text">Thông tin tài khoản.</span>
                    </div>
                    <div style={{
                        marginTop: '20px',
                        fontSize: '0.95rem',
                        fontWeight: 600,
                        color: darkMode ? 'var(--text-secondary)' : '#4b5563',
                        textAlign: 'center',
                        paddingTop: '12px',
                        borderTop: `1px solid ${darkMode ? 'rgba(255,255,255,0.1)' : 'rgba(0,0,0,0.05)'}`
                    }}>
                        Ấn phím tắt <span className="kbd-key">Enter</span> để hoàn tất hướng dẫn.
                    </div>
                </div>
            ),
            placement: 'center',
            disableBeacon: true,
        }
    ], [darkMode]);

    const [run, setRun] = useState(false);
    const [stepIndex, setStepIndex] = useState(() => {
        const savedIndex = localStorage.getItem('tourStepIndex');
        return (savedIndex && savedIndex !== '-1') ? parseInt(savedIndex, 10) : 0;
    });

    const finalizeTour = () => {
        setRun(false);
        setStepIndex(0);
        localStorage.setItem('hasSeenTour', 'true');
        localStorage.setItem('tourStepIndex', '-1');

        if (onTourEnd) onTourEnd();

        // Remove focus from whatever triggered the end/skip to prevent persistent focus outlines
        if (document.activeElement && typeof document.activeElement.blur === 'function') {
            document.activeElement.blur();
        }
    };

    const handleJoyrideCallback = (data) => {
        const { action, index, status, type, size } = data;

        if (type === 'step:after' || type === 'target:not_found') {
            const isLastStep = index === size - 1;
            if (isLastStep && action === 'next') {
                finalizeTour();
                return;
            }

            const nextIndex = index + (action === 'next' ? 1 : -1);
            if (nextIndex >= 0 && nextIndex < size) {
                setStepIndex(nextIndex);
                localStorage.setItem('tourStepIndex', nextIndex.toString());
            }
        }

        const finishedStatuses = [STATUS.FINISHED, STATUS.SKIPPED];
        if (finishedStatuses.includes(status)) {
            finalizeTour();
        }
    };

    useEffect(() => {
        const hasSeenTour = localStorage.getItem('hasSeenTour');
        const savedIndex = localStorage.getItem('tourStepIndex');

        if (tourVersion > 0) {
            setStepIndex(0);
            localStorage.setItem('tourStepIndex', '0');
            setRun(true);
        } else if (tourVersion === -1) {
            setRun(false);
        } else if (!hasSeenTour || (savedIndex !== null && savedIndex !== '-1')) {
            setRun(true);
        } else {
            setRun(false);
        }
    }, [tourVersion]);

    useEffect(() => {
        if (!run) return;

        const handleKeyDown = (e) => {
            const isLastStep = stepIndex === steps.length - 1;
            const isFirstStep = stepIndex === 0;

            switch (e.key) {
                case 'ArrowRight':
                    if (!isLastStep) {
                        e.preventDefault();
                        const nextIndex = stepIndex + 1;
                        setStepIndex(nextIndex);
                        localStorage.setItem('tourStepIndex', nextIndex.toString());
                    }
                    break;
                case 'ArrowLeft':
                    if (!isFirstStep) {
                        e.preventDefault();
                        const prevIndex = stepIndex - 1;
                        setStepIndex(prevIndex);
                        localStorage.setItem('tourStepIndex', prevIndex.toString());
                    }
                    break;
                case 'Enter':
                    e.preventDefault();
                    if (isLastStep) {
                        finalizeTour();
                    }
                    break;
                case 'Escape':
                    e.preventDefault();
                    finalizeTour();
                    break;
                default:
                    break;
            }
        };

        window.addEventListener('keydown', handleKeyDown);
        return () => window.removeEventListener('keydown', handleKeyDown);
    }, [run, stepIndex, steps]);

    const CustomTooltip = ({
        index,
        step,
        size,
        backProps,
        primaryProps,
        skipProps,
        tooltipProps,
        arrowProps,
        isLastStep
    }) => {
        const safeTooltipProps = tooltipProps || {};
        const placement = safeTooltipProps['data-placement'] || step?.placement || 'bottom';

        return (
            <div {...safeTooltipProps} className="tour-tooltip glass" data-placement={placement}>
                <div className="tour-header">
                    <div className="tour-header-left">
                        <span className="tour-progress">{index + 1} / {size}</span>
                    </div>
                    <div className="tour-header-right">
                        {index > 0 && (
                            <button {...backProps} className="tour-btn-nav tour-btn-back-header">
                                Quay lại
                            </button>
                        )}
                        <button {...primaryProps} className="tour-btn-nav tour-btn-next-header">
                            {isLastStep ? 'Hoàn tất' : 'Tiếp theo'}
                        </button>
                    </div>
                </div>

                <div className="tour-content">
                    {step?.title && <h4 className="tour-title">{step.title}</h4>}
                    <div className="tour-body">{step?.content}</div>
                </div>

                <div className="tour-footer">
                    {!isLastStep && (
                        <button {...skipProps} className="tour-btn-skip">
                            Bỏ qua
                        </button>
                    )}
                </div>

                <style dangerouslySetInnerHTML={{
                    __html: `
                    .tour-tooltip {
                        max-width: 360px;
                        padding: 20px;
                        border-radius: 20px;
                        box-shadow: 0 25px 50px -12px rgba(0, 0, 0, 0.5);
                        font-family: 'Inter', sans-serif;
                        color: var(--text-primary);
                        border: 1px solid var(--border-light);
                        position: relative;
                        background: ${darkMode ? 'var(--bg-surface)' : '#f9fafb'} !important;
                    }
                    .tour-header {
                        display: flex;
                        align-items: center;
                        justify-content: space-between;
                        margin-bottom: 20px;
                        padding-bottom: 12px;
                        border-bottom: 1px solid var(--border-light);
                    }
                    .tour-header-right {
                        display: flex;
                        gap: 8px;
                    }
                    .tour-progress {
                        font-size: 0.75rem;
                        font-weight: 700;
                        color: var(--brand-primary);
                        background: var(--bg-surface-hover);
                        padding: 4px 10px;
                        border-radius: 12px;
                        font-family: 'Outfit', sans-serif;
                    }
                    .tour-btn-nav {
                        border: none;
                        padding: 6px 14px;
                        border-radius: 8px;
                        font-weight: 700;
                        font-size: 0.85rem;
                        cursor: pointer;
                        transition: background 0.2s, color 0.2s;
                        font-family: 'Outfit', sans-serif;
                        outline: none !important;
                    }
                    .tour-btn-next-header {
                        background: var(--brand-primary);
                        color: white;
                    }
                    .tour-btn-next-header:hover {
                        background: var(--brand-hover);
                    }
                    .tour-btn-back-header {
                        background: var(--bg-surface-hover);
                        color: var(--text-secondary);
                    }
                    .tour-btn-back-header:hover {
                        color: var(--text-primary);
                        background: var(--border-light);
                    }
                    .tour-title {
                        font-family: 'Outfit', sans-serif;
                        font-size: 1.2rem;
                        font-weight: 800;
                        margin: 0 0 10px 0;
                        color: var(--text-primary);
                        letter-spacing: -0.01em;
                    }
                    .tour-body {
                        font-size: 0.95rem;
                        line-height: 1.6;
                        color: ${darkMode ? 'var(--text-secondary)' : '#4b5563'};
                        white-space: pre-wrap;
                        font-weight: 600;
                    }
                    .tour-footer {
                        margin-top: 16px;
                        display: flex;
                        justify-content: flex-start;
                    }
                    .tour-btn-skip {
                        background: transparent;
                        color: var(--text-tertiary);
                        border: none;
                        padding: 4px 0;
                        font-weight: 600;
                        font-size: 0.85rem;
                        cursor: pointer;
                        transition: color 0.2s;
                        text-decoration: underline;
                        text-underline-offset: 4px;
                        font-family: 'Outfit', sans-serif;
                        outline: none !important;
                    }
                    .tour-btn-skip:hover {
                        color: var(--text-primary);
                    }
                    .kbd-key {
                        background: ${darkMode ? '#2d2d2d' : '#ffffff'};
                        border: 1px solid ${darkMode ? '#444' : '#94a3b8'};
                        border-bottom-width: 3px;
                        border-radius: 6px;
                        padding: 1px 8px;
                        font-size: 0.8rem;
                        font-weight: 800;
                        color: ${darkMode ? 'var(--text-primary)' : '#1e293b'};
                        font-family: 'Inter', system-ui, sans-serif;
                        display: inline-flex;
                        align-items: center;
                        justify-content: center;
                        min-width: 24px;
                        height: 24px;
                        margin: 0 2px;
                        box-shadow: 0 2px 0 ${darkMode ? 'rgba(0,0,0,0.5)' : 'rgba(0,0,0,0.15)'};
                    }
                    .tour-shortcuts-container {
                        text-align: left;
                        font-weight: 600;
                    }
                    .shortcuts-intro {
                        margin-bottom: 12px;
                        color: var(--text-primary);
                    }
                    .shortcuts-grid {
                        display: grid;
                        grid-template-columns: 20px 80px 10px 1fr;
                        align-items: center;
                        gap: 6px 0;
                    }
                    .kbd-bullet {
                        color: var(--text-tertiary);
                        font-size: 1.2rem;
                    }
                    .kbd-center {
                        display: flex;
                        justify-content: center;
                        gap: 6px;
                    }
                    .kbd-colon {
                        text-align: center;
                        font-weight: 800;
                        color: var(--text-secondary);
                    }
                    .kbd-text {
                        padding-left: 8px;
                        color: ${darkMode ? 'var(--text-secondary)' : '#4b5563'};
                    }
                `}} />
            </div>
        );
    };

    return (
        <Joyride
            key={tourVersion}
            steps={steps}
            run={run}
            stepIndex={stepIndex}
            continuous
            showSkipButton
            showProgress
            disableOverlayClose={true}
            disableBeacon={true}
            disableScrolling={false}
            tooltipComponent={CustomTooltip}
            callback={handleJoyrideCallback}
            styles={{
                options: {
                    arrowColor: 'transparent',
                    overlayColor: 'rgba(0, 0, 0, 0.7)',
                    zIndex: 10000,
                },
                spotlight: {
                    borderRadius: 8,
                    border: `4px dashed ${darkMode ? 'rgba(255, 255, 255, 0.7)' : '#334155'}`,
                },
                beacon: {
                    display: 'none',
                }
            }}
        />
    );
};

export default GuideTour;
