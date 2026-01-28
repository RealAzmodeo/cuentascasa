import { Config, Summary, Analytics } from './types';

// IP genérica para el emulador. 
// TIP: Para móvil físico, se debería usar la IP local del servidor (ej. 192.168.1.XX)
const BASE_URL = 'http://10.0.2.2:5000';

const fetchWithTimeout = async (url: string, options = {}, timeout = 5000) => {
    const controller = new AbortController();
    const id = setTimeout(() => controller.abort(), timeout);
    try {
        const response = await fetch(url, { ...options, signal: controller.signal });
        clearTimeout(id);
        return response;
    } catch (e) {
        clearTimeout(id);
        throw e;
    }
};

export const apiClient = {
    getBaseUrl(): string {
        return BASE_URL;
    },
    async getConfig(): Promise<Config | null> {
        try {
            const res = await fetchWithTimeout(`${BASE_URL}/api/config`);
            return res.json();
        } catch (e) {
            console.warn("Config fetch failed", e);
            return null;
        }
    },
    async getSummary(): Promise<Summary | null> {
        try {
            const res = await fetchWithTimeout(`${BASE_URL}/api/summary`);
            return res.json();
        } catch (e) {
            console.warn("Summary fetch failed", e);
            return null;
        }
    },
    async getAnalytics(): Promise<Analytics | null> {
        try {
            const res = await fetchWithTimeout(`${BASE_URL}/api/analytics`);
            return res.json();
        } catch (e) {
            console.warn("Analytics fetch failed", e);
            return null;
        }
    },
    async addTransaction(data: any): Promise<{ status: string, message?: string }> {
        try {
            const res = await fetch(`${BASE_URL}/api/transactions`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            return res.json();
        } catch (e) {
            return { status: 'error', message: 'Conexión fallida' };
        }
    },
    async askGemini(prompt: string): Promise<{ reply: string }> {
        try {
            const res = await fetch(`${BASE_URL}/api/ai/ask`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ prompt })
            });
            return res.json();
        } catch (e) {
            return { reply: 'Error al contactar con Gemini' };
        }
    },
    async updateConfig(config: Config): Promise<{ status: string }> {
        try {
            const res = await fetch(`${BASE_URL}/api/config`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(config)
            });
            return res.json();
        } catch (e) {
            return { status: 'error' };
        }
    }
};
