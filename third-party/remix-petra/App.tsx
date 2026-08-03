import React, { useState, useEffect, useRef } from 'react';
import { Activity, Settings, AlertTriangle, Camera, Calendar, Video } from 'lucide-react';
import { 
    CONFIG, INITIAL_PET_DATA, VIDEO_SCRIPT, 
    generateCalendarData, getHistoryLogs 
} from './constants';
import { PetData, LogEntry, PlayModalState, EditFormState, PushNotificationData, ChatMessage } from './types';
import TimelineView from './components/TimelineView';
import SettingsView from './components/SettingsView';
import EditPetModal from './components/EditPetModal';
import VideoOverlay from './components/VideoOverlay';
import ShareView from './components/ShareView';
import HomeView from './components/HomeView';
import LiveStreamView from './components/LiveStreamView';
import AuthOnboardingView from './components/AuthOnboardingView';

// Push Notification Component
const PushNotification = ({ data, onClick }: { data: PushNotificationData, onClick: () => void }) => (
    <div onClick={onClick} className="absolute top-4 left-4 right-4 bg-white/95 backdrop-blur-md rounded-2xl shadow-xl z-[60] border-l-4 border-orange-500 p-4 animate-slide-down cursor-pointer flex items-start gap-3 ring-1 ring-black/5">
        <div className="bg-orange-100 p-2 rounded-full text-orange-600 flex-shrink-0 mt-0.5"><AlertTriangle size={20} /></div>
        <div className="flex-1 min-w-0">
            <div className="flex justify-between items-start"><h4 className="font-bold text-gray-900 text-sm">看护警报</h4><span className="text-[10px] text-gray-400">刚刚</span></div>
            <p className="font-medium text-gray-800 text-xs mt-1 truncate">{data.title}</p>
            <p className="text-gray-500 text-[10px] mt-0.5 line-clamp-2">{data.text}</p>
        </div>
    </div>
);

const TabButton = ({ id, icon: Icon, label, activeTab, onClick }: any) => (
    <button onClick={() => onClick(id)} className={`flex flex-col items-center justify-center w-full py-2 transition-colors ${activeTab === id ? 'text-orange-600' : 'text-gray-400'}`}>
        <Icon size={24} className={`mb-1 ${activeTab === id ? 'scale-110' : ''} transition-transform`} />
        <span className="text-[10px] font-medium">{label}</span>
    </button>
);

function App() {
    const [activeTab, setActiveTab] = useState('home'); // Default to home after login for a nice greeting
    const [videoUrl] = useState(CONFIG.defaultVideo);
    const [playModal, setPlayModal] = useState<PlayModalState>({ show: false, startTime: 0, src: null });
    const [selectedDate, setSelectedDate] = useState('24');
    const [currentLogs, setCurrentLogs] = useState<LogEntry[]>([]);
    const [selectedCatFilter, setSelectedCatFilter] = useState('all');
    const [selectedEventFilter, setSelectedEventFilter] = useState('all');
    const [pushNotification, setPushNotification] = useState<PushNotificationData | null>(null);
    const [triggeredAlerts, setTriggeredAlerts] = useState(new Set());

    // User authentication and session states
    const [userSession, setUserSession] = useState<{ phone: string; isNew: boolean; hasDevice: boolean; passwordSet: boolean } | null>(() => {
        try {
            const stored = localStorage.getItem('petra_user_session');
            return stored ? JSON.parse(stored) : null;
        } catch {
            return null;
        }
    });

    // Share State
    const [sharingLog, setSharingLog] = useState<LogEntry | null>(null);

    // Chat Data State
    const [chatMessages, setChatMessages] = useState<ChatMessage[]>([
        { id: 'welcome', sender: 'bot', type: 'text', time: '11:00', text: '你好！我是AI智能看护。今天也在帮你守护毛孩子，有问题要问我吗？' },
        {
            id: 'init-alert-chat',
            sender: 'bot',
            time: '23:09',
            type: 'event',
            text: '', // Card type doesn't need text
            eventData: {
                id: 'alert-24-init',
                time: '23:09',
                cat: '双猫',
                act: ["多猫互动"],
                desc: '检测到深夜跑酷追逐，双方在客厅快速移动。',
                details: {
                    '栗子': '栗子在客厅中心发起冲刺，试图追上前方奔跑的奶油。',
                    '奶油': '奶油在沙发边缘灵活跳跃，利用障碍物躲避栗子的追逐。'
                },
                stat: '高能玩耍',
                videoTime: 14,
                thumbColor: 'bg-orange-50 text-orange-600'
            }
        },
        {
            id: 'init-vlog-feed',
            sender: 'bot',
            time: '10:00',
            type: 'vlog',
            text: '智能看护助手为您推送今日vlog：\n今日已为您精选打包了 栗子与奶油 的日常高光视频，总结了两个小生命今日的超萌瞬间。快点击播放，感受专属于他们的治愈日常吧！🐾',
            vlogSegments: [
                {
                    time: '08:30',
                    petName: '栗子',
                    behavior: '竖耳寻找声音',
                    title: '栗子 · 听到主人微弱叫声瞬间警觉',
                    url: '/cats-reacting.mp4',
                    duration: '00:15',
                    desc: '监控中突然传来熟悉的主人呼唤声，栗子两只耳朵迅速竖起，全神贯注地四处搜寻温暖的声源。'
                },
                {
                    time: '12:15',
                    petName: '奶油',
                    behavior: '大脸凑近镜头',
                    title: '奶油 · 零距离大脸贴近安防广角镜',
                    url: '/cats-reacting.mp4',
                    duration: '00:08',
                    desc: '听到熟悉的慰问与昵称，奶油迈着好奇的步履凑到极近处的探针下，仔细端详发出声音的摄像头。'
                },
                {
                    time: '15:40',
                    petName: '栗子&奶油',
                    behavior: '同步转头凝视',
                    title: '双猫 · 听到广播名宇温馨同步回头',
                    url: '/cats-reacting.mp4',
                    duration: '00:12',
                    desc: '看护音响中播放起主人的呼唤，打闹中的两只小猫极其治愈地动作同步转头，朝看护镜发出灵动凝视。'
                },
                {
                    time: '18:00',
                    petName: '栗子',
                    behavior: '温顺趴下听话',
                    title: '栗子 · 听到叮嘱乖乖趴下安静陪伴',
                    url: '/cats-reacting.mp4',
                    duration: '00:10',
                    desc: '当扬声器里传来“要乖乖看家哦”的细心叮咛时，栗子耳朵偏转并温顺地在镜头前安心趴下，AI 识别：情绪高度平静。'
                }
            ]
        }
    ]);

    // Pet Data State (tries to load custom onboarded pet)
    const [petData, setPetData] = useState<PetData>(() => {
        try {
            const stored = localStorage.getItem('petra_custom_pet');
            if (stored) {
                const customPet = JSON.parse(stored);
                return {
                    ...INITIAL_PET_DATA,
                    [customPet.name]: {
                        type: customPet.type,
                        weight: customPet.weight,
                        features: customPet.features,
                        avatarColor: 'bg-orange-500 text-white',
                        report: `**【${customPet.name}日报】**\n今日标签：**全天候智能守护**。\n已根据其品种 ${customPet.type}，定制了专门的饮食与跑酷识别模型！`,
                        avatarUrl: customPet.avatarUrl
                    }
                };
            }
        } catch (e) {
            console.error(e);
        }
        return INITIAL_PET_DATA;
    });

    const [editModalOpen, setEditModalOpen] = useState(false);
    const [editingPetKey, setEditingPetKey] = useState<string | null>(null);
    const [editForm, setEditForm] = useState<EditFormState>({ name: '', type: '', weight: '', features: '' });

    // Simulate Meme Messages
    useEffect(() => {
        const timers = [
            setTimeout(() => {
                const memeMsg: ChatMessage = {
                    id: `meme-1-${Date.now()}`,
                    sender: 'bot',
                    time: '20:00',
                    type: 'meme',
                    text: '叮！今天抓拍到一个鬼鬼祟祟的身影……栗子自以为神不知鬼不觉，结果全被本 AI 偷偷录下来啦！快来查收这张新鲜出炉的“犯罪铁证”，赶紧发朋友圈曝光它！',
                    memeUrl: '/作案.gif'
                };
                setChatMessages(prev => prev.find(m => m.id.startsWith('meme-1-')) ? prev : [...prev, memeMsg]);
            }, 5000),
            setTimeout(() => {
                const memeMsg: ChatMessage = {
                    id: `meme-2-${Date.now()}`,
                    sender: 'bot',
                    time: '20:05',
                    type: 'meme',
                    text: '呼叫，呼叫！隐藏摄像机好像暴露了！今天栗子朝我走过来，大脸直接怼在了镜头上……这份超近距离的“霸总压迫感”，你必须亲自感受一下！',
                    memeUrl: '/这监控你安的.gif'
                };
                setChatMessages(prev => prev.find(m => m.id.startsWith('meme-2-')) ? prev : [...prev, memeMsg]);
            }, 8000),
            setTimeout(() => {
                const memeMsg: ChatMessage = {
                    id: `meme-3-${Date.now()}`,
                    sender: 'bot',
                    time: '20:10',
                    type: 'meme',
                    text: '战况速报！今天家里上演了一场精彩的“猫猫拳争霸赛”！这行云流水的动作不去做武术指导可惜了！我连夜给你做成了动图，快来看看栗子和奶油到底是谁先动的手？',
                    memeUrl: '/偷袭.gif'
                };
                setChatMessages(prev => prev.find(m => m.id.startsWith('meme-3-')) ? prev : [...prev, memeMsg]);
            }, 11000),
            setTimeout(() => {
                const memeMsg: ChatMessage = {
                    id: `meme-4-${Date.now()}`,
                    sender: 'bot',
                    time: '20:15',
                    type: 'meme',
                    text: '报告主人！家里出现了一个“偷粮大盗”！捕捉到有猫试图徒手破解喂食器的安全防线……瞧瞧这熟练的掏粮手法，这无辜又焦急的小眼神，简直太好笑了！本 AI 贴心地为你保存了证据，快来查收！',
                    memeUrl: '/饭呢.gif'
                };
                setChatMessages(prev => prev.find(m => m.id.startsWith('meme-4-')) ? prev : [...prev, memeMsg]);
            }, 14000)
        ];
        return () => timers.forEach(clearTimeout);
    }, []);

    const videoRef = useRef<HTMLVideoElement>(null);
    const CALENDAR_DAYS = generateCalendarData();

    // Init Logs
    useEffect(() => {
        setCurrentLogs(getHistoryLogs(selectedDate));
    }, [selectedDate]);

    // Background Video Logic
    useEffect(() => {
        if (videoUrl === CONFIG.defaultVideo && videoRef.current) {
            setTimeout(() => videoRef.current?.play().catch(() => console.log("Autoplay blocked")), 800);
        }
    }, [videoUrl]);

    // Core Loop for Simulated Alerts & Chatbot Events
    useEffect(() => {
        if (!videoRef.current) return;
        const videoElement = videoRef.current;
        const handleTimeUpdate = () => {
            const time = videoElement.currentTime;
            const activeScript = VIDEO_SCRIPT.find(s => time >= s.startTime && time < s.endTime);

            if (activeScript?.triggerAlert && Math.floor(time) === activeScript.triggerAlert.timeTrigger) {
                const alertId = `alert-${Math.floor(time)}`;
                if (!triggeredAlerts.has(alertId)) {
                    setTriggeredAlerts(prev => new Set(prev).add(alertId));

                    // 1. Push Notification
                    setPushNotification({
                        title: activeScript.triggerAlert.title,
                        text: activeScript.triggerAlert.desc,
                        videoTime: activeScript.triggerAlert.videoTime
                    });
                    setTimeout(() => setPushNotification(null), 6000);

                    // 2. Add to Timeline Logs
                    const newLog: LogEntry = {
                        id: 'alert-24',
                        time: '23:09',
                        cat: '双猫',
                        act: activeScript.triggerAlert!.act,
                        desc: activeScript.triggerAlert!.desc,
                        details: activeScript.triggerAlert!.details,
                        stat: activeScript.triggerAlert!.stat,
                        videoTime: activeScript.triggerAlert!.videoTime,
                        thumbColor: 'bg-orange-50 text-orange-600'
                    };

                    if (selectedDate === '24') {
                        setCurrentLogs(prev => {
                            if (prev.find(l => l.time === '23:09')) return prev;
                            return [newLog, ...prev];
                        });
                    }
                }
            }
        };
        videoElement.addEventListener('timeupdate', handleTimeUpdate);
        return () => videoElement.removeEventListener('timeupdate', handleTimeUpdate);
    }, [videoUrl, triggeredAlerts, selectedDate]);

    const handleJumpToVideo = (time: number, src: string | null = null) => {
        const targetSrc = src || videoUrl;
        if (time === null || time === undefined) return;
        if (!targetSrc) {
            console.warn("视频源未加载");
            return;
        }
        setPlayModal({ show: true, startTime: time, src: targetSrc });
        setPushNotification(null);
    };

    const handleShare = (log: LogEntry) => {
        setSharingLog(log);
    };

    const handleTriggerVlog = () => {
        // 1. Add the custom vlog message to the chat messages
        const vlogId = `bot-vlog-${Date.now()}`;
        setChatMessages(prev => {
            // Avoid duplicate pushing of the exact same message too rapidly if they spam the button
            if (prev.find(m => m.id.startsWith('bot-vlog-') && (Date.now() - parseInt(m.id.split('-')[2]) < 3000))) {
                return prev;
            }
            const simulatedVlog: ChatMessage = {
                id: vlogId,
                sender: 'bot',
                time: '10:00',
                type: 'vlog',
                text: '智能看护助手为您推送今日vlog：\n今日已为您精选打包了 栗子与奶油 的日常高光视频，总结了两个小生命今日的超萌瞬间。快点击播放，感受专属于他们的治愈日常吧！🐾',
                vlogSegments: [
                    {
                        time: '08:30',
                        petName: '栗子',
                        behavior: '竖耳寻找声音',
                        title: '栗子 · 听到主人微弱叫声瞬间警觉',
                        url: '/cats-reacting.mp4',
                        duration: '00:15',
                        desc: '监控中突然传来熟悉的主人呼唤声，栗子两只耳朵迅速竖起，全神贯注地四处搜寻温暖的声源。'
                    },
                    {
                        time: '12:15',
                        petName: '奶油',
                        behavior: '大脸凑近镜头',
                        title: '奶油 · 零距离大脸贴近安防广角镜',
                        url: '/cats-reacting.mp4',
                        duration: '00:08',
                        desc: '听到熟悉的慰问与昵称，奶油迈着好奇的步履凑到极近处的探针下，仔细端详发出声音的摄像头。'
                    },
                    {
                        time: '15:40',
                        petName: '栗子&奶油',
                        behavior: '同步转头凝视',
                        title: '双猫 · 听到广播名宇温馨同步回头',
                        url: '/cats-reacting.mp4',
                        duration: '00:12',
                        desc: '看护音响中播放起主人的呼唤，打闹中的两只小猫极其治愈地动作同步转头，朝看护镜发出灵动凝视。'
                    },
                    {
                        time: '18:00',
                        petName: '栗子',
                        behavior: '温顺趴下听话',
                        title: '栗子 · 听到叮嘱乖乖趴下安静陪伴',
                        url: '/cats-reacting.mp4',
                        duration: '00:10',
                        desc: '当扬声器里传来“要乖乖看家哦”的细心叮咛时，栗子耳朵偏转并温顺地在镜头前安心趴下，AI 识别：情绪高度平静。'
                    }
                ]
            };
            return [...prev, simulatedVlog];
        });
    };

    const handleSendMessage = (text: string) => {
        // Add User Message
        const userMsg: ChatMessage = {
            id: `user-${Date.now()}`,
            sender: 'user',
            text: text,
            time: new Date().toLocaleTimeString('zh-CN', {hour: '2-digit', minute:'2-digit'}),
            type: 'text'
        };
        setChatMessages(prev => [...prev, userMsg]);

        // Simulate Bot Response
        setTimeout(() => {
            const petNames = Object.keys(petData);
            // Get the last pet as the primary (usually the custom one they register)
            const primaryPet = petNames[petNames.length - 1];
            const info = petData[primaryPet];
            const textLower = text.toLowerCase();

            let customReply = "";
            let replyType: 'text' | 'vlog' = 'text';
            let vlogSegments: any[] = undefined;

            if (textLower.includes('vlog') || textLower.includes('集锦') || textLower.includes('十点') || textLower.includes('日记') || textLower.includes('推送') || textLower.includes('剪辑') || textLower.includes('10')) {
                replyType = 'vlog';
                customReply = "智能看护助手为您推送今日vlog：\n今日已为您精选打包了 栗子与奶油 的日常高光视频，总结了两个小生命今日的超萌瞬间。快点击播放，感受专属于他们的治愈日常吧！🐾";
                vlogSegments = [
                    {
                        time: '08:30',
                        petName: '栗子',
                        behavior: '竖耳寻找声音',
                        title: '栗子 · 听到主人微弱叫声瞬间警觉',
                        url: '/cats-reacting.mp4',
                        duration: '00:15',
                        desc: '监控中突然传来熟悉的主人呼唤声，栗子两只耳朵迅速竖起，全神贯注地四处搜寻温暖的声源。'
                    },
                    {
                        time: '12:15',
                        petName: '奶油',
                        behavior: '大脸凑近镜头',
                        title: '奶油 · 零距离大脸贴近安防广角镜',
                        url: '/cats-reacting.mp4',
                        duration: '00:08',
                        desc: '听到熟悉的慰问与昵称，奶油迈着好奇的步履凑到极近处的探针下，仔细端详发出声音的摄像头。'
                    },
                    {
                        time: '15:40',
                        petName: '栗子&奶油',
                        behavior: '同步转头凝视',
                        title: '双猫 · 听到广播名宇温馨同步回头',
                        url: '/cats-reacting.mp4',
                        duration: '00:12',
                        desc: '看护音响中播放起主人的呼唤，打闹中的两只小猫极其治愈地动作同步转头，朝看护镜发出灵动凝视。'
                    },
                    {
                        time: '18:00',
                        petName: '栗子',
                        behavior: '温顺趴下听话',
                        title: '栗子 · 听到叮嘱乖乖趴下安静陪伴',
                        url: '/cats-reacting.mp4',
                        duration: '00:10',
                        desc: '当扬声器里传来“要乖乖看家哦”的细心叮咛时，栗子耳朵偏转并温顺地在镜头前安心趴下，AI 识别：情绪高度平静。'
                    }
                ];
            } else if (textLower.includes('总结栗子表现') || (textLower.includes('栗子') && textLower.includes('表现'))) {
                customReply = `🐱 **栗子今日表现总结**：
- **今日情绪**：非常活泼好动，上午在客厅和卧室之间进行了高频探索，精神相当饱满；
- **今日饮食**：在清晨按时吃了香喷喷的主粮，主动摄水量充足，排泄习惯良好；
- **温顺指数**：🌟🌟🌟🌟🌟（5颗星），在听到您的语音安详呼唤后非常听话，立刻在镜头前安心趴下。
总体来看，栗子今天表现非常棒，非常省心哦！`;
            } else if (textLower.includes('奶油运动量') || textLower.includes('奶油运动量分析') || (textLower.includes('奶油') && textLower.includes('运动'))) {
                customReply = `🐱 **奶油今日运动量分析**：
- **运动时长**：累计活跃时长约为 45 分钟，属于正常的健康活泼水平；
- **活跃形态**：今天和栗子共同进行了一次“跑酷追逐”高能运动。其余时段表现非常安静内敛；
- **静息状态**：在猫爬架及看护窝里安稳小憩，呼吸状态平稳，拥有十分充足的高质量好睡眠。
总体来说，奶油今天的静息与微运动配比非常合理，状态特别健康！`;
            } else if (textLower.includes('吃') || textLower.includes('饿') || textLower.includes('喂') || textLower.includes('主粮') || textLower.includes('水') || textLower.includes('饮')) {
                customReply = `汪！喵！针对您为【栗子】和【奶油】配置的专属健康饮食习惯，我的摄像头与饮水检测器正在精细守护中。刚才的实时录像显示，栗子今天进食状态非常健康，奶油也非常乖地在自动饮水机前补充了足够水分。我已经根据两只毛孩子的习惯，将喂食计划和饮水报警设置为最佳状态啦！`;
            } else if (textLower.includes('状态') || textLower.includes('怎么') || textLower.includes('情况') || textLower.includes('乖') || textLower.includes('活') || textLower.includes('干嘛')) {
                customReply = `根据我们之前设定的专属看护知识库（偏好描述：栗子喜欢玩闹、奶油偏安静），【栗子】和【奶油】当前一切尽在掌控之中。目前它们表现极佳，正舒服地趴在看护窝里打呼噜小憩呢，没有发生异常跑酷或剧烈碰撞，非常省心噢。`;
            } else {
                const responses = [
                    `收到您的消息！我会为毛孩子【栗子】和【奶油】持续留意实时看护画面。`,
                    `放心吧！我们刚刚已成功开通强消息推送授权，如有任何呕吐或深度异常，我会立刻发送推送警告到您的手机，【栗子】和【奶油】目前十分安全。`,
                    `了解了，已为您特别建立【栗子】与【奶油】的专属行为与情绪习惯标记，你可以放心地在外面工作！`,
                    `太棒了！刚刚我也将【栗子】和【奶油】的萌趣镜头和打闹瞬间打包成GIF写入了本地相册呢。`,
                    `正在为您检查针对【栗子】与【奶油】的全天候 2.4K 智能抓拍日志，它们今天的饮水量、排泄频次与磨爪习惯皆处于健康安全数值内！`,
                    `收到命令。如果之后有任何关于【栗子】与【奶油】的个性化看护偏好改动，您可以随时在“设置”栏中重新编辑或对安防设备进行标定哦！`
                ];
                customReply = responses[Math.floor(Math.random() * responses.length)];
            }
            
            const botMsg: ChatMessage = {
                id: `bot-${Date.now()}`,
                sender: 'bot',
                text: customReply,
                time: new Date().toLocaleTimeString('zh-CN', {hour: '2-digit', minute:'2-digit'}),
                type: replyType,
                vlogSegments: vlogSegments
            };
            setChatMessages(prev => [...prev, botMsg]);
        }, 1200);
    };

    // --- Editing Logic ---
    const openEditModal = (catKey: string) => {
        setEditingPetKey(catKey);
        setEditForm({
            name: catKey,
            type: petData[catKey].type,
            weight: petData[catKey].weight,
            features: petData[catKey].features || '',
            avatarUrl: petData[catKey].avatarUrl
        });
        setEditModalOpen(true);
    };

    const savePetInfo = () => {
        if (!editingPetKey) return;
        
        const newPetData = { ...petData };
        const oldName = editingPetKey;
        const newName = editForm.name;

        const updatedInfo = {
            type: editForm.type,
            weight: editForm.weight,
            features: editForm.features,
            avatarColor: petData[oldName].avatarColor, 
            report: petData[oldName].report,
            avatarUrl: editForm.avatarUrl
        };

        if (oldName !== newName) {
            newPetData[newName] = { ...updatedInfo };
            delete newPetData[oldName];
        } else {
            newPetData[oldName] = { ...updatedInfo };
        }

        setPetData(newPetData);
        setEditModalOpen(false);
    };

    const handleOnboardingComplete = (session: any, customPet?: any) => {
        setUserSession(session);
        localStorage.setItem('petra_user_session', JSON.stringify(session));
        
        if (customPet) {
            const petArray = Array.isArray(customPet) ? customPet : [customPet];
            if (petArray.length > 0) {
                localStorage.setItem('petra_custom_pet', JSON.stringify(petArray[0]));
                localStorage.setItem('petra_custom_pets', JSON.stringify(petArray));
            }
            
            const newPets: any = {};
            const welcomeMessages: any[] = [];
            
            petArray.forEach((petItem, idx) => {
                newPets[petItem.name] = {
                    type: petItem.type,
                    weight: petItem.weight,
                    features: petItem.features,
                    avatarColor: idx % 2 === 0 ? 'bg-orange-500 text-white' : 'bg-amber-500 text-white',
                    report: `**【${petItem.name}日报】**\n今日标签：**初建AI看护档案**。\n已为您关联绑定 Petra C1 监护端，正在开启对品种 ${petItem.type} 与专属习惯的特征适配中。`,
                    avatarUrl: petItem.avatarUrl
                };
                
                welcomeMessages.push({
                    id: `custom-welcome-${Date.now()}-${idx}`,
                    sender: 'bot',
                    time: new Date().toLocaleTimeString('zh-CN', {hour: '2-digit', minute:'2-digit'}),
                    type: 'text',
                    text: `🎉 Petra 智能硬件匹配激活成功！我已经准备好对专属萌宠【${petItem.name}】（品种: ${petItem.type}）进行 2.4K 声音与画面实时监护。您可以在这里向我随时提问！`
                });
            });

            setPetData(prev => ({
                ...prev,
                ...newPets
            }));

            // Set first pet active if existing
            if (petArray.length > 0) {
                localStorage.setItem('petra_active_pet_name', petArray[0].name);
            }

            setChatMessages(prev => [
                ...prev,
                ...welcomeMessages
            ]);
        } else {
            setChatMessages(prev => [
                ...prev,
                {
                    id: `welcome-back-${Date.now()}`,
                    sender: 'bot',
                    time: new Date().toLocaleTimeString('zh-CN', {hour: '2-digit', minute:'2-digit'}),
                    type: 'text',
                    text: `👋 欢迎回归！AI派爪在线监护雷达已启动完毕，一切安全状况表现优良！`
                }
            ]);
        }
        setActiveTab('home');
    };

    const handleLogout = () => {
        localStorage.removeItem('petra_user_session');
        localStorage.removeItem('petra_custom_pet');
        setUserSession(null);
        setPetData(INITIAL_PET_DATA);
        setChatMessages([
            { id: 'welcome', sender: 'bot', type: 'text', time: '11:00', text: '你好！我是AI智能看护。今天也在帮你守护毛孩子，有问题要问我吗？' }
        ]);
        setActiveTab('home');
    };

    return (
        <div className="bg-gray-50 h-screen font-sans text-gray-900 relative max-w-md mx-auto shadow-2xl overflow-hidden border-x border-gray-200 flex flex-col">
            
            {/* Hidden background video for simulation logic */}
            <div className="hidden">
                <video ref={videoRef} src={videoUrl} loop muted playsInline />
            </div>

            {pushNotification && (
                <PushNotification 
                    data={pushNotification} 
                    onClick={() => handleJumpToVideo(pushNotification.videoTime)} 
                />
            )}

            <VideoOverlay 
                show={playModal.show} 
                src={playModal.src} 
                startTime={playModal.startTime} 
                onClose={() => setPlayModal({ show: false, startTime: 0, src: null })} 
            />

            {sharingLog && (
                <ShareView 
                    log={sharingLog} 
                    onClose={() => setSharingLog(null)} 
                />
            )}

            <EditPetModal 
                isOpen={editModalOpen} 
                onClose={() => setEditModalOpen(false)} 
                editForm={editForm} 
                setEditForm={setEditForm} 
                onSave={savePetInfo} 
            />

            {/* Views Container */}
            <div className="flex-1 relative overflow-hidden flex flex-col">
                {!userSession ? (
                    <AuthOnboardingView 
                        currentPetData={petData}
                        onComplete={handleOnboardingComplete}
                    />
                ) : (
                    <>
                        {activeTab === 'home' && (
                            <HomeView 
                                videoUrl={videoUrl}
                                messages={chatMessages}
                                handleJumpToVideo={handleJumpToVideo}
                                onSendMessage={handleSendMessage}
                                onTriggerVlog={handleTriggerVlog}
                            />
                        )}

                        {activeTab === 'live' && (
                            <LiveStreamView 
                                videoUrl={videoUrl}
                            />
                        )}

                        {activeTab === 'timeline' && (
                            <TimelineView 
                                selectedDate={selectedDate}
                                setSelectedDate={setSelectedDate}
                                currentLogs={currentLogs}
                                selectedCatFilter={selectedCatFilter}
                                setSelectedCatFilter={setSelectedCatFilter}
                                selectedEventFilter={selectedEventFilter}
                                setSelectedEventFilter={setSelectedEventFilter}
                                petData={petData}
                                calendarDays={CALENDAR_DAYS}
                                handleJumpToVideo={handleJumpToVideo}
                                onShare={handleShare}
                            />
                        )}

                        {activeTab === 'settings' && (
                            <SettingsView 
                                petData={petData} 
                                openEditModal={openEditModal} 
                                onLogout={handleLogout}
                            />
                        )}
                    </>
                )}
            </div>

            {/* Bottom Nav */}
            {userSession && (
                <div className="bg-white border-t border-gray-100 flex justify-around items-center px-6 pb-safe pt-1 z-40 h-[65px] shadow-[0_-1px_10px_rgba(0,0,0,0.02)] flex-shrink-0 animate-slide-up">
                    <TabButton id="timeline" icon={Calendar} label="记录" activeTab={activeTab} onClick={setActiveTab} />
                    <TabButton id="home" icon={Camera} label="AI助手" activeTab={activeTab} onClick={setActiveTab} />
                    <TabButton id="live" icon={Video} label="实时" activeTab={activeTab} onClick={setActiveTab} />
                    <TabButton id="settings" icon={Settings} label="设置" activeTab={activeTab} onClick={setActiveTab} />
                </div>
            )}
        </div>
    );
}

export default App;