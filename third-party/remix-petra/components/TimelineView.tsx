import React, { useRef, useEffect, useState } from 'react';
import { Play, Video, Sparkles, Share2, ThumbsUp, ThumbsDown } from 'lucide-react';
import { PetData, PetInfo, LogEntry, CalendarDay } from '../types';
import { getEventStyle, getThumbIcon, getTagStyle, formatText } from '../constants';

// --- Sub-component for individual Log Card to handle local feedback state ---
interface LogCardProps {
    log: LogEntry;
    petData: PetData;
    handleJumpToVideo: (time: number, src?: string) => void;
    onShare: (log: LogEntry) => void;
}

const LogCard: React.FC<LogCardProps> = ({ log, petData, handleJumpToVideo, onShare }) => {
    const [feedback, setFeedback] = useState<'up' | 'down' | null>(null);
    const style = getEventStyle(log.act[0]);

    const handleFeedback = (type: 'up' | 'down') => {
        // Toggle logic: if clicking the same one, clear it. If new, set it.
        setFeedback(prev => prev === type ? null : type);
    };

    const renderCatBadges = () => {
        if (log.cat === '双猫') {
            return (
                <div className="flex gap-1.5">
                    {(Object.entries(petData) as [string, PetInfo][]).map(([name, info]) => (
                        <span key={name} className={`text-[10px] px-2 py-0.5 rounded-full font-bold flex items-center gap-1 ${info.avatarColor}`}>
                            {info.avatarUrl && (
                                <img src={info.avatarUrl} alt="" className="w-3.5 h-3.5 rounded-full object-cover border border-white/45" referrerPolicy="no-referrer" />
                            )}
                            {name}
                        </span>
                    ))}
                </div>
            );
        }
        
        // Single cat logic: if we have data, use the style
        if (petData[log.cat]) {
             return (
                 <span className={`text-[10px] px-2 py-0.5 rounded-full font-bold flex items-center gap-1.5 ${petData[log.cat].avatarColor}`}>
                    {petData[log.cat].avatarUrl && (
                        <img src={petData[log.cat].avatarUrl} alt="" className="w-4.5 h-4.5 rounded-full object-cover border border-white/45" referrerPolicy="no-referrer" />
                    )}
                    {log.cat}
                 </span>
             );
        }
        
        // Fallback for unknown
        return <span className="font-bold text-sm text-gray-800">{log.cat}</span>;
    };

    return (
        <div className="relative pl-8 group animate-fade-in">
            <div className={`absolute left-0 top-3 w-8 h-8 rounded-full border-4 border-white shadow-sm flex items-center justify-center z-10 ${style.iconBg}`}>
                {style.icon}
            </div>
            
            <div className="bg-white rounded-xl shadow-sm border border-gray-100 overflow-hidden">
                {/* Video Thumbnail Area */}
                <div 
                    onClick={() => handleJumpToVideo(log.videoTime, log.videoSrc)} 
                    className={`w-full h-32 relative cursor-pointer group/vid ${log.thumbColor}`}
                >
                    <div className="absolute inset-0 bg-black/5 group-hover/vid:bg-black/10 transition-colors"></div>
                    {/* Thumbnail Icon */}
                    <div className="absolute inset-0 flex items-center justify-center opacity-30 group-hover/vid:opacity-40 transition-opacity">
                        {getThumbIcon(log.act[0])}
                    </div>
                    
                    <div className="absolute inset-0 flex items-center justify-center">
                        <div className="w-10 h-10 bg-white/30 backdrop-blur-md rounded-full flex items-center justify-center shadow-lg transition-transform group-hover/vid:scale-110">
                            <Play size={18} className="text-white fill-current ml-0.5" />
                        </div>
                    </div>
                    <div className="absolute bottom-2 right-2 flex items-center gap-1 text-[10px] text-white font-medium bg-black/40 px-2 py-1 rounded backdrop-blur-sm">
                        <Video size={10} /> 点击回放
                    </div>
                </div>

                <div className="p-3">
                    <div className="flex justify-between items-start mb-2">
                        <div className="flex flex-col flex-1">
                            <div className="flex items-center gap-2 mb-1 h-6">
                                {renderCatBadges()}
                                <span className="text-xs text-gray-400 ml-1">{log.time}</span>
                            </div>
                            <div className="flex gap-1 flex-wrap">
                                {log.act.map((tag, i) => (
                                    <span key={i} className={`text-[10px] px-1.5 py-0.5 rounded border ${getTagStyle(tag)}`}>{tag}</span>
                                ))}
                            </div>
                        </div>
                        
                        {/* Share Button */}
                        <button 
                            onClick={(e) => { e.stopPropagation(); onShare(log); }}
                            className="p-1.5 rounded-full text-gray-300 hover:text-orange-500 hover:bg-orange-50 transition-colors"
                        >
                            <Share2 size={16} />
                        </button>
                    </div>
                    
                    {log.details ? (
                        <div className="space-y-3 mb-4">
                            {Object.entries(log.details).map(([catName, catDesc]) => (
                                <div key={catName} className="relative pl-3">
                                    <div className={`absolute left-0 top-1.5 bottom-1.5 w-0.5 rounded-full ${petData[catName]?.avatarColor.split(' ')[0] || 'bg-gray-200'}`} />
                                    <span className="text-[10px] font-bold text-gray-400 block mb-0.5">{catName}</span>
                                    <p className="text-xs text-gray-600 leading-relaxed">{catDesc}</p>
                                </div>
                            ))}
                        </div>
                    ) : (
                        <p className="text-xs text-gray-700 leading-relaxed mb-3">{log.desc}</p>
                    )}
                    
                    {/* AI Status & Feedback Row */}
                    <div className="flex items-end justify-between gap-3">
                        <div className="bg-gray-50 rounded-lg p-2 flex items-start gap-2 flex-1 min-w-0">
                            <div className="mt-0.5 flex-shrink-0"><Sparkles size={12} className="text-indigo-400"/></div>
                            <p className="text-[10px] text-gray-500 leading-snug truncate">
                                {log.stat}
                            </p>
                        </div>

                        {/* Feedback Controls */}
                        <div className="flex flex-col items-end gap-1 flex-shrink-0">
                            <span className={`text-[9px] font-medium transition-all ${feedback ? 'text-orange-400 scale-100' : 'text-gray-300 scale-90 opacity-0 group-hover:opacity-100'}`}>
                                {feedback ? '感谢反馈' : 'AI 准吗?'}
                            </span>
                            <div className="flex gap-2">
                                <button
                                    onClick={(e) => { e.stopPropagation(); handleFeedback('up'); }}
                                    className={`transition-all p-1 rounded-md ${feedback === 'up' ? 'text-green-500 bg-green-50 scale-110' : 'text-gray-300 hover:text-green-500 hover:bg-gray-50'}`}
                                >
                                    <ThumbsUp size={14} className={feedback === 'up' ? 'fill-current' : ''} />
                                </button>
                                <button
                                    onClick={(e) => { e.stopPropagation(); handleFeedback('down'); }}
                                    className={`transition-all p-1 rounded-md ${feedback === 'down' ? 'text-orange-500 bg-orange-50 scale-110' : 'text-gray-300 hover:text-orange-500 hover:bg-gray-50'}`}
                                >
                                    <ThumbsDown size={14} className={feedback === 'down' ? 'fill-current' : ''} />
                                </button>
                            </div>
                        </div>
                    </div>

                </div>
            </div>
        </div>
    );
};

// --- Custom Hook for Mouse Drag to Scroll ---
const useDragScroll = () => {
    const ref = useRef<HTMLDivElement>(null);
    const [isDragging, setIsDragging] = useState(false);
    const [startX, setStartX] = useState(0);
    const [scrollLeft, setScrollLeft] = useState(0);

    const onMouseDown = (e: React.MouseEvent) => {
        if (!ref.current) return;
        setIsDragging(true);
        setStartX(e.pageX - ref.current.offsetLeft);
        setScrollLeft(ref.current.scrollLeft);
    };

    const onMouseLeave = () => {
        setIsDragging(false);
    };

    const onMouseUp = () => {
        setIsDragging(false);
    };

    const onMouseMove = (e: React.MouseEvent) => {
        if (!isDragging || !ref.current) return;
        e.preventDefault();
        const x = e.pageX - ref.current.offsetLeft;
        const walk = (x - startX) * 1.5; // Scroll speed multiplier
        ref.current.scrollLeft = scrollLeft - walk;
    };

    return {
        ref,
        events: {
            onMouseDown,
            onMouseLeave,
            onMouseUp,
            onMouseMove
        },
        isDragging
    };
};

// --- Main Timeline Component ---
interface TimelineViewProps {
    selectedDate: string;
    setSelectedDate: (date: string) => void;
    currentLogs: LogEntry[];
    selectedCatFilter: string;
    setSelectedCatFilter: (filter: string) => void;
    selectedEventFilter: string;
    setSelectedEventFilter: (filter: string) => void;
    petData: PetData;
    calendarDays: CalendarDay[];
    handleJumpToVideo: (time: number, src?: string) => void;
    onShare: (log: LogEntry) => void;
}

const TimelineView: React.FC<TimelineViewProps> = ({
    selectedDate, setSelectedDate, currentLogs, selectedCatFilter, 
    setSelectedCatFilter, selectedEventFilter, setSelectedEventFilter,
    petData, calendarDays, handleJumpToVideo, onShare
}) => {
    const dateScroll = useDragScroll();
    const petScroll = useDragScroll();
    const eventScroll = useDragScroll();
    const eventTypes = ['全部', '饮食饮水', '活动', '休息', '多猫互动', '呕吐'];
    const catNames = ['全部', ...Object.keys(petData)];

    // Auto-scroll calendar to end on mount
    useEffect(() => {
        setTimeout(() => {
            if (dateScroll.ref.current) {
                dateScroll.ref.current.scrollLeft = dateScroll.ref.current.scrollWidth;
            }
        }, 100);
    }, []);

    return (
        <div className="flex-1 bg-gray-50 overflow-y-auto flex flex-col scrollbar-hide">
            {/* Calendar Header */}
            <div className="bg-white pt-4 pb-3 border-b border-gray-100 sticky top-0 z-20 shadow-sm">
                <div className="px-4 mb-3">
                    <h2 className="text-xl font-bold text-gray-900">派爪Petra 日志</h2>
                </div>

                {/* Date Selector */}
                <div 
                    className={`flex gap-2 overflow-x-auto pb-3 px-4 scrollbar-hide cursor-grab active:cursor-grabbing select-none`}
                    ref={dateScroll.ref}
                    {...dateScroll.events}
                >
                    {calendarDays.map(d => (
                        <button 
                            key={d.fullDate} 
                            onClick={() => !dateScroll.isDragging && setSelectedDate(d.day)} 
                            className={`flex-shrink-0 w-10 h-12 rounded-xl flex flex-col items-center justify-center border transition-all ${selectedDate === d.day ? 'bg-orange-500 border-orange-500 text-white shadow-md' : 'bg-white border-gray-100 text-gray-400'}`}
                        >
                            <span className="text-[9px] opacity-80">{d.week}</span>
                            <span className="text-xs font-bold">{d.day}</span>
                        </button>
                    ))}
                </div>

                {/* Filters Section */}
                <div className="space-y-4 px-4 pb-2">
                    {/* Pet Filter - Fixed label, scrolling list */}
                    <div className="flex items-center gap-3">
                        <span className="text-[10px] font-bold text-gray-400 uppercase flex-shrink-0 w-8">成员</span>
                        <div 
                            className="flex gap-2 overflow-x-auto scrollbar-hide py-1 flex-nowrap -mr-4 pr-4 cursor-grab active:cursor-grabbing select-none"
                            ref={petScroll.ref}
                            {...petScroll.events}
                        >
                            {catNames.map(name => {
                                const filterValue = name === '全部' ? 'all' : name;
                                const isActive = selectedCatFilter === filterValue;
                                return (
                                    <button 
                                        key={name} 
                                        onClick={() => !petScroll.isDragging && setSelectedCatFilter(filterValue)} 
                                        className={`flex-shrink-0 px-3.5 py-1 text-xs rounded-full border transition-all flex items-center gap-1.5 ${isActive ? 'bg-orange-500 border-orange-500 text-white shadow-md font-medium' : 'bg-white border-gray-200 text-gray-500 hover:border-orange-200'}`}
                                    >
                                        {name !== '全部' && petData[name] && (
                                            petData[name].avatarUrl ? (
                                                <img src={petData[name].avatarUrl} alt="" className="w-4.5 h-4.5 rounded-full object-cover border border-gray-100" referrerPolicy="no-referrer" />
                                            ) : (
                                                <div className={`w-2 h-2 rounded-full ${petData[name].avatarColor.split(' ')[0]}`} />
                                            )
                                        )}
                                        {name}
                                    </button>
                                );
                            })}
                        </div>
                    </div>

                    {/* Event Type Filter - Fixed label, scrolling list */}
                    <div className="flex items-center gap-3">
                        <span className="text-[10px] font-bold text-gray-400 uppercase flex-shrink-0 w-8">类型</span>
                        <div 
                            className="flex gap-2 overflow-x-auto scrollbar-hide py-1 flex-nowrap -mr-4 pr-4 cursor-grab active:cursor-grabbing select-none"
                            ref={eventScroll.ref}
                            {...eventScroll.events}
                        >
                            {eventTypes.map(type => {
                                const filterValue = type === '全部' ? 'all' : type;
                                const isActive = selectedEventFilter === filterValue;
                                return (
                                    <button 
                                        key={type} 
                                        onClick={() => !eventScroll.isDragging && setSelectedEventFilter(filterValue)} 
                                        className={`flex-shrink-0 px-4 py-1.5 text-xs rounded-full border transition-all ${isActive ? 'bg-indigo-500 border-indigo-500 text-white shadow-md font-medium' : 'bg-white border-gray-200 text-gray-500 hover:border-indigo-200'}`}
                                    >
                                        {type}
                                    </button>
                                );
                            })}
                        </div>
                    </div>
                </div>
            </div>

            <div className="p-4 space-y-6">
                {/* Daily Report Card */}
                <div className="space-y-3">
                    {(selectedCatFilter === 'all' || selectedCatFilter === '栗子') && petData['栗子'] && (
                        <div className="bg-white p-4 rounded-xl border border-orange-100 shadow-sm relative overflow-hidden animate-fade-in">
                            <div className="flex items-center gap-2 mb-2">
                                <div className="w-5 h-5 rounded-full bg-gray-200 flex items-center justify-center text-[10px] font-bold text-gray-600">栗</div>
                                <span className="font-bold text-sm text-gray-800">栗子</span>
                            </div>
                            <div className="text-xs text-gray-600 leading-relaxed whitespace-pre-line">{formatText(petData['栗子'].report)}</div>
                        </div>
                    )}
                    {(selectedCatFilter === 'all' || selectedCatFilter === '奶油') && petData['奶油'] && (
                        <div className="bg-white p-4 rounded-xl border border-yellow-100 shadow-sm relative overflow-hidden animate-fade-in">
                            <div className="flex items-center gap-2 mb-2">
                                <div className="w-5 h-5 rounded-full bg-yellow-100 flex items-center justify-center text-[10px] font-bold text-yellow-700">奶</div>
                                <span className="font-bold text-sm text-gray-800">奶油</span>
                            </div>
                            <div className="text-xs text-gray-600 leading-relaxed whitespace-pre-line">{formatText(petData['奶油'].report)}</div>
                        </div>
                    )}
                </div>

                {/* Timeline List */}
                <div>
                    <h3 className="text-xs font-bold text-gray-400 mb-4 uppercase tracking-wider flex items-center justify-between">
                        <span>事件时间轴</span>
                        <span className="font-normal">{currentLogs.length} 条记录</span>
                    </h3>
                    <div className="space-y-6 relative before:absolute before:left-[15px] before:top-2 before:bottom-0 before:w-0.5 before:bg-gray-200">
                        {currentLogs
                            .filter(log => {
                                const catMatch = selectedCatFilter === 'all' || log.cat.includes(selectedCatFilter) || (log.cat === '双猫' && selectedCatFilter !== 'all');
                                const eventMatch = selectedEventFilter === 'all' || log.act.some(a => a.includes(selectedEventFilter));
                                return catMatch && eventMatch;
                            })
                            .map(log => (
                                <LogCard 
                                    key={log.id}
                                    log={log}
                                    petData={petData}
                                    handleJumpToVideo={handleJumpToVideo}
                                    onShare={onShare}
                                />
                            ))}
                    </div>
                </div>
            </div>
        </div>
    );
};

export default TimelineView;