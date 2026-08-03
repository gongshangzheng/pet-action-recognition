import React, { useEffect, useRef, useState } from 'react';
import { Bot, Send, User, Sparkles, Play, Pause, Volume2, VolumeX, MessageSquare, X, ChevronUp, Share2, Film, Clock, Video, Download, Maximize2 } from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';
import { ChatMessage } from '../types';
import { getThumbIcon } from '../constants';

interface HomeViewProps {
    videoUrl: string;
    messages: ChatMessage[];
    handleJumpToVideo: (time: number, src?: string) => void;
    onSendMessage: (text: string) => void;
    onTriggerVlog?: () => void;
}

const PRESET_QUESTIONS = [
    "总结栗子表现",
    "奶油运动量分析",
    "🎬 查看 10:00 每日Vlog",
    "今天它们吃饭了吗？",
    "最近两只猫相处得好吗？"
];

// Interactive Vlog Card Component
const VlogBubble: React.FC<{ 
    msg: ChatMessage; 
    showToast: (msg: string) => void;
}> = ({ msg, showToast }) => {
    const segments = msg.vlogSegments || [];
    
    // Total simulated timeline duration calculations
    // segment 1: 15s (0 to 15s)
    // segment 2: 8s (15s to 23s)
    // segment 3: 12s (23s to 35s)
    // segment 4: 10s (35s to 45s)
    const segmentDurations = [15, 8, 12, 10];
    const segmentStarts = [0, 15, 23, 35];
    const totalDuration = 45;

    const [isPlaying, setIsPlaying] = useState(true);
    const [isMuted, setIsMuted] = useState(true);
    const [playbackRate, setPlaybackRate] = useState(2.0); // 2x default speed requested
    const [currentTime, setCurrentTime] = useState(0);
    const [showSpeedMenu, setShowSpeedMenu] = useState(false);
    const [isFullScreen, setIsFullScreen] = useState(false);

    const videoRef = useRef<HTMLVideoElement>(null);
    const fullscreenVideoRef = useRef<HTMLVideoElement>(null);

    // Sync play/pause and speed actions for video elements
    useEffect(() => {
        const video = videoRef.current;
        if (video) {
            video.playbackRate = playbackRate;
            if (isPlaying) {
                video.play().catch(() => {});
            } else {
                video.pause();
            }
        }
    }, [isPlaying, playbackRate]);

    useEffect(() => {
        const video = fullscreenVideoRef.current;
        if (video) {
            video.playbackRate = playbackRate;
            if (isPlaying) {
                video.play().catch(() => {});
            } else {
                video.pause();
            }
        }
    }, [isPlaying, playbackRate, isFullScreen]);

    // Sync volume/mute states
    useEffect(() => {
        const video = videoRef.current;
        if (video) {
            video.muted = isMuted;
        }
    }, [isMuted]);

    useEffect(() => {
        const video = fullscreenVideoRef.current;
        if (video) {
            video.muted = isMuted;
        }
    }, [isMuted, isFullScreen]);

    // Sync currentTime changes
    useEffect(() => {
        const video = videoRef.current;
        if (video) {
            if (Math.abs(video.currentTime - currentTime) > 0.6) {
                video.currentTime = currentTime;
            }
        }
    }, [currentTime]);

    useEffect(() => {
        const video = fullscreenVideoRef.current;
        if (video) {
            if (Math.abs(video.currentTime - currentTime) > 0.6) {
                video.currentTime = currentTime;
            }
        }
    }, [currentTime, isFullScreen]);

    // High performance animation frame timer for updating currentTime
    useEffect(() => {
        let lastTime = performance.now();
        let frameId: number;

        const update = () => {
            if (isPlaying) {
                const now = performance.now();
                const delta = (now - lastTime) / 1000;
                lastTime = now;
                setCurrentTime(prev => {
                    const next = prev + delta * playbackRate;
                    return next >= totalDuration ? 0 : next;
                });
            } else {
                lastTime = performance.now();
            }
            frameId = requestAnimationFrame(update);
        };

        frameId = requestAnimationFrame(update);
        return () => cancelAnimationFrame(frameId);
    }, [isPlaying, playbackRate]);

    const getActiveIndexFromTime = (time: number) => {
        if (time < 15) return 0;
        if (time < 23) return 1;
        if (time < 35) return 2;
        return 3;
    };

    const activeIndex = getActiveIndexFromTime(currentTime);
    const activeSegment = segments[activeIndex] || null;

    if (!activeSegment) return null;

    const handleProgressClick = (e: React.MouseEvent<HTMLDivElement>) => {
        const rect = e.currentTarget.getBoundingClientRect();
        const clickX = e.clientX - rect.left;
        const percentage = clickX / rect.width;
        const newTime = Math.max(0, Math.min(percentage * totalDuration, totalDuration - 0.1));
        setCurrentTime(newTime);
    };

    const formatTime = (secs: number) => {
        if (isNaN(secs) || secs === Infinity) return "00:00";
        const m = Math.floor(secs / 60);
        const s = Math.floor(secs % 60);
        return `${m < 10 ? '0' : ''}${m}:${s < 10 ? '0' : ''}${s}`;
    };

    return (
        <div className="bg-white rounded-2xl overflow-hidden shadow-lg border border-indigo-100 w-full max-w-sm animate-slide-up mt-1">
            {/* Interactive Player Screen */}
            <div 
                onClick={() => setIsFullScreen(true)}
                className="relative aspect-video bg-black flex items-center justify-center overflow-hidden group cursor-pointer"
                title="点击进入沉浸全屏播放"
            >
                {/* Standard robust element rendering the pet material perfectly */}
                {activeSegment.url.endsWith('.mp4') ? (
                    <video 
                        ref={videoRef}
                        src={activeSegment.url} 
                        className="w-full h-full object-cover select-none"
                        muted={isMuted}
                        playsInline
                        loop
                    />
                ) : (
                    <img 
                        src={activeSegment.url} 
                        alt={activeSegment.title}
                        className="w-full h-full object-cover select-none"
                        referrerPolicy="no-referrer"
                    />
                )}

                {/* Shading & overlay controls */}
                <div className="absolute inset-0 bg-gradient-to-t from-black/95 via-black/10 to-transparent pointer-events-none opacity-90" />

                {/* Corner indicators */}
                <div className="absolute top-3 left-3 flex items-center gap-1.5 z-10 select-none pointer-events-none">
                    <div className="bg-indigo-600/95 shadow-lg backdrop-blur-md px-2 py-1 rounded-lg text-white font-sans text-[9.5px] font-black tracking-wide flex items-center gap-1">
                        <Film size={9.5} className="text-orange-400" />
                        每日Vlog
                    </div>
                    <div className="bg-black/60 shadow-lg backdrop-blur-md px-2 py-1 rounded-lg text-white font-mono text-[9px] flex items-center gap-1">
                        <Video size={10} className="text-orange-500" />
                        段落 {activeIndex + 1} / {segments.length}
                    </div>
                </div>

                <div className="absolute top-3 right-3 bg-indigo-600/90 text-white text-[9px] font-bold px-2 py-1 rounded-lg backdrop-blur-md flex items-center gap-1 z-10 select-none">
                    <Sparkles size={9} /> {activeSegment.time}
                </div>

                {/* Progress bar container */}
                <div className="absolute bottom-12 left-3 right-3 z-10" onClick={(e) => e.stopPropagation()}>
                    <div 
                        onClick={handleProgressClick}
                        className="w-full h-1.5 bg-white/20 hover:bg-white/40 rounded-full cursor-pointer relative transition-all group/bar"
                    >
                        {/* Played progress line */}
                        <div 
                            className="absolute top-0 left-0 h-full bg-indigo-500 rounded-full"
                            style={{ width: `${(currentTime / totalDuration) * 100}%` }}
                        />
                        {/* Playhead thumb indicator */}
                        <div 
                            className="absolute top-1/2 w-2 h-2 bg-white rounded-full shadow-sm transform -translate-y-1/2 -translate-x-1/2 opacity-0 group-hover/bar:opacity-100 transition-opacity"
                            style={{ left: `${(currentTime / totalDuration) * 100}%` }}
                        />
                    </div>
                </div>

                {/* Player Bottom Control Bar */}
                <div className="absolute bottom-2.5 left-3 right-3 flex items-center justify-between text-white z-10" onClick={(e) => e.stopPropagation()}>
                    <div className="flex items-center gap-2 min-w-0 flex-1 mr-2">
                        {/* Play/Pause Button */}
                        <button 
                            type="button"
                            onClick={() => setIsPlaying(!isPlaying)}
                            className="w-7 h-7 rounded-full bg-white/10 hover:bg-white/25 active:scale-90 backdrop-blur-md flex items-center justify-center text-white transition-all flex-shrink-0 cursor-pointer"
                        >
                            {isPlaying ? (
                                <Pause size={12} className="fill-current text-white" />
                            ) : (
                                <Play size={12} className="fill-current translate-x-[1px] text-white" />
                            )}
                        </button>

                        {/* Metadata details */}
                        <div className="min-w-0 leading-none">
                            <p className="text-[10px] text-gray-200 font-mono tracking-wide">
                                {formatTime(currentTime)} / {formatTime(totalDuration)}
                            </p>
                        </div>
                    </div>

                    <div className="flex items-center gap-1.5 flex-shrink-0 select-none">
                        {/* Audio / Volume Option Button */}
                        <button
                            type="button"
                            onClick={() => {
                                setIsMuted(!isMuted);
                                showToast(isMuted ? "🔊 声音已打开！" : "🔇 已切换为静音播放");
                            }}
                            className={`w-7 h-7 rounded-full flex items-center justify-center backdrop-blur-md active:scale-95 transition-all cursor-pointer ${
                                isMuted ? 'bg-white/10 text-gray-300 hover:bg-white/20' : 'bg-amber-600/90 text-white shadow-sm'
                            }`}
                        >
                            {isMuted ? <VolumeX size={12} /> : <Volume2 size={12} />}
                        </button>

                        {/* Playback rate multiplier speed controls */}
                        <div className="relative">
                            <button
                                type="button"
                                onClick={() => setShowSpeedMenu(!showSpeedMenu)}
                                className="h-7 px-2 rounded-full bg-white/10 hover:bg-white/20 active:scale-95 backdrop-blur-md text-[10px] font-mono font-bold text-white flex items-center justify-center gap-0.5 transition-all cursor-pointer"
                            >
                                {playbackRate.toFixed(1)}x
                            </button>
                            
                            {showSpeedMenu && (
                                <div className="absolute bottom-9 right-0 bg-black/95 backdrop-blur-lg rounded-xl border border-white/10 p-1 flex flex-col gap-0.5 shadow-2xl z-30 min-w-[56px] overflow-hidden">
                                    {[1.0, 1.5, 2.0, 2.5].map((rate) => (
                                        <button
                                            key={rate}
                                            type="button"
                                            onClick={() => {
                                                setPlaybackRate(rate);
                                                setShowSpeedMenu(false);
                                                showToast(`⚡ 已切换至 ${rate.toFixed(1)} 倍速播放`);
                                            }}
                                            className={`text-[9.5px] font-mono py-1 px-1.5 rounded-lg text-center transition-all cursor-pointer ${
                                                playbackRate === rate 
                                                ? 'bg-indigo-600 text-white font-black shadow-sm' 
                                                : "text-gray-300 hover:bg-white/15"
                                            }`}
                                        >
                                            {rate.toFixed(1)}x
                                        </button>
                                    ))}
                                </div>
                            )}
                        </div>

                        {/* Expand full screen button */}
                        <button
                            type="button"
                            onClick={() => setIsFullScreen(true)}
                            className="w-7 h-7 rounded-full bg-white/10 hover:bg-white/25 active:scale-90 backdrop-blur-md flex items-center justify-center text-white transition-all cursor-pointer"
                        >
                            <Maximize2 size={12} />
                        </button>
                    </div>
                </div>
            </div>



            {/* Actions Footer */}
            <div className="p-3 bg-white border-t border-gray-100 flex gap-2">
                <button 
                    type="button"
                    onClick={() => {
                        showToast("🎉 Vlog 下载成功！完整视频及成长日志已保存至本地相册。");
                    }}
                    className="flex-1 bg-gray-50 hover:bg-gray-100 border border-gray-100 text-gray-600 py-2.5 rounded-xl text-xs font-bold flex items-center justify-center gap-1.5 active:scale-95 transition-all text-center leading-none"
                >
                    <Download size={13} />
                    下载完整 Vlog
                </button>
                <button 
                    type="button"
                    onClick={() => showToast("正在为您生成精美的 Vlog 高光分享卡片...")}
                    className="flex-1 bg-indigo-600 hover:bg-indigo-700 text-white py-2.5 rounded-xl text-xs font-bold flex items-center justify-center gap-1.5 active:scale-95 transition-all shadow-md shadow-indigo-100 text-center leading-none"
                >
                    <Share2 size={13} />
                    一键分享
                </button>
            </div>

            {/* Custom Cinematic Full Screen Player Modal */}
            <AnimatePresence>
                {isFullScreen && (
                    <div 
                        className="fixed inset-0 z-[100] bg-black flex flex-col justify-between p-4 select-none"
                        onClick={() => setIsFullScreen(false)}
                    >
                        {/* Top close bar */}
                        <div className="flex items-center justify-between text-white/90 z-10 w-full max-w-lg mx-auto" onClick={(e) => e.stopPropagation()}>
                            <span className="text-xs font-mono font-bold bg-white/10 px-3 py-1 rounded-full flex items-center gap-1">
                                <Sparkles size={11} className="text-yellow-400" /> Vlog 沉浸模式
                            </span>
                            <button 
                                onClick={() => setIsFullScreen(false)}
                                className="p-2 bg-white/10 rounded-full hover:bg-white/20 transition-all cursor-pointer"
                            >
                                <X size={18} />
                            </button>
                        </div>

                        {/* Centered Large Main View */}
                        <div className="flex-1 flex flex-col items-center justify-center w-full max-w-lg mx-auto relative my-4" onClick={(e) => e.stopPropagation()}>
                            <div className="w-full aspect-video bg-neutral-900 rounded-2xl overflow-hidden relative border border-white/5 shadow-2xl flex items-center justify-center">
                                {activeSegment.url.endsWith('.mp4') ? (
                                    <video 
                                        ref={fullscreenVideoRef}
                                        src={activeSegment.url} 
                                        className="max-h-full max-w-full object-contain select-none"
                                        muted={isMuted}
                                        playsInline
                                        loop
                                    />
                                ) : (
                                    <img 
                                        src={activeSegment.url} 
                                        alt={activeSegment.title}
                                        className="max-h-full max-w-full object-contain select-none"
                                        referrerPolicy="no-referrer"
                                    />
                                )}

                                {/* Corner indicator */}
                                <div className="absolute top-3 left-3 bg-black/60 backdrop-blur-md px-2 py-1 rounded-lg text-white font-mono text-[9px] flex items-center gap-1 z-10 select-none">
                                    <Video size={10} className="text-orange-500" />
                                    段落 {activeIndex + 1} / {segments.length}
                                </div>

                                <div className="absolute top-3 right-3 bg-indigo-600/90 text-white text-[9px] font-bold px-2 py-1 rounded-lg backdrop-blur-md flex items-center gap-1 z-10 select-none">
                                    <Sparkles size={9} /> {activeSegment.time}
                                </div>
                            </div>


                        </div>

                        {/* Bottom controls */}
                        <div className="w-full max-w-lg mx-auto space-y-4 pb-safe bg-neutral-950/60 p-4 rounded-3xl border border-white/5 backdrop-blur-md" onClick={(e) => e.stopPropagation()}>
                            {/* Progress bar container */}
                            <div className="px-1">
                                <div 
                                    onClick={handleProgressClick}
                                    className="w-full h-1.5 bg-white/20 hover:bg-white/45 rounded-full cursor-pointer relative transition-all group/fullbar"
                                >
                                    <div 
                                        className="absolute top-0 left-0 h-full bg-indigo-500 rounded-full"
                                        style={{ width: `${(currentTime / totalDuration) * 100}%` }}
                                    />
                                    <div 
                                        className="absolute top-1/2 w-2.5 h-2.5 bg-white rounded-full shadow-md transform -translate-y-1/2 -translate-x-1/2"
                                        style={{ left: `${(currentTime / totalDuration) * 100}%` }}
                                    />
                                </div>
                            </div>

                            {/* Control actions */}
                            <div className="flex items-center justify-between text-white text-xs">
                                <div className="flex items-center gap-3">
                                    {/* Play/Pause Button */}
                                    <button 
                                        type="button"
                                        onClick={() => setIsPlaying(!isPlaying)}
                                        className="w-8 h-8 rounded-full bg-white/10 hover:bg-white/25 active:scale-90 flex items-center justify-center text-white transition-all cursor-pointer"
                                    >
                                        {isPlaying ? (
                                            <Pause size={14} className="fill-current text-white" />
                                        ) : (
                                            <Play size={14} className="fill-current translate-x-[1px] text-white" />
                                        )}
                                    </button>

                                    <div className="leading-tight">
                                        <span className="text-[10px] text-gray-400 font-bold uppercase tracking-wider">播放进度</span>
                                        <p className="text-[11.5px] font-mono text-white font-black mt-0.5">
                                            {formatTime(currentTime)} / {formatTime(totalDuration)}
                                        </p>
                                    </div>
                                </div>

                                <div className="flex items-center gap-2 select-none">
                                    {/* Audio Toggle */}
                                    <button
                                        type="button"
                                        onClick={() => {
                                            setIsMuted(!isMuted);
                                            showToast(isMuted ? "🔊 声音已打开！" : "🔇 已切换为静音播放");
                                        }}
                                        className={`w-8 h-8 rounded-full flex items-center justify-center active:scale-95 transition-all cursor-pointer ${
                                            isMuted ? 'bg-white/10 text-gray-300 hover:bg-white/20' : 'bg-amber-600 shadow-sm text-white'
                                        }`}
                                    >
                                        {isMuted ? <VolumeX size={14} /> : <Volume2 size={14} />}
                                    </button>

                                    {/* Play Rate multiplier speed controls */}
                                    <div className="relative">
                                        <button
                                            type="button"
                                            onClick={() => setShowSpeedMenu(!showSpeedMenu)}
                                            className="h-8 px-2.5 rounded-full bg-white/10 hover:bg-white/20 active:scale-95 text-[10px] font-mono font-bold text-white flex items-center justify-center gap-0.5 transition-all cursor-pointer"
                                        >
                                            {playbackRate.toFixed(1)}x
                                        </button>
                                        
                                        {showSpeedMenu && (
                                            <div className="absolute bottom-10 right-0 bg-neutral-900 border border-white/10 p-1 flex flex-col gap-0.5 rounded-xl shadow-2xl z-30 min-w-[56px] overflow-hidden">
                                                {[1.0, 1.5, 2.0, 2.5].map((rate) => (
                                                    <button
                                                        key={rate}
                                                        type="button"
                                                        onClick={() => {
                                                            setPlaybackRate(rate);
                                                            setShowSpeedMenu(false);
                                                            showToast(`⚡ 已切换至 ${rate.toFixed(1)} 倍速播放`);
                                                        }}
                                                        className={`text-[9.5px] font-mono py-1 px-1.5 rounded-lg text-center transition-all cursor-pointer ${
                                                            playbackRate === rate 
                                                            ? 'bg-indigo-600 text-white font-black' 
                                                            : "text-gray-300 hover:bg-white/15"
                                                        }`}
                                                    >
                                                        {rate.toFixed(1)}x
                                                    </button>
                                                ))}
                                            </div>
                                        )}
                                    </div>
                                </div>
                            </div>


                        </div>
                    </div>
                )}
            </AnimatePresence>
        </div>
    );
};

const ChatBubble: React.FC<{ 
    msg: ChatMessage; 
    handleJumpToVideo: any; 
    showToast: (msg: string) => void;
    onShareMeme: (text: string, url: string) => void;
}> = ({ msg, handleJumpToVideo, showToast, onShareMeme }) => {
    const isBot = msg.sender === 'bot';
    
    return (
        <div className={`flex gap-3 mb-4 animate-fade-in ${isBot ? '' : 'flex-row-reverse'}`}>
            {/* Avatar */}
            <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 shadow-sm ${isBot ? 'bg-indigo-600 text-white' : 'bg-gray-200 text-gray-500'}`}>
                {isBot ? <Bot size={18} /> : <User size={18} />}
            </div>
            
            <div className={`max-w-[80%] flex flex-col ${isBot ? 'items-start' : 'items-end'}`}>
                {/* Name & Time */}
                <div className="flex items-center gap-2 mb-1 px-1">
                    <span className="text-[10px] text-gray-400">{isBot ? '派爪Petra 智能助手' : '我'}</span>
                    <span className="text-[10px] text-gray-300">{msg.time}</span>
                </div>

                {/* Content Bubble */}
                {msg.type === 'text' ? (
                    <div className={`px-4 py-2.5 rounded-2xl text-sm leading-relaxed shadow-sm ${isBot ? 'bg-white text-gray-700 rounded-tl-none border border-gray-100' : 'bg-indigo-600 text-white rounded-tr-none'}`}>
                        {msg.text}
                    </div>
                ) : msg.type === 'vlog' ? (
                    <div className="flex flex-col gap-2">
                        {msg.text && (
                            <div className="px-4 py-2.5 rounded-2xl text-sm leading-relaxed shadow-sm bg-white text-gray-700 rounded-tl-none border border-gray-100">
                                {msg.text}
                            </div>
                        )}
                        <VlogBubble msg={msg} showToast={showToast} />
                    </div>
                ) : msg.type === 'meme' ? (
                    // Meme Card Bubble
                    <div className="bg-white rounded-2xl overflow-hidden shadow-lg border border-indigo-100 w-72 animate-slide-up">
                        <div className="p-4">
                            <p className="text-sm text-gray-700 leading-relaxed mb-4">
                                {msg.text}
                            </p>
                            <div className="relative rounded-xl overflow-hidden bg-gray-900 aspect-square flex items-center justify-center group">
                                {msg.memeUrl?.endsWith('.gif') ? (
                                    <img 
                                        src={msg.memeUrl} 
                                        alt="Meme GIF" 
                                        className="w-full h-full object-cover"
                                        referrerPolicy="no-referrer"
                                    />
                                ) : (
                                    <video 
                                        src={msg.memeUrl} 
                                        autoPlay 
                                        loop 
                                        muted 
                                        playsInline 
                                        className="w-full h-full object-cover"
                                    />
                                )}
                                <div className="absolute top-2 right-2 bg-black/40 backdrop-blur-md text-white text-[10px] px-2 py-1 rounded-full flex items-center gap-1">
                                    <Sparkles size={10} /> 精彩瞬间
                                </div>
                            </div>
                            <button 
                                onClick={() => onShareMeme(msg.text || '', msg.memeUrl || '')}
                                className="w-full mt-4 bg-indigo-600 hover:bg-indigo-750 text-white py-2.5 rounded-xl text-xs font-bold flex items-center justify-center gap-2 active:scale-95 transition-all shadow-md shadow-indigo-100 cursor-pointer"
                            >
                                <Share2 size={14} /> 分享给好友
                            </button>
                        </div>
                    </div>
                ) : (
                    // Event Card Bubble - Consistent with TimelineView
                    <div 
                        onClick={() => handleJumpToVideo(msg.eventData?.videoTime || 0, msg.eventData?.videoSrc)}
                        className="bg-white rounded-xl overflow-hidden shadow-md border border-indigo-50 w-64 cursor-pointer hover:ring-2 hover:ring-indigo-100 transition-all group"
                    >
                        <div className={`h-28 relative ${msg.eventData?.thumbColor} flex items-center justify-center`}>
                            <div className="absolute inset-0 bg-black/5 group-hover:bg-black/10 transition-colors"></div>
                            <div className="opacity-30 scale-125">{getThumbIcon(msg.eventData?.act[0] || '')}</div>
                            <div className="absolute inset-0 flex items-center justify-center">
                                <div className="w-8 h-8 bg-white/30 backdrop-blur-md rounded-full flex items-center justify-center shadow-lg group-hover:scale-110 transition-transform">
                                    <Play size={14} className="text-white fill-current ml-0.5"/>
                                </div>
                            </div>
                             <div className="absolute top-2 right-2 bg-black/40 text-white text-[9px] px-1.5 py-0.5 rounded backdrop-blur-md flex items-center gap-1">
                                <Sparkles size={8} /> {msg.eventData?.videoTime}s
                            </div>
                        </div>
                        <div className="p-3">
                            <div className="flex items-center gap-2 mb-1.5">
                                <span className="text-[10px] px-1.5 py-0.5 rounded-full font-bold bg-indigo-50 text-indigo-600">
                                    {msg.eventData?.cat}
                                </span>
                                <span className="text-[10px] text-gray-400">{msg.eventData?.time}</span>
                            </div>
                            <div className="flex gap-1 mb-2 flex-wrap">
                                {msg.eventData?.act.map((tag: string, i: number) => (
                                    <span key={i} className="text-[9px] px-1.5 py-0.5 rounded border border-indigo-100 bg-indigo-50/30 text-indigo-500">{tag}</span>
                                ))}
                            </div>
                            <p className="text-xs text-gray-600 line-clamp-2 leading-relaxed mb-3">
                                {msg.eventData?.desc}
                            </p>
                            <div className="bg-gray-50 rounded-lg p-2 flex items-start gap-2">
                                <Sparkles size={10} className="text-indigo-400 mt-0.5 flex-shrink-0"/>
                                <p className="text-[10px] text-gray-500 leading-snug">
                                    {msg.eventData?.stat}
                                </p>
                            </div>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};

const HomeView: React.FC<HomeViewProps> = ({ messages, handleJumpToVideo, onSendMessage, onTriggerVlog }) => {
    const scrollRef = useRef<HTMLDivElement>(null);
    const [inputText, setInputText] = useState('');
    const [isExpanded, setIsExpanded] = useState(false);
    const inputRef = useRef<HTMLInputElement>(null);
    const [toast, setToast] = useState<string | null>(null);
    const [shareMeme, setShareMeme] = useState<{ text: string; url: string } | null>(null);

    const showToast = (msg: string) => {
        setToast(msg);
        setTimeout(() => setToast(null), 3000);
    };

    const handleShareMemeTrigger = (text: string, url: string) => {
        setShareMeme({ text, url });
    };

    const handleDownloadMeme = async () => {
        if (!shareMeme) return;
        try {
            const response = await fetch(shareMeme.url);
            const blob = await response.blob();
            const blobUrl = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = blobUrl;
            link.download = shareMeme.url.split('/').pop() || 'meme.gif';
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            URL.revokeObjectURL(blobUrl);
            showToast("💾 表情包已保存至本地相册！");
        } catch (err) {
            const link = document.createElement('a');
            link.href = shareMeme.url;
            link.download = 'meme.gif';
            link.target = '_blank';
            link.click();
            showToast("💾 已打开表情包，请长按保存！");
        }
    };

    const handleJumpToWeChat = () => {
        try {
            window.location.href = "weixin://";
            showToast("正在尝试跳转微信，快去和好友分享表情包吧！");
        } catch (e) {
            showToast("无法拉起微信，请手动打开微信分享！");
        }
    };

    // Auto scroll to bottom
    useEffect(() => {
        if (scrollRef.current) {
            scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
        }
    }, [messages]);

    const handleSubmit = (e?: React.FormEvent) => {
        e?.preventDefault();
        if (!inputText.trim()) return;
        onSendMessage(inputText);
        setInputText('');
        setIsExpanded(false);
    };

    const handlePresetClick = (question: string) => {
        onSendMessage(question);
        setIsExpanded(false);
    };

    return (
        <div className="flex flex-col h-full bg-gray-50 relative overflow-hidden">
            {/* Toast alert */}
            <AnimatePresence>
                {toast && (
                    <motion.div 
                        initial={{ opacity: 0, y: 30, scale: 0.95 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        exit={{ opacity: 0, y: 20, scale: 0.95 }}
                        className="absolute bottom-20 left-4 right-4 bg-gray-900/90 backdrop-blur-xs text-white text-xs font-medium py-2.5 px-4 rounded-xl shadow-lg z-[99] text-center pointer-events-none"
                    >
                        {toast}
                    </motion.div>
                )}
            </AnimatePresence>
            {/* Header */}
            <div className="bg-white px-4 pt-6 pb-4 border-b border-gray-100 flex-shrink-0">
                <div className="flex items-center justify-between mb-4">
                    <h1 className="text-xl font-bold text-gray-900 flex items-center gap-2">
                        <Sparkles className="text-orange-500" size={20} />
                        派爪Petra AI 看护
                    </h1>
                    <div className="bg-green-50 text-green-600 text-[10px] font-bold px-2 py-1 rounded-full flex items-center gap-1">
                        <div className="w-1 h-1 bg-green-600 rounded-full"></div> 在线监护中
                    </div>
                </div>

                {/* Pet Status Cards */}
                <div className="grid grid-cols-2 gap-3">
                    <div className="bg-gray-50 rounded-xl p-3 flex flex-col relative overflow-hidden border border-gray-100">
                        <div className="flex items-center gap-2 mb-2">
                            <div className="w-6 h-6 rounded-full bg-gray-200 text-gray-600 text-[10px] font-bold flex items-center justify-center">栗</div>
                            <span className="font-bold text-xs text-gray-800">栗子</span>
                        </div>
                        <div className="flex justify-between items-end">
                            <span className="text-[10px] text-gray-400 uppercase tracking-wider">活跃度</span>
                            <span className="text-xs font-bold text-orange-500">92%</span>
                        </div>
                        <div className="w-full h-1 bg-gray-200 rounded-full mt-1.5 overflow-hidden">
                            <div className="h-full bg-gradient-to-r from-orange-400 to-orange-600 w-[92%] transition-all duration-1000"></div>
                        </div>
                    </div>
                    <div className="bg-gray-50 rounded-xl p-3 flex flex-col relative overflow-hidden border border-gray-100">
                        <div className="flex items-center gap-2 mb-2">
                            <div className="w-6 h-6 rounded-full bg-yellow-100 text-yellow-700 text-[10px] font-bold flex items-center justify-center">奶</div>
                            <span className="font-bold text-xs text-gray-800">奶油</span>
                        </div>
                        <div className="flex justify-between items-end">
                            <span className="text-[10px] text-gray-400 uppercase tracking-wider">活跃度</span>
                            <span className="text-xs font-bold text-yellow-500">28%</span>
                        </div>
                        <div className="w-full h-1 bg-gray-200 rounded-full mt-1.5 overflow-hidden">
                            <div className="h-full bg-yellow-400 w-[28%] transition-all duration-1000"></div>
                        </div>
                    </div>
                </div>
            </div>

            {/* Chatbot Area */}
            <div className="flex-1 overflow-y-auto p-4 bg-gray-50 scrollbar-hide pb-24" ref={scrollRef}>
                {messages.map((msg) => (
                    <ChatBubble key={msg.id} msg={msg} handleJumpToVideo={handleJumpToVideo} showToast={showToast} onShareMeme={handleShareMemeTrigger} />
                ))}
            </div>

            {/* Collapsed Bottom Bar */}
            {!isExpanded && (
                <motion.div 
                    layoutId="chat-input"
                    onClick={() => setIsExpanded(true)}
                    className="absolute bottom-4 left-4 right-4 bg-white rounded-full shadow-lg border border-gray-100 p-3 flex items-center gap-3 cursor-pointer hover:bg-gray-50 transition-colors z-20"
                >
                    <div className="w-8 h-8 rounded-full bg-indigo-50 flex items-center justify-center text-indigo-600">
                        <Bot size={18} />
                    </div>
                    <span className="text-sm text-gray-400 flex-1">和爱宠管家聊聊吧...</span>
                    <ChevronUp size={18} className="text-gray-300" />
                </motion.div>
            )}

            {/* Expanded Input Area */}
            <AnimatePresence>
                {isExpanded && (
                    <>
                        <motion.div 
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            onClick={() => setIsExpanded(false)}
                            className="absolute inset-0 bg-black/20 backdrop-blur-[2px] z-30"
                        />
                        <motion.div 
                            layoutId="chat-input"
                            initial={{ y: 100 }}
                            animate={{ y: 0 }}
                            exit={{ y: 100 }}
                            className="absolute bottom-0 left-0 right-0 bg-white rounded-t-3xl shadow-2xl z-40 p-4 pb-6"
                        >
                            <div className="flex items-center justify-between mb-4">
                                <div className="flex items-center gap-2">
                                    <div className="w-6 h-6 rounded-full bg-indigo-600 flex items-center justify-center text-white">
                                        <Bot size={14} />
                                    </div>
                                    <span className="text-sm font-bold text-gray-800">智能助手提问</span>
                                </div>
                                <button onClick={() => setIsExpanded(false)} className="p-1 text-gray-400 hover:text-gray-600">
                                    <X size={20} />
                                </button>
                            </div>

                            {/* Preset Questions */}
                            <div className="flex flex-wrap gap-2 mb-6">
                                {PRESET_QUESTIONS.map((q, idx) => (
                                    <button 
                                        key={idx}
                                        onClick={() => handlePresetClick(q)}
                                        className="px-3 py-1.5 bg-indigo-50 text-indigo-600 rounded-full text-xs font-medium hover:bg-indigo-100 transition-colors border border-indigo-100"
                                    >
                                        {q}
                                    </button>
                                ))}
                            </div>

                            <form onSubmit={handleSubmit} className="flex items-center gap-2 bg-gray-100 rounded-2xl px-4 py-2 focus-within:ring-2 focus-within:ring-indigo-500/50 transition-all">
                                <input 
                                    autoFocus
                                    ref={inputRef}
                                    type="text"
                                    value={inputText}
                                    onChange={(e) => setInputText(e.target.value)}
                                    placeholder="输入你的问题..."
                                    className="flex-1 bg-transparent py-2 text-sm text-gray-900 focus:outline-none"
                                />
                                <button 
                                    type="submit" 
                                    disabled={!inputText.trim()}
                                    className="p-2 text-white bg-orange-500 rounded-xl shadow-md shadow-orange-200 active:scale-95 transition-all disabled:opacity-50 disabled:shadow-none"
                                >
                                    <Send size={18} />
                                </button>
                            </form>
                        </motion.div>
                    </>
                )}
            </AnimatePresence>

            {/* Premium Meme Share Modal Overlay */}
            <AnimatePresence>
                {shareMeme && (
                    <div className="fixed inset-0 bg-black/60 backdrop-blur-xs flex items-center justify-center p-4 z-50">
                        {/* Modal backdrop clicks can close too */}
                        <div className="absolute inset-0" onClick={() => setShareMeme(null)} />
                        
                        <motion.div 
                            initial={{ opacity: 0, scale: 0.9, y: 20 }}
                            animate={{ opacity: 1, scale: 1, y: 0 }}
                            exit={{ opacity: 0, scale: 0.9, y: 20 }}
                            className="bg-white rounded-3xl w-full max-w-sm overflow-hidden shadow-2xl relative z-10 border border-gray-100 flex flex-col"
                        >
                            {/* Header */}
                            <div className="bg-gradient-to-r from-indigo-600 via-indigo-700 to-indigo-800 p-4 pb-3 flex justify-between items-center text-white">
                                <div className="flex items-center gap-1.5">
                                    <Share2 size={16} className="text-orange-400 animate-pulse" />
                                    <h3 className="text-sm font-black font-sans leading-none">分享毛孩子表情包</h3>
                                </div>
                                <button 
                                    onClick={() => setShareMeme(null)}
                                    className="w-6 h-6 rounded-full bg-white/20 hover:bg-white/30 flex items-center justify-center hover:scale-105 active:scale-95 transition-all text-white outline-none cursor-pointer"
                                >
                                    <X size={14} />
                                </button>
                            </div>

                            {/* Content */}
                            <div className="p-4 space-y-4">
                                {/* Media Preview Box */}
                                <div className="relative rounded-2xl overflow-hidden bg-gray-950 aspect-square flex items-center justify-center shadow-inner border border-gray-100">
                                    {shareMeme.url.endsWith('.gif') ? (
                                        <img 
                                            src={shareMeme.url} 
                                            alt="Shared Meme Preview" 
                                            className="max-h-full max-w-full object-contain"
                                            referrerPolicy="no-referrer"
                                        />
                                    ) : (
                                        <video 
                                            src={shareMeme.url} 
                                            autoPlay 
                                            loop 
                                            muted 
                                            playsInline 
                                            className="max-h-full max-w-full object-contain"
                                        />
                                    )}
                                    <div className="absolute bottom-2.5 left-2.5 bg-black/50 backdrop-blur-xs text-white text-[9px] font-bold px-2 py-0.5 rounded-full flex items-center gap-1">
                                        <Sparkles size={8} className="text-amber-400" />
                                        预览画面
                                    </div>
                                </div>

                                {/* Dynamic description banner without copy capability */}
                                <div className="bg-indigo-50/55 border border-indigo-100/40 rounded-xl p-3 space-y-1 text-left">
                                    <div className="flex items-center gap-1.5 text-xs text-indigo-800 font-extrabold leading-none">
                                        <Sparkles size={11} className="text-indigo-500" />
                                        表情包描述：
                                    </div>
                                    <p className="text-[11px] text-gray-600 leading-relaxed font-sans line-clamp-3 bg-white/70 p-2 rounded-lg border border-indigo-50/50 select-text outline-none">
                                        {shareMeme.text}
                                    </p>
                                </div>

                                {/* Actions Row */}
                                <div className="grid grid-cols-2 gap-2.5">
                                    <button
                                        onClick={handleDownloadMeme}
                                        className="bg-indigo-50 hover:bg-indigo-100 active:scale-95 text-indigo-700 py-3 rounded-2xl text-xs font-black flex items-center justify-center gap-1.5 transition-all border border-indigo-100 outline-none shadow-xs cursor-pointer"
                                    >
                                        <Download size={14} className="animate-bounce" />
                                        下载表情包
                                    </button>

                                    <button
                                        onClick={handleJumpToWeChat}
                                        className="bg-gradient-to-r from-emerald-500 via-emerald-600 to-green-600 hover:from-emerald-600 hover:to-green-700 active:scale-95 text-white py-3 rounded-2xl text-xs font-black flex items-center justify-center gap-1.5 transition-all outline-none shadow-md shadow-emerald-150 cursor-pointer"
                                    >
                                        <MessageSquare size={14} />
                                        跳转微信
                                    </button>
                                </div>
                                
                                <p className="text-[10px] text-gray-400 text-center select-none font-medium leading-normal pt-1">
                                    提示：点击跳转微信即可一键拉起微信进行分享。
                                </p>
                            </div>
                        </motion.div>
                    </div>
                )}
            </AnimatePresence>
        </div>
    );
};

export default HomeView;