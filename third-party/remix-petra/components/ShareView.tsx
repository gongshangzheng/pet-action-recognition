import React, { useEffect, useState } from 'react';
import { ArrowLeft, Download, Check, Copy, Share2, MessageCircle } from 'lucide-react';
import { LogEntry } from '../types';
import { getThumbIcon } from '../constants';

interface ShareViewProps {
    log: LogEntry;
    onClose: () => void;
}

const ShareView: React.FC<ShareViewProps> = ({ log, onClose }) => {
    const [copied, setCopied] = useState(false);
    const [downloading, setDownloading] = useState(false);
    const [progress, setProgress] = useState(0);

    const [successMessage, setSuccessMessage] = useState<string | null>(null);

    useEffect(() => {
        // Prepare text content
        const textToShare = `【派爪Petra 萌宠日报】\n📅 时间：${log.time}\n🐱 主角：${log.cat}\n✨ 事件：${log.act.join(' ')}\n📝 详情：${log.desc}\n------------------\n来自 派爪Petra 智能守护`;
        
        // Auto copy to clipboard on mount
        if (navigator && navigator.clipboard) {
            navigator.clipboard.writeText(textToShare).then(() => {
                setCopied(true);
                setTimeout(() => setCopied(false), 3000);
            }).catch(err => console.error("Clipboard write failed", err));
        }
    }, [log]);

    const handleDownloadAndShare = () => {
        if (downloading) return;
        setDownloading(true);
        setProgress(0);

        // Simulate download progress
        const interval = setInterval(() => {
            setProgress(prev => {
                if (prev >= 100) {
                    clearInterval(interval);
                    // Finished
                    setTimeout(() => {
                        setDownloading(false);
                        setSuccessMessage("✅ 视频已保存到相册！\n文案已复制到剪贴板，您可以直接前往社交平台分享。");
                        setTimeout(() => setSuccessMessage(null), 5000);
                    }, 500);
                    return 100;
                }
                return prev + 10;
            });
        }, 150);
    };

    return (
        <div className="fixed inset-0 z-[100] bg-gray-50 flex flex-col animate-slide-up pb-safe">
            {/* Header */}
            <div className="bg-white px-4 py-3 border-b border-gray-100 flex items-center justify-between sticky top-0 z-10">
                <button onClick={onClose} className="p-2 -ml-2 text-gray-600 hover:bg-gray-50 rounded-full transition-colors">
                    <ArrowLeft size={24} />
                </button>
                <h2 className="font-bold text-lg text-gray-900">分享动态</h2>
                <div className="w-10"></div> {/* Spacer */}
            </div>

            <div className="flex-1 overflow-y-auto p-6 flex flex-col items-center">
                
                {/* Auto Copy Notification */}
                <div className={`fixed top-20 bg-black/75 text-white px-4 py-2 rounded-full text-sm font-medium transition-all duration-300 transform flex items-center gap-2 z-50 ${copied ? 'translate-y-0 opacity-100' : '-translate-y-4 opacity-0 pointer-events-none'}`}>
                    <Check size={16} className="text-green-400" /> 文案已复制到剪贴板
                </div>

                {/* Preview Card */}
                <div className="w-full max-w-sm bg-white rounded-2xl shadow-xl overflow-hidden border border-gray-100 mb-6">
                    {/* Video Preview */}
                    <div className={`h-48 w-full relative ${log.thumbColor} flex items-center justify-center`}>
                        <div className="opacity-20 transform scale-150">
                            {getThumbIcon(log.act[0])}
                        </div>
                        <div className="absolute inset-0 bg-gradient-to-t from-black/50 to-transparent"></div>
                        <div className="absolute bottom-3 left-3 text-white">
                             <div className="text-xs font-medium opacity-80">{log.time}</div>
                             <div className="font-bold text-lg">{log.cat} · {log.act[0]}</div>
                        </div>
                    </div>
                    
                    {/* Text Content */}
                    <div className="p-5 bg-white relative">
                         <div className="absolute -top-6 right-4 w-12 h-12 bg-orange-500 rounded-full flex items-center justify-center shadow-lg border-4 border-white">
                            <Share2 size={20} className="text-white" />
                         </div>
                         <h3 className="font-bold text-gray-800 mb-2 text-lg">萌宠时刻</h3>
                         <div className="bg-gray-50 rounded-xl p-3 text-sm text-gray-600 leading-relaxed border border-gray-100 mb-4">
                            {log.desc}
                         </div>
                         <div className="flex items-center gap-2 text-xs text-gray-400">
                             <div className="w-1 h-1 rounded-full bg-gray-300"></div>
                             <span>派爪Petra 智能生成</span>
                         </div>
                    </div>
                </div>

                <div className="w-full max-w-sm">
                    <h3 className="text-sm font-bold text-gray-500 mb-3 ml-1 uppercase">分享选项</h3>
                    <div className="grid grid-cols-2 gap-3">
                         <button className="flex flex-col items-center justify-center gap-2 bg-white p-4 rounded-xl border border-gray-200 text-gray-600 hover:border-green-200 hover:bg-green-50 hover:text-green-600 transition-all" onClick={() => {
                             navigator.clipboard.writeText(log.desc);
                             setCopied(true);
                             setTimeout(() => setCopied(false), 2000);
                         }}>
                             <Copy size={24} />
                             <span className="text-xs font-medium">复制文案</span>
                         </button>
                         <button className="flex flex-col items-center justify-center gap-2 bg-white p-4 rounded-xl border border-gray-200 text-gray-600 hover:border-blue-200 hover:bg-blue-50 hover:text-blue-600 transition-all">
                             <MessageCircle size={24} />
                             <span className="text-xs font-medium">去微信转发</span>
                         </button>
                    </div>
                </div>
            </div>

            {/* Bottom Action Bar */}
            <div className="p-4 bg-white border-t border-gray-100 pb-safe">
                <button 
                    onClick={handleDownloadAndShare}
                    disabled={downloading}
                    className="w-full bg-green-600 text-white font-bold py-3.5 rounded-full shadow-lg shadow-green-600/20 active:scale-[0.98] transition-all flex items-center justify-center gap-2 relative overflow-hidden"
                >
                    {downloading ? (
                        <>
                           <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div>
                           <span>正在处理 {progress}%</span>
                           <div className="absolute bottom-0 left-0 h-1 bg-white/20 transition-all duration-150 ease-linear" style={{ width: `${progress}%` }}></div>
                        </>
                    ) : (
                        <>
                            <Download size={20} />
                            <span>下载视频并去微信转发</span>
                        </>
                    )}
                </button>
                <p className="text-center text-[10px] text-gray-400 mt-2">
                    视频将自动保存到相册，文案已自动复制
                </p>
            </div>
            {/* Success Message Notification Card */}
            {successMessage && (
                <div className="fixed inset-0 bg-black/40 backdrop-blur-xs flex items-center justify-center p-6 z-[110] animate-fade-in">
                    <div className="bg-white rounded-2xl p-6 max-w-xs shadow-2xl text-center space-y-4 animate-zoom-in">
                        <div className="w-12 h-12 bg-green-50 text-green-500 rounded-full flex items-center justify-center mx-auto text-xl">
                            ✓
                        </div>
                        <p className="text-sm font-bold text-gray-900 leading-snug">操作成功</p>
                        <p className="text-xs text-gray-500 whitespace-pre-wrap">{successMessage}</p>
                        <button 
                            onClick={() => setSuccessMessage(null)}
                            className="w-full bg-green-600 text-white text-xs font-bold py-2 rounded-xl active:scale-95 transition-all shadow-sm"
                        >
                            知道了
                        </button>
                    </div>
                </div>
            )}
        </div>
    );
};

export default ShareView;