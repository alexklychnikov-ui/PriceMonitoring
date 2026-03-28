/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_SUBSCRIPTION_WEB_KEY?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
