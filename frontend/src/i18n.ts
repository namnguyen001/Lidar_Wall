import { create } from 'zustand'
import { vi } from './locales/vi'
import { en } from './locales/en'

type Lang = 'vi' | 'en'

interface I18nState {
  lang: Lang
  t: typeof vi
  setLang: (lang: Lang) => void
}

export const useI18n = create<I18nState>((set) => ({
  lang: 'vi',
  t: vi,
  setLang: (lang: Lang) => set({ lang, t: lang === 'vi' ? vi : en }),
}))
