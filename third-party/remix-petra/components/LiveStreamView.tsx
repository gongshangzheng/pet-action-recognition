import React, { useState, useRef, useEffect } from 'react';
import { 
    Mic, MicOff, Camera as CameraIcon, Video, VideoOff, 
    ChevronUp, ChevronDown, ChevronLeft, ChevronRight, Maximize2, 
    Volume2, VolumeX, Radio, Download
} from 'lucide-react';
import { motion, AnimatePresence } from 'motion/react';

interface LiveStreamViewProps {
    videoUrl: string;
}

export default function LiveStreamView({ videoUrl }: LiveStreamViewProps) {
    // Media & Player States
    const [isPlaying, setIsPlaying] = useState(true);
    const [isMuted, setIsMuted] = useState(true);
    const [isMicActive, setIsMicActive] = useState(false);
    const [isRecording, setIsRecording] = useState(false);
    const [recordingTime, setRecordingTime] = useState(0);
    
    // PTZ Offset States (for simulated camera movement)
    const [panAngle, setPanAngle] = useState(0); // -180 to 180
    const [tiltAngle, setTiltAngle] = useState(15); // -30 to 75
    const [offset, setOffset] = useState({ x: 0, y: 0 });

    // Interactive Action Feedbacks
    const [isShutterFlashing, setIsShutterFlashing] = useState(false);
    const [screenshots, setScreenshots] = useState<string[]>([]);
    const [recordedVideos, setRecordedVideos] = useState<{ id: string; url: string; duration: number; time: string }[]>([]);
    const [notification, setNotification] = useState<string | null>(null);

    const videoRef = useRef<HTMLVideoElement>(null);
    const recordIntervalRef = useRef<NodeJS.Timeout | null>(null);

    // Sync play/pause when isPlaying changes
    useEffect(() => {
        if (videoRef.current) {
            if (isPlaying) {
                videoRef.current.play().catch(err => console.log('Autoplay issue:', err));
            } else {
                videoRef.current.pause();
            }
        }
    }, [isPlaying]);

    // Handle recording timer
    useEffect(() => {
        if (isRecording) {
            recordIntervalRef.current = setInterval(() => {
                setRecordingTime(prev => prev + 1);
            }, 1000);
        } else {
            if (recordIntervalRef.current) {
                clearInterval(recordIntervalRef.current);
            }
            setRecordingTime(0);
        }
        return () => {
            if (recordIntervalRef.current) clearInterval(recordIntervalRef.current);
        };
    }, [isRecording]);

    const showToast = (message: string) => {
        setNotification(message);
        setTimeout(() => setNotification(null), 3000);
    };

    // PTZ Controls
    const handlePTZ = (direction: 'up' | 'down' | 'left' | 'right' | 'center') => {
        const step = 8;
        const angleStep = 5;
        if (direction === 'up') {
            setOffset(prev => ({ ...prev, y: Math.min(prev.y + step, 40) }));
            setTiltAngle(prev => Math.min(prev + angleStep, 75));
        } else if (direction === 'down') {
            setOffset(prev => ({ ...prev, y: Math.max(prev.y - step, -40) }));
            setTiltAngle(prev => Math.max(prev - angleStep, -30));
        } else if (direction === 'left') {
            setOffset(prev => ({ ...prev, x: Math.min(prev.x + step, 40) }));
            setPanAngle(prev => {
                let next = prev - angleStep;
                if (next < -180) next += 360;
                return next;
            });
        } else if (direction === 'right') {
            setOffset(prev => ({ ...prev, x: Math.max(prev.x - step, -40) }));
            setPanAngle(prev => {
                let next = prev + angleStep;
                if (next > 180) next -= 360;
                return next;
            });
        } else if (direction === 'center') {
            setOffset({ x: 0, y: 0 });
            setPanAngle(0);
            setTiltAngle(15);
            showToast('云台已复位');
        }
    };

    // Fullscreen behavior toggle 
    const handleFullscreen = () => {
        if (videoRef.current) {
            setIsMuted(false); // Unmute toggle as requested
            showToast('已开启声音并进入全屏');
            if (videoRef.current.requestFullscreen) {
                videoRef.current.requestFullscreen();
            } else if ((videoRef.current as any).webkitRequestFullscreen) {
                (videoRef.current as any).webkitRequestFullscreen();
            } else if ((videoRef.current as any).mozRequestFullScreen) {
                (videoRef.current as any).mozRequestFullScreen();
            } else if ((videoRef.current as any).msRequestFullscreen) {
                (videoRef.current as any).msRequestFullscreen();
            }
        }
    };

    // Screenshot capture on canvas 
    const handleScreenshot = () => {
        setIsShutterFlashing(true);
        setTimeout(() => setIsShutterFlashing(false), 200);

        // Synthesize Shutter Sound (Web Audio API)
        try {
            const tempCtx = new (window.AudioContext || (window as any).webkitAudioContext)();
            const osc = tempCtx.createOscillator();
            const gain = tempCtx.createGain();
            osc.connect(gain);
            gain.connect(tempCtx.destination);
            osc.type = 'triangle';
            osc.frequency.setValueAtTime(800, tempCtx.currentTime);
            osc.frequency.exponentialRampToValueAtTime(120, tempCtx.currentTime + 0.15);
            gain.gain.setValueAtTime(0.12, tempCtx.currentTime);
            gain.gain.linearRampToValueAtTime(0.01, tempCtx.currentTime + 0.15);
            osc.start();
            osc.stop(tempCtx.currentTime + 0.15);
        } catch (e) {
            console.log('Audio Context block:', e);
        }

        if (videoRef.current) {
            const canvas = document.createElement('canvas');
            canvas.width = videoRef.current.videoWidth || 640;
            canvas.height = videoRef.current.videoHeight || 360;
            const ctx = canvas.getContext('2d');
            if (ctx) {
                ctx.drawImage(videoRef.current, 0, 0, canvas.width, canvas.height);
                const dataUrl = canvas.toDataURL('image/png');
                setScreenshots(prev => [dataUrl, ...prev].slice(0, 8));
                showToast('截屏成功！已保存至本地相册');
            }
        } else {
            showToast('截屏失败：无流画面');
        }
    };

    // Recording Control
    const toggleRecording = () => {
        if (isRecording) {
            // Stop recording
            setIsRecording(false);
            const timeStr = new Date().toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' });
            setRecordedVideos(prev => [
                {
                    id: `rec-${Date.now()}`,
                    url: videoUrl,
                    duration: recordingTime,
                    time: timeStr
                },
                ...prev
            ]);
            showToast(`录像完成！时长: ${recordingTime}秒`);
        } else {
            // Start recording
            setIsRecording(true);
            showToast('开始录像...');
        }
    };

    const formatTime = (seconds: number) => {
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
    };

    return (
        <div className="flex flex-col h-full bg-gray-50 overflow-y-auto pb-4">
            {/* Header */}
            <div className="bg-white px-4 pt-5 pb-3 border-b border-gray-100 flex-shrink-0 z-10 shadow-sm">
                <div className="flex items-center justify-between">
                    <h1 className="text-lg font-bold text-gray-900 flex items-center gap-1.5">
                        <Radio className="text-red-500 animate-pulse" size={18} />
                        实时监控直播
                    </h1>
                    <div className="bg-red-50 text-red-600 text-[9px] font-bold px-2 py-0.5 rounded-full flex items-center gap-1 border border-red-100">
                        <div className="w-1.5 h-1.5 bg-red-600 rounded-full animate-ping"></div>
                        1080P • LIVE
                    </div>
                </div>
            </div>

            {/* Video Live Feed Container */}
            <div className="relative aspect-video bg-black overflow-hidden shadow-inner flex-shrink-0 w-full">
                {/* Simulated Shutter White Flash */}
                <AnimatePresence>
                    {isShutterFlashing && (
                        <motion.div 
                            initial={{ opacity: 0 }}
                            animate={{ opacity: 1 }}
                            exit={{ opacity: 0 }}
                            className="absolute inset-0 bg-white z-[30] pointer-events-none"
                        />
                    )}
                </AnimatePresence>

                {/* Live Video Feed */}
                <video 
                    ref={videoRef}
                    src={videoUrl}
                    loop
                    muted={isMuted}
                    playsInline
                    autoPlay
                    className="w-full h-full object-cover transition-transform duration-300"
                    style={{ 
                        transform: `scale(1.2) translate(${offset.x}px, ${offset.y}px)`
                    }}
                />

                {/* Corner Bounds (Camera Viewport Styling) */}
                <div className="absolute top-4 left-4 w-3 h-3 border-t-2 border-l-2 border-white/45 pointer-events-none z-10" />
                <div className="absolute top-4 right-4 w-3 h-3 border-t-2 border-r-2 border-white/45 pointer-events-none z-10" />
                <div className="absolute bottom-4 left-4 w-3 h-3 border-b-2 border-l-2 border-white/45 pointer-events-none z-10" />
                <div className="absolute bottom-4 right-4 w-3 h-3 border-b-2 border-r-2 border-white/45 pointer-events-none z-10" />

                {/* Streaming Info Overlays */}
                <div className="absolute top-3 left-3 right-3 flex justify-between items-start pointer-events-none z-10">
                    <span className="text-[9px] font-mono text-white drop-shadow bg-black/35 px-1.5 py-0.5 rounded-sm">
                        CAM01 - LIVING ROOM
                    </span>

                    {isRecording && (
                        <div className="bg-red-600/90 text-white text-[9px] font-bold font-mono px-1.5 py-0.5 rounded flex items-center gap-1 animate-pulse">
                            <span className="w-1 h-1 bg-white rounded-full"></span>
                            REC_ {formatTime(recordingTime)}
                        </div>
                    )}
                </div>

                {/* Simplified Left Overlay controls: Only Mute Button & Fullscreen Button */}
                <div className="absolute bottom-3 left-3 flex gap-2 z-20">
                    <button 
                        onClick={() => {
                            setIsMuted(!isMuted);
                            showToast(!isMuted ? '已静音' : '声音已开启');
                        }}
                        className="w-7 h-7 rounded-full bg-black/60 text-white flex items-center justify-center cursor-pointer hover:bg-black/80 transition-colors backdrop-blur-sm shadow"
                    >
                        {isMuted ? <VolumeX size={13} /> : <Volume2 size={13} />}
                    </button>
                    <button 
                        onClick={handleFullscreen}
                        className="w-7 h-7 rounded-full bg-black/60 text-white flex items-center justify-center cursor-pointer hover:bg-black/80 transition-colors backdrop-blur-sm shadow"
                    >
                        <Maximize2 size={13} />
                    </button>
                </div>
            </div>

            {/* Compact Quick Action Dock */}
            <div className="grid grid-cols-3 gap-2 px-4 py-3 bg-white border-b border-gray-100 shadow-sm">
                <button 
                    onClick={handleScreenshot}
                    className="flex flex-col items-center justify-center gap-1 py-1.5 bg-gray-50 rounded-xl active:bg-gray-100 transition-colors group cursor-pointer border border-gray-100"
                >
                    <div className="w-8 h-8 rounded-full bg-orange-50 text-orange-600 flex items-center justify-center group-hover:scale-105 transition-transform">
                        <CameraIcon size={15} />
                    </div>
                    <span className="text-[10px] font-bold text-gray-700">拍照截屏</span>
                </button>

                <button 
                    onClick={toggleRecording}
                    className={`flex flex-col items-center justify-center gap-1 py-1.5 rounded-xl transition-colors group cursor-pointer border ${isRecording ? 'bg-red-50 border-red-100' : 'bg-gray-50 border-gray-100 active:bg-gray-100'}`}
                >
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center group-hover:scale-105 transition-transform ${isRecording ? 'bg-red-600 text-white animate-pulse' : 'bg-red-50 text-red-600'}`}>
                        {isRecording ? <VideoOff size={15} /> : <Video size={15} />}
                    </div>
                    <span className={`text-[10px] font-bold ${isRecording ? 'text-red-700' : 'text-gray-700'}`}>
                        {isRecording ? '停止录像' : '录屏保存'}
                    </span>
                </button>

                <button 
                    onClick={() => {
                        setIsMicActive(!isMicActive);
                        showToast(isMicActive ? '对讲已关闭' : '开启双向对讲中...');
                    }}
                    className={`flex flex-col items-center justify-center gap-1 py-1.5 rounded-xl transition-colors group cursor-pointer border ${isMicActive ? 'bg-indigo-50 border-indigo-100' : 'bg-gray-50 border-gray-100 active:bg-gray-100'}`}
                >
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center group-hover:scale-105 transition-transform ${isMicActive ? 'bg-indigo-600 text-white' : 'bg-indigo-100 text-indigo-600'}`}>
                        {isMicActive ? <MicOff size={15} /> : <Mic size={15} />}
                    </div>
                    <span className={`text-[10px] font-bold ${isMicActive ? 'text-indigo-700' : 'text-gray-700'}`}>
                        {isMicActive ? '关闭话筒' : '向猫说话'}
                    </span>
                </button>
            </div>

            {/* Simulated PTZ Joystick Section */}
            <div className="px-4 mt-3 flex flex-col gap-3">
                <div className="bg-white rounded-2xl p-4 shadow-sm border border-gray-100 flex flex-col items-center">
                    <h3 className="text-xs font-bold text-gray-800 mb-3 w-full text-left flex items-center gap-2">
                        <span>智能物理云台</span>
                        <span className="text-[9px] font-normal text-gray-400">控制摄像机方向盘旋</span>
                    </h3>
                    
                    <div className="flex flex-col items-center justify-center py-1 w-full">
                        {/* Virtual Pan Tilt Joystick */}
                        <div className="relative w-32 h-32 rounded-full bg-gray-100 border border-gray-200 shadow-inner flex items-center justify-center">
                            {/* Inner Circle Track */}
                            <div className="absolute w-20 h-20 rounded-full border border-gray-200/50 flex items-center justify-center bg-gray-50">
                                <button 
                                    onClick={() => handlePTZ('center')}
                                    className="w-9 h-9 rounded-full bg-white shadow-md active:bg-gray-100 border border-gray-100 text-[10px] font-bold text-indigo-600 flex items-center justify-center text-center transition-all cursor-pointer z-10"
                                >
                                    复位
                                </button>
                            </div>

                            {/* Up */}
                            <button 
                                onClick={() => handlePTZ('up')}
                                className="absolute top-1 p-1.5 text-gray-500 hover:text-indigo-600 active:scale-110 transition-transform cursor-pointer"
                                aria-label="云台向上"
                            >
                                <ChevronUp size={20} />
                            </button>
                            {/* Down */}
                            <button 
                                onClick={() => handlePTZ('down')}
                                className="absolute bottom-1 p-1.5 text-gray-500 hover:text-indigo-600 active:scale-110 transition-transform cursor-pointer"
                                aria-label="云台向下"
                            >
                                <ChevronDown size={20} />
                            </button>
                            {/* Left */}
                            <button 
                                onClick={() => handlePTZ('left')}
                                className="absolute left-1 p-1.5 text-gray-500 hover:text-indigo-600 active:scale-110 transition-transform cursor-pointer"
                                aria-label="云台向左"
                            >
                                <ChevronLeft size={20} />
                            </button>
                            {/* Right */}
                            <button 
                                onClick={() => handlePTZ('right')}
                                className="absolute right-1 p-1.5 text-gray-500 hover:text-indigo-600 active:scale-110 transition-transform cursor-pointer"
                                aria-label="云台向右"
                            >
                                <ChevronRight size={20} />
                            </button>
                        </div>
                    </div>
                </div>

                {/* Local Captures Gallery */}
                {(screenshots.length > 0 || recordedVideos.length > 0) && (
                    <div className="bg-white rounded-2xl p-4 shadow-sm border border-gray-100">
                        <h3 className="text-xs font-bold text-gray-800 mb-2.5">本地录屏文件</h3>
                        
                        <div className="flex flex-col gap-2.5">
                            {/* Screenshots Carousel */}
                            {screenshots.length > 0 && (
                                <div className="flex flex-col gap-1">
                                    <span className="text-[9px] text-gray-400 font-bold">本地截图集</span>
                                    <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-hide">
                                        {screenshots.map((src, i) => (
                                            <div key={i} className="relative w-14 h-14 rounded-xl overflow-hidden bg-gray-100 border border-gray-200 flex-shrink-0 group">
                                                <img src={src} className="w-full h-full object-cover" alt="Capture thumbnail" />
                                                <a 
                                                    href={src} 
                                                    download={`capture-${i}.png`}
                                                    className="absolute inset-0 bg-black/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center text-white"
                                                >
                                                    <Download size={12} />
                                                </a>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* Recorded Videos List */}
                            {recordedVideos.length > 0 && (
                                <div className="flex flex-col gap-1">
                                    <div className="flex flex-col gap-1.5">
                                        {recordedVideos.map((vid) => (
                                            <div key={vid.id} className="flex items-center justify-between p-1.5 rounded-lg bg-gray-50 border border-gray-100">
                                                <div className="flex items-center gap-1.5">
                                                    <div className="w-7 h-7 rounded-md bg-orange-100 text-orange-600 flex items-center justify-center flex-shrink-0">
                                                        <Video size={12} />
                                                    </div>
                                                    <div className="flex flex-col">
                                                        <span className="text-xs font-bold text-gray-800">监控录制片段</span>
                                                        <span className="text-[9px] text-gray-400">{vid.time} • Duration: {vid.duration}s</span>
                                                    </div>
                                                </div>
                                                <button 
                                                    onClick={() => showToast('开始下载视频文件...')}
                                                    className="p-1 text-indigo-500 hover:text-indigo-600 hover:bg-indigo-50 rounded"
                                                >
                                                    <Download size={12} />
                                                </button>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                )}
            </div>

            {/* Notification alert / toast */}
            <AnimatePresence>
                {notification && (
                    <motion.div 
                        initial={{ opacity: 0, y: 30, scale: 0.95 }}
                        animate={{ opacity: 1, y: 0, scale: 1 }}
                        exit={{ opacity: 0, y: 20, scale: 0.95 }}
                        className="absolute bottom-20 left-4 right-4 bg-gray-900/90 backdrop-blur text-white text-xs font-medium py-2.5 px-4 rounded-xl shadow-lg z-[99] text-center pointer-events-none"
                    >
                        {notification}
                    </motion.div>
                )}
            </AnimatePresence>
        </div>
    );
}
