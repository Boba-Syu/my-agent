import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export type ThemeColor = 'pink' | 'purple' | 'blue' | 'mint' | 'peach'

interface ThemeColors {
  primary: string
  primaryLight: string
  income: string
  expense: string
  bg: string
  card: string
  border: string
  textPrimary: string
  textSecondary: string
  textMuted: string
}

const THEME_PRESETS: Record<ThemeColor, ThemeColors> = {
  pink: {
    primary: '#FF9AA2',
    primaryLight: '#FFB8C6',
    income: '#95D1CC',
    expense: '#FF8A80',
    bg: '#FFF5F5',
    card: '#FFFFFF',
    border: '#FFE5E5',
    textPrimary: '#2D3436',
    textSecondary: '#636E72',
    textMuted: '#B2BEC3'
  },
  purple: {
    primary: '#B19CD9',
    primaryLight: '#C9B8E0',
    income: '#A6E3E9',
    expense: '#F8BBD5',
    bg: '#FDF4FF',
    card: '#FFFFFF',
    border: '#E8E0FF',
    textPrimary: '#2D3436',
    textSecondary: '#636E72',
    textMuted: '#B2BEC3'
  },
  blue: {
    primary: '#8EC5FC',
    primaryLight: '#B4D9FF',
    income: '#7DD3FC',
    expense: '#FFA8A8',
    bg: '#F0F9FF',
    card: '#FFFFFF',
    border: '#E0F5FF',
    textPrimary: '#2D3436',
    textSecondary: '#636E72',
    textMuted: '#B2BEC3'
  },
  mint: {
    primary: '#6BCB77',
    primaryLight: '#A8E6CF',
    income: '#4ADEDE',
    expense: '#FF9F9F',
    bg: '#F0FFF4',
    card: '#FFFFFF',
    border: '#E0FFE8',
    textPrimary: '#2D3436',
    textSecondary: '#636E72',
    textMuted: '#B2BEC3'
  },
  peach: {
    primary: '#FFB389',
    primaryLight: '#FFCDA8',
    income: '#A3CB38',
    expense: '#FF8552',
    bg: '#FFFBF0',
    card: '#FFFFFF',
    border: '#FFF5E0',
    textPrimary: '#2D3436',
    textSecondary: '#636E72',
    textMuted: '#B2BEC3'
  }
}

export const useThemeStore = defineStore('theme', () => {
  const currentColor = ref<ThemeColor>('mint')
  const sidebarOpen = ref(false)

  const colors = computed(() => THEME_PRESETS[currentColor.value])

  function setTheme(color: ThemeColor) {
    currentColor.value = color
    applyTheme(THEME_PRESETS[color])
    localStorage.setItem('theme-color', color)
  }

  function toggleSidebar() {
    sidebarOpen.value = !sidebarOpen.value
  }

  function applyTheme(colors: ThemeColors) {
    const root = document.documentElement
    root.style.setProperty('--color-primary', colors.primary)
    root.style.setProperty('--color-primary-light', colors.primaryLight)
    root.style.setProperty('--color-income', colors.income)
    root.style.setProperty('--color-expense', colors.expense)
    root.style.setProperty('--color-bg', colors.bg)
    root.style.setProperty('--color-card', colors.card)
    root.style.setProperty('--color-border', colors.border)
    root.style.setProperty('--color-text-primary', colors.textPrimary)
    root.style.setProperty('--color-text-secondary', colors.textSecondary)
    root.style.setProperty('--color-text-muted', colors.textMuted)
  }

  function initTheme() {
    const savedColor = localStorage.getItem('theme-color') as ThemeColor
    if (savedColor && THEME_PRESETS[savedColor]) {
      setTheme(savedColor)
    } else {
      applyTheme(THEME_PRESETS[currentColor.value])
    }
  }

  return {
    currentColor,
    sidebarOpen,
    colors,
    setTheme,
    toggleSidebar,
    initTheme
  }
})
