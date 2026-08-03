import { ReactNode } from "react";

export interface PetInfo {
  type: string;
  weight: string;
  features: string;
  avatarColor: string;
  report: string;
  avatarUrl?: string;
}

export interface PetData {
  [key: string]: PetInfo;
}

export interface LogEntry {
  id: string;
  time: string;
  cat: string;
  act: string[];
  desc: string;
  details?: { [catName: string]: string };
  stat: string;
  videoTime: number;
  thumbColor: string;
  videoSrc?: string;
}

export interface CalendarDay {
  fullDate: string;
  day: string;
  week: string;
  isToday: boolean;
}

export interface VideoScriptEvent {
  startTime: number;
  endTime: number;
  hasMotion: boolean;
  triggerAlert?: {
    timeTrigger: number;
    cat: string;
    act: string[];
    title: string;
    desc: string;
    details?: { [catName: string]: string };
    stat: string;
    videoTime: number;
  };
}

export interface PushNotificationData {
  title: string;
  text: string;
  videoTime: number;
}

export interface PlayModalState {
  show: boolean;
  startTime: number;
  src: string | null;
}

export interface EditFormState {
  name: string;
  type: string;
  weight: string;
  features: string;
  avatarUrl?: string;
}

export interface ChatMessage {
  id: string;
  sender: 'bot' | 'user';
  text: string | ReactNode;
  time: string;
  type: 'text' | 'event' | 'meme' | 'vlog';
  eventData?: LogEntry; // If it's an event card
  memeUrl?: string; // If it's a meme
  vlogSegments?: {
    time: string;
    title: string;
    url: string;
    duration: string;
    desc: string;
    petName?: string;
    behavior?: string;
  }[];
}