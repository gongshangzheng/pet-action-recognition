import React from 'react';
import { 
  Activity, AlertTriangle, Clock, Film, Moon, Utensils, Zap 
} from 'lucide-react';
import { CalendarDay, LogEntry, PetData, VideoScriptEvent } from './types';

// ==========================================
// 🔧 Configuration & Data
// ==========================================

export const CONFIG = {
    // Using a sample video for demonstration purposes
    defaultVideo: "https://media.w3.org/2010/05/sintel/trailer_hd.mp4", 
    secondaryVideo: "https://media.w3.org/2010/05/sintel/trailer_hd.mp4",
    currentDate: "11/24", 
};

export const INITIAL_PET_DATA: PetData = {
    '栗子': { 
        type: '狸花猫', weight: '4.2kg',
        features: '短毛，全身覆盖黑灰相间的经典斑纹。',
        avatarColor: 'bg-gray-200 text-gray-700',
        report: `**【栗子日报】**\n今日标签：**精力过剩**。\n06:30 进行了高强度的**活动**（跑酷）。`
    },
    '奶油': { 
        type: '金渐层', weight: '5.5kg',
        features: '长毛，背部呈现金渐层色。',
        avatarColor: 'bg-yellow-100 text-yellow-700',
        report: `**【奶油日报】**\n今日标签：**岁月静好**。\n大部分时间处于**休息**状态。`
    },
    '小黑': { type: '玄猫', weight: '4.0kg', features: '全身纯黑', avatarColor: 'bg-zinc-800 text-white', report: '今日表现正常。' },
    '大白': { type: '临清狮子猫', weight: '5.0kg', features: '全身雪白', avatarColor: 'bg-slate-100 text-slate-800', report: '今日表现正常。' },
    '花花': { type: '三花猫', weight: '3.8kg', features: '三色斑块', avatarColor: 'bg-orange-100 text-orange-800', report: '今日表现正常。' },
    '橘子': { type: '橘猫', weight: '6.0kg', features: '橘黄色条纹', avatarColor: 'bg-orange-200 text-orange-900', report: '今日表现正常。' },
    '咪咪': { type: '美短', weight: '4.5kg', features: '银虎斑', avatarColor: 'bg-blue-100 text-blue-800', report: '今日表现正常。' },
    '皮皮': { type: '英短蓝猫', weight: '5.2kg', features: '灰色短毛', avatarColor: 'bg-indigo-100 text-indigo-800', report: '今日表现正常。' },
    '闹闹': { type: '暹罗猫', weight: '3.5kg', features: '重点色', avatarColor: 'bg-stone-200 text-stone-800', report: '今日表现正常。' },
    '球球': { type: '布偶猫', weight: '5.8kg', features: '蓝眼睛，重点色', avatarColor: 'bg-sky-100 text-sky-800', report: '今日表现正常。' }
};

export const VIDEO_SCRIPT: VideoScriptEvent[] = [
  { startTime: 0, endTime: 12, hasMotion: false },
  { 
    startTime: 12, endTime: 16, hasMotion: true, 
    triggerAlert: { 
      timeTrigger: 14, cat: '双猫', 
      act: ["多猫互动"], 
      title: '检测到多猫互动', 
      desc: '检测到深夜跑酷追逐，双方在客厅快速移动。', 
      details: {
        '栗子': '栗子在客厅中心发起冲刺，试图追上前方奔跑的奶油。',
        '奶油': '奶油在沙发边缘灵活跳跃，利用障碍物躲避栗子的追逐。'
      },
      stat: '高能玩耍',
      videoTime: 14 
    }
  },
  { startTime: 16, endTime: 100, hasMotion: false }
];

// ==========================================
// 🎨 Styling Helpers
// ==========================================

export const getEventStyle = (action: string) => {
    if (action === '多猫互动' || action === '异常') {
        return {
            bg: 'bg-orange-50', border: 'border-orange-100', 
            text: 'text-orange-700', iconColor: 'text-orange-500',
            iconBg: 'bg-orange-500', icon: <AlertTriangle size={14} className="text-white"/>
        };
    }
    return {
        bg: 'bg-white', border: 'border-blue-50', 
        text: 'text-gray-600', iconColor: 'text-blue-400',
        iconBg: 'bg-blue-50', icon: <Clock size={14} className="text-blue-400"/>
    };
};

export const getThumbIcon = (action: string) => {
     if (!action) return <Film size={24}/>;
     if (action.includes('饮食') || action.includes('饮水')) return <Utensils size={24}/>;
     if (action.includes('休息')) return <Moon size={24}/>;
     if (action.includes('活动') || action.includes('跑酷')) return <Zap size={24}/>;
     if (action.includes('互动') || action.includes('多猫')) return <Activity size={24}/>;
     if (action.includes('异常')) return <AlertTriangle size={24}/>;
     return <Film size={24}/>;
}

export const getTagStyle = (tag: string) => {
    if (tag === '多猫互动' || tag.includes('异常')) {
        return 'bg-orange-100 text-orange-700 border-orange-200';
    }
    if (tag === '饮食饮水') return 'bg-blue-50 text-blue-600 border-blue-100';
    if (tag === '休息') return 'bg-purple-50 text-purple-600 border-purple-100';
    return 'bg-gray-100 text-gray-600 border-gray-200';
};

// ==========================================
// 📝 Logic Helpers
// ==========================================

export const generateCalendarData = (): CalendarDay[] => {
    const days: CalendarDay[] = [];
    const today = new Date(); 
    // Hardcoding specific date relative to demo for consistency with "24th"
    const demoDate = new Date(2025, 10, 24); 
    const weekMap = ['日', '一', '二', '三', '四', '五', '六'];
    
    for (let i = 29; i >= 0; i--) {
        const d = new Date(demoDate);
        d.setDate(d.getDate() - i);
        days.push({
            fullDate: `${d.getMonth() + 1}/${d.getDate()}`,
            day: String(d.getDate()),
            week: weekMap[d.getDay()],
            isToday: i === 0
        });
    }
    return days;
};

export const getHistoryLogs = (date: string): LogEntry[] => {
    if (date.includes('24')) { 
        return [
            { 
                id: '24-1', 
                time: '14:30', 
                cat: '奶油', 
                act: ["活动", "多猫互动"], 
                desc: "奶油在客厅地面悠闲地巡视了一圈，随后轻快地跳上猫爬架，并抬头看向高处的同伴。", 
                stat: "状态非常活泼，探索欲满满，是个充满好奇心的小可爱。",
                videoTime: 10, 
                thumbColor: 'bg-yellow-100 text-yellow-600'
            },
            { 
                id: '24-2', 
                time: '14:28', 
                cat: '栗子', 
                act: ["休息", "多猫互动"], 
                desc: "栗子一直稳稳地趴在猫爬架的高层窝里，俯瞰着下方活动的同伴，神情淡定自若。", 
                stat: "情绪稳定且放松，像是在享受它的午后静谧时光，状态很好。",
                videoTime: 10,
                thumbColor: 'bg-gray-200 text-gray-600'
            },
            { 
                id: '24-3', 
                time: '09:40', 
                cat: '奶油', 
                act: ["饮食饮水"], 
                desc: "奶油走到饮水机前，持续饮水约 45 秒。饮水量正常。", 
                stat: "水分补充充足，肾脏健康守护中。",
                videoTime: 10, 
                thumbColor: 'bg-blue-50 text-blue-500'
            },
            { 
                id: '24-4', 
                time: '08:15', 
                cat: '双猫', 
                act: ["饮食饮水"], 
                desc: "自动喂食器出粮，栗子和奶油同时听到声音跑来进食。", 
                details: {
                    '栗子': '栗子在喂食器左侧快速进食，食欲旺盛。',
                    '奶油': '奶油在喂食器右侧细嚼慢咽，进食状态平稳。'
                },
                stat: "食欲良好，进食积极。",
                videoTime: 10,
                thumbColor: 'bg-green-100 text-green-600'
            }, 
            { 
                id: '24-5', 
                time: '06:30', 
                cat: '栗子', 
                act: ["活动"], 
                desc: "检测到高频移动（跑酷），持续时间约 5 分钟。", 
                stat: "高能运动", 
                videoTime: 10, 
                thumbColor: 'bg-red-50 text-red-500'
            }
        ];
    } 
    if (date.includes('23')) { 
        return [
            { id: '23-1', time: '23:15', cat: '奶油', act: ["异常"], desc: "检测到腹部抽搐，吐出毛球", stat: "⚠️ 异常检测", videoTime: 0, thumbColor: 'bg-red-100 text-red-600', videoSrc: CONFIG.secondaryVideo },
            { id: '23-2', time: '14:20', cat: '双猫', act: ["休息"], desc: "午后小憩，环境安静", stat: "放松", videoTime: 10, thumbColor: 'bg-blue-50 text-blue-500' },
            { id: '23-3', time: '08:00', cat: '栗子', act: ["饮食饮水"], desc: "正常早餐", stat: "正常", videoTime: 10, thumbColor: 'bg-green-50 text-green-600' }
        ];
    }
    return [
        { id: 'x-1', time: '18:00', cat: '双猫', act: ["饮食饮水"], desc: "晚餐时间", stat: "进食", videoTime: 10, thumbColor: 'bg-green-50 text-green-600' },
        { id: 'x-2', time: '14:00', cat: '奶油', act: ["休息"], desc: "在猫爬架睡觉", stat: "休息", videoTime: 10, thumbColor: 'bg-yellow-50 text-yellow-600' },
        { id: 'x-3', time: '09:00', cat: '栗子', act: ["活动"], desc: "抓板磨爪", stat: "活动", videoTime: 10, thumbColor: 'bg-gray-50 text-gray-500' }
    ];
};

export const formatText = (text: string) => {
    if (!text) return null;
    return text.split(/(\*\*.*?\*\*)/g).map((part, i) => 
        part.startsWith('**') ? <strong key={i} className="font-bold text-indigo-700">{part.slice(2, -2)}</strong> : part
    );
};