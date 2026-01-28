export interface Config {
    taxonomy: Record<string, { budget: number }>;
}

export interface Transaction {
    id: string;
    tienda?: string;
    detalle: string;
    monto: number;
    categoria: string;
    cuenta: string;
    tipo: string;
}

export interface MonthData {
    income: number;
    total: number;
    categories: Record<string, number>;
    transactions: Transaction[];
}

export interface HistoryItem {
    month: string;
    total: number;
    growth: number;
}

export interface Analytics {
    current_month_key: string;
    months: Record<string, MonthData>;
    history: HistoryItem[];
}

export interface Summary {
    savings: number;
}
