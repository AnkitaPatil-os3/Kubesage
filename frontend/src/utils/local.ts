// src/utils/local.ts
export const local = {
    get(key: string) {
      const value = window.localStorage.getItem(key)
      return value ? JSON.parse(value) : null
    },
    set(key: string, value: any) {
      window.localStorage.setItem(key, JSON.stringify(value))
    },
    remove(key: string) {
      window.localStorage.removeItem(key)
    }
  }
  