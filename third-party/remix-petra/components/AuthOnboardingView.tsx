import React, { useState, useEffect } from 'react';
import { 
    Smartphone, Lock, Key, CheckCircle, Wifi, Bluetooth, Sparkles, 
    ChevronRight, Check, Shield, AlertCircle, Camera, Mic, Bell, Info, ArrowLeft, Loader2,
    QrCode, Scan
} from 'lucide-react';
import { PetData } from '../types';

interface AuthOnboardingViewProps {
    onComplete: (userSession: { phone: string; isNew: boolean; hasDevice: boolean; passwordSet: boolean }, customPet?: any) => void;
    currentPetData: PetData;
}

// Preset tags for pet profiles
const BREED_TAGS_CAT = ["狸花猫", "金渐层", "布偶猫", "暹罗猫", "美短", "英短蓝猫", "橘猫", "三花猫"];
const BREED_TAGS_DOG = ["金毛犬", "柴犬", "柯基", "萨摩耶", "比熊", "哈士奇", "贵宾犬", "流浪小土狗"];
const WEIGHT_TAGS = ["1.5kg", "3.2kg", "4.5kg", "5.8kg", "7.0kg", "12.0kg", "20.0kg"];
const AGE_TAGS = ["3个月 (幼生期)", "6个月", "1岁 (成年)", "3岁", "5岁", "8岁 (老年)"];
const HABIT_TAGS = [
    "💧 饮水积极", "🍗 冻干狂热", "🐟 最爱猫罐头", "🏃 喜欢跑酷", "🐾 脾气极好", 
    "🛋️ 喜欢抓沙发", "🤫 安静温顺", "⚡ 精力过剩", "📦 痴迷纸箱", "🦁 霸道傲娇", "🐭 好奇心极重"
];

const WIFI_LIST = ["Home_Router_2.4G", "TP-LINK_SmartPet_5G", "ChinaNet-LivingRoom", "WIFI_For_My_Cats"];

export default function AuthOnboardingView({ onComplete, currentPetData }: AuthOnboardingViewProps) {
    // Flows: 'login' | 'register' | 'setPassword' | 'unconnectedAlert' | 'stepDevice' | 'stepPet' | 'stepPermissions' | 'forgotPassword'
    const [viewState, setViewState] = useState<'login' | 'register' | 'setPassword' | 'unconnectedAlert' | 'stepDevice' | 'stepPet' | 'stepPermissions' | 'forgotPassword'>('login');
    
    // Auth inputs
    const [loginTab, setLoginTab] = useState<'code' | 'password'>('code');
    const [phone, setPhone] = useState('');
    const [loginCode, setLoginCode] = useState('');
    const [loginPassword, setLoginPassword] = useState('');
    
    // For SMS Registration
    const [registerPhone, setRegisterPhone] = useState('');
    const [registerCode, setRegisterCode] = useState('');
    const [regTimer, setRegTimer] = useState(0);
    const [isSendingRegCode, setIsSendingRegCode] = useState(false);

    // For Password Retrieval
    const [forgotPhone, setForgotPhone] = useState('');
    const [forgotCode, setForgotCode] = useState('');
    const [forgotNewPassword, setForgotNewPassword] = useState('');
    const [forgotConfirmPassword, setForgotConfirmPassword] = useState('');
    const [forgotTimer, setForgotTimer] = useState(0);
    const [isSendingForgotCode, setIsSendingForgotCode] = useState(false);
    
    // Set Password Flow (optional)
    const [newPassword, setNewPassword] = useState('');
    const [confirmPassword, setConfirmPassword] = useState('');
    const [passError, setPassError] = useState('');

    // Session status tracker
    const [sessionData, setSessionData] = useState({
        phone: '',
        isNew: false,
        hasDevice: false,
        passwordSet: false
    });

    // Device connection step inputs
    const [pairingStage, setPairingStage] = useState<'scanDeviceQr' | 'wifiSelect' | 'displayAppQr' | 'connecting' | 'success'>('scanDeviceQr');
    const [selectedWifi, setSelectedWifi] = useState('TP-LINK_SmartPet_5G');
    const [wifiPassword, setWifiPassword] = useState('');
    const [pairedDevice, setPairedDevice] = useState<string | null>(null);
    const [connectingProgress, setConnectingProgress] = useState(0);

    // Optimized Pet profile inputs
    const [petName, setPetName] = useState('');
    const [petImage, setPetImage] = useState<string | null>(null);
    const [isDragging, setIsDragging] = useState(false);
    const [petType, setPetType] = useState<'cat' | 'dog' | 'other' | ''>(''); // 'cat' | 'dog' | 'other'
    const [selectedBreed, setSelectedBreed] = useState('');
    const [customBreed, setCustomBreed] = useState('');
    const [selectedWeight, setSelectedWeight] = useState('3.2kg');
    const [customWeight, setCustomWeight] = useState('3.2');
    const [selectedAge, setSelectedAge] = useState('');
    const [selectedHabits, setSelectedHabits] = useState<string[]>([]);
    const [additionalFeatures, setAdditionalFeatures] = useState('');
    
    // New manual text inputs requested by the user
    const [petWeight, setPetWeight] = useState('');
    const [petCoatColor, setPetCoatColor] = useState('');
    const [petFeatures, setPetFeatures] = useState('');
    const [skipMultiAngle, setSkipMultiAngle] = useState(false);
    const [addedPets, setAddedPets] = useState<any[]>([]);
    
    // Custom Redesigned Row Selection states
    const [petGender, setPetGender] = useState<'GG (男生)' | 'MM (女生)' | '未知'>('GG (男生)');
    const [petState, setPetState] = useState<'在身边' | '寄养中' | '暂离守护' | '生病中'>('在身边');
    
    // Dates (Birth)
    const [birthYear, setBirthYear] = useState('2024');
    const [birthMonth, setBirthMonth] = useState('3');
    const [birthDay, setBirthDay] = useState('15');

    const [isSpayed, setIsSpayed] = useState<'已绝育' | '暂未绝育' | '不详'>('暂未绝育');

    // Multi-angle images for precision AI identification
    const [angleImages, setAngleImages] = useState<{
        front?: string;
        left?: string;
        right?: string;
        back?: string;
    }>({});

    // Bottom Picker sheets
    const [activeBottomSheet, setActiveBottomSheet] = useState<'gender' | 'status' | 'birthDate' | 'isSpayed' | 'petType' | null>(null);

    // Temporary values for bottom picker sheets
    const [tempGender, setTempGender] = useState<'GG (男生)' | 'MM (女生)' | '未知'>('GG (男生)');
    const [tempType, setTempType] = useState<'cat' | 'dog' | 'other' | ''>('');
    const [tempStateVal, setTempStateVal] = useState<'在身边' | '寄养中' | '暂离守护' | '生病中'>('在身边');
    const [tempSpayed, setTempSpayed] = useState<'已绝育' | '暂未绝育' | '不详'>('暂未绝育');

    const [tempBYear, setTempBYear] = useState('2024');
    const [tempBMonth, setTempBMonth] = useState('3');
    const [tempBDay, setTempBDay] = useState('15');

    const fileInputRef = React.useRef<HTMLInputElement>(null);

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (file) {
            if (file.size > 8 * 1024 * 1024) {
                showToastMsg('图片太大啦，请上传 8MB 以内的图片 📸');
                return;
            }
            const reader = new FileReader();
            reader.onload = (event) => {
                setPetImage(event.target?.result as string);
                showToastMsg('✨ 爱宠形象上传成功！');
            };
            reader.readAsDataURL(file);
        }
    };

    const handleDragOver = (e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(true);
    };

    const handleDragLeave = () => {
        setIsDragging(false);
    };

    const handleDrop = (e: React.DragEvent) => {
        e.preventDefault();
        setIsDragging(false);
        const file = e.dataTransfer.files?.[0];
        if (file) {
            if (!file.type.startsWith('image/')) {
                showToastMsg('请拖拽图片格式的文件哦 🖼️');
                return;
            }
            if (file.size > 8 * 1024 * 1024) {
                showToastMsg('图片太大啦，请上传 8MB 以内的图片 📸');
                return;
            }
            const reader = new FileReader();
            reader.onload = (event) => {
                setPetImage(event.target?.result as string);
                showToastMsg('✨ 爱宠形象上传成功！');
            };
            reader.readAsDataURL(file);
        }
    };

    // Detailed age and custom tags states
    const [ageYears, setAgeYears] = useState<number>(1);
    const [ageMonths, setAgeMonths] = useState<number>(3);
    const [customAgeText, setCustomAgeText] = useState('');
    const [isCustomAge, setIsCustomAge] = useState(false);
    const [customHabitTags, setCustomHabitTags] = useState<string[]>([]);
    const [newHabitInput, setNewHabitInput] = useState('');

    // Native permission authorization simulations
    const [permMic, setPermMic] = useState<'idle' | 'granted' | 'denied'>('idle');
    const [permPhoto, setPermPhoto] = useState<'idle' | 'granted' | 'denied'>('idle');
    const [permBell, setPermBell] = useState<'idle' | 'granted' | 'denied'>('idle');
    const [showSystemPrompt, setShowSystemPrompt] = useState<string | null>(null);

    // Validation/Toast
    const [toast, setToast] = useState<string | null>(null);

    const showToastMsg = (msg: string) => {
        setToast(msg);
        setTimeout(() => setToast(null), 2500);
    };

    // SMS registration countdown timer
    useEffect(() => {
        if (regTimer > 0) {
            const t = setTimeout(() => setRegTimer(prev => prev - 1), 1000);
            return () => clearTimeout(t);
        }
    }, [regTimer]);

    // SMS forgot password countdown timer
    useEffect(() => {
        if (forgotTimer > 0) {
            const t = setTimeout(() => setForgotTimer(prev => prev - 1), 1000);
            return () => clearTimeout(t);
        }
    }, [forgotTimer]);

    // 1. Phone camera scanning device QR code simulator
    useEffect(() => {
        if (viewState === 'stepDevice' && pairingStage === 'scanDeviceQr') {
            const timer = setTimeout(() => {
                setPairedDevice('Petra SmartCam C1');
                setPairingStage('wifiSelect');
            }, 15000);
            return () => clearTimeout(timer);
        }
    }, [viewState, pairingStage]);

    // 2. Device scanning App QR code simulator
    useEffect(() => {
        if (viewState === 'stepDevice' && pairingStage === 'displayAppQr') {
            const timer = setTimeout(() => {
                setPairingStage('connecting');
                setConnectingProgress(0);
            }, 15000);
            return () => clearTimeout(timer);
        }
    }, [viewState, pairingStage]);

    // 3. Wifi connection progress simulator
    useEffect(() => {
        if (viewState === 'stepDevice' && pairingStage === 'connecting') {
            const timer = setInterval(() => {
                setConnectingProgress(prev => {
                    if (prev >= 100) {
                        clearInterval(timer);
                        setPairingStage('success');
                        return 100;
                    }
                    return prev + 10;
                });
            }, 250);
            return () => clearInterval(timer);
        }
    }, [viewState, pairingStage]);

    // Handle Login Submit
    const handleLogin = (e: React.FormEvent) => {
        e.preventDefault();
        
        if (!phone.replace(/\D/g, '')) {
            showToastMsg('请输入有效的手机号码');
            return;
        }

        if (loginTab === 'code' && !loginCode) {
            showToastMsg('请输入验证码');
            return;
        }

        if (loginTab === 'password' && !loginPassword) {
            showToastMsg('请输入密码');
            return;
        }

        // Simulating accounts:
        // 1. Phone "13888888888" is an existing user but they have NO device bound yet!
        // To show "unconnectedAlert" popup -> click -> initialization.
        // 2. Other phones are existing users with fully bound state.
        // 3. Registering is "New user", goes directly to initialization set.
        
        const purePhone = phone.trim();
        if (purePhone === '13888888888') {
            // Existing user, unconnected
            const session = {
                phone: purePhone,
                isNew: false,
                hasDevice: false,
                passwordSet: true
            };
            setSessionData(session);
            setViewState('unconnectedAlert');
        } else {
            // Fully active user
            const session = {
                phone: purePhone,
                isNew: false,
                hasDevice: true,
                passwordSet: true
            };
            setSessionData(session);
            onComplete(session);
        }
    };

    // Send SMS registration code mock
    const sendRegCode = () => {
        if (!registerPhone || registerPhone.length < 11) {
            showToastMsg('请输入正确的11位手机号码');
            return;
        }
        setIsSendingRegCode(true);
        setTimeout(() => {
            setIsSendingRegCode(false);
            setRegTimer(60);
            setRegisterCode('5829'); // Preset simulated code
            showToastMsg('【派爪Petra】验证码已发送：5829');
        }, 800);
    };

    // Submit Registration
    const handleRegister = (e: React.FormEvent) => {
        e.preventDefault();
        if (!registerPhone || registerPhone.length < 11) {
            showToastMsg('请输入正确的11位手机号');
            return;
        }
        if (!registerCode) {
            showToastMsg('请填写验证码');
            return;
        }
        if (registerCode !== '5829' && registerCode !== '1234') {
            showToastMsg('验证码不正确');
            return;
        }

        // Successfully registered! Proceed to Set Password guide
        setSessionData({
            phone: registerPhone,
            isNew: true,
            hasDevice: false,
            passwordSet: false
        });
        setViewState('setPassword');
    };

    // Send Forgot Password Code
    const sendForgotCode = () => {
        if (!forgotPhone || forgotPhone.length < 11) {
            showToastMsg('请输入正确的11位手机号码');
            return;
        }
        setIsSendingForgotCode(true);
        setTimeout(() => {
            setIsSendingForgotCode(false);
            setForgotTimer(60);
            setForgotCode('8819');
            showToastMsg('【派爪Petra】找回密码验证码已发送：8819');
        }, 800);
    };

    // Submit Forgot Password Rest
    const handleForgotPasswordSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (!forgotPhone || forgotPhone.length < 11) {
            showToastMsg('请输入正确的11位手机号');
            return;
        }
        if (!forgotCode) {
            showToastMsg('请填写验证码');
            return;
        }
        if (forgotCode !== '8819' && forgotCode !== '1234') {
            showToastMsg('验证码不正确');
            return;
        }
        if (!forgotNewPassword || forgotNewPassword.length < 6) {
            showToastMsg('新密码长度不能少于6位');
            return;
        }
        if (forgotNewPassword !== forgotConfirmPassword) {
            showToastMsg('两次输入的密码不一致');
            return;
        }

        showToastMsg('🎉 密码重置成功！正在为您自动登录');
        
        const purePhone = forgotPhone.trim();
        if (purePhone === '13888888888') {
            const session = {
                phone: purePhone,
                isNew: false,
                hasDevice: false,
                passwordSet: true
            };
            setSessionData(session);
            setViewState('unconnectedAlert');
        } else {
            const session = {
                phone: purePhone,
                isNew: false,
                hasDevice: true,
                passwordSet: true
            };
            setSessionData(session);
            onComplete(session);
        }
    };

    // Set / Skip Password View
    const handleSetPassword = (set: boolean) => {
        if (set) {
            if (!newPassword || newPassword.length < 6) {
                setPassError('密码长度不能少于6位');
                return;
            }
            if (newPassword !== confirmPassword) {
                setPassError('两次输入的密码不一致');
                return;
            }
            setPassError('');
            
            setSessionData(prev => ({ ...prev, passwordSet: true }));
            showToastMsg('密码设置成功！正在开启初始化流程');
        } else {
            showToastMsg('已跳过设置，直接进入初始化流程');
        }

        // Direct registration completes -> proceed to Step 1: Device Pairing
        setTimeout(() => {
            setViewState('stepDevice');
            setPairingStage('scanDeviceQr');
        }, 600);
    };

    // One-click Autofill Demo Pets (栗子 & 奶油)
    const handleAutofillDemoPets = () => {
        // Scottish Fold "奶油" (Naiyou) added directly to addedPets
        const mockNaiyou = {
            name: "奶油",
            type: "苏格兰折耳猫",
            weight: "3.8kg",
            features: "可爱猫咪（苏格兰折耳猫）。性别：MM (女生)，体重：3.8kg，毛色：白灰渐层，出生时间：2023年8月12日，绝育状态：已绝育。 特征描述：性格十分安静内敛，喜欢在猫爬架和看护窝里安稳小憩，拥有非常高质量的好睡眠。",
            avatarUrl: "https://images.unsplash.com/photo-1533738363-b7f9aef128ce?auto=format&fit=crop&w=150&q=80"
        };
        setAddedPets([mockNaiyou]);

        // "栗子" (Lizi) populated in active form fields
        setPetName("栗子");
        setPetType("cat");
        setSelectedBreed("金渐层");
        setPetGender("GG (男生)");
        setPetWeight("4.2");
        setPetCoatColor("淡金黄带有深色条纹");
        setBirthYear("2023");
        setBirthMonth("5");
        setBirthDay("20");
        setIsSpayed("已绝育");
        setPetFeatures("性格非常活泼好动，喜欢吃冻干主粮，听到呼唤会立刻趴下并保持安详，AI 识别情绪高度平静。");
        setPetImage("https://images.unsplash.com/photo-1514888286974-6c03e2ca1dba?auto=format&fit=crop&w=150&q=80");
        
        showToastMsg("✨ 已一键成功导入演示小猫“栗子”与“奶油”的看护档案！");
    };

    // Toggle Habits presets
    const toggleHabit = (tag: string) => {
        setSelectedHabits(prev => 
            prev.includes(tag) ? prev.filter(t => t !== tag) : [...prev, tag]
        );
    };

    // Form auto-features builder combining selection tags
    const buildAutoFeatures = () => {
        const breed = selectedBreed;
        const basic = `这只${petType === 'cat' ? '可爱猫咪' : petType === 'dog' ? '忠诚狗狗' : '神奇萌宠'}${breed ? `（${breed}）` : ''}。`;
        const profile = `性别：${petGender}，体重：${petWeight}${petWeight.toLowerCase().includes('kg') ? '' : 'kg'}，毛色：${petCoatColor}，出生时间：${birthYear}年${birthMonth}月${birthDay}日，绝育状态：${isSpayed}。`;
        const featuresText = petFeatures.trim() ? ` 特征描述：${petFeatures}。` : '';
        const multiPhotos = Object.keys(angleImages).length > 0 
            ? ` 已在云端建立 AI 3D 视觉深度识别档案库（已录入 ${Object.keys(angleImages).length} 个识别角度：${Object.keys(angleImages).map(k => k === 'front' ? '正脸' : k === 'left' ? '左侧' : k === 'right' ? '右侧' : '背体').join('、')}）。`
            : '';

        return `${basic}${profile}${featuresText}${multiPhotos}`;
    };

    // Complete Pet Entry
    const handlePetEntrySubmit = () => {
        const hasSomeInputs = petName.trim() || petType || selectedBreed.trim() || petWeight.trim();
        
        if (hasSomeInputs) {
            const missingFields: string[] = [];
            if (!petName.trim()) missingFields.push('宠物昵称');
            if (!petType) missingFields.push('宠物类型');
            if (!selectedBreed.trim()) missingFields.push('宠物品种');
            if (!petWeight.trim()) missingFields.push('宠物体重');
            if (!petCoatColor.trim()) missingFields.push('宠物毛色');
            if (!petFeatures.trim()) missingFields.push('特征描述');

            if (missingFields.length > 0) {
                showToastMsg(`尚未完成当前宠物填写，请补充或清空：${missingFields.join('、')}`);
                return;
            }

            const newPet = {
                name: petName.trim(),
                type: selectedBreed,
                weight: petWeight.toLowerCase().includes('kg') ? petWeight : `${petWeight}kg`,
                features: buildAutoFeatures(),
                avatarUrl: petImage || undefined
            };

            setAddedPets(prev => [...prev, newPet]);
            showToastMsg(`✅ 已保存宠物：${newPet.name}`);
            
            // Clear current state so we don't duplicate on end
            setPetName('');
            setPetImage(null);
            setPetType('');
            setSelectedBreed('');
            setCustomBreed('');
            setPetWeight('');
            setPetCoatColor('');
            setPetFeatures('');
            setAngleImages({});
            setSkipMultiAngle(false);
            setPetGender('GG (男生)');
            setPetState('在身边');
            setBirthYear('2024');
            setBirthMonth('3');
            setBirthDay('15');
            setIsSpayed('暂未绝育');
        } else {
            if (addedPets.length === 0) {
                showToastMsg('请先输入第一个宠物（或在上方添加完毕）才可以进入下一步哦');
                return;
            }
        }

        // Go to Step 3: Permissions
        setViewState('stepPermissions');
    };

    // Save current pet and reset form so user can enter the next pet
    const handleSaveAndContinueNext = () => {
        const missingFields: string[] = [];
        
        if (!petName.trim()) missingFields.push('宠物昵称');
        if (!petType) missingFields.push('宠物类型');
        if (!selectedBreed.trim()) missingFields.push('宠物品种');
        if (!petWeight.trim()) missingFields.push('宠物体重');
        if (!petCoatColor.trim()) missingFields.push('宠物毛色');
        if (!petFeatures.trim()) missingFields.push('特征描述');

        if (missingFields.length > 0) {
            showToastMsg(`尚有未填项，请先补充：${missingFields.join('、')}`);
            return;
        }

        const newPet = {
            name: petName.trim(),
            type: selectedBreed,
            weight: petWeight.toLowerCase().includes('kg') ? petWeight : `${petWeight}kg`,
            features: buildAutoFeatures(),
            avatarUrl: petImage || undefined
        };

        setAddedPets(prev => [...prev, newPet]);
        showToastMsg(`✅ 已录入 ${newPet.name}。现在，请开始录入您的下一个宠物！`);

        // Reset details for next pet
        setPetName('');
        setPetImage(null);
        setPetType('');
        setSelectedBreed('');
        setCustomBreed('');
        setPetWeight('');
        setPetCoatColor('');
        setPetFeatures('');
        setAngleImages({});
        setSkipMultiAngle(false);
        setPetGender('GG (男生)');
        setPetState('在身边');
        setBirthYear('2024');
        setBirthMonth('3');
        setBirthDay('15');
        setIsSpayed('暂未绝育');
    };

    // Request simulated permissions
    const requestPermission = (type: 'mic' | 'photo' | 'bell') => {
        setShowSystemPrompt(type);
    };

    const confirmSystemPrompt = (granted: boolean) => {
        const type = showSystemPrompt;
        setShowSystemPrompt(null);
        if (!type) return;

        if (type === 'mic') {
            setPermMic(granted ? 'granted' : 'denied');
            if (granted) showToastMsg('🎙️ 麦克风访问权限已开启');
        } else if (type === 'photo') {
            setPermPhoto(granted ? 'granted' : 'denied');
            if (granted) showToastMsg('🖼️ 相册及存储权限已开启');
        } else if (type === 'bell') {
            setPermBell(granted ? 'granted' : 'denied');
            if (granted) showToastMsg('🔔 智能看护通知已开启');
        }
    };

    const handleAllFinished = () => {
        // Complete the Onboarding flow! Give the parent component userSession and customPet array
        let petsToSubmit: any[] = [...addedPets];
        
        if (petName.trim() && petType && selectedBreed) {
            const finalPet = {
                name: petName.trim(),
                type: selectedBreed,
                weight: petWeight.toLowerCase().includes('kg') ? petWeight : `${petWeight}kg`,
                features: buildAutoFeatures(),
                avatarUrl: petImage || undefined
            };
            petsToSubmit.push(finalPet);
        }

        if (petsToSubmit.length === 0) {
            petsToSubmit.push({
                name: petName || '新成员',
                type: selectedBreed || '其他陪护',
                weight: petWeight ? (petWeight.toLowerCase().includes('kg') ? petWeight : `${petWeight}kg`) : '3.0kg',
                features: buildAutoFeatures(),
                avatarUrl: petImage || undefined
            });
        }

        const finalSession = {
            ...sessionData,
            hasDevice: true
        };

        onComplete(finalSession, petsToSubmit);
    };

    return (
        <div className="flex-1 flex flex-col bg-[#FAF9F6] overflow-y-auto scrollbar-hide relative text-gray-900 pb-12">
            
            {/* Custom Toast Alert */}
            {toast && (
                <div className="absolute top-6 left-12 right-12 bg-gray-900/90 text-white text-xs py-2.5 px-4 rounded-xl text-center shadow-lg z-[99] animate-fade-in pointer-events-none">
                    {toast}
                </div>
            )}

            {/* Quick Experience / Demo Bypass bar */}
            {viewState === 'login' && (
                <div className="bg-orange-50 px-4 py-2 flex items-center justify-between text-xs text-orange-800 border-b border-orange-100 flex-shrink-0">
                    <div className="flex items-center gap-1.5 font-medium">
                        <Info size={14} className="text-orange-500" />
                        <span>演示专用入口：可以使用测试账号快捷体验</span>
                    </div>
                    <button 
                        onClick={() => {
                            setPhone('13888888888');
                            setLoginTab('password');
                            setLoginPassword('123456');
                            showToastMsg('已自动填充未联网测试账号！');
                        }}
                        className="text-orange-600 font-bold bg-white px-2 py-0.5 rounded-md border border-orange-200 active:scale-95"
                    >
                        填充账号
                    </button>
                </div>
            )}

            {/* Simulated System Permissions Overlay Box */}
            {showSystemPrompt && (
                <div className="fixed inset-0 bg-black/50 backdrop-blur-xs flex items-center justify-center z-[100] p-6 animate-fade-in">
                    <div className="bg-white rounded-2xl p-5 w-full max-w-xs shadow-2xl text-center animate-zoom-in">
                        <div className="bg-amber-100 p-3 rounded-full text-amber-600 w-12 h-12 flex items-center justify-center mx-auto mb-3">
                            {showSystemPrompt === 'mic' && <Mic size={24} />}
                            {showSystemPrompt === 'photo' && <Camera size={24} />}
                            {showSystemPrompt === 'bell' && <Bell size={24} />}
                        </div>
                        <h4 className="font-bold text-gray-800 text-sm mb-1.5">
                            想要使用您的{showSystemPrompt === 'mic' ? '麦克风' : showSystemPrompt === 'photo' ? '相册照片' : '通知和推送'}
                        </h4>
                        <p className="text-gray-500 text-xs leading-relaxed mb-5">
                            {showSystemPrompt === 'mic' 
                                ? '我们需要访问麦克风以允许您在办公室与在家的爱宠实时语音，录制抓拍视频的声音。' 
                                : showSystemPrompt === 'photo' 
                                ? '我们需要访问您的相册以保存由AI每日自动生成的猫咪/狗狗趣图与犯罪Gif动图。' 
                                : '我们需要发送重要看护警告（如猫咪剧烈打闹或异常呕吐状况等深夜急救推送）。'
                            }
                        </p>
                        <div className="flex gap-3">
                            <button 
                                onClick={() => confirmSystemPrompt(false)}
                                className="flex-1 py-2 rounded-xl text-xs font-semibold text-gray-500 bg-gray-100 hover:bg-gray-200"
                            >
                                不允许
                            </button>
                            <button 
                                onClick={() => confirmSystemPrompt(true)}
                                className="flex-1 py-2 rounded-xl text-xs font-bold text-white bg-orange-600 hover:bg-orange-700 shadow-md shadow-orange-100"
                            >
                                好
                            </button>
                        </div>
                    </div>
                </div>
            )}

            {/* UNCONNECTED DEVICE DIALOG popup (from flowchart) */}
            {viewState === 'unconnectedAlert' && (
                <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-[90] p-6">
                    <div className="bg-white rounded-3xl p-6 w-full max-w-sm shadow-2xl animate-zoom-in border border-orange-100">
                        <div className="bg-orange-50 p-4 rounded-full text-orange-600 w-16 h-16 flex items-center justify-center mx-auto mb-4">
                            <AlertCircle size={32} />
                        </div>
                        <h3 className="text-lg font-bold text-gray-900 text-center mb-2">未连接智能看护设备</h3>
                        <p className="text-xs text-gray-500 text-center leading-relaxed mb-6">
                            您已成功登录 <span className="font-bold text-gray-700">{sessionData.phone}</span> 账号，但此账号尚未绑定任何派爪Petra智能监护设备。请点击下方按钮，开始设备的初始化连网与宠物档案建立。
                        </p>
                        <div className="flex flex-col gap-2">
                            <button 
                                onClick={() => {
                                    setViewState('stepDevice');
                                    setPairingStage('scanDeviceQr');
                                }}
                                className="w-full bg-orange-500 text-white py-3 rounded-full text-xs font-bold shadow-lg shadow-orange-100 active:scale-95 transition-transform flex items-center justify-center gap-1.5 hover:bg-orange-600"
                            >
                                去匹配设备并初始化 <ChevronRight size={14} />
                            </button>
                            <button 
                                onClick={() => setViewState('login')}
                                className="w-full text-gray-400 py-2 rounded-full text-xs font-semibold hover:text-gray-600"
                            >
                                退出登录
                            </button>
                        </div>
                    </div>
                </div>
            )}


            {/* ==================================================== */}
            {/* 1. LOGIN STATE                                       */}
            {/* ==================================================== */}
            {viewState === 'login' && (
                <div className="px-6 flex flex-col flex-1 pt-12 animate-fade-in">
                    {/* Header Logo */}
                    <div className="text-center mb-8">
                        <div className="inline-flex bg-orange-500 text-white p-4 rounded-3xl shadow-lg shadow-orange-100 mb-4 animate-bounce">
                            <Sparkles size={32} />
                        </div>
                        <h2 className="text-2xl font-black tracking-tight text-gray-800">派爪Petra</h2>
                    </div>

                    {/* Tab Selection */}
                    <div className="bg-gray-100 p-1 rounded-2xl flex mb-6">
                        <button 
                            onClick={() => setLoginTab('code')}
                            className={`flex-1 py-2 text-xs font-bold rounded-xl transition-all ${loginTab === 'code' ? 'bg-white text-orange-600 shadow-sm' : 'text-gray-500'}`}
                        >
                            验证码登录
                        </button>
                        <button 
                            onClick={() => setLoginTab('password')}
                            className={`flex-1 py-2 text-xs font-bold rounded-xl transition-all ${loginTab === 'password' ? 'bg-white text-orange-600 shadow-sm' : 'text-gray-500'}`}
                        >
                            密码登录
                        </button>
                    </div>

                    {/* Form */}
                    <form onSubmit={handleLogin} className="space-y-4">
                        <div className="bg-white p-3 rounded-2xl border border-gray-100 shadow-sm flex items-center gap-3">
                            <Smartphone className="text-gray-400 flex-shrink-0" size={18} />
                            <input 
                                type="tel"
                                maxLength={11}
                                value={phone}
                                onChange={(e) => setPhone(e.target.value)}
                                placeholder="输入手机号"
                                className="bg-transparent text-sm w-full outline-none"
                            />
                        </div>

                        {loginTab === 'code' ? (
                            <div className="bg-white p-3 rounded-2xl border border-gray-100 shadow-sm flex items-center gap-3 relative">
                                <Key className="text-gray-400 flex-shrink-0" size={18} />
                                <input 
                                    type="text"
                                    maxLength={4}
                                    value={loginCode}
                                    onChange={(e) => setLoginCode(e.target.value)}
                                    placeholder="输入验证码 (1234)"
                                    className="bg-transparent text-sm w-full outline-none"
                                />
                                <button 
                                    type="button"
                                    onClick={() => {
                                        setLoginCode('1234');
                                        showToastMsg('短信获取成功，验证码已填：1234');
                                    }}
                                    className="absolute right-3 bg-orange-50 text-orange-600 text-[10px] font-bold px-3 py-1.5 rounded-lg active:scale-95"
                                >
                                    获取验证码
                                </button>
                            </div>
                        ) : (
                            <div className="space-y-2">
                                <div className="bg-white p-3 rounded-2xl border border-gray-100 shadow-sm flex items-center gap-3">
                                    <Lock className="text-gray-400 flex-shrink-0" size={18} />
                                    <input 
                                        type="password"
                                        value={loginPassword}
                                        onChange={(e) => setLoginPassword(e.target.value)}
                                        placeholder="输入密码"
                                        className="bg-transparent text-sm w-full outline-none"
                                    />
                                </div>
                                <div className="flex justify-end px-1">
                                    <button 
                                        type="button"
                                        onClick={() => {
                                            setForgotPhone(phone); // prefill with phone if filled
                                            setViewState('forgotPassword');
                                        }}
                                        className="text-xs text-orange-600 font-bold hover:underline transition-all active:scale-95"
                                    >
                                        找回密码？
                                    </button>
                                </div>
                            </div>
                        )}

                        <button 
                            type="submit"
                            className="w-full bg-orange-500 text-white font-bold py-3.5 rounded-2xl text-sm shadow-xl shadow-orange-100 hover:bg-orange-600 transition-colors active:scale-[98%] flex items-center justify-center gap-1"
                        >
                            立即登录
                        </button>
                    </form>

                    {/* Bottom Register Switch */}
                    <div className="mt-8 text-center bg-white border border-gray-100 p-4 rounded-3xl shadow-sm">
                        <span className="text-xs text-gray-500">没有账号？ </span>
                        <button 
                            onClick={() => setViewState('register')}
                            className="text-xs text-orange-600 font-bold hover:underline"
                        >
                            手机验证码注册
                        </button>
                    </div>
                </div>
            )}


            {/* ==================================================== */}
            {/* 2. REGISTRATION STATE                                */}
            {/* ==================================================== */}
            {viewState === 'register' && (
                <div className="px-6 flex flex-col flex-1 pt-12 animate-fade-in">
                    <button 
                        onClick={() => setViewState('login')}
                        className="flex items-center gap-1.5 text-xs text-gray-400 hover:text-gray-600 mb-8 self-start"
                    >
                        <ArrowLeft size={16} /> 返回登录
                    </button>

                    <div className="mb-6">
                        <h2 className="text-2xl font-black tracking-tight text-gray-800">手机号注册</h2>
                        <p className="text-xs text-gray-400 mt-1">仅需一秒获取智能看护码开通</p>
                    </div>

                    <form onSubmit={handleRegister} className="space-y-4">
                        <div className="bg-white p-3 rounded-2xl border border-gray-100 shadow-sm flex items-center gap-3">
                            <Smartphone className="text-gray-400 flex-shrink-0" size={18} />
                            <input 
                                type="tel"
                                maxLength={11}
                                value={registerPhone}
                                onChange={(e) => setRegisterPhone(e.target.value)}
                                placeholder="请输入您的11位手机号码"
                                className="bg-transparent text-sm w-full outline-none"
                            />
                        </div>

                        <div className="bg-white p-3 rounded-2xl border border-gray-100 shadow-sm flex items-center gap-3 relative">
                            <Key className="text-gray-400 flex-shrink-0" size={18} />
                            <input 
                                type="text"
                                maxLength={4}
                                value={registerCode}
                                onChange={(e) => setRegisterCode(e.target.value)}
                                placeholder="验证码"
                                className="bg-transparent text-sm w-full outline-none pr-24"
                            />
                            <button 
                                type="button"
                                disabled={regTimer > 0 || isSendingRegCode}
                                onClick={sendRegCode}
                                className="absolute right-3 bg-orange-50 text-orange-600 text-[10px] font-bold px-3 py-1.5 rounded-lg active:scale-95 disabled:bg-gray-100 disabled:text-gray-400"
                            >
                                {isSendingRegCode ? '发送中...' : regTimer > 0 ? `${regTimer}s后重新获取` : '获取验证码'}
                            </button>
                        </div>

                        <div className="flex items-center gap-2 px-1">
                            <input type="checkbox" defaultChecked className="rounded border-gray-300 text-orange-500 focus:ring-orange-500" />
                            <span className="text-[10px] text-gray-400">已阅读并同意 <a className="text-orange-500 underline" href="#">派爪看护与隐私协议</a></span>
                        </div>

                        <button 
                            type="submit"
                            className="w-full bg-orange-500 text-white font-bold py-3.5 rounded-2xl text-sm shadow-xl shadow-orange-100 hover:bg-orange-600 transition-colors active:scale-[98%] flex items-center justify-center gap-1"
                        >
                            立即注册并下一步
                        </button>
                    </form>
                </div>
            )}


            {/* ==================================================== */}
            {/* RETRIEVE PASSWORD STATE                              */}
            {/* ==================================================== */}
            {viewState === 'forgotPassword' && (
                <div className="px-6 flex flex-col flex-1 pt-12 animate-fade-in">
                    <button 
                        type="button"
                        onClick={() => setViewState('login')}
                        className="flex items-center gap-1.5 text-xs text-gray-500 hover:text-gray-700 mb-8 self-start bg-gray-50 px-3 py-1.5 rounded-xl border border-gray-100/60 active:scale-95 transition-all"
                    >
                        <ArrowLeft size={16} /> 返回登录
                    </button>

                    <div className="mb-6">
                        <h2 className="text-2xl font-black tracking-tight text-gray-800">找回密码</h2>
                        <p className="text-xs text-gray-400 mt-1">通过手机验证码重置您的登录密码</p>
                    </div>

                    <form onSubmit={handleForgotPasswordSubmit} className="space-y-4">
                        <div className="bg-white p-3 rounded-2xl border border-gray-100 shadow-sm flex items-center gap-3">
                            <Smartphone className="text-gray-400 flex-shrink-0" size={18} />
                            <input 
                                type="tel"
                                maxLength={11}
                                value={forgotPhone}
                                onChange={(e) => setForgotPhone(e.target.value)}
                                placeholder="请输入您的11位手机号码"
                                className="bg-transparent text-sm w-full outline-none"
                            />
                        </div>

                        <div className="bg-white p-3 rounded-2xl border border-gray-100 shadow-sm flex items-center gap-3 relative">
                            <Key className="text-gray-400 flex-shrink-0" size={18} />
                            <input 
                                type="text"
                                maxLength={4}
                                value={forgotCode}
                                onChange={(e) => setForgotCode(e.target.value)}
                                placeholder="验证码"
                                className="bg-transparent text-sm w-full outline-none pr-24"
                            />
                            <button 
                                type="button"
                                disabled={forgotTimer > 0 || isSendingForgotCode}
                                onClick={sendForgotCode}
                                className="absolute right-3 bg-orange-50 text-orange-600 text-[10px] font-bold px-3 py-1.5 rounded-lg active:scale-95 disabled:bg-gray-100 disabled:text-gray-400"
                            >
                                {isSendingForgotCode ? '发送中...' : forgotTimer > 0 ? `${forgotTimer}s后重新获取` : '获取验证码'}
                            </button>
                        </div>

                        <div className="bg-white p-3 rounded-2xl border border-gray-100 shadow-sm flex items-center gap-3">
                            <Lock className="text-gray-400 flex-shrink-0" size={18} />
                            <input 
                                type="password"
                                value={forgotNewPassword}
                                onChange={(e) => setForgotNewPassword(e.target.value)}
                                placeholder="输入新密码 (不少于6位)"
                                className="bg-transparent text-sm w-full outline-none"
                            />
                        </div>

                        <div className="bg-white p-3 rounded-2xl border border-gray-100 shadow-sm flex items-center gap-3">
                            <Lock className="text-gray-400 flex-shrink-0" size={18} />
                            <input 
                                type="password"
                                value={forgotConfirmPassword}
                                onChange={(e) => setForgotConfirmPassword(e.target.value)}
                                placeholder="再次确认您的新密码"
                                className="bg-transparent text-sm w-full outline-none"
                            />
                        </div>

                        <button 
                            type="submit"
                            className="w-full bg-orange-500 text-white font-bold py-3.5 rounded-2xl text-sm shadow-xl shadow-orange-100 hover:bg-orange-600 transition-colors active:scale-[98%] flex items-center justify-center gap-1"
                        >
                            重置密码并直接登录
                        </button>
                    </form>
                </div>
            )}


            {/* ==================================================== */}
            {/* 3. SET PASSWORD STATE (OPTIONAL GUIDE)               */}
            {/* ==================================================== */}
            {viewState === 'setPassword' && (
                <div className="px-6 flex flex-col flex-1 pt-12 animate-fade-in">
                    <div className="text-center mb-8">
                        <div className="inline-flex bg-green-100 text-green-600 p-3 rounded-full mb-3">
                            <Check size={28} />
                        </div>
                        <h2 className="text-2xl font-black text-gray-800">注册成功！</h2>
                        <p className="text-xs text-gray-400 mt-1">推荐为您的账户设置安全访问密码</p>
                    </div>

                    <div className="bg-amber-50 border border-amber-200/50 p-4 rounded-2xl text-amber-800 text-[11px] leading-relaxed mb-6 flex gap-2">
                        <Info size={16} className="text-amber-500 flex-shrink-0 mt-0.5" />
                        <span>设置专属密码后，每次进入设备无需再次等待验证码。您也可以点击<b>暂不设置</b>跳过。</span>
                    </div>

                    <div className="space-y-4">
                        <div className="bg-white p-3 rounded-2xl border border-gray-100 shadow-sm flex items-center gap-3">
                            <Lock className="text-gray-400 flex-shrink-0" size={18} />
                            <input 
                                type="password"
                                value={newPassword}
                                onChange={(e) => setNewPassword(e.target.value)}
                                placeholder="输入密码 (不少于6位)"
                                className="bg-transparent text-sm w-full outline-none"
                            />
                        </div>

                        <div className="bg-white p-3 rounded-2xl border border-gray-100 shadow-sm flex items-center gap-3">
                            <CheckCircle className="text-gray-400 flex-shrink-0" size={18} />
                            <input 
                                type="password"
                                value={confirmPassword}
                                onChange={(e) => setConfirmPassword(e.target.value)}
                                placeholder="再次确认您的密码"
                                className="bg-transparent text-sm w-full outline-none"
                            />
                        </div>

                        {passError && (
                            <p className="text-[11px] text-red-500 px-1 font-medium">{passError}</p>
                        )}

                        <div className="pt-4 flex flex-col gap-3">
                            <button 
                                onClick={() => handleSetPassword(true)}
                                className="w-full bg-orange-500 text-white font-bold py-3.5 rounded-2xl text-sm shadow-xl shadow-orange-100 hover:bg-orange-600 active:scale-95"
                            >
                                确认设置安全密码
                            </button>
                            <button 
                                onClick={() => handleSetPassword(false)}
                                className="w-full bg-gray-100 text-gray-600 font-bold py-3 rounded-2xl text-xs hover:bg-gray-200 active:scale-95 text-center"
                            >
                                暂不设置，直接进入
                            </button>
                        </div>
                    </div>
                </div>
            )}


            {/* ==================================================== */}
            {/* 4. STEP 1: DEVICE CONNECTION FLOW (设备匹配)          */}
            {/* ==================================================== */}
            {viewState === 'stepDevice' && (
                <div className="px-6 flex flex-col flex-1 pt-8 animate-fade-in">
                    {/* Progress indicator */}
                    <div className="mb-6 flex items-center justify-between">
                        <div className="flex gap-2 items-center">
                            <span className="text-xs bg-orange-500 text-white w-5 h-5 rounded-full flex items-center justify-center font-bold">1</span>
                            <span className="text-xs font-bold text-gray-700">设备匹配联网</span>
                        </div>
                        <span className="text-[10px] text-gray-400">步骤 1/3</span>
                    </div>

                    {pairingStage === 'scanDeviceQr' && (
                        <div className="flex-1 flex flex-col items-center justify-between py-2 animate-fade-in">
                            <div className="text-center w-full">
                                <h3 className="font-bold text-gray-900 text-sm">第一步：手机扫看护仪上的二维码</h3>
                                <p className="text-[11px] text-gray-500 mt-1 max-w-xs mx-auto leading-relaxed">
                                    请使用您的手机对准派爪 Petra 看护设备底部、背面或包装盒上的绑定二维码进行扫描。
                                </p>
                            </div>

                            {/* Beautiful Simulated QR Code Scanner Viewfinder */}
                            <div className="relative w-56 h-56 my-4 bg-gray-950 rounded-3xl border border-gray-800 shadow-xl overflow-hidden flex flex-col items-center justify-center">
                                {/* Grid texture background */}
                                <div className="absolute inset-0 opacity-15 bg-[radial-gradient(#ffffff_1px,transparent_1px)] [background-size:16px_16px]" />
                                
                                {/* Target Viewfinder brackets */}
                                <div className="absolute top-8 left-8 w-6 h-6 border-t-4 border-l-4 border-orange-500 rounded-tl" />
                                <div className="absolute top-8 right-8 w-6 h-6 border-t-4 border-r-4 border-orange-500 rounded-tr" />
                                <div className="absolute bottom-8 left-8 w-6 h-6 border-b-4 border-l-4 border-orange-500 rounded-bl" />
                                <div className="absolute bottom-8 right-8 w-6 h-6 border-b-4 border-r-4 border-orange-500 rounded-br" />

                                {/* Moving Scanning Laser Line */}
                                <div className="animate-scan-line" />

                                {/* Simulated Camera Frame containing a mini device with QR Code */}
                                <div className="z-10 flex flex-col items-center justify-center bg-white/10 backdrop-blur-xs px-4 py-3 rounded-2xl border border-white/20">
                                    <div className="w-16 h-16 bg-white p-1 rounded-xl shadow-md flex items-center justify-center">
                                        <QrCode size={48} className="text-gray-900" />
                                    </div>
                                    <span className="text-[9px] text-white/80 font-bold mt-2">Petra_C1_SN_8218</span>
                                </div>

                                {/* Pulsing scanning status indicator */}
                                <div className="absolute bottom-3 text-white/70 text-[9px] font-medium tracking-wider animate-pulse flex items-center gap-1">
                                    <Scan size={10} className="animate-spin" />
                                    <span>对准二维码中...</span>
                                </div>
                            </div>

                            <div className="w-full space-y-2">
                                <button
                                    onClick={() => {
                                        setPairedDevice('Petra SmartCam C1');
                                        setPairingStage('wifiSelect');
                                    }}
                                    className="w-full bg-orange-500 text-white font-bold py-3.5 rounded-2xl text-xs shadow-md shadow-orange-100 hover:bg-orange-600 active:scale-95 transition-all flex items-center justify-center gap-1"
                                >
                                    确认扫码成功
                                </button>
                                <p className="text-[10px] text-gray-400 text-center">
                                    对准后APP将自动识别，或者您可以手动点击上方按钮
                                </p>
                            </div>
                        </div>
                    )}

                    {pairingStage === 'wifiSelect' && (
                        <div className="space-y-4 animate-fade-in flex flex-col flex-1">
                            <div className="bg-white p-3.5 rounded-2xl border border-gray-100 shadow-xs flex items-center gap-3">
                                <div className="bg-green-100 p-2 rounded-full text-green-600"><CheckCircle size={16} /></div>
                                <div>
                                    <p className="text-xs font-bold text-gray-800">已成功识别看护设备</p>
                                    <p className="text-[10px] text-gray-400">{pairedDevice} (SN: PET78281AF)</p>
                                </div>
                            </div>

                            <div className="bg-orange-50/50 border border-orange-100 p-3 rounded-xl">
                                <p className="text-[10px] text-orange-800 leading-relaxed">
                                    <b>第二步：网络设置</b> — 请填写下方 Wi-Fi 信息。稍后 App 将展示一个联网配置二维码，供看护仪镜头扫描以使其连网。
                                </p>
                            </div>

                            <div>
                                <h4 className="text-[11px] font-bold text-gray-600 mb-2">选择设备需要连接的 WiFi (必须为 2.4GHz)：</h4>
                                <div className="space-y-2">
                                    {WIFI_LIST.map(wifi => (
                                        <button 
                                            key={wifi}
                                            type="button"
                                            onClick={() => setSelectedWifi(wifi)}
                                            className={`w-full p-3 rounded-xl border text-xs font-semibold text-left flex items-center justify-between transition-all ${selectedWifi === wifi ? 'border-orange-500 bg-orange-50 text-orange-700' : 'border-gray-100 bg-white hover:border-gray-300'}`}
                                        >
                                            <div className="flex items-center gap-2">
                                                <Wifi size={14} className={selectedWifi === wifi ? 'text-orange-500' : 'text-gray-400'} />
                                                <span>{wifi}</span>
                                            </div>
                                            {selectedWifi === wifi && <Check size={14} />}
                                        </button>
                                    ))}
                                </div>
                            </div>

                            <div className="bg-white p-3 rounded-xl border border-gray-100 shadow-xs flex items-center gap-3">
                                <Lock size={16} className="text-gray-400" />
                                <input 
                                    type="password"
                                    value={wifiPassword}
                                    onChange={(e) => setWifiPassword(e.target.value)}
                                    placeholder="输入该 WiFi 联网密码"
                                    className="bg-transparent text-xs w-full outline-none"
                                />
                            </div>

                            <button 
                                onClick={() => {
                                    if (!wifiPassword) {
                                        showToastMsg('请输入 Wi-Fi 密码以生成二维码');
                                        return;
                                    }
                                    setPairingStage('displayAppQr');
                                }}
                                className="w-full bg-orange-500 text-white font-bold py-3.5 rounded-2xl text-xs shadow-lg mt-auto hover:bg-orange-600 transition-colors flex items-center justify-center gap-1"
                            >
                                生成联网二维码 <ChevronRight size={14} />
                            </button>
                        </div>
                    )}

                    {pairingStage === 'displayAppQr' && (
                        <div className="flex-1 flex flex-col items-center justify-between py-2 animate-fade-in">
                            <div className="text-center w-full">
                                <h3 className="font-bold text-gray-900 text-sm">第三步：看护仪镜头扫码联网</h3>
                                <p className="text-[11px] text-gray-500 mt-1 max-w-xs mx-auto leading-relaxed">
                                    请把手机屏幕展示给派爪看护设备镜头（保持 15-20 厘米距离），设备检测到后会自动获取 Wi-Fi 凭证联网。
                                </p>
                            </div>

                            {/* Premium generated QR Code card with sweep effect */}
                            <div className="relative p-5 bg-white rounded-3xl shadow-xl border border-gray-100 my-4 flex flex-col items-center">
                                {/* Sweep animation lines on QR code container to represent scanning */}
                                <div className="absolute inset-0 rounded-3xl overflow-hidden pointer-events-none">
                                    <div className="animate-scan-line-green" />
                                </div>

                                {/* Custom generated QR code vector mockup */}
                                <div className="relative w-48 h-48 bg-gray-50 p-2 rounded-2xl border border-gray-200 flex items-center justify-center overflow-hidden">
                                    {/* Grid dots simulating dynamic pixel QR */}
                                    <div className="absolute inset-2 grid grid-cols-12 grid-rows-12 gap-0.5 opacity-90">
                                        {/* Row 1 */}
                                        <div className="bg-gray-900 rounded-xs col-span-3 row-span-3"></div>
                                        <div className="col-span-1"></div>
                                        <div className="bg-gray-900 rounded-xs col-span-1"></div>
                                        <div className="bg-gray-900 rounded-xs col-span-2"></div>
                                        <div className="col-span-1"></div>
                                        <div className="bg-gray-900 rounded-xs col-span-3 row-span-3"></div>
                                        {/* Row 4 */}
                                        <div className="bg-gray-900 rounded-xs col-span-1"></div>
                                        <div className="bg-gray-900 rounded-xs col-span-2"></div>
                                        <div className="bg-gray-900 rounded-xs col-span-3"></div>
                                        <div className="bg-gray-900 rounded-xs col-span-1"></div>
                                        <div className="bg-gray-900 rounded-xs col-span-2"></div>
                                        {/* Row 5 */}
                                        <div className="bg-gray-900 rounded-xs col-span-4"></div>
                                        <div className="bg-gray-900 rounded-xs col-span-1"></div>
                                        <div className="bg-gray-900 rounded-xs col-span-3"></div>
                                        <div className="bg-gray-900 rounded-xs col-span-2"></div>
                                        {/* Row 6 */}
                                        <div className="bg-gray-900 rounded-xs col-span-2"></div>
                                        <div className="bg-gray-900 rounded-xs col-span-3"></div>
                                        <div className="bg-gray-900 rounded-xs col-span-4"></div>
                                        <div className="bg-gray-900 rounded-xs col-span-1"></div>
                                        {/* Row 9 */}
                                        <div className="bg-gray-900 rounded-xs col-span-3 row-span-3"></div>
                                        <div className="col-span-1"></div>
                                        <div className="bg-gray-900 rounded-xs col-span-2"></div>
                                        <div className="bg-gray-900 rounded-xs col-span-1"></div>
                                        <div className="bg-gray-900 rounded-xs col-span-1"></div>
                                        {/* Row 12 */}
                                        <div className="bg-gray-900 rounded-xs col-span-1"></div>
                                        <div className="bg-gray-900 rounded-xs col-span-3"></div>
                                        <div className="bg-gray-900 rounded-xs col-span-2"></div>
                                    </div>

                                    {/* Central App icon frame */}
                                    <div className="z-10 w-11 h-11 rounded-full bg-white border-2 border-orange-500 shadow-md flex items-center justify-center overflow-hidden">
                                        <Sparkles size={16} className="text-orange-500 animate-pulse" />
                                    </div>
                                </div>

                                <div className="mt-3 px-3 py-1 bg-orange-50 rounded-full border border-orange-100 flex items-center gap-1 text-[10px] text-orange-600 font-extrabold">
                                    <Wifi size={10} />
                                    <span>配网中: {selectedWifi}</span>
                                </div>
                            </div>

                            <div className="w-full space-y-2">
                                <button 
                                    onClick={() => {
                                        setPairingStage('connecting');
                                        setConnectingProgress(0);
                                    }}
                                    className="w-full bg-green-500 text-white font-bold py-3.5 rounded-2xl text-xs shadow-lg hover:bg-green-600 transition-colors flex items-center justify-center gap-1.5 animate-bounce"
                                >
                                    确认听到提示音 <Check size={14} />
                                </button>
                                <p className="text-[10px] text-gray-400 text-center">
                                    看护设备摄像头正在读取，听到提示音后可手动点击或等待 15 秒自动跳转
                                </p>
                            </div>
                        </div>
                    )}

                    {pairingStage === 'connecting' && (
                        <div className="flex-1 flex flex-col items-center justify-center py-8">
                            <div className="w-24 h-24 mb-6 relative flex items-center justify-center">
                                <Loader2 size={48} className="text-orange-500 animate-spin" />
                                <span className="absolute text-xs font-extrabold text-orange-600">{connectingProgress}%</span>
                            </div>
                            <h3 className="font-bold text-gray-800 text-sm">正在向设备下发配置参数并联通云端...</h3>
                        </div>
                    )}

                    {pairingStage === 'success' && (
                        <div className="flex-1 flex flex-col items-center justify-center py-8 animate-fade-in">
                            <div className="bg-green-100 p-5 rounded-full text-green-600 mb-6 border-4 border-green-50 shadow-inner">
                                <Wifi size={36} />
                            </div>
                            <h3 className="font-bold text-gray-900 text-sm">恭喜！设备联网激活成功</h3>
                            <p className="text-xs text-gray-400 mt-1 text-center max-w-xs">设备状态：<b>在线</b> | 云存储：已开启配对</p>
                            
                            <button 
                                onClick={() => setViewState('stepPet')}
                                className="w-full mt-10 bg-orange-500 text-white font-bold py-3.5 rounded-2xl text-xs shadow-lg active:scale-95 hover:bg-orange-600 flex items-center justify-center gap-1"
                            >
                                下一步：设定您的爱宠档案 <ChevronRight size={14} />
                            </button>
                        </div>
                    )}
                </div>
            )}


            {/* ==================================================== */}
            {/* 5. STEP 2: PET PROFILE FORM WITH TAGS (宠物档案录入)    */}
            {/* ==================================================== */}
            {viewState === 'stepPet' && (
                <div className="px-5 flex flex-col flex-1 pt-4 animate-fade-in">
                    
                    {/* Cute design banner describing onboarding status */}
                    <div className="mb-4 bg-orange-50/60 border border-orange-100 p-3 rounded-2xl flex items-center justify-between text-[11px] text-orange-900 leading-relaxed">
                        <div className="flex gap-2 items-center">
                            <span className="text-xs bg-orange-500 text-white w-5 h-5 rounded-full flex-shrink-0 flex items-center justify-center font-bold">2</span>
                            <span className="font-extrabold text-orange-950">建立爱宠云端看护档案</span>
                        </div>
                        <span className="text-[10px] text-gray-400 font-bold">步骤 2/3</span>
                    </div>

                    {/* One-click Autofill Demo Option */}
                    <button
                        onClick={handleAutofillDemoPets}
                        type="button"
                        className="mb-4 w-full py-3 px-4 bg-gradient-to-r from-amber-500 via-orange-500 to-red-500 hover:from-amber-600 hover:to-red-600 text-white rounded-2xl text-xs font-black shadow-md shadow-orange-100 flex items-center justify-center gap-2 transition-all active:scale-[0.98] border border-orange-200"
                    >
                        <Sparkles size={14} className="text-white animate-pulse" />
                        一键快速填充演示档案 (栗子与奶油)
                    </button>

                    {/* Added Pets Card list for Multi-Pet Household */}
                    {addedPets.length > 0 && (
                        <div className="mb-4 bg-orange-50/35 border border-dashed border-orange-200 p-3.5 rounded-2xl animate-fade-in">
                            <h4 className="text-[10px] font-black text-orange-900 uppercase tracking-widest mb-2 flex items-center justify-between">
                                <span>🐾 已录入看护档案的宠物 ({addedPets.length})：</span>
                                <span className="text-orange-500 font-bold normal-case text-[9px]">多宠巡视模式已激活</span>
                            </h4>
                            <div className="flex flex-col gap-2">
                                {addedPets.map((pet, idx) => (
                                    <div key={idx} className="bg-white px-3 py-2 rounded-xl border border-gray-100 flex items-center justify-between shadow-xs">
                                        <div className="flex items-center gap-2.5">
                                            <div className="w-8 h-8 rounded-full bg-orange-100 flex items-center justify-center overflow-hidden font-black text-orange-600 text-xs shadow-inner">
                                                {pet.avatarUrl ? (
                                                    <img src={pet.avatarUrl} alt={pet.name} className="w-full h-full object-cover" referrerPolicy="no-referrer" />
                                                ) : (
                                                    pet.name.substring(0, 1)
                                                )}
                                            </div>
                                            <div>
                                                <div className="flex items-center gap-1.5">
                                                    <span className="font-extrabold text-xs text-gray-800">{pet.name}</span>
                                                    <span className="text-[8px] bg-amber-50 text-amber-600 border border-amber-100 px-1 py-0.2 rounded font-bold">{pet.type}</span>
                                                </div>
                                                <p className="text-[9px] text-gray-400 mt-0.5 font-medium">体重: {pet.weight} | AI 档案就绪</p>
                                            </div>
                                        </div>
                                        
                                        <button 
                                            type="button"
                                            onClick={() => {
                                                setAddedPets(prev => prev.filter((_, i) => i !== idx));
                                                showToastMsg(`已移除宠物：${pet.name}`);
                                            }}
                                            className="w-6 h-6 rounded-full hover:bg-red-50 text-gray-400 hover:text-red-500 flex items-center justify-center transition-colors text-xs font-bold"
                                        >
                                            ×
                                        </button>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Cute Visual Header & Circle camera avatar based on FIG 1 */}
                    <div className="flex flex-col items-center justify-center pb-2 pt-1">
                        {/* Title header */}
                        <div className="w-full flex justify-between items-center px-1 mb-4">
                            <button 
                                type="button"
                                onClick={() => setViewState('stepDevice')}
                                className="w-8 h-8 rounded-full bg-white flex items-center justify-center border border-gray-100 cursor-pointer shadow-xs hover:bg-orange-50/50"
                            >
                                <ArrowLeft size={14} className="text-gray-500" />
                            </button>
                            <h3 className="font-black text-orange-950 text-sm tracking-widest">萌宠信息</h3>
                            <div className="w-8 h-8" />
                        </div>

                        {/* Large Circle avatar styled exactly like Fig 1 */}
                        <div className="relative group mb-3">
                            <div className="border-[3.5px] border-orange-400 p-1.5 rounded-full bg-white shadow-sm transition-transform duration-300 hover:rotate-6">
                                <div className="w-24 h-24 rounded-full overflow-hidden bg-orange-50/10 flex items-center justify-center shadow-inner relative">
                                    {petImage ? (
                                        <img src={petImage} alt="Avatar" className="w-full h-full object-cover" referrerPolicy="no-referrer" />
                                    ) : (
                                        <div className="flex flex-col items-center text-orange-300/80">
                                            <span className="text-xs font-bold text-orange-400">选择照片</span>
                                        </div>
                                    )}
                                </div>
                            </div>
                            {/* Camera overlay button */}
                            <div 
                                onClick={() => fileInputRef.current?.click()}
                                className="absolute bottom-1 right-1 w-8 h-8 rounded-full bg-orange-500 border-2 border-white flex items-center justify-center text-white shadow-md cursor-pointer hover:bg-orange-600 transition-transform active:scale-90"
                            >
                                <Camera size={14} className="text-white" />
                            </div>
                            <input 
                                type="file" 
                                ref={fileInputRef}
                                onChange={handleFileChange}
                                accept="image/*"
                                className="hidden"
                            />
                        </div>
                        {/* Interactive hand-styled curved helper tag */}
                        <div className="border border-dashed border-orange-300/60 bg-orange-50/50 text-orange-600 px-4 py-0.5 rounded-full text-[10px] text-center font-black tracking-wider mb-5">
                            点击更换头像
                        </div>
                        
                        {/* Centered Name Input matching FIG 1 */}
                        <div className="w-full max-w-sm px-1 mb-5">
                            <input 
                                type="text"
                                value={petName}
                                onChange={(e) => setPetName(e.target.value)}
                                placeholder="请输入宠物昵称"
                                className="w-full bg-orange-50/20 border-[1.5px] border-orange-200 rounded-2xl py-3 px-4 text-xs font-bold placeholder:text-orange-950/40 text-orange-950 text-center outline-none focus:ring-2 focus:ring-orange-400 focus:bg-white shadow-inner transition-all"
                            />
                        </div>
                    </div>

                    {/* FIG 1 Row design list: 类型, 品种, 宠物性别, 出生时间, 到家时间, 是否绝育 */}
                    <div className="space-y-3">
                        {/* 1. Row: 类型 */}
                        <div 
                            onClick={() => {
                                setTempType(petType || 'cat');
                                setActiveBottomSheet('petType');
                            }}
                            className="bg-orange-50/25 border border-orange-100/70 rounded-xl px-4 py-3.5 flex items-center justify-between cursor-pointer hover:bg-orange-50/50 active:scale-[0.99] transition-all duration-200"
                        >
                            <span className="text-xs font-bold text-orange-950">类型</span>
                            <div className="flex items-center gap-1.5 text-right">
                                <span className={`text-xs font-bold flex items-center gap-1 ${petType ? 'text-orange-600' : 'text-orange-900/40'}`}>
                                    {petType === 'cat' ? '猫咪' : petType === 'dog' ? '狗狗' : petType === 'other' ? '其他陪护' : '请先选择宠物类型'}
                                </span>
                                <span className="text-[9px] text-orange-400/80">▼</span>
                            </div>
                        </div>

                        {/* 2. Row: 品种 */}
                        <div className="bg-orange-50/25 border border-orange-100/70 rounded-xl px-4 py-3 flex flex-col gap-1">
                            <span className="text-xs font-bold text-orange-950">品种</span>
                            <input 
                                type="text"
                                value={selectedBreed}
                                onChange={(e) => setSelectedBreed(e.target.value)}
                                placeholder="请输入宠物品种 (如：金渐层、金毛、哈士奇)"
                                className="w-full bg-transparent text-xs font-bold text-orange-700 outline-none placeholder:text-orange-950/30"
                            />
                        </div>

                        {/* 3. Row: 宠物性别 */}
                        <div 
                            onClick={() => {
                                setTempGender(petGender);
                                setActiveBottomSheet('gender');
                            }}
                            className="bg-orange-50/25 border border-orange-100/70 rounded-xl px-4 py-3.5 flex items-center justify-between cursor-pointer hover:bg-orange-50/50 active:scale-[0.99] transition-all duration-200"
                        >
                            <span className="text-xs font-bold text-orange-950">宠物性别</span>
                            <div className="flex items-center gap-1.5 text-right">
                                <span className="text-xs font-bold text-orange-700 flex items-center gap-1">
                                    {petGender === 'GG (男生)' ? 'GG' : petGender === 'MM (女生)' ? 'MM' : '未指定'}
                                </span>
                                <span className="text-[9px] text-orange-400/80">▼</span>
                            </div>
                        </div>

                        {/* 4. Row: 宠物体重 */}
                        <div className="bg-orange-50/25 border border-orange-100/70 rounded-xl px-4 py-3 flex flex-col gap-1">
                            <span className="text-xs font-bold text-orange-950">宠物体重</span>
                            <div className="flex items-center gap-1">
                                <input 
                                    type="text"
                                    value={petWeight}
                                    onChange={(e) => setPetWeight(e.target.value)}
                                    placeholder="输入宠物重量 (例如：4.5)"
                                    className="w-full bg-transparent text-xs font-bold text-orange-700 outline-none placeholder:text-orange-950/30 font-mono"
                                />
                                <span className="text-xs font-black text-orange-700 select-none">kg</span>
                            </div>
                        </div>

                        {/* 5. Row: 宠物毛色 */}
                        <div className="bg-orange-50/25 border border-orange-100/70 rounded-xl px-4 py-3 flex flex-col gap-1">
                            <span className="text-xs font-bold text-orange-950">宠物毛色</span>
                            <input 
                                type="text"
                                value={petCoatColor}
                                onChange={(e) => setPetCoatColor(e.target.value)}
                                placeholder="输入宠物的毛色 (如：白底橘斑、纯黑色)"
                                className="w-full bg-transparent text-xs font-bold text-orange-700 outline-none placeholder:text-orange-950/30"
                            />
                        </div>

                        {/* 6. Row: 出生时间 */}
                        <div 
                            onClick={() => {
                                setTempBYear(birthYear);
                                setTempBMonth(birthMonth);
                                setTempBDay(birthDay);
                                setActiveBottomSheet('birthDate');
                            }}
                            className="bg-orange-50/25 border border-orange-100/70 rounded-xl px-4 py-3.5 flex items-center justify-between cursor-pointer hover:bg-orange-50/50 active:scale-[0.99] transition-all duration-200"
                        >
                            <span className="text-xs font-bold text-orange-950">出生时间</span>
                            <div className="flex items-center gap-1.5 text-right">
                                <span className="text-xs font-bold text-orange-700">{`${birthYear}年${birthMonth}月${birthDay}日`}</span>
                                <span className="text-[9px] text-orange-400/80">▼</span>
                            </div>
                        </div>

                        {/* 7. Row: 是否绝育 */}
                        <div 
                            onClick={() => {
                                setTempSpayed(isSpayed);
                                setActiveBottomSheet('isSpayed');
                            }}
                            className="bg-orange-50/25 border border-orange-100/70 rounded-xl px-4 py-3.5 flex items-center justify-between cursor-pointer hover:bg-orange-50/50 active:scale-[0.99] transition-all duration-200"
                        >
                            <span className="text-xs font-bold text-orange-950">是否绝育</span>
                            <div className="flex items-center gap-1.5 text-right">
                                <span className="text-xs font-bold text-orange-700">{isSpayed}</span>
                                <span className="text-[9px] text-orange-400/80">▼</span>
                            </div>
                        </div>

                        {/* 8. Row: 特征描述 */}
                        <div className="bg-orange-50/25 border border-orange-100/70 rounded-xl px-4 py-3 flex flex-col gap-1.5">
                            <span className="text-xs font-bold text-orange-950">特征描述</span>
                            <textarea
                                value={petFeatures}
                                onChange={(e) => setPetFeatures(e.target.value)}
                                placeholder="请输入外形及行为习惯特征"
                                rows={2.5}
                                className="w-full bg-transparent text-xs font-bold text-orange-700 outline-none placeholder:text-orange-950/30 resize-none leading-relaxed"
                            />
                        </div>
                    </div>

                    {/* PET VISUAL ALIGNMENT AND 3D MULTI-ANGLE PORTFOLIO (NEWLY DEVELOPED) */}
                    <div className="bg-white p-4 rounded-2xl border border-gray-150 shadow-xs space-y-3.5 mt-4">
                        <div className="flex items-start justify-between gap-4">
                            <div>
                                <div className="flex items-center gap-1.5">
                                    <span className="bg-orange-50 text-orange-500 text-[9px] font-black px-2 py-0.5 rounded tracking-wide">AI 视觉对齐</span>
                                    <h4 className="text-xs font-black text-gray-800">AI 多角度素材库</h4>
                                </div>
                                <p className="text-[10px] text-gray-400 mt-1 leading-normal">
                                    {skipMultiAngle 
                                        ? '您已跳过该步骤。后续需要时，您可以再次点击“开启设置”上传照片来帮助 AI 精准识别。'
                                        : '上传宠物多角度日常照片，可以有效提取宠物独特的形象特征信息（如五官轮廓、毛色细节、身形特征等），让 AI 识别分析宠物的行为和身份探测更精准。'
                                    }
                                </p>
                            </div>
                            <button
                                type="button"
                                onClick={() => {
                                    setSkipMultiAngle(!skipMultiAngle);
                                    if (!skipMultiAngle) {
                                        showToastMsg('已跳过 AI 多角度素材库设置');
                                    } else {
                                        showToastMsg('已重新启用 AI 多角度素材库');
                                    }
                                }}
                                className={`px-2.5 py-1 text-[10px] font-extrabold rounded-lg border transition-all flex-shrink-0 ${
                                    skipMultiAngle 
                                        ? 'bg-gray-100 hover:bg-gray-200 text-gray-600 border-gray-200' 
                                        : 'bg-orange-50/50 hover:bg-orange-100/55 text-orange-600 border-orange-200/50 hover:shadow-xs active:scale-[0.98]'
                                }`}
                            >
                                {skipMultiAngle ? '开启设置' : '跳过此设置'}
                            </button>
                        </div>

                        {/* Angle interactive slots */}
                        <div className={`grid grid-cols-4 gap-2 transition-all duration-300 ${skipMultiAngle ? 'opacity-35 pointer-events-none select-none' : ''}`}>
                            {[
                                { id: 'front', label: '正脸' },
                                { id: 'left', label: '左侧' },
                                { id: 'right', label: '右侧' },
                                { id: 'back', label: '背部' }
                            ].map(angle => {
                                const currentImg = angleImages[angle.id as keyof typeof angleImages];
                                return (
                                    <div 
                                        key={angle.id}
                                        onClick={() => {
                                            if (skipMultiAngle) return;
                                            const input = document.createElement('input');
                                            input.type = 'file';
                                            input.accept = 'image/*';
                                            input.onchange = (e: any) => {
                                                const file = e.target.files?.[0];
                                                if (file) {
                                                    const reader = new FileReader();
                                                    reader.onload = (event) => {
                                                        setAngleImages(prev => ({
                                                            ...prev,
                                                            [angle.id]: event.target?.result as string
                                                        }));
                                                        showToastMsg(`✅ 已添加 ${angle.label} 照片`);
                                                    };
                                                    reader.readAsDataURL(file);
                                                }
                                            };
                                            input.click();
                                        }}
                                        className={`border-[1.5px] border-dashed rounded-xl p-2 flex flex-col items-center justify-center text-center cursor-pointer transition-all aspect-square relative overflow-hidden ${
                                            currentImg 
                                                ? 'border-green-300 bg-green-50/25 hover:border-green-400' 
                                                : 'border-orange-200/80 bg-orange-50/20 hover:border-orange-300 hover:bg-orange-5/35'
                                        }`}
                                    >
                                        {currentImg ? (
                                            <>
                                                <img src={currentImg} alt={angle.label} className="w-full h-full object-cover rounded-lg" referrerPolicy="no-referrer" />
                                                <div className="absolute inset-x-0 bottom-0 bg-black/60 text-white text-[8px] py-0.5 truncate text-center font-bold">
                                                    已采集
                                                </div>
                                            </>
                                        ) : (
                                            <div className="flex flex-col items-center justify-center h-full">
                                                <Camera size={14} className="text-orange-500/80 mb-1" />
                                                <span className="text-[10px] font-bold text-orange-950">{angle.label}</span>
                                            </div>
                                        )}

                                        {currentImg && (
                                            <span 
                                                onClick={(e) => {
                                                    e.stopPropagation();
                                                    if (skipMultiAngle) return;
                                                    setAngleImages(prev => {
                                                        const copy = { ...prev };
                                                        delete copy[angle.id as keyof typeof angleImages];
                                                        return copy;
                                                    });
                                                    showToastMsg('已删除此图层图片');
                                                }}
                                                className="absolute top-0.5 right-0.5 w-4 h-4 rounded-full bg-red-100 text-red-600 flex items-center justify-center text-[9px] font-black shadow-sm"
                                            >
                                                ×
                                            </span>
                                        )}
                                    </div>
                                );
                            })}
                        </div>

                        {/* Simplified Completeness Panel */}
                        <div className="bg-orange-50/15 p-3.5 rounded-2xl border border-orange-100 space-y-2">
                            <div className="flex items-center justify-between">
                                <span className="text-xs font-bold text-orange-700 flex items-center gap-1.5">
                                    图像信息完善度
                                </span>
                                <span className={`text-xs font-black ${
                                    skipMultiAngle
                                        ? 'text-gray-400'
                                        : Object.keys(angleImages).length === 0 
                                            ? 'text-gray-400' 
                                            : Object.keys(angleImages).length === 4 
                                                ? 'text-green-600' 
                                                : 'text-orange-500'
                                }`}>
                                    {skipMultiAngle ? '已跳过' : (Object.keys(angleImages).length === 0 ? '0%' : Object.keys(angleImages).length === 1 ? '25%' : Object.keys(angleImages).length === 2 ? '50%' : Object.keys(angleImages).length === 3 ? '75%' : '100%')}
                                </span>
                            </div>
                            <div className="w-full h-2 bg-gray-100 rounded-full overflow-hidden">
                                <div 
                                    className={`h-full transition-all duration-300 rounded-full ${skipMultiAngle ? 'bg-gray-300' : 'bg-orange-400'}`}
                                    style={{ width: `${skipMultiAngle ? 100 : (Object.keys(angleImages).length === 0 ? 0 : Object.keys(angleImages).length === 1 ? 25 : Object.keys(angleImages).length === 2 ? 50 : Object.keys(angleImages).length === 3 ? 75 : 100)}%` }}
                                />
                            </div>
                            <p className="text-[10px] text-orange-700/90 font-medium leading-normal">
                                {skipMultiAngle 
                                    ? '友情提醒：跳过本步骤不影响设备正常联网和基础监护功能，您可直接点击下方“保存”。'
                                    : Object.keys(angleImages).length === 4 
                                        ? '已录入全部 4 个视角的关键图像特征，将获得最佳识别匹配效果。' 
                                        : '提示：增加上传不同视角的照片将更利于 AI 更加准确地辨识宠物实时的状态特征。'}
                            </p>
                        </div>
                    </div>

                    {/* BUTTON ACTIONS FOR MULTI-PET FAMILIES */}
                    <div className="w-full flex flex-col gap-2.5 px-1 mt-6 mb-8">
                        <button 
                            type="button"
                            onClick={handleSaveAndContinueNext}
                            className="w-full py-3.5 bg-orange-50 hover:bg-orange-100/80 text-orange-700 font-extrabold rounded-2xl text-xs active:scale-[0.98] transition-all flex items-center justify-center gap-1.5 border border-orange-200/45 shadow-xs"
                        >
                            <Sparkles size={13} className="text-orange-600 animate-pulse" />
                            <span>保存当前，并设置下一个宠物基础信息</span>
                        </button>
                        
                        <button 
                            type="button"
                            onClick={handlePetEntrySubmit}
                            className="w-full py-3.5 bg-orange-500 hover:bg-orange-600 text-white font-extrabold rounded-2xl text-xs shadow-lg shadow-orange-100 active:scale-[0.98] transition-all text-center flex items-center justify-center gap-1"
                        >
                            <span>{addedPets.length > 0 ? `全部保存并进入下一步 (已录入 ${addedPets.length + (petName.trim() ? 1 : 0)} 只)` : '保存并进入下一步：授权设置'}</span>
                            <ChevronRight size={14} />
                        </button>
                    </div>
                </div>
            )}




            {/* ==================================================== */}
            {/* 6. STEP 3: NATIVE PERMISSIONS AUTHORIZATION (授权环境) */}
            {/* ==================================================== */}
            {viewState === 'stepPermissions' && (
                <div className="px-6 flex flex-col flex-1 pt-8 animate-fade-in">
                    <div className="mb-6 flex items-center justify-between">
                        <div className="flex gap-2 items-center">
                            <span className="text-xs bg-orange-500 text-white w-5 h-5 rounded-full flex items-center justify-center font-bold">3</span>
                            <span className="text-xs font-bold text-gray-700">看护核心权限授权授权</span>
                        </div>
                        <span className="text-[10px] text-gray-400">步骤 3/3</span>
                    </div>

                    <div className="text-center mb-8">
                        <div className="inline-flex bg-indigo-50 p-4 rounded-full text-indigo-600 mb-3">
                            <Shield size={36} />
                        </div>
                        <h3 className="font-extrabold text-gray-800 text-sm">让 AI 管家更好地守护安全</h3>
                        <p className="text-xs text-gray-400 mt-1">我们需要您的系统授权，以便为您提供不间断的智能分析服务。</p>
                    </div>

                    {/* Permissions checklist cards */}
                    <div className="space-y-4 flex-1">
                        
                        {/* Mic */}
                        <div className="bg-white p-4 rounded-2xl border border-gray-100 shadow-sm flex items-center justify-between transition-colors hover:border-gray-200">
                            <div className="flex gap-3 items-center min-w-0">
                                <div className={`p-2 rounded-xl flex-shrink-0 ${permMic === 'granted' ? 'bg-green-50 text-green-600' : 'bg-orange-50 text-orange-600'}`}>
                                    <Mic size={18} />
                                </div>
                                <div className="min-w-0">
                                    <h4 className="font-bold text-gray-800 text-xs">麦克风双向声音监控</h4>
                                </div>
                            </div>
                            <button 
                                onClick={() => requestPermission('mic')}
                                disabled={permMic === 'granted'}
                                className={`px-4 py-1.5 rounded-full text-[10px] font-bold flex-shrink-0 transition-colors ${permMic === 'granted' ? 'bg-green-100 text-green-600 cursor-not-allowed' : 'bg-gray-100 hover:bg-gray-200 text-gray-700'}`}
                            >
                                {permMic === 'granted' ? '已授权✓' : '去开启'}
                            </button>
                        </div>

                        {/* Photo Album */}
                        <div className="bg-white p-4 rounded-2xl border border-gray-100 shadow-sm flex items-center justify-between transition-colors hover:border-gray-200">
                            <div className="flex gap-3 items-center min-w-0">
                                <div className={`p-2 rounded-xl flex-shrink-0 ${permPhoto === 'granted' ? 'bg-green-50 text-green-600' : 'bg-orange-50 text-orange-600'}`}>
                                    <Camera size={18} />
                                </div>
                                <div className="min-w-0">
                                    <h4 className="font-bold text-gray-800 text-xs">相册写入与读取</h4>
                                </div>
                            </div>
                            <button 
                                onClick={() => requestPermission('photo')}
                                disabled={permPhoto === 'granted'}
                                className={`px-4 py-1.5 rounded-full text-[10px] font-bold flex-shrink-0 transition-colors ${permPhoto === 'granted' ? 'bg-green-100 text-green-600 cursor-not-allowed' : 'bg-gray-100 hover:bg-gray-200 text-gray-700'}`}
                            >
                                {permPhoto === 'granted' ? '已授权✓' : '去开启'}
                            </button>
                        </div>

                        {/* Notification Push */}
                        <div className="bg-white p-4 rounded-2xl border border-gray-100 shadow-sm flex items-center justify-between transition-colors hover:border-gray-200">
                            <div className="flex gap-3 items-center min-w-0">
                                <div className={`p-2 rounded-xl flex-shrink-0 ${permBell === 'granted' ? 'bg-green-50 text-green-600' : 'bg-orange-50 text-orange-600'}`}>
                                    <Bell size={18} />
                                </div>
                                <div className="min-w-0">
                                    <h4 className="font-bold text-gray-800 text-xs">消息强推送权限</h4>
                                </div>
                            </div>
                            <button 
                                onClick={() => requestPermission('bell')}
                                disabled={permBell === 'granted'}
                                className={`px-4 py-1.5 rounded-full text-[10px] font-bold flex-shrink-0 transition-colors ${permBell === 'granted' ? 'bg-green-100 text-green-600 cursor-not-allowed' : 'bg-gray-100 hover:bg-gray-200 text-gray-700'}`}
                            >
                                {permBell === 'granted' ? '已授权✓' : '去开启'}
                            </button>
                        </div>
                    </div>

                    <button 
                        onClick={handleAllFinished}
                        className="w-full bg-orange-500 text-white font-bold py-3.5 rounded-2xl text-xs shadow-lg active:scale-95 text-center mt-6"
                    >
                        全部完成，开启守护之旅！
                    </button>
                </div>
            )}

            {/* FIG 2 BOTTOM PICKER SHEET POPUP */}
            {activeBottomSheet && (
                <div className="fixed inset-0 bg-black/60 backdrop-blur-xs z-[250] flex items-end justify-center animate-fade-in animate-duration-150">
                    <div className="bg-white rounded-t-3xl w-full max-w-md shadow-2xl p-5 flex flex-col space-y-4 animate-slide-up max-h-[85vh]">
                        {/* Title bar / Controls */}
                        <div className="flex justify-between items-center pb-2.5 border-b border-gray-150 flex-shrink-0">
                            <button 
                                type="button"
                                onClick={() => setActiveBottomSheet(null)}
                                className="text-gray-500 hover:text-gray-900 text-xs font-semibold px-2 py-1"
                            >
                                取消
                            </button>
                            <span className="font-extrabold text-orange-950 text-xs">
                                {activeBottomSheet === 'gender' && '选择宠物性别'}
                                {activeBottomSheet === 'status' && '选择宠物生活状态'}
                                {activeBottomSheet === 'isSpayed' && '绝育选项'}
                                {activeBottomSheet === 'birthDate' && '选择出生日期 (年-月-日)'}
                                {activeBottomSheet === 'petType' && '选择宠物类型'}
                            </span>
                            <button 
                                type="button"
                                onClick={() => {
                                    // Save temporary variables back into actual state variables
                                    if (activeBottomSheet === 'gender') {
                                        setPetGender(tempGender);
                                    } else if (activeBottomSheet === 'status') {
                                        setPetState(tempStateVal);
                                    } else if (activeBottomSheet === 'isSpayed') {
                                        setIsSpayed(tempSpayed);
                                    } else if (activeBottomSheet === 'birthDate') {
                                        setBirthYear(tempBYear);
                                        setBirthMonth(tempBMonth);
                                        setBirthDay(tempBDay);
                                    } else if (activeBottomSheet === 'petType') {
                                        if (tempType !== petType) {
                                            setPetType(tempType as 'cat' | 'dog' | 'other' || '');
                                            setSelectedBreed('');
                                            setCustomBreed('');
                                        }
                                    }
                                    setActiveBottomSheet(null);
                                    showToastMsg('💾 选项保存成功');
                                }}
                                className="bg-orange-500 hover:bg-orange-600 text-white px-4 py-1 rounded-full text-xs font-bold transition-all"
                            >
                                确定
                            </button>
                        </div>

                        {/* Content rollers/options */}
                        <div className="flex-1 overflow-y-auto py-2">
                            {/* 0. PET TYPE OPTIONS */}
                            {activeBottomSheet === 'petType' && (
                                <div className="space-y-2">
                                    {([
                                        { key: 'cat', label: '猫咪' },
                                        { key: 'dog', label: '狗狗' },
                                        { key: 'other', label: '其他陪护' }
                                    ] as const).map(option => (
                                        <button
                                            key={option.key}
                                            type="button"
                                            onClick={() => setTempType(option.key)}
                                            className={`w-full p-4 rounded-2xl border text-xs font-bold text-center transition-all ${
                                                tempType === option.key 
                                                    ? 'bg-orange-50 border-orange-300 text-orange-700' 
                                                    : 'bg-gray-50 border-gray-150 text-gray-700 hover:bg-gray-100'
                                            }`}
                                        >
                                            {option.label}
                                        </button>
                                    ))}
                                </div>
                            )}

                            {/* 1. GENDER OPTIONS */}
                            {activeBottomSheet === 'gender' && (
                                <div className="space-y-2">
                                    {(['GG (男生)', 'MM (女生)', '未知'] as const).map(option => (
                                        <button
                                            key={option}
                                            type="button"
                                            onClick={() => setTempGender(option)}
                                            className={`w-full p-4 rounded-2xl border text-xs font-bold text-center transition-all ${
                                                tempGender === option 
                                                    ? 'bg-orange-50 border-orange-300 text-orange-700' 
                                                    : 'bg-gray-50 border-gray-150 text-gray-700 hover:bg-gray-100'
                                            }`}
                                        >
                                            {option === 'GG (男生)' ? 'GG (男生)' : option === 'MM (女生)' ? 'MM (女生)' : '保密 / 未知'}
                                        </button>
                                    ))}
                                </div>
                            )}

                            {/* 2. CHOOSE STATUS */}
                            {activeBottomSheet === 'status' && (
                                <div className="space-y-2">
                                    {(['在身边', '寄养中', '暂离守护', '生病中'] as const).map(option => (
                                        <button
                                            key={option}
                                            type="button"
                                            onClick={() => setTempStateVal(option)}
                                            className={`w-full p-4 rounded-2xl border text-xs font-bold text-center transition-all ${
                                                tempStateVal === option 
                                                    ? 'bg-orange-50 border-orange-300 text-orange-700' 
                                                    : 'bg-gray-50 border-gray-150 text-gray-700 hover:bg-gray-100'
                                            }`}
                                        >
                                            {option === '在身边' ? '在身边陪伴' : option === '寄养中' ? '萌宠学校/寄养中' : option === '暂离守护' ? '暂离远端守护' : '医院看护/生病中'}
                                        </button>
                                    ))}
                                </div>
                            )}

                            {/* 3. CHOOSE IS_SPAYED */}
                            {activeBottomSheet === 'isSpayed' && (
                                <div className="space-y-2">
                                    {(['已绝育', '暂未绝育', '不详'] as const).map(option => (
                                        <button
                                            key={option}
                                            type="button"
                                            onClick={() => setTempSpayed(option)}
                                            className={`w-full p-4 rounded-2xl border text-xs font-bold text-center transition-all ${
                                                tempSpayed === option 
                                                    ? 'bg-orange-50 border-orange-300 text-orange-700' 
                                                    : 'bg-gray-50 border-gray-150 hover:bg-gray-100 text-gray-700'
                                            }`}
                                        >
                                            {option}
                                        </button>
                                    ))}
                                </div>
                            )}

                            {/* 4. BIRTHDATE SCROLLER ROLLER (Fig 2 Wheel design) */}
                            {activeBottomSheet === 'birthDate' && (
                                <div className="space-y-4">
                                    {/* Subtitle helper */}
                                    <span className="text-[10px] text-gray-400 block text-center">快捷点击各列的选项进行即刻设定</span>

                                    {/* 3-Column layout */}
                                    <div className="flex gap-2 bg-gray-50 rounded-2xl p-2 relative border border-gray-200">
                                        {/* Center Highlighting Bar overlay */}
                                        <div className="absolute left-0 right-0 top-[calc(50%-18px)] h-9 bg-orange-500/10 border-y border-orange-200 pointer-events-none" />

                                        {/* Columns: Years */}
                                        <div className="flex-1 h-36 overflow-y-auto scrollbar-hide flex flex-col items-center">
                                            <span className="text-[9px] font-bold text-gray-400 sticky top-0 bg-gray-50/95 py-1 z-10">年</span>
                                            {Array.from({ length: 17 }, (_, i) => String(2010 + i)).map(yr => {
                                                const isSel = tempBYear === yr;
                                                return (
                                                    <button
                                                        key={yr}
                                                        type="button"
                                                        onClick={() => setTempBYear(yr)}
                                                        className={`w-full py-1.5 text-xs font-bold text-center transition-all ${isSel ? 'text-[#ef9f27] scale-110' : 'text-gray-400 hover:text-gray-700'}`}
                                                    >
                                                        {yr}年
                                                    </button>
                                                );
                                            })}
                                        </div>

                                        {/* Columns: Months */}
                                        <div className="flex-1 h-36 overflow-y-auto scrollbar-hide flex flex-col items-center border-x border-gray-200">
                                            <span className="text-[9px] font-bold text-orange-700 sticky top-0 bg-gray-50/95 py-1 z-10">月</span>
                                            {Array.from({ length: 12 }, (_, i) => String(i + 1)).map(mo => {
                                                const isSel = tempBMonth === mo;
                                                return (
                                                    <button
                                                        key={mo}
                                                        type="button"
                                                        onClick={() => setTempBMonth(mo)}
                                                        className={`w-full py-1.5 text-xs font-bold text-orange-700 text-center transition-all ${isSel ? 'text-[#ef9f27] scale-110 font-black' : 'text-gray-400 hover:text-gray-700'}`}
                                                    >
                                                        {mo}月
                                                    </button>
                                                );
                                            })}
                                        </div>

                                        {/* Columns: Days */}
                                        <div className="flex-1 h-36 overflow-y-auto scrollbar-hide flex flex-col items-center">
                                            <span className="text-[9px] font-bold text-gray-400 sticky top-0 bg-gray-50/95 py-1 z-10">日</span>
                                            {Array.from({ length: 31 }, (_, i) => String(i + 1)).map(dy => {
                                                const isSel = tempBDay === dy;
                                                return (
                                                    <button
                                                        key={dy}
                                                        type="button"
                                                        onClick={() => setTempBDay(dy)}
                                                        className={`w-full py-1.5 text-xs font-bold text-center transition-all ${isSel ? 'text-[#ef9f27] scale-110' : 'text-gray-400 hover:text-gray-700'}`}
                                                    >
                                                        {dy}日
                                                    </button>
                                                );
                                            })}
                                        </div>
                                    </div>
                                    
                                    {/* Live output indicator */}
                                    <div className="text-center font-bold text-orange-950 text-[11px] bg-orange-50/30 py-2 rounded-xl border border-orange-100">
                                        当前选取：
                                        <span className="text-orange-600 font-extrabold ml-1">
                                            {`${tempBYear}年 ${tempBMonth}月 ${tempBDay}日`}
                                        </span>
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            )}

        </div>
    );
}
