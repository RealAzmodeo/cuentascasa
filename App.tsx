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
    ActivityIndicator,
    Modal,
    TextInput,
    Alert,
    KeyboardAvoidingView,
    Platform,
    Pressable
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
    ChevronLeft,
    Edit3,
    Search,
    Filter,
    UploadCloud,
    Check,
    X,
    Info,
    Brain
} from 'lucide-react-native';
import * as DocumentPicker from 'expo-document-picker';
import Svg, { G, Path, Circle } from 'react-native-svg';
import { theme } from './src/theme/colors';
import { apiClient } from './src/api/client';
import { Config, Analytics, Summary, Transaction, MonthData, HistoryItem } from './src/api/types';

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

    // Modals visibility
    const [addModalVisible, setAddModalVisible] = useState(false);
    const [settingsModalVisible, setSettingsModalVisible] = useState(false);

    // Add Form states
    const [addTab, setAddTab] = useState<'manual' | 'ai'>('manual');
    const [amount, setAmount] = useState('');
    const [desc, setDesc] = useState('');
    const [category, setCategory] = useState('');
    const [account, setAccount] = useState('Germán');
    const [type, setType] = useState('Gasto');

    // AI Chat state
    const [aiPrompt, setAiPrompt] = useState('');
    const [aiChat, setAiChat] = useState<{ role: 'u' | 'a', text: string }[]>([]);
    const [aiLoading, setAiLoading] = useState(false);

    useEffect(() => {
        loadInitialData();
    }, []);

    const handleSaveManual = async () => {
        if (!amount || !desc) {
            Alert.alert("Campos requeridos", "Por favor introduce monto y detalle.");
            return;
        }
        const res = await apiClient.addTransaction({
            monto: parseFloat(amount),
            detalle: desc,
            categoria: category || 'Otros',
            cuenta: account,
            tipo: type,
            fecha: new Date().toISOString().split('T')[0]
        });

        if (res.status === 'success') {
            setAddModalVisible(false);
            setAmount(''); setDesc('');
            loadInitialData();
        } else {
            Alert.alert("Error", "No se pudo guardar el movimiento.");
        }
    };

    const handleSendAI = async () => {
        if (!aiPrompt) return;
        const userMsg = aiPrompt;
        setAiPrompt('');
        setAiChat(prev => [...prev, { role: 'u', text: userMsg }]);
        setAiLoading(true);

        const res = await apiClient.askGemini(userMsg);
        setAiChat(prev => [...prev, { role: 'a', text: res.reply }]);
        setAiLoading(false);
    };

    const renderAddModal = () => (
        <Modal visible={addModalVisible} animationType="slide" transparent={true}>
            <View style={styles.modalOverlay}>
                <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : 'height'} style={styles.modalContent}>
                    <View style={styles.modalHeader}>
                        <View style={styles.tabContainer}>
                            <TouchableOpacity style={[styles.tab, addTab === 'manual' && styles.tabActive]} onPress={() => setAddTab('manual')}>
                                <Text style={[styles.tabText, addTab === 'manual' && styles.tabTextActive]}>MANUAL</Text>
                            </TouchableOpacity>
                            <TouchableOpacity style={[styles.tab, addTab === 'ai' && styles.tabActive]} onPress={() => setAddTab('ai')}>
                                <Text style={[styles.tabText, addTab === 'ai' && styles.tabTextActive]}>IA GEMINI</Text>
                            </TouchableOpacity>
                        </View>
                        <TouchableOpacity onPress={() => setAddModalVisible(false)}><X color={theme.colors.textCharcoal} /></TouchableOpacity>
                    </View>

                    {addTab === 'manual' ? (
                        <ScrollView>
                            <View style={styles.typeToggle}>
                                <TouchableOpacity style={[styles.typeBtn, type === 'Gasto' && styles.typeBtnActive]} onPress={() => setType('Gasto')}>
                                    <Text style={[styles.typeBtnText, type === 'Gasto' && styles.typeBtnTextActive]}>GASTO</Text>
                                </TouchableOpacity>
                                <TouchableOpacity style={[styles.typeBtn, type === 'Ingreso' && styles.typeBtnActive]} onPress={() => setType('Ingreso')}>
                                    <Text style={[styles.typeBtnText, type === 'Ingreso' && styles.typeBtnTextActive]}>INGRESO</Text>
                                </TouchableOpacity>
                            </View>

                            <View style={styles.inputGroup}>
                                <Text style={styles.label}>Monto (€)</Text>
                                <TextInput style={styles.input} keyboardType="numeric" value={amount} onChangeText={setAmount} placeholder="0.00" />
                            </View>

                            <View style={styles.inputGroup}>
                                <Text style={styles.label}>Tienda / Detalle</Text>
                                <TextInput style={styles.input} value={desc} onChangeText={setDesc} placeholder="Ej: Mercadona" />
                            </View>

                            <TouchableOpacity style={styles.btnAction} onPress={handleSaveManual}>
                                <Text style={styles.btnActionText}>REGISTRAR</Text>
                            </TouchableOpacity>
                        </ScrollView>
                    ) : (
                        <View style={{ flex: 1 }}>
                            <ScrollView style={styles.chatBox}>
                                {aiChat.map((msg, i) => (
                                    <View key={i} style={[styles.chatBubble, msg.role === 'u' ? styles.bubbleUser : styles.bubbleAi]}>
                                        <Text style={{ color: msg.role === 'u' ? 'white' : theme.colors.textCharcoal }}>{msg.text}</Text>
                                    </View>
                                ))}
                                {aiLoading && <ActivityIndicator color={theme.colors.retroOrange} style={{ alignSelf: 'flex-start', margin: 10 }} />}
                            </ScrollView>
                            <View style={styles.chatInputRow}>
                                <TextInput style={styles.chatInput} value={aiPrompt} onChangeText={setAiPrompt} placeholder="Escribe el gasto..." />
                                <TouchableOpacity style={styles.sendBtn} onPress={handleSendAI}>
                                    <Plus color="white" />
                                </TouchableOpacity>
                            </View>
                        </View>
                    )}
                </KeyboardAvoidingView>
            </View>
        </Modal>
    );

    const fetchInsights = async () => {
        setAiLoading(true);
        setAddModalVisible(true);
        setAddTab('ai');
        const res = await apiClient.askGemini("Dame un resumen rápido de mi estado financiero actual y algún consejo.");
        setAiChat(prev => [...prev, { role: 'a', text: res.reply }]);
        setAiLoading(false);
    };

    const renderSettingsModal = () => (
        <Modal visible={settingsModalVisible} animationType="fade" transparent={true}>
            <View style={styles.modalOverlay}>
                <View style={[styles.modalContent, { height: '80%' }]}>
                    <View style={styles.modalHeader}>
                        <Text style={styles.sectionTitle}>Ajustes y Reglas</Text>
                        <TouchableOpacity onPress={() => setSettingsModalVisible(false)}><X color={theme.colors.textCharcoal} /></TouchableOpacity>
                    </View>

                    <ScrollView>
                        <Text style={[styles.label, { marginTop: 10 }]}>Categorías y Presupuestos</Text>
                        {data.config && Object.entries(data.config.taxonomy).map(([name, cfg]) => (
                            <View key={name} style={styles.timelineItem}>
                                <Text style={{ flex: 1, fontWeight: '700' }}>{name}</Text>
                                <TextInput
                                    style={{ borderBottomWidth: 1, borderColor: '#DDD', width: 60, textAlign: 'right' }}
                                    defaultValue={cfg.budget.toString()}
                                    keyboardType="numeric"
                                />
                                <Text style={{ marginLeft: 5 }}>€</Text>
                            </View>
                        ))}

                        <TouchableOpacity style={[styles.btnAction, { marginTop: 20 }]} onPress={() => Alert.alert("Guardado", "Ajustes actualizados localmente.")}>
                            <Text style={styles.btnActionText}>GUARDAR CAMBIOS</Text>
                        </TouchableOpacity>

                        <View style={{ height: 50 }} />
                    </ScrollView>
                </View>
            </View>
        </Modal>
    );

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
                        <TouchableOpacity onPress={fetchInsights}><Sparkles color={theme.colors.retroOrange} size={24} /></TouchableOpacity>
                        <TouchableOpacity style={{ marginLeft: 15 }} onPress={() => setSettingsModalVisible(true)}><Settings color={theme.colors.textCharcoal} size={24} /></TouchableOpacity>
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

    const DonutChart = ({ data }: { data: { label: string, value: number, color: string }[] }) => {
        const total = data.reduce((acc, item) => acc + item.value, 0);
        let startAngle = 0;
        const radius = 70;
        const innerRadius = 50;
        const center = 100;

        return (
            <View style={{ alignItems: 'center', justifyContent: 'center' }}>
                <Svg width={200} height={200} viewBox="0 0 200 200">
                    <G transform={`translate(0, 0)`}>
                        {data.map((item, i) => {
                            const sliceAngle = total > 0 ? (item.value / total) * 360 : 0;
                            const endAngle = startAngle + sliceAngle;

                            const x1 = center + radius * Math.cos((Math.PI * startAngle) / 180);
                            const y1 = center + radius * Math.sin((Math.PI * startAngle) / 180);
                            const x2 = center + radius * Math.cos((Math.PI * endAngle) / 180);
                            const y2 = center + radius * Math.sin((Math.PI * endAngle) / 180);

                            const x3 = center + innerRadius * Math.cos((Math.PI * endAngle) / 180);
                            const y3 = center + innerRadius * Math.sin((Math.PI * endAngle) / 180);
                            const x4 = center + innerRadius * Math.cos((Math.PI * startAngle) / 180);
                            const y4 = center + innerRadius * Math.sin((Math.PI * startAngle) / 180);

                            const largeArc = sliceAngle > 180 ? 1 : 0;
                            const pathData = [
                                `M ${x1} ${y1}`,
                                `A ${radius} ${radius} 0 ${largeArc} 1 ${x2} ${y2}`,
                                `L ${x3} ${y3}`,
                                `A ${innerRadius} ${innerRadius} 0 ${largeArc} 0 ${x4} ${y4}`,
                                'Z'
                            ].join(' ');

                            const currentStart = startAngle;
                            startAngle = endAngle;

                            return <Path key={i} d={pathData} fill={item.color} />;
                        })}
                        {total === 0 && <Circle cx={center} cy={center} r={radius} fill="#F0F0F0" />}
                    </G>
                </Svg>
                <View style={{ position: 'absolute' }}>
                    <Text style={{ fontSize: 24, fontWeight: '800', color: theme.colors.textCharcoal }}>
                        €{total.toLocaleString('es-ES', { maximumFractionDigits: 0 })}
                    </Text>
                    <Text style={{ fontSize: 10, color: theme.colors.textMuted, textAlign: 'center', fontWeight: '700' }}>TOTAL GASTO</Text>
                </View>
            </View>
        );
    };

    const renderAnalytics = () => {
        const currentMonthKey = data.analytics?.current_month_key;
        const currentMonthData = currentMonthKey ? data.analytics?.months[currentMonthKey] : null;
        if (!currentMonthData) return (
            <View style={styles.view}><Text style={styles.emptyText}>Cargando datos...</Text></View>
        );

        const cats = Object.entries(currentMonthData.categories)
            .filter(([name]) => name !== 'Ingresos' && currentMonthData.categories[name] > 0)
            .sort((a, b) => b[1] - a[1]);

        const total = cats.reduce((acc, [_, val]) => acc + val, 0);

        const chartColors = ['#E54B4B', '#F78C58', '#E8B059', '#889E81', '#5D737E', '#2C2C2C'];
        const chartData = cats.slice(0, 6).map(([label, value], i) => ({
            label,
            value,
            color: chartColors[i % chartColors.length]
        }));

        return (
            <ScrollView style={styles.view} showsVerticalScrollIndicator={false}>
                <View style={styles.header}>
                    <Text style={styles.sectionTitle}>Distribución</Text>
                    <TouchableOpacity style={styles.filterBtn}>
                        <Text style={styles.filterText}>Mes Actual</Text>
                    </TouchableOpacity>
                </View>

                <View style={[styles.card, { alignItems: 'center', paddingVertical: 30 }]}>
                    <DonutChart data={chartData} />
                </View>

                <View style={{ marginTop: 20 }}>
                    {cats.map(([name, val], i) => {
                        const perc = total > 0 ? (val / total * 100).toFixed(0) : 0;
                        return (
                            <View key={name} style={styles.timelineItem}>
                                <View style={[styles.timelineIconContainer, { backgroundColor: chartColors[i % chartColors.length] + '20' }]}>
                                    <LayoutDashboard size={16} color={chartColors[i % chartColors.length]} />
                                </View>
                                <View style={{ flex: 1, marginLeft: 12 }}>
                                    <Text style={styles.timelineTitle}>{name}</Text>
                                    <Text style={styles.timelineSub}>{perc}% del gasto total</Text>
                                </View>
                                <Text style={styles.timelineAmount}>€{val.toLocaleString('es-ES')}</Text>
                            </View>
                        );
                    })}
                </View>
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

    const renderEvolution = () => {
        const history = data.analytics?.history || [];
        const latest = history[history.length - 1];
        const mom = latest ? latest.growth : 0;

        return (
            <ScrollView style={styles.view} showsVerticalScrollIndicator={false}>
                <View style={styles.header}>
                    <Text style={styles.sectionTitle}>Histórico Mensual</Text>
                </View>

                <View style={styles.balanceCard}>
                    <Text style={[styles.statsValue, { fontSize: 28, color: mom > 0 ? theme.colors.vhsRed : theme.colors.sageGreen }]}>
                        {mom > 0 ? '↑' : '↓'} {Math.abs(mom).toFixed(1)}%
                    </Text>
                    <Text style={[styles.statsLabel, { color: 'white' }]}>VS MES PASADO</Text>
                    <Text style={{ color: 'rgba(255,255,255,0.6)', fontSize: 12, marginTop: 10 }}>
                        {mom > 0 ? 'Tus gastos han subido. Revisa tus presupuestos.' : '¡Genial! Estás gastando menos que el mes pasado.'}
                    </Text>
                </View>

                <View style={[styles.card, { padding: 20 }]}>
                    <View style={{ flexDirection: 'row', alignItems: 'flex-end', height: 150, justifyContent: 'space-between' }}>
                        {history.slice(-6).map((h: HistoryItem, i: number) => {
                            const max = Math.max(...history.map((x: HistoryItem) => x.total));
                            const height = (h.total / max) * 120;
                            return (
                                <View key={i} style={{ alignItems: 'center', flex: 1 }}>
                                    <View style={{ width: 30, height, backgroundColor: i === history.length - 1 ? theme.colors.vhsRed : theme.colors.slateBlue, borderRadius: 5 }} />
                                    <Text style={{ fontSize: 8, marginTop: 5, color: theme.colors.textMuted }}>{h.month}</Text>
                                </View>
                            );
                        })}
                    </View>
                </View>

                <View style={{ height: 120 }} />
            </ScrollView>
        );
    };

    const [uploading, setUploading] = useState(false);
    const [pendingTx, setPendingTx] = useState<Transaction[]>([]);

    const handlePickDocument = async () => {
        try {
            const result = await DocumentPicker.getDocumentAsync({
                type: ['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 'application/pdf'],
            });

            if (!result.canceled) {
                setUploading(true);
                const asset = result.assets[0];
                const formData = new FormData();
                // @ts-ignore
                formData.append('file', {
                    uri: asset.uri,
                    name: asset.name,
                    type: asset.mimeType,
                });

                const response = await fetch(`${apiClient.getBaseUrl()}/bank/process`, {
                    method: 'POST',
                    body: formData,
                });

                const resData = await response.json();
                if (resData.status === 'success') {
                    setPendingTx(resData.transactions);
                    setActiveTab('bank');
                } else {
                    alert('Error: ' + resData.message);
                }
            }
        } catch (error) {
            console.error(error);
            alert('Error al seleccionar archivo');
        } finally {
            setUploading(false);
        }
    };

    const renderBank = () => {
        return (
            <View style={styles.view}>
                <View style={styles.header}>
                    <Text style={styles.sectionTitle}>Carga de Extractos</Text>
                </View>

                {pendingTx.length === 0 ? (
                    <TouchableOpacity style={styles.dropZone} onPress={handlePickDocument} disabled={uploading}>
                        {uploading ? (
                            <ActivityIndicator size="large" color={theme.colors.retroOrange} />
                        ) : (
                            <>
                                <UploadCloud size={40} color={theme.colors.textMuted} />
                                <Text style={styles.dropZoneText}>Toca para subir Excel o PDF</Text>
                                <Text style={styles.dropZoneSub}>Extractos de BBVA</Text>
                            </>
                        )}
                    </TouchableOpacity>
                ) : (
                    <ScrollView showsVerticalScrollIndicator={false}>
                        <View style={styles.sectionHeader}>
                            <Text style={styles.sectionTitle}>Nuevos Movimientos</Text>
                            <TouchableOpacity onPress={() => setPendingTx([])}><X size={20} color={theme.colors.vhsRed} /></TouchableOpacity>
                        </View>
                        {pendingTx.map((tx, i) => (
                            <View key={i} style={styles.timelineItem}>
                                <View style={styles.timelineIconContainer}>
                                    <LayoutDashboard size={16} color={theme.colors.textCharcoal} />
                                </View>
                                <View style={{ flex: 1, marginLeft: 10 }}>
                                    <Text style={styles.timelineTitle}>{tx.tienda || tx.detalle}</Text>
                                    <Text style={styles.timelineSub}>{tx.monto}€ - {tx.categoria}</Text>
                                </View>
                                <Check size={20} color={theme.colors.sageGreen} />
                            </View>
                        ))}
                        <TouchableOpacity style={[styles.btnPrimary, { marginTop: 20 }]}>
                            <Text style={styles.btnPrimaryText}>CONFIRMAR CARGA</Text>
                        </TouchableOpacity>
                        <View style={{ height: 120 }} />
                    </ScrollView>
                )}
            </View>
        );
    };

    return (
        <SafeAreaView style={styles.container}>
            <StatusBar barStyle="dark-content" />

            <View style={{ flex: 1 }}>
                {activeTab === 'home' && renderHome()}
                {activeTab === 'timeline' && renderTimeline()}
                {activeTab === 'bank' && renderBank()}
                {activeTab === 'analytics' && renderAnalytics()}
                {activeTab === 'evolution' && renderEvolution()}
            </View>

            {renderAddModal()}
            {renderSettingsModal()}

            <View style={styles.bottomNav}>
                <NavTab icon={LayoutDashboard} label="Resumen" active={activeTab === 'home'} onPress={() => setActiveTab('home')} />
                <NavTab icon={Landmark} label="Timeline" active={activeTab === 'timeline'} onPress={() => setActiveTab('timeline')} />
                <NavTab icon={FileText} label="Banco" active={activeTab === 'bank'} onPress={() => setActiveTab('bank')} />
                <NavTab icon={PieChart} label="Categorías" active={activeTab === 'analytics'} onPress={() => setActiveTab('analytics')} />
                <NavTab icon={TrendingUp} label="Evolución" active={activeTab === 'evolution'} onPress={() => setActiveTab('evolution')} />
            </View>

            <TouchableOpacity style={styles.fab} onPress={() => setAddModalVisible(true)}>
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
    card: {
        backgroundColor: 'white',
        borderRadius: theme.radius.md,
        padding: 15,
        borderWidth: 1,
        borderColor: theme.colors.border,
        elevation: 3,
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.1,
        shadowRadius: 4,
    },
    dropZone: {
        height: 200,
        borderWidth: 2,
        borderColor: theme.colors.border,
        borderStyle: 'dashed',
        borderRadius: theme.radius.lg,
        justifyContent: 'center',
        alignItems: 'center',
        backgroundColor: 'rgba(255,255,255,0.5)',
    },
    dropZoneText: {
        marginTop: 15,
        fontSize: 14,
        fontWeight: '700',
        color: theme.colors.textCharcoal,
    },
    dropZoneSub: {
        fontSize: 10,
        color: theme.colors.textMuted,
        marginTop: 5,
    },
    btnPrimary: {
        backgroundColor: theme.colors.textCharcoal,
        paddingVertical: 15,
        borderRadius: theme.radius.md,
        alignItems: 'center',
    },
    btnPrimaryText: {
        color: 'white',
        fontWeight: '800',
        fontSize: 14,
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
    },
    modalOverlay: {
        flex: 1,
        backgroundColor: 'rgba(0,0,0,0.5)',
        justifyContent: 'flex-end',
    },
    modalContent: {
        backgroundColor: theme.colors.bgCream,
        borderTopLeftRadius: 30,
        borderTopRightRadius: 30,
        padding: 25,
        minHeight: '60%',
        maxHeight: '90%',
    },
    modalHeader: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 25,
    },
    tabContainer: {
        flexDirection: 'row',
        backgroundColor: '#EEE',
        borderRadius: 50,
        padding: 4,
        flex: 1,
        marginRight: 15,
    },
    tab: {
        flex: 1,
        paddingVertical: 10,
        alignItems: 'center',
        borderRadius: 50,
    },
    tabActive: {
        backgroundColor: 'white',
    },
    tabText: {
        fontSize: 12,
        fontWeight: '700',
        color: theme.colors.textMuted,
    },
    tabTextActive: {
        color: theme.colors.textCharcoal,
    },
    typeToggle: {
        flexDirection: 'row',
        marginBottom: 20,
    },
    typeBtn: {
        flex: 1,
        paddingVertical: 12,
        alignItems: 'center',
        borderWidth: 1,
        borderColor: theme.colors.border,
    },
    typeBtnActive: {
        backgroundColor: theme.colors.textCharcoal,
        borderColor: theme.colors.textCharcoal,
    },
    typeBtnText: {
        fontWeight: '700',
        color: theme.colors.textMuted,
    },
    typeBtnTextActive: {
        color: 'white',
    },
    inputGroup: {
        marginBottom: 20,
    },
    label: {
        fontSize: 12,
        fontWeight: '700',
        color: theme.colors.textMuted,
        marginBottom: 8,
    },
    input: {
        backgroundColor: 'white',
        borderWidth: 1,
        borderColor: theme.colors.border,
        borderRadius: theme.radius.md,
        padding: 15,
        fontSize: 16,
    },
    btnAction: {
        backgroundColor: theme.colors.textCharcoal,
        padding: 18,
        borderRadius: theme.radius.md,
        alignItems: 'center',
        marginTop: 10,
    },
    btnActionText: {
        color: 'white',
        fontWeight: '800',
        fontSize: 16,
    },
    chatBox: {
        flex: 1,
        paddingVertical: 10,
    },
    chatBubble: {
        padding: 15,
        borderRadius: 20,
        marginBottom: 10,
        maxWidth: '85%',
    },
    bubbleUser: {
        backgroundColor: theme.colors.slateBlue,
        alignSelf: 'flex-end',
        borderBottomRightRadius: 4,
    },
    bubbleAi: {
        backgroundColor: 'white',
        alignSelf: 'flex-start',
        borderBottomLeftRadius: 4,
        borderWidth: 1,
        borderColor: theme.colors.border,
    },
    chatInputRow: {
        flexDirection: 'row',
        alignItems: 'center',
        marginVertical: 15,
    },
    chatInput: {
        flex: 1,
        backgroundColor: 'white',
        borderWidth: 1,
        borderColor: theme.colors.border,
        borderRadius: 25,
        paddingHorizontal: 20,
        paddingVertical: 12,
        marginRight: 10,
    },
    sendBtn: {
        width: 50,
        height: 50,
        borderRadius: 25,
        backgroundColor: theme.colors.retroOrange,
        justifyContent: 'center',
        alignItems: 'center',
    }
});
