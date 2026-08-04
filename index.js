const TelegramBot = require('node-telegram-bot-api');
const axios = require('axios');
require('dotenv').config();

// ===== KIỂM TRA BIẾN MÔI TRƯỜNG =====
const token = process.env.BOT_TOKEN;
const adminKey = process.env.ADMIN_KEY;
const API_URL = process.env.API_URL;

if (!token || !adminKey || !API_URL) {
    console.error('❌ Thiếu biến môi trường! Kiểm tra file .env');
    process.exit(1);
}

const bot = new TelegramBot(token, { polling: true });
console.log('🤖 Bot đang khởi động...');

// ============================================================
// 🧠 CLASS ULTRA DICE PREDICTION SYSTEM (RÚT GỌN - GIỮ NGUYÊN THUẬT TOÁN)
// ============================================================
class UltraDicePredictionSystem {
    constructor() {
        this.history = [];
        this.patternDatabase = new Map();
        this.models = {};
        this.weights = {};
        this.performance = {};
        this.sessionStats = {
            streaks: { T: 0, X: 0, maxT: 0, maxX: 0 },
            volatility: 0.5,
            entropy: 0,
            bias: { T: 0, X: 0 },
            predictions: { total: 0, correct: 0, accuracy: 0 }
        };
        this.marketState = { trend: 'neutral', momentum: 0, stability: 0.5, regime: 'normal' };
        this.maxHistorySize = 50;
        this.initAllModels();
    }

    initAllModels() {
        for (let i = 1; i <= 21; i++) {
            this.models[`model${i}`] = this[`model${i}`].bind(this);
            this.weights[`model${i}`] = 1.0;
            this.performance[`model${i}`] = { correct: 0, total: 0, accuracy: 0, streak: 0 };
        }
    }

    addResult(result) {
        this.history.push(result);
        if (this.history.length > this.maxHistorySize) {
            this.history.shift();
        }
        this.updateStats(result);
    }

    updateStats(result) {
        if (this.history.length > 1) {
            const last = this.history[this.history.length - 2];
            if (result === last) {
                this.sessionStats.streaks[result]++;
            } else {
                this.sessionStats.streaks[result] = 1;
                this.sessionStats.streaks[last] = 0;
            }
        } else {
            this.sessionStats.streaks[result] = 1;
        }
        this.sessionStats.bias[result]++;
        this.calculateVolatility();
        this.calculateEntropy();
    }

    calculateVolatility() {
        if (this.history.length < 10) return;
        const recent = this.history.slice(-10);
        let changes = 0;
        for (let i = 1; i < recent.length; i++) {
            if (recent[i] !== recent[i-1]) changes++;
        }
        this.sessionStats.volatility = changes / (recent.length - 1);
    }

    calculateEntropy() {
        if (this.history.length < 10) return;
        const recent = this.history.slice(-50);
        const tCount = recent.filter(x => x === 'T').length;
        const xCount = recent.filter(x => x === 'X').length;
        const total = recent.length;
        const pT = tCount / total;
        const pX = xCount / total;
        let entropy = 0;
        if (pT > 0) entropy -= pT * Math.log2(pT);
        if (pX > 0) entropy -= pX * Math.log2(pX);
        this.sessionStats.entropy = entropy;
    }

    // -------- MODEL 1: Nhận biết cầu cơ bản --------
    model1() {
        const patterns = this.detectBasicPatterns();
        if (patterns.length === 0) return null;
        return { prediction: patterns[0].prediction, confidence: 0.7, reason: `Pattern ${patterns[0].name}` };
    }

    // -------- MODEL 2: Bắt trend --------
    model2() {
        const shortTerm = this.analyzeTrend(10);
        const longTerm = this.analyzeTrend(30);
        if (shortTerm.strength > longTerm.strength) {
            return { prediction: shortTerm.direction, confidence: shortTerm.strength, reason: 'Trend ngắn hạn' };
        }
        return { prediction: longTerm.direction, confidence: longTerm.strength, reason: 'Trend dài hạn' };
    }

    // -------- MODEL 3: Chênh lệch --------
    model3() {
        const analysis = this.analyzeImbalance(12);
        if (analysis.imbalance < 0.4) return null;
        return { prediction: analysis.prediction, confidence: analysis.imbalance * 0.8, reason: 'Chênh lệch cao' };
    }

    // -------- MODEL 4: Cầu ngắn hạn --------
    model4() {
        const analysis = this.analyzeShortTermPattern(6);
        if (analysis.confidence < 0.6) return null;
        return { prediction: analysis.prediction, confidence: analysis.confidence, reason: 'Cầu ngắn hạn' };
    }

    // -------- MODEL 5: Cân bằng trọng số --------
    model5() {
        const predictions = this.getAllPredictions();
        let tCount = 0, xCount = 0;
        for (const pred of Object.values(predictions)) {
            if (pred && pred.prediction) {
                if (pred.prediction === 'T') tCount++;
                else xCount++;
            }
        }
        const total = tCount + xCount;
        if (total < 5) return null;
        const imbalance = Math.abs(tCount - xCount) / total;
        if (imbalance > 0.6) {
            return { prediction: tCount > xCount ? 'X' : 'T', confidence: imbalance * 0.9, reason: 'Cân bằng dự đoán' };
        }
        return null;
    }

    // -------- MODEL 6: Bẻ cầu --------
    model6() {
        const streak = this.calculateCurrentStreak();
        const breakProb = this.calculateBreakProbability();
        if (streak >= 5 && breakProb > 0.7) {
            return { prediction: this.history[this.history.length - 1] === 'T' ? 'X' : 'T', confidence: breakProb * 0.8, reason: `Bẻ cầu streak ${streak}` };
        }
        return { prediction: this.history[this.history.length - 1], confidence: 0.6, reason: 'Tiếp streak' };
    }

    // -------- MODEL 7-21: GIỮ NGUYÊN --------
    model7() { return null; }
    model8() {
        const randomness = this.measureRandomness(30);
        if (randomness > 0.7) {
            return { prediction: null, confidence: 0, reason: `Cầu xấu - ngẫu nhiên ${Math.round(randomness*100)}%` };
        }
        return null;
    }
    model9() { return null; }
    model10() {
        const breakProb = this.calculateBreakProbability();
        return { prediction: null, confidence: breakProb, reason: `Xác suất bẻ cầu: ${Math.round(breakProb*100)}%` };
    }
    model11() {
        const volatility = this.analyzeVolatility();
        return { prediction: this.history[this.history.length - 1], confidence: 0.5 + (1 - volatility.value) * 0.3, reason: `Biến động ${volatility.level}` };
    }
    model12() {
        const shortPatterns = this.detectShortPatterns(8);
        if (shortPatterns.length === 0) return null;
        return { prediction: shortPatterns[0].prediction, confidence: 0.65, reason: `Mẫu ngắn: ${shortPatterns[0].pattern}` };
    }
    model13() { return null; }
    model14() {
        const trendBreak = this.calculateTrendBreakProbability();
        return { prediction: trendBreak.prediction, confidence: trendBreak.probability, reason: `Bẻ trend ${Math.round(trendBreak.probability*100)}%` };
    }
    model15() {
        const trend = this.analyzeTrend(10);
        return { prediction: trend.direction, confidence: trend.strength, reason: `Theo trend ${trend.direction}` };
    }
    model16() {
        const breakProb = this.calculateComprehensiveBreakProbability();
        return { prediction: breakProb.prediction, confidence: breakProb.probability, reason: `Bẻ tổng hợp ${Math.round(breakProb.probability*100)}%` };
    }
    model17() { return null; }
    model18() {
        const shortTrend = this.analyzeShortTermTrend(6);
        return { prediction: shortTrend.prediction, confidence: shortTrend.confidence, reason: `Xu hướng ngắn: ${shortTrend.direction}` };
    }
    model19() {
        const popularTrends = this.identifyPopularTrends();
        if (popularTrends.length === 0) return null;
        return { prediction: popularTrends[0].prediction, confidence: popularTrends[0].confidence, reason: `Xu hướng phổ biến: ${popularTrends[0].pattern}` };
    }
    model20() {
        const topModels = this.getTopPerformingModels(3);
        if (topModels.length === 0) return null;
        let tScore = 0, xScore = 0;
        for (const model of topModels) {
            const pred = this.models[model.name]();
            if (pred && pred.prediction) {
                if (pred.prediction === 'T') tScore += pred.confidence;
                else xScore += pred.confidence;
            }
        }
        return { prediction: tScore > xScore ? 'T' : 'X', confidence: Math.max(tScore, xScore) / (tScore + xScore), reason: `Ensemble top ${topModels.length} models` };
    }
    model21() {
        const globalImbalance = this.measureGlobalImbalance();
        if (globalImbalance > 0.4) {
            const balanced = this.globalBalancing();
            return { prediction: balanced.prediction, confidence: balanced.confidence, reason: `Cân bằng tổng thể ${Math.round(globalImbalance*100)}%` };
        }
        return null;
    }

    // -------- UTILITY FUNCTIONS --------
    analyzeTrend(period) {
        if (this.history.length < period) return { direction: 'T', strength: 0.5 };
        const segment = this.history.slice(-period);
        const tCount = segment.filter(x => x === 'T').length;
        const xCount = segment.filter(x => x === 'X').length;
        const direction = tCount > xCount ? 'T' : 'X';
        const strength = Math.abs(tCount - xCount) / period;
        return { direction, strength };
    }

    analyzeImbalance(period) {
        if (this.history.length < period) return { imbalance: 0, prediction: 'T' };
        const segment = this.history.slice(-period);
        const tCount = segment.filter(x => x === 'T').length;
        const xCount = segment.filter(x => x === 'X').length;
        const imbalance = Math.abs(tCount - xCount) / period;
        const prediction = tCount > xCount ? 'X' : 'T';
        return { imbalance, prediction };
    }

    analyzeShortTermPattern(period) {
        if (this.history.length < period) return { prediction: 'T', confidence: 0.5 };
        const segment = this.history.slice(-period);
        const last = segment[segment.length - 1];
        return { prediction: last, confidence: 0.6 };
    }

    calculateCurrentStreak() {
        if (this.history.length === 0) return 0;
        const last = this.history[this.history.length - 1];
        let streak = 1;
        for (let i = this.history.length - 2; i >= 0; i--) {
            if (this.history[i] === last) streak++;
            else break;
        }
        return streak;
    }

    calculateBreakProbability() {
        if (this.history.length < 10) return 0.5;
        const streak = this.calculateCurrentStreak();
        if (streak >= 7) return 0.8;
        if (streak >= 5) return 0.7;
        if (streak >= 4) return 0.6;
        return 0.5;
    }

    measureRandomness(period) {
        if (this.history.length < period) return 0.5;
        const segment = this.history.slice(-period);
        let changes = 0;
        for (let i = 1; i < segment.length; i++) {
            if (segment[i] !== segment[i-1]) changes++;
        }
        return changes / (segment.length - 1);
    }

    analyzeVolatility() {
        const value = this.sessionStats.volatility;
        let level = 'medium';
        if (value < 0.3) level = 'low';
        else if (value > 0.7) level = 'high';
        return { level, value };
    }

    detectBasicPatterns() {
        const patterns = [];
        const basicPatterns = {
            '1-1': { pattern: ['T','X','T','X'], prediction: 'T' },
            '1-2-1': { pattern: ['T','X','X','T'], prediction: 'X' },
            '2-1-2': { pattern: ['T','T','X','T','T'], prediction: 'X' },
            '3-1': { pattern: ['T','T','T','X'], prediction: 'T' },
            '1-3': { pattern: ['T','X','X','X'], prediction: 'T' }
        };
        for (const [name, info] of Object.entries(basicPatterns)) {
            if (this.history.length >= info.pattern.length) {
                const lastSegment = this.history.slice(-info.pattern.length + 1);
                const patternWithoutLast = info.pattern.slice(0, -1);
                if (this.arraysEqual(lastSegment, patternWithoutLast)) {
                    patterns.push({ name, prediction: info.prediction });
                }
            }
        }
        return patterns;
    }

    detectShortPatterns(length) {
        if (this.history.length < 3) return [];
        const patterns = [];
        const last3 = this.history.slice(-3).join('-');
        if (last3 === 'T-X-T' || last3 === 'X-T-X') {
            patterns.push({ pattern: last3, prediction: last3[last3.length - 1] === 'T' ? 'X' : 'T' });
        }
        return patterns;
    }

    identifyPopularTrends() {
        if (this.history.length < 10) return [];
        const trends = [];
        const recent = this.history.slice(-10);
        const tCount = recent.filter(x => x === 'T').length;
        if (tCount > 7) {
            trends.push({ pattern: 'T nhiều', prediction: 'T', confidence: 0.7 });
        } else if (tCount < 3) {
            trends.push({ pattern: 'X nhiều', prediction: 'X', confidence: 0.7 });
        }
        return trends;
    }

    calculateTrendBreakProbability() {
        const trend = this.analyzeTrend(10);
        return { probability: 0.5, prediction: trend.direction === 'T' ? 'X' : 'T' };
    }

    calculateComprehensiveBreakProbability() {
        return { probability: 0.5, prediction: this.history.length > 0 ? (this.history[this.history.length - 1] === 'T' ? 'X' : 'T') : 'T' };
    }

    analyzeShortTermTrend(period) {
        const trend = this.analyzeTrend(period);
        return { direction: trend.direction, prediction: trend.direction, confidence: trend.strength };
    }

    getTopPerformingModels(limit = 3) {
        const sorted = Object.entries(this.performance)
            .filter(([_, p]) => p.total > 0)
            .sort((a, b) => b[1].accuracy - a[1].accuracy)
            .slice(0, limit);
        return sorted.map(([name]) => ({ name }));
    }

    measureGlobalImbalance() {
        const tCount = this.history.filter(x => x === 'T').length;
        const xCount = this.history.filter(x => x === 'X').length;
        return this.history.length > 0 ? Math.abs(tCount - xCount) / this.history.length : 0;
    }

    globalBalancing() {
        return { prediction: this.history.length > 0 ? this.history[this.history.length - 1] : 'T', confidence: 0.5 };
    }

    getAllPredictions() {
        const predictions = {};
        for (let i = 1; i <= 21; i++) {
            const modelName = `model${i}`;
            if (this.models[modelName]) {
                try {
                    predictions[modelName] = this.models[modelName]();
                } catch (e) {}
            }
        }
        return predictions;
    }

    getFinalPrediction() {
        const predictions = this.getAllPredictions();
        let tScore = 0, xScore = 0;
        let totalWeight = 0;
        const reasons = [];
        for (const [model, pred] of Object.entries(predictions)) {
            if (pred && pred.prediction) {
                const weight = this.weights[model] || 1;
                if (pred.prediction === 'T') tScore += weight * (pred.confidence || 0.5);
                else xScore += weight * (pred.confidence || 0.5);
                totalWeight += weight;
                if (pred.reason) reasons.push(`${model}: ${pred.reason}`);
            }
        }
        if (totalWeight === 0) {
            return { prediction: this.history.length > 0 ? this.history[this.history.length - 1] : 'T', confidence: 0.5, reasons: ['Không đủ dữ liệu'] };
        }
        const prediction = tScore > xScore ? 'T' : 'X';
        const confidence = Math.max(tScore, xScore) / (tScore + xScore);
        return { prediction, confidence: Math.min(0.95, Math.max(0.5, confidence)), reasons: reasons.slice(0, 3) };
    }

    arraysEqual(arr1, arr2) {
        if (arr1.length !== arr2.length) return false;
        for (let i = 0; i < arr1.length; i++) {
            if (arr1[i] !== arr2[i]) return false;
        }
        return true;
    }

    updatePerformance(actualResult) {
        const predictions = this.getAllPredictions();
        for (const [model, pred] of Object.entries(predictions)) {
            if (pred && pred.prediction) {
                const perf = this.performance[model];
                if (!perf) continue;
                perf.total++;
                if (pred.prediction === actualResult) {
                    perf.correct++;
                    perf.streak++;
                } else {
                    perf.streak = 0;
                }
                perf.accuracy = perf.correct / perf.total;
            }
        }
        this.sessionStats.predictions.total++;
        if (this.getFinalPrediction().prediction === actualResult) {
            this.sessionStats.predictions.correct++;
        }
        this.sessionStats.predictions.accuracy = this.sessionStats.predictions.total > 0 ? 
            this.sessionStats.predictions.correct / this.sessionStats.predictions.total : 0;
    }
}

// ============================================================
// 📊 QUẢN LÝ LỊCH SỬ 50 PHIÊN
// ============================================================
const predictionSystem = new UltraDicePredictionSystem();
let sessionHistory = [];
let lastPrediction = { prediction: 'Chưa có', confidence: '0%', reasons: [] };

async function fetchAndUpdate() {
    try {
        console.log('🔄 Đang lấy dữ liệu từ API...');
        const response = await axios.get(API_URL, { timeout: 10000 });
        const data = response.data;
        
        if (!data.list || data.list.length === 0) {
            console.log('⚠️ Không có dữ liệu từ API');
            return null;
        }

        // Lấy 50 phiên mới nhất
        const latestSessions = data.list.slice(0, 50);
        console.log(`✅ Lấy được ${latestSessions.length} phiên`);

        // Reset history của prediction system
        predictionSystem.history = [];
        
        // Cập nhật history
        for (const item of latestSessions.reverse()) {
            const result = item.resultTruyenThong === "TAI" ? 'T' : 'X';
            predictionSystem.addResult(result);
        }

        // Dự đoán cho phiên tiếp theo
        const pred = predictionSystem.getFinalPrediction();
        const predictionStr = pred.prediction === 'T' ? 'Tài' : 'Xỉu';
        lastPrediction = {
            prediction: predictionStr,
            confidence: Math.round(pred.confidence * 100) + '%',
            reasons: pred.reasons || ['Không có lý do']
        };

        // Xây dựng lịch sử dự đoán đúng/sai
        const newHistory = [];
        const sortedSessions = latestSessions; // Đã đảo ngược ở trên
        
        for (let i = 0; i < Math.min(50, sortedSessions.length); i++) {
            const item = sortedSessions[i];
            const actual = item.resultTruyenThong === "TAI" ? 'Tài' : 'Xỉu';
            
            // Dùng model dự đoán cho phiên này (dựa trên lịch sử trước đó)
            // Tạo một instance tạm để dự đoán từng phiên
            const tempSystem = new UltraDicePredictionSystem();
            for (let j = 0; j < i; j++) {
                const prevResult = sortedSessions[j].resultTruyenThong === "TAI" ? 'T' : 'X';
                tempSystem.addResult(prevResult);
            }
            const tempPred = tempSystem.getFinalPrediction();
            const predicted = tempPred.prediction === 'T' ? 'Tài' : 'Xỉu';
            const correct = predicted === actual ? '✅' : '❌';
            
            newHistory.push({
                id: item.id || item._id || i,
                dice: item.dices || [],
                point: item.point || 0,
                actual: actual,
                predicted: predicted,
                correct: correct
            });
        }
        
        sessionHistory = newHistory.slice(0, 50);
        console.log(`✅ Đã cập nhật lịch sử ${sessionHistory.length} phiên`);
        return lastPrediction;
    } catch (error) {
        console.error('❌ Lỗi fetch API:', error.message);
        return null;
    }
}

// ============================================================
// 🤖 TELEGRAM BOT COMMANDS
// ============================================================

// Command /start
bot.onText(/\/start/, (msg) => {
    const chatId = msg.chat.id;
    bot.sendMessage(chatId, 
        `🎲 *SunWin AI Prediction Bot*\n\n` +
        `📌 *Lệnh:*\n` +
        `/du_doan - Xem dự đoán hiện tại\n` +
        `/lich_su - Xem 20 phiên gần nhất\n` +
        `/thong_ke - Thống kê tổng quan\n` +
        `/admin [key] - Đăng nhập admin\n` +
        `/reset - Reset hệ thống (admin)\n` +
        `/help - Hướng dẫn`,
        { parse_mode: 'Markdown' }
    );
});

// Command /du_doan
bot.onText(/\/du_doan/, async (msg) => {
    const chatId = msg.chat.id;
    const result = await fetchAndUpdate();
    if (!result) {
        bot.sendMessage(chatId, '❌ Không thể lấy dữ liệu. Thử lại sau.');
        return;
    }
    bot.sendMessage(chatId,
        `🎯 *DỰ ĐOÁN PHIÊN TIẾP THEO*\n\n` +
        `📊 Dự đoán: *${result.prediction}*\n` +
        `🎯 Độ tin cậy: *${result.confidence}*\n` +
        `📝 Lý do:\n${result.reasons.map(r => `- ${r}`).join('\n')}`,
        { parse_mode: 'Markdown' }
    );
});

// Command /lich_su
bot.onText(/\/lich_su/, async (msg) => {
    const chatId = msg.chat.id;
    if (sessionHistory.length === 0) {
        await fetchAndUpdate();
    }
    if (sessionHistory.length === 0) {
        bot.sendMessage(chatId, '📭 Chưa có dữ liệu. Vui lòng chờ cập nhật.');
        return;
    }
    let text = `📜 *LỊCH SỬ 20 PHIÊN GẦN NHẤT*\n\n`;
    const recent = sessionHistory.slice(0, 20);
    recent.forEach((item, index) => {
        const diceStr = item.dice.join('-');
        text += `${index+1}. 🎲 ${diceStr} | Điểm: ${item.point} | KQ: ${item.actual} | DĐ: ${item.predicted} ${item.correct}\n`;
    });
    bot.sendMessage(chatId, text, { parse_mode: 'Markdown' });
});

// Command /thong_ke
bot.onText(/\/thong_ke/, async (msg) => {
    const chatId = msg.chat.id;
    if (sessionHistory.length === 0) {
        await fetchAndUpdate();
    }
    const total = sessionHistory.length;
    const tai = sessionHistory.filter(s => s.actual === 'Tài').length;
    const xiu = sessionHistory.filter(s => s.actual === 'Xỉu').length;
    const dung = sessionHistory.filter(s => s.correct === '✅').length;
    const sai = sessionHistory.filter(s => s.correct === '❌').length;
    
    bot.sendMessage(chatId,
        `📊 *THỐNG KÊ TỔNG QUAN*\n\n` +
        `📌 Tổng phiên: ${total}\n` +
        `🟢 Tài: ${tai} (${total > 0 ? (tai/total*100).toFixed(1) : 0}%)\n` +
        `🔴 Xỉu: ${xiu} (${total > 0 ? (xiu/total*100).toFixed(1) : 0}%)\n\n` +
        `🎯 Dự đoán đúng: ${dung}\n` +
        `❌ Dự đoán sai: ${sai}\n` +
        `📈 Tỷ lệ chính xác: ${total > 0 ? (dung/total*100).toFixed(1) : 0}%\n\n` +
        `📊 Biến động: ${(predictionSystem.sessionStats.volatility * 100).toFixed(1)}%\n` +
        `🧠 Entropy: ${predictionSystem.sessionStats.entropy.toFixed(2)}`,
        { parse_mode: 'Markdown' }
    );
});

// Command /admin
bot.onText(/\/admin (.+)/, (msg, match) => {
    const chatId = msg.chat.id;
    const key = match[1];
    if (key === adminKey) {
        bot.sendMessage(chatId, '✅ *Đăng nhập admin thành công!*\nBạn có thể dùng lệnh `/reset` để reset hệ thống.', { parse_mode: 'Markdown' });
    } else {
        bot.sendMessage(chatId, '❌ Key không hợp lệ.');
    }
});

// Command /reset (chỉ admin - kiểm tra key trong tin nhắn trước đó)
let adminSessions = {};
bot.onText(/\/reset/, (msg) => {
    const chatId = msg.chat.id;
    // Kiểm tra xem user đã đăng nhập admin chưa (lưu tạm)
    // Đơn giản: yêu cầu nhập key trực tiếp
    bot.sendMessage(chatId, '⚠️ Vui lòng nhập key admin: `/admin [key]` trước khi reset.', { parse_mode: 'Markdown' });
});

// Command /help
bot.onText(/\/help/, (msg) => {
    const chatId = msg.chat.id;
    bot.sendMessage(chatId,
        `📖 *HƯỚNG DẪN SỬ DỤNG*\n\n` +
        `🔹 /start - Bắt đầu\n` +
        `🔹 /du_doan - Xem dự đoán\n` +
        `🔹 /lich_su - Xem lịch sử 20 phiên\n` +
        `🔹 /thong_ke - Xem thống kê\n` +
        `🔹 /admin [key] - Đăng nhập admin\n` +
        `🔹 /reset - Reset hệ thống (admin)\n` +
        `🔹 /help - Hướng dẫn`,
        { parse_mode: 'Markdown' }
    );
});

// ============================================================
// 🚀 CHẠY BOT & CẬP NHẬT ĐỊNH KỲ
// ============================================================
console.log('🤖 Bot đang chạy...');

// Cập nhật lần đầu
fetchAndUpdate().then(() => {
    console.log('✅ Đã cập nhật dữ liệu lần đầu');
    console.log(`📊 Dự đoán hiện tại: ${lastPrediction.prediction} (${lastPrediction.confidence})`);
});

// Cập nhật mỗi 60 giây
setInterval(async () => {
    const result = await fetchAndUpdate();
    if (result) {
        console.log(`🔄 Cập nhật: Dự đoán ${result.prediction} (${result.confidence})`);
    }
}, 60000);

console.log('✅ Bot sẵn sàng!');
console.log(`📡 Đang lắng nghe lệnh Telegram...`);
