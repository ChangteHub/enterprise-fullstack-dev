import { create } from "zustand"

interface UserState {
  user: string | null
}

export const useUserStore = create<UserState>(() => ({ user: null }))
