import React, { useRef, useEffect } from 'react';
import { X, Sparkles } from 'lucide-react';

interface VideoOverlayProps {
    show: boolean;
    src: string | null;
    startTime: number;
    onClose: () => void;
}

const VideoOverlay: React.FC<VideoOverlayProps> = ({ show, src, startTime, onClose }) => {
    const modalVideoRef = useRef<HTMLVideoElement>(null);

    useEffect(() => {
        if (show && modalVideoRef.current) {
            modalVideoRef.current.currentTime = startTime;
            modalVideoRef.current.play().catch(e => console.log("Video playback error", e));
        }
    }, [show, startTime]);

    if (!show) return null;

    return (
        <div className="fixed inset-0 z-[70] bg-black/95 flex flex-col justify-center items-center animate-fade-in">
            <button 
                onClick={onClose} 
                className="absolute top-4 right-4 text-white p-2 bg-white/10 rounded-full hover:bg-white/20 transition-colors z-50"
            >
                <X size={24} />
            </button>
            <div className="w-full aspect-video bg-black relative">
                <video 
                    ref={modalVideoRef} 
                    src={src || ""} 
                    className="w-full h-full object-contain" 
                    controls 
                    autoPlay 
                    playsInline 
                />
            </div>
            <div className="mt-6 text-white/90 text-sm bg-gray-800/80 px-6 py-2 rounded-full border border-white/10 flex items-center gap-2">
                <Sparkles size={14} className="text-yellow-400"/> 智能回放
            </div>
        </div>
    );
};

export default VideoOverlay;