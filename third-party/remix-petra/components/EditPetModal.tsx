import React from 'react';
import { X, Save } from 'lucide-react';
import { EditFormState } from '../types';

interface EditPetModalProps {
    isOpen: boolean;
    onClose: () => void;
    editForm: EditFormState;
    setEditForm: (form: EditFormState) => void;
    onSave: () => void;
}

const EditPetModal: React.FC<EditPetModalProps> = ({ 
    isOpen, onClose, editForm, setEditForm, onSave 
}) => {
    const fileRef = React.useRef<HTMLInputElement>(null);
    const [isDrag, setIsDrag] = React.useState(false);

    if (!isOpen) return null;

    return (
        <div className="fixed inset-0 z-[80] bg-black/60 backdrop-blur-sm flex items-center justify-center animate-fade-in">
            <div className="bg-white w-[85%] max-w-sm rounded-2xl p-6 shadow-2xl animate-zoom-in">
                <div className="flex justify-between items-center mb-4">
                    <h3 className="text-lg font-bold text-gray-900">编辑信息</h3>
                    <button onClick={onClose} className="text-gray-400 hover:text-gray-600">
                        <X size={20}/>
                    </button>
                </div>
                <div className="space-y-4">
                    {/* Pet Image Upload */}
                    <div className="flex flex-col items-center justify-center space-y-2 pb-2 border-b border-gray-100">
                        <label className="block text-xs font-medium text-gray-500 w-full text-left">爱宠图像</label>
                        <div 
                            onClick={() => fileRef.current?.click()}
                            onDragOver={(e) => { e.preventDefault(); setIsDrag(true); }}
                            onDragLeave={() => setIsDrag(false)}
                            onDrop={(e) => {
                                e.preventDefault();
                                setIsDrag(false);
                                const file = e.dataTransfer.files?.[0];
                                if (file && file.type.startsWith('image/')) {
                                    const r = new FileReader();
                                    r.onload = (ev) => {
                                        setEditForm({ ...editForm, avatarUrl: ev.target?.result as string });
                                    };
                                    r.readAsDataURL(file);
                                }
                            }}
                            className={`relative w-20 h-20 rounded-full border-2 border-dashed flex flex-col items-center justify-center cursor-pointer transition-all ${
                                isDrag 
                                    ? 'border-orange-500 bg-orange-50/50' 
                                    : 'border-gray-205 hover:border-orange-400 bg-gray-50 hover:bg-gray-100/50 shadow-inner'
                            }`}
                        >
                            <input 
                                type="file" 
                                ref={fileRef} 
                                accept="image/*" 
                                className="hidden" 
                                onChange={(e) => {
                                    const file = e.target.files?.[0];
                                    if (file) {
                                        const r = new FileReader();
                                        r.onload = (ev) => {
                                            setEditForm({ ...editForm, avatarUrl: ev.target?.result as string });
                                        };
                                        r.readAsDataURL(file);
                                    }
                                }}
                            />
                            {editForm.avatarUrl ? (
                                <img 
                                    src={editForm.avatarUrl} 
                                    alt="宠物头像" 
                                    className="w-full h-full object-cover rounded-full"
                                    referrerPolicy="no-referrer"
                                />
                            ) : (
                                <div className="text-gray-400 flex flex-col items-center">
                                    <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M23 19a2 2 0 0 1-2 2H3a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h4l2-3h6l2 3h4a2 2 0 0 1 2 2z"></path><circle cx="12" cy="13" r="4"></circle></svg>
                                    <span className="text-[10px] mt-1 font-semibold text-gray-500">点击/拖拽</span>
                                </div>
                            )}
                            
                            {editForm.avatarUrl && (
                                <button
                                    type="button"
                                    onClick={(e) => {
                                        e.stopPropagation();
                                        setEditForm({ ...editForm, avatarUrl: undefined });
                                    }}
                                    className="absolute -right-1 -bottom-1 p-1 bg-red-100 text-red-600 rounded-full hover:bg-red-200 transition-colors shadow-xs border border-white"
                                    title="移除头像"
                                    id="remove-avatar-btn"
                                >
                                    <svg xmlns="http://www.w3.org/2000/svg" width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg>
                                </button>
                            )}
                        </div>
                    </div>

                    <div>
                        <label className="block text-xs font-medium text-gray-500 mb-1">名字</label>
                        <input 
                            type="text" 
                            value={editForm.name} 
                            onChange={(e) => setEditForm({...editForm, name: e.target.value})}
                            className="w-full bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-orange-500/50 transition-all"
                        />
                    </div>
                    <div>
                        <label className="block text-xs font-medium text-gray-500 mb-1">品种</label>
                        <input 
                            type="text" 
                            value={editForm.type} 
                            onChange={(e) => setEditForm({...editForm, type: e.target.value})}
                            className="w-full bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-orange-500/50 transition-all"
                        />
                    </div>
                    <div>
                        <label className="block text-xs font-medium text-gray-500 mb-1">体重</label>
                        <input 
                            type="text" 
                            value={editForm.weight} 
                            onChange={(e) => setEditForm({...editForm, weight: e.target.value})}
                            className="w-full bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-orange-500/50 transition-all"
                        />
                    </div>
                    <div>
                        <label className="block text-xs font-medium text-gray-500 mb-1">外表特征</label>
                        <textarea
                            value={editForm.features}
                            onChange={(e) => setEditForm({...editForm, features: e.target.value})}
                            className="w-full bg-gray-50 border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-orange-500/50 transition-all resize-none h-20"
                            placeholder="例如：毛色、长短毛、花色分布..."
                        />
                    </div>
                </div>
                <div className="mt-6 flex gap-3">
                    <button onClick={onClose} className="flex-1 py-2 text-sm text-gray-600 font-medium bg-gray-100 rounded-full hover:bg-gray-200 transition-colors">
                        取消
                    </button>
                    <button onClick={onSave} className="flex-1 py-2 text-sm text-white font-bold bg-orange-500 rounded-full hover:bg-orange-600 transition-colors shadow-md active:scale-95 flex items-center justify-center gap-1">
                        <Save size={14}/> 保存
                    </button>
                </div>
            </div>
        </div>
    );
};

export default EditPetModal;