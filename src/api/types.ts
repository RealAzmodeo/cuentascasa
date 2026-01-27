export interface Config {
    current_month: string;
    months: string[];
}

export interface Transaction {
    id: string;
    fecha: string;
    concepto: string;
    importe: number;
    categoria: string;
    cuenta: string;
    tipo: 'gasto' | 'ingreso';
}

export interface Summary {
    total_ingresos: number;
    total_gastos: number;
    balance: number;
    presupuesto_total: number;
    gastos_por_categoria: Record<string, number>;
    presupuestos: Record<string, number>;
}

export interface Analytics {
    monthly_trend: { month: string, ingresos: number, gastos: number }[];
    categorized_spending: { category: string, amount: number }[];
}
