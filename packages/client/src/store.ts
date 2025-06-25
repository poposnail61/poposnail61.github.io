import create from 'zustand';

interface State {
  sessionId: string | null;
  factor: number;
  setSession: (id: string) => void;
  setFactor: (n: number) => void;
}

const useStore = create<State>(set => ({
  sessionId: null,
  factor: 1,
  setSession: id => set({ sessionId: id }),
  setFactor: n => set({ factor: n })
}));

export default useStore;
