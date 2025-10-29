declare module 'react' {
  export type FormEvent<T = Element> = any;
  export type ChangeEvent<T = Element> = any;
  export type SetStateAction<T> = T | ((prevState: T) => T);
  export function useState<T>(initialState: T | (() => T)): [T, (value: SetStateAction<T>) => void];
  export function useEffect(effect: (...args: any[]) => void | (() => void), deps?: any[]): void;
  export function useMemo<T>(factory: () => T, deps: any[]): T;
  export function StrictMode(props: { children?: any }): any;
  const React: {
    StrictMode: typeof StrictMode;
  };
  export default React;
}

declare module 'react/jsx-runtime' {
  export const jsx: unknown;
  export const jsxs: unknown;
  export const Fragment: unknown;
}

declare namespace JSX {
  interface IntrinsicElements {
    [elementName: string]: any;
  }
}
