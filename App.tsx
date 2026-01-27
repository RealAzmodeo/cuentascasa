import React, { useState, useEffect } from 'react';
import {
    StyleSheet,
    Text,
    View,
    ScrollView,
    TouchableOpacity,
    SafeAreaView,
    StatusBar,
    Dimensions,
    ActivityIndicator
} from 'react-native';
import {
    LayoutDashboard,
    Landmark,
    FileText,
    PieChart,
    TrendingUp,
    Plus,
    Sparkles,
    Settings,
    ChevronRight,
    Edit3
} from 'lucide-react-native';
import { theme } from './src/theme/colors';
import { apiClient } from './src/api/client';
import { Config, Analytics, Summary, Transaction } from './src/api/types';

const { width } = Dimensions.get('window');

// --- Components ---

const BudgetRow = ({ name, spent, budget }: { name: string, spent: number, budget: number }) => {
    const perc = Math.min((spent / budget) * 100, 100);
    const isExceeded = spent > budget;

    return (
        <View style={styles.budgetRow}>
            <View style={styles.budgetHeader}>
                <View style={styles.budgetIconContainer}>
                    <LayoutDashboard size={14} color={theme.colors.textCharcoal} />
                </View>
                <View style={{ flex: 1 }}>
                    <Text style={styles.catName}>{name}</Text>
                    <Text style={styles.budgetSub}>Gasto: €{spent.toLocaleString('es-ES')} / €{budget}</Text>
                </View>
                <Text style={[styles.spentPerc, { color: isExceeded ? theme.colors.vhsRed : theme.colors.textCharcoal }]}>
                    {perc.toFixed(0)}%
                </Text>
            </View>
            <View style={styles.progressContainer}>
                <View style={[styles.progressSegment, { width: `${perc}%`, backgroundColor: isExceeded ? theme.colors.vhsRed : theme.colors.sageGreen }]} />
            </View>
        </View>
    );
};

const TimelineItem = ({ tx }: { tx: Transaction }) => {
    const isGasto = tx.tipo.toLowerCase() === 'gasto';
    return (
        <View style={styles.timelineItem}>
            <View style={styles.timelineIconContainer}>
                <LayoutDashboard size={16} color={theme.colors.textCharcoal} />
            </View>
            <View style={{ flex: 1, marginLeft: 10 }}>
                <View style={{ flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' }}>
                    <Text style={styles.timelineTitle} numberOfLines={1}>{tx.tienda || tx.detalle}</Text>
                    <Text style={[styles.timelineAmount, { color: isGasto ? theme.colors.textCharcoal : theme.colors.sageGreen }]}>
                        {isGasto ? '-' : '+'}{tx.monto.toLocaleString('es-ES')}€
                    </Text>
                </View>
                <View style={{ flexDirection: 'row', alignItems: 'center', marginTop: 2 }}>
                    <Text style={styles.timelineSub}>{tx.categoria}</Text>
                    <View style={styles.accountBadge}><Text style={styles.accountBadgeText}>{tx.cuenta}</Text></View>
                </View>
            </View>
            <TouchableOpacity style={styles.editBtn}>
                <Edit3 size={14} color={theme.colors.textMuted} />
            </TouchableOpacity>
        </View>
    );
};

const NavTab = ({ icon: Icon, label, active, onPress }: { icon: any, label: string, active: boolean, onPress: () => void }) => (
    <TouchableOpacity style={styles.navItem} onPress={onPress}>
        <Icon color={active ? theme.colors.textCharcoal : theme.colors.textMuted} size={24} />
        <Text style={[styles.navLabel, active && styles.navLabelActive]}>{label}</Text>
    </TouchableOpacity>
);

// --- Main App ---

export default function App() {
    const [activeTab, setActiveTab] = useState('home');
    const [loading, setLoading] = useState(true);
    const [data, setData] = useState<{
        config: Config | null;
        analytics: Analytics | null;
        summary: Summary | null;
    }>({
        config: null,
        analytics: null,
        summary: null,
    });

    useEffect(() => {
        loadInitialData();
    }, []);

    const loadInitialData = async () => {
        setLoading(true);
        try {
            const [config, analytics, summary] = await Promise.all([
                apiClient.getConfig().catch(() => null),
                apiClient.getAnalytics().catch(() => null),
                apiClient.getSummary().catch(() => null)
            ]);
            setData({ config, analytics, summary });
        } catch (error) {
            console.error("Initial load failed", error);
        } finally {
            setLoading(false);
        }
    };

    const renderHome = () => {
        const currentMonthKey = data.analytics?.current_month_key;
        const currentMonthData = currentMonthKey ? data.analytics?.months[currentMonthKey] : null;

        return (
            <ScrollView style={styles.view} showsVerticalScrollIndicator={false}>
                <View style={styles.header}>
                    <Text style={styles.logo}>ELITE FINANCE</Text>
                    <View style={styles.headerIcons}>
                        <TouchableOpacity><Sparkles color={theme.colors.retroOrange} size={24} /></TouchableOpacity>
                        <TouchableOpacity style={{ marginLeft: 15 }}><Settings color={theme.colors.textCharcoal} size={24} /></TouchableOpacity>
                    </View>
                </View>

                <View style={styles.balanceCard}>
                    <Text style={styles.balanceLabel}>Balance Total</Text>
                    <Text style={styles.balanceAmount}>€{data.summary?.savings.toLocaleString('es-ES') || '0'}</Text>
                    <View style={styles.statsRow}>
                        <View>
                            <Text style={styles.statsLabel}>INGRESOS MES</Text>
                            <Text style={[styles.statsValue, { color: theme.colors.sageGreen }]}>
                                +€{currentMonthData?.income.toLocaleString('es-ES') || '0'}
                            </Text>
                        </View>
                        <View style={{ marginLeft: 30 }}>
                            <Text style={styles.statsLabel}>GASTOS MES</Text>
                            <Text style={[styles.statsValue, { color: theme.colors.vhsRed }]}>
                                -€{currentMonthData?.total.toLocaleString('es-ES') || '0'}
                            </Text>
                        </View>
                    </View>
                </View>

                <View style={styles.sectionHeader}>
                    <Text style={styles.sectionTitle}>Presupuestos</Text>
                    <TouchableOpacity style={styles.seeAllBtn}>
                        <Text style={styles.seeAllText}>Mes Actual</Text>
                    </TouchableOpacity>
                </View>

                {data.config && currentMonthData ? (
                    Object.entries(data.config.taxonomy).map(([name, cfg]) => {
                        if (cfg.budget === 0 || name === 'Ingresos') return null;
                        const spent = currentMonthData.categories[name] || 0;
                        return <BudgetRow key={name} name={name} spent={spent} budget={cfg.budget} />;
                    })
                ) : (
                    <View style={styles.emptyCard}>
                        {loading ? <ActivityIndicator color={theme.colors.textMuted} /> : <Text style={styles.emptyText}>Sin presupuestos configurados</Text>}
                    </View>
                )}
                <View style={{ height: 120 }} />
            </ScrollView>
        );
    };

    const renderTimeline = () => {
        const currentMonthKey = data.analytics?.current_month_key;
        const transactions = currentMonthKey ? data.analytics?.months[currentMonthKey]?.transactions : [];

        return (
            <View style={styles.view}>
                <View style={styles.header}>
                    <Text style={styles.sectionTitle}>Timeline</Text>
                    <View style={styles.headerIcons}>
                        <TouchableOpacity style={styles.filterBtn}>
                            <Text style={styles.filterText}>Filtros</Text>
                        </TouchableOpacity>
                    </View>
                </View>

                <ScrollView showsVerticalScrollIndicator={false}>
                    {transactions && transactions.length > 0 ? (
                        transactions.map((tx) => <TimelineItem key={tx.id} tx={tx} />)
                    ) : (
                        <View style={styles.emptyCard}>
                            <Text style={styles.emptyText}>No hay movimientos recientes</Text>
                        </View>
                    )}
                    <View style={{ height: 120 }} />
                </ScrollView>
            </View>
        );
    };

    return (
        <SafeAreaView style={styles.container}>
            <StatusBar barStyle="dark-content" />

            <View style={{ flex: 1 }}>
                {activeTab === 'home' && renderHome()}
                {activeTab === 'timeline' && renderTimeline()}
                {activeTab === 'bank' && <View style={styles.view}><Text style={styles.placeholderText}>Carga de Extractos (Próximamente)</Text></View>}
                {activeTab === 'analytics' && <View style={styles.view}><Text style={styles.placeholderText}>Análisis de Categorías (Próximamente)</Text></View>}
                {activeTab === 'evolution' && <View style={styles.view}><Text style={styles.placeholderText}>Evolución Histórica (Próximamente)</Text></View>}
            </View>

            <View style={styles.bottomNav}>
                <NavTab icon={LayoutDashboard} label="Resumen" active={activeTab === 'home'} onPress={() => setActiveTab('home')} />
                <NavTab icon={Landmark} label="Timeline" active={activeTab === 'timeline'} onPress={() => setActiveTab('timeline')} />
                <NavTab icon={FileText} label="Banco" active={activeTab === 'bank'} onPress={() => setActiveTab('bank')} />
                <NavTab icon={PieChart} label="Categorías" active={activeTab === 'analytics'} onPress={() => setActiveTab('analytics')} />
                <NavTab icon={TrendingUp} label="Evolución" active={activeTab === 'evolution'} onPress={() => setActiveTab('evolution')} />
            </View>

            <TouchableOpacity style={styles.fab}>
                <Plus color="white" size={32} />
            </TouchableOpacity>
        </SafeAreaView>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: theme.colors.bgCream,
    },
    view: {
        flex: 1,
        paddingHorizontal: 20,
    },
    header: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        paddingVertical: 20,
    },
    logo: {
        fontSize: 18,
        fontWeight: '900',
        color: theme.colors.textCharcoal,
        letterSpacing: 1,
    },
    headerIcons: {
        flexDirection: 'row',
    },
    balanceCard: {
        backgroundColor: theme.colors.textCharcoal,
        borderRadius: theme.radius.lg,
        padding: 25,
        marginBottom: 25,
        elevation: 12,
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 10 },
        shadowOpacity: 0.3,
        shadowRadius: 15,
    },
    balanceLabel: {
        color: 'rgba(255,255,255,0.6)',
        fontSize: 12,
        fontWeight: '600',
        textTransform: 'uppercase',
    },
    balanceAmount: {
        color: 'white',
        fontSize: 38,
        fontWeight: '700',
        marginVertical: 10,
    },
    statsRow: {
        flexDirection: 'row',
        marginTop: 10,
        borderTopWidth: 1,
        borderTopColor: 'rgba(255,255,255,0.1)',
        paddingTop: 15,
    },
    statsLabel: {
        fontSize: 10,
        color: 'rgba(255,255,255,0.5)',
        fontWeight: '700',
        marginBottom: 4,
    },
    statsValue: {
        fontSize: 16,
        fontWeight: '700',
    },
    sectionHeader: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 15,
        marginTop: 10,
    },
    sectionTitle: {
        fontSize: 18,
        fontWeight: '700',
        color: theme.colors.textCharcoal,
    },
    seeAllBtn: {
        padding: 6,
    },
    seeAllText: {
        fontSize: 12,
        color: theme.colors.retroOrange,
        fontWeight: '700',
    },
    emptyCard: {
        backgroundColor: 'white',
        borderRadius: theme.radius.md,
        padding: 30,
        borderWidth: 1,
        borderColor: theme.colors.border,
        alignItems: 'center',
        justifyContent: 'center',
    },
    emptyText: {
        color: theme.colors.textMuted,
        fontSize: 14,
    },
    budgetRow: {
        marginBottom: 15,
        backgroundColor: 'white',
        padding: 18,
        borderRadius: theme.radius.md,
        borderWidth: 1,
        borderColor: theme.colors.border,
        elevation: 2,
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.05,
        shadowRadius: 4,
    },
    budgetHeader: {
        flexDirection: 'row',
        alignItems: 'center',
        marginBottom: 12,
    },
    budgetIconContainer: {
        width: 32,
        height: 32,
        backgroundColor: theme.colors.bgCream,
        borderRadius: 8,
        justifyContent: 'center',
        alignItems: 'center',
        marginRight: 12,
    },
    catName: {
        fontSize: 14,
        fontWeight: '700',
        color: theme.colors.textCharcoal,
    },
    budgetSub: {
        fontSize: 11,
        color: theme.colors.textMuted,
        marginTop: 2,
    },
    spentPerc: {
        fontSize: 16,
        fontWeight: '800',
    },
    progressContainer: {
        height: 8,
        backgroundColor: '#F0F0F0',
        borderRadius: 4,
        overflow: 'hidden',
    },
    progressSegment: {
        height: '100%',
        borderRadius: 4,
    },
    timelineItem: {
        flexDirection: 'row',
        alignItems: 'center',
        backgroundColor: 'white',
        padding: 15,
        borderRadius: theme.radius.md,
        marginBottom: 12,
        borderWidth: 1,
        borderColor: theme.colors.border,
    },
    timelineIconContainer: {
        width: 38,
        height: 38,
        backgroundColor: theme.colors.bgCream,
        borderRadius: 10,
        justifyContent: 'center',
        alignItems: 'center',
    },
    timelineTitle: {
        fontSize: 14,
        fontWeight: '700',
        color: theme.colors.textCharcoal,
        flex: 1,
    },
    timelineSub: {
        fontSize: 11,
        color: theme.colors.textMuted,
    },
    timelineAmount: {
        fontSize: 15,
        fontWeight: '800',
        marginLeft: 10,
    },
    accountBadge: {
        backgroundColor: theme.colors.bgCream,
        paddingHorizontal: 8,
        paddingVertical: 2,
        borderRadius: 6,
        marginLeft: 8,
        borderWidth: 1,
        borderColor: theme.colors.border,
    },
    accountBadgeText: {
        fontSize: 9,
        fontWeight: '800',
        color: theme.colors.slateBlue,
        textTransform: 'uppercase',
    },
    editBtn: {
        padding: 8,
        marginLeft: 5,
    },
    filterBtn: {
        backgroundColor: 'white',
        borderWidth: 1,
        borderColor: theme.colors.border,
        paddingHorizontal: 15,
        paddingVertical: 8,
        borderRadius: 20,
    },
    filterText: {
        fontSize: 12,
        fontWeight: '700',
        color: theme.colors.textMuted,
    },
    placeholderText: {
        marginTop: 50,
        textAlign: 'center',
        color: theme.colors.textMuted,
        fontStyle: 'italic',
    },
    bottomNav: {
        flexDirection: 'row',
        backgroundColor: 'white',
        paddingBottom: 25,
        paddingTop: 15,
        borderTopWidth: 1,
        borderTopColor: theme.colors.border,
        justifyContent: 'space-around',
        position: 'absolute',
        bottom: 0,
        width: '100%',
    },
    navItem: {
        alignItems: 'center',
        flex: 1,
    },
    navLabel: {
        fontSize: 10,
        color: theme.colors.textMuted,
        marginTop: 6,
    },
    navLabelActive: {
        color: theme.colors.textCharcoal,
        fontWeight: '700',
    },
    fab: {
        position: 'absolute',
        right: 25,
        bottom: 110,
        width: 60,
        height: 60,
        borderRadius: 30,
        backgroundColor: theme.colors.retroOrange,
        justifyContent: 'center',
        alignItems: 'center',
        elevation: 8,
        shadowColor: theme.colors.retroOrange,
        shadowOffset: { width: 0, height: 6 },
        shadowOpacity: 0.4,
        shadowRadius: 10,
        zIndex: 1000,
    }
});
