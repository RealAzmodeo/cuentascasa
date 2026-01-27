import { Config, Summary, Analytics } from './types';

// IP genérica para el emulador de Android (10.0.2.2 apunta al localhost del PC)
const BASE_URL = 'http://10.0.2.2:5000';

export const apiClient = {
    async getConfig(): Promise<Config> {
        const res = await fetch(`${BASE_URL}/api/config`);
        return res.json();
    },
    async getSummary(month: string): Promise<Summary> {
        const res = await fetch(`${BASE_URL}/api/summary?month=${month}`);
        return res.json();
    },
    async getAnalytics(month: string): Promise<Analytics> {
        const res = await fetch(`${BASE_URL}/api/analytics?month=${month}`);
        return res.json();
    }
};
