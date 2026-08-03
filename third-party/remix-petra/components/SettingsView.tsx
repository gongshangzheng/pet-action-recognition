import React, { useState } from 'react';
import { 
    Edit2, Wifi, Bell, Utensils, Sparkles, 
    ShieldAlert, Activity, Heart, Eye, Zap, Users, Moon, AlertTriangle
} from 'lucide-react';
import { PetData } from '../types';

interface SettingsViewProps {
    petData: PetData;
    openEditModal: (catKey: string) => void;
    onLogout: () => void;
}

const ToggleSwitch: React.FC<{ 
    checked: boolean; 
    onChange: () => void; 
    disabled?: boolean;
    colorClass?: string;
}> = ({ checked, onChange, disabled = false, colorClass = 'bg-orange-500' }) => {
    return (
        <button
            type="button"
            disabled={disabled}
            onClick={onChange}
            className={`w-9 h-5 rounded-full relative transition-colors duration-200 focus:outline-none ${
                checked && !disabled ? colorClass : 'bg-gray-200'
            } ${disabled ? 'opacity-40 cursor-not-allowed' : 'cursor-pointer'}`}
        >
            <span
                className={`absolute top-0.5 left-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform duration-200 ${
                    checked ? 'translate-x-4' : 'translate-x-0'
                }`}
            />
        </button>
    );
};

const SettingsView: React.FC<SettingsViewProps> = ({ petData, openEditModal, onLogout }) => {
    // Parent Switch state
    const [smartNotifications, setSmartNotifications] = useState(true);

    // Sub-switch states aligned to log events (活动, 多猫互动, 进食进水, 休息, 异常)
    const [subSettings, setSubSettings] = useState({
        activity: true,     // 活动
        interaction: true,  // 多猫互动
        diet: true,         // 进食进水 / 饮食饮水
        rest: true,         // 休息
        anomaly: true       // 异常
    });

    const toggleSub = (key: keyof typeof subSettings) => {
        setSubSettings(prev => ({
            ...prev,
            [key]: !prev[key]
        }));
    };

    return (
        <div className="flex-1 bg-gray-50 overflow-y-auto">
            <div className="bg-white px-6 py-8 border-b border-gray-100">
                <h2 className="text-2xl font-bold text-gray-900 mb-1">设置</h2>
                <p className="text-sm text-gray-500">管理您的设备与宠物档案</p>
            </div>
            
            <div className="p-4 space-y-6">
                {/* Pet Profiles Section */}
                <section>
                    <div className="flex justify-between items-center mb-3 px-1">
                        <h3 className="text-sm font-bold text-gray-700 uppercase tracking-wide">我的宠物</h3>
                    </div>
                    <div className="space-y-3">
                        {Object.keys(petData).map(cat => (
                            <div key={cat} className="bg-white p-4 rounded-xl shadow-sm border border-gray-100 flex items-center justify-between group cursor-pointer hover:border-orange-200 transition-colors">
                                <div className="flex items-center gap-4">
                                    <div className={`w-12 h-12 rounded-full overflow-hidden flex-shrink-0 ${petData[cat].avatarUrl ? 'bg-gray-100 border border-gray-100' : petData[cat].avatarColor} flex items-center justify-center text-lg font-bold shadow-inner`}>
                                        {petData[cat].avatarUrl ? (
                                            <img src={petData[cat].avatarUrl} alt={cat} className="w-full h-full object-cover" referrerPolicy="no-referrer" />
                                        ) : (
                                            cat[0]
                                        )}
                                    </div>
                                    <div>
                                        <div className="font-bold text-gray-900">{cat}</div>
                                        <div className="text-xs text-gray-500 mt-0.5">
                                            {petData[cat].type} · {petData[cat].weight}
                                            {petData[cat].features && <div className="mt-1 text-[10px] text-gray-400 line-clamp-1">{petData[cat].features}</div>}
                                        </div>
                                    </div>
                                </div>
                                <div onClick={() => openEditModal(cat)} className="bg-gray-50 p-2 rounded-full text-gray-400 group-hover:bg-orange-50 group-hover:text-orange-500 transition-colors">
                                    <Edit2 size={16}/>
                                </div>
                            </div>
                        ))}
                    </div>
                </section>

                {/* Device & Notification Section */}
                <section>
                    <h3 className="text-sm font-bold text-gray-700 uppercase tracking-wide mb-3 px-1">通用设置</h3>
                    <div className="bg-white rounded-xl shadow-sm border border-gray-100 divide-y divide-gray-50 overflow-hidden">
                        
                        {/* Device Conn */}
                        <div className="p-4 flex items-center justify-between">
                            <div className="flex items-center gap-3">
                                <div className="bg-blue-50 p-2 rounded-lg text-blue-600"><Wifi size={18}/></div>
                                <span className="text-sm font-medium text-gray-700">设备连接</span>
                            </div>
                            <div className="text-xs text-green-500 font-medium bg-green-50 px-2 py-0.5 rounded-full">在线</div>
                        </div>

                        {/* Master Notification Toggle */}
                        <div className="p-4 flex items-center justify-between bg-white">
                            <div className="flex items-center gap-3">
                                <div className="bg-orange-50 p-2 rounded-lg text-orange-600"><Bell size={18}/></div>
                                <div className="flex flex-col">
                                    <span className="text-sm font-bold text-gray-700">智能通知</span>
                                    <span className="text-[10px] text-gray-400 mt-0.5">总开关：控制所有自动行为提醒</span>
                                </div>
                            </div>
                            <ToggleSwitch 
                                checked={smartNotifications} 
                                onChange={() => setSmartNotifications(!smartNotifications)} 
                            />
                        </div>

                        {/* Conditional Sub-settings Checklist */}
                        <div className={`transition-all duration-300 ease-in-out bg-gray-50/50 ${
                            smartNotifications ? 'max-h-[600px] opacity-100 border-t border-gray-100' : 'max-h-0 opacity-0 pointer-events-none overflow-hidden'
                        }`}>
                            <div className="px-5 py-3 divide-y divide-gray-100/70">
                                
                                {/* 1. 活动 */}
                                <div className="py-3 flex items-center justify-between">
                                    <div className="flex items-center gap-2.5">
                                        <div className="p-1.5 rounded bg-gray-100 text-gray-600">
                                            <Zap size={14} />
                                        </div>
                                        <div className="flex flex-col">
                                            <span className="text-xs font-bold text-gray-700">活动通知</span>
                                            <span className="text-[9px] text-gray-400">跑酷、磨爪、抓跳等日常高能运动状态通报</span>
                                        </div>
                                    </div>
                                    <ToggleSwitch 
                                        checked={subSettings.activity} 
                                        onChange={() => toggleSub('activity')} 
                                        colorClass="bg-gray-500"
                                    />
                                </div>

                                {/* 2. 多猫互动 */}
                                <div className="py-3 flex items-center justify-between">
                                    <div className="flex items-center gap-2.5">
                                        <div className="p-1.5 rounded bg-purple-50 text-purple-600">
                                            <Users size={14} />
                                        </div>
                                        <div className="flex flex-col">
                                            <span className="text-xs font-bold text-gray-700">多猫互动</span>
                                            <span className="text-[9px] text-gray-400">贴贴、相互舔毛、追逐打闹等社交行为</span>
                                        </div>
                                    </div>
                                    <ToggleSwitch 
                                        checked={subSettings.interaction} 
                                        onChange={() => toggleSub('interaction')} 
                                        colorClass="bg-purple-500"
                                    />
                                </div>

                                {/* 3. 进食进水 */}
                                <div className="py-3 flex items-center justify-between">
                                    <div className="flex items-center gap-2.5">
                                        <div className="p-1.5 rounded bg-blue-50 text-blue-600">
                                            <Utensils size={14} />
                                        </div>
                                        <div className="flex flex-col">
                                            <span className="text-xs font-bold text-gray-700">进食进水</span>
                                            <span className="text-[9px] text-gray-400">摄食次数、饮水量变化及进食频率提醒</span>
                                        </div>
                                    </div>
                                    <ToggleSwitch 
                                        checked={subSettings.diet} 
                                        onChange={() => toggleSub('diet')} 
                                        colorClass="bg-blue-500"
                                    />
                                </div>

                                {/* 4. 休息 */}
                                <div className="py-3 flex items-center justify-between">
                                    <div className="flex items-center gap-2.5">
                                        <div className="p-1.5 rounded bg-amber-50 text-amber-600">
                                            <Moon size={14} />
                                        </div>
                                        <div className="flex flex-col">
                                            <span className="text-xs font-bold text-gray-700">休息通报</span>
                                            <span className="text-[9px] text-gray-400">安静睡眠、午后小憩及深度放松状态</span>
                                        </div>
                                    </div>
                                    <ToggleSwitch 
                                        checked={subSettings.rest} 
                                        onChange={() => toggleSub('rest')} 
                                        colorClass="bg-amber-500"
                                    />
                                </div>

                                {/* 5. 异常 */}
                                <div className="py-3 flex items-center justify-between">
                                    <div className="flex items-center gap-2.5">
                                        <div className="p-1.5 rounded bg-red-50 text-red-600">
                                            <AlertTriangle size={14} />
                                        </div>
                                        <div className="flex flex-col">
                                            <span className="text-xs font-bold text-gray-700">异常状况</span>
                                            <span className="text-[9px] text-gray-400">呕吐、设备跌落、剧烈冲突异常吵闹警报</span>
                                        </div>
                                    </div>
                                    <ToggleSwitch 
                                        checked={subSettings.anomaly} 
                                        onChange={() => toggleSub('anomaly')} 
                                        colorClass="bg-red-500"
                                    />
                                </div>

                            </div>
                        </div>

                    </div>
                </section>

                {/* Account Reset Operation */}
                <div className="px-1 mt-6">
                    <button 
                        onClick={onLogout}
                        className="w-full bg-white border border-red-200 text-red-500 py-3 rounded-2xl text-xs font-bold shadow-sm hover:bg-red-50 active:scale-95 transition-all text-center"
                    >
                        退出当前账号
                    </button>
                </div>

                <div className="text-center text-xs text-gray-400 py-4">派爪Petra Dev Reference v1.0 • Smart AI Nest</div>
            </div>
        </div>
    );
};

export default SettingsView;
