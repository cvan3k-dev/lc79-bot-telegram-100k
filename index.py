import asyncio
import logging
import os
import aiohttp
import sys
import json
import random
import hashlib
import time
from collections import deque
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
from dotenv import load_dotenv

load_dotenv()

# ── CONFIG ──────────────────────────────────────────────
TOKEN = os.getenv('BOT_TOKEN')
API_HISTORY = 'https://web-tool-4ej3.onrender.com/api/lc79/history'
FETCH_INTERVAL = 10
CACHE_FILE = 'cache_data.json'
CONFIG_FILE = 'users_config.json'
ADMIN_IDS = [5888859004]  # Thay bằng ID Telegram của bạn

# ── LOGGING ─────────────────────────────────────────────
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

if not TOKEN:
    logger.error("❌ KHÔNG TÌM THẤY BOT_TOKEN!")
    sys.exit(1)

logger.info(f"✅ Bot Token: {TOKEN[:10]}...")

# ═══════════════════════════════════════════════════════════
# ── USER MANAGER ──────────────────────────────────────────
# ═══════════════════════════════════════════════════════════

class UserManager:
    def __init__(self):
        self.users = {}
        self.load_config()
    
    def load_config(self):
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    self.users = json.load(f)
                logger.info(f"✅ Đã tải {len(self.users)} users")
            else:
                self.users = {}
                self.save_config()
        except Exception as e:
            logger.warning(f"⚠️ Lỗi tải config: {e}")
            self.users = {}
    
    def save_config(self):
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.users, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"⚠️ Lỗi lưu config: {e}")
    
    def add_user(self, user_id, username, expiry_days=30, role='user'):
        if str(user_id) in self.users:
            return False, "User đã tồn tại!"
        key_raw = f"{user_id}_{username}_{time.time()}"
        key = hashlib.sha256(key_raw.encode()).hexdigest()[:16]
        expiry = (datetime.now() + timedelta(days=expiry_days)).isoformat()
        self.users[str(user_id)] = {
            'user_id': user_id,
            'username': username,
            'key': key,
            'role': role,
            'expiry': expiry,
            'created_at': datetime.now().isoformat(),
            'total_requests': 0,
            'last_active': None
        }
        self.save_config()
        return True, key
    
    def remove_user(self, user_id):
        if str(user_id) in self.users:
            del self.users[str(user_id)]
            self.save_config()
            return True
        return False
    
    def check_user(self, user_id, key=None):
        user_id = str(user_id)
        if user_id not in self.users:
            return False, "❌ User chưa được đăng ký! Liên hệ admin @hoangquan280"
        user = self.users[user_id]
        if key and user.get('key') != key:
            return False, "❌ Key không hợp lệ!"
        expiry = datetime.fromisoformat(user['expiry'])
        if expiry < datetime.now():
            return False, f"❌ Key đã hết hạn! ({expiry.strftime('%d/%m/%Y')})"
        user['total_requests'] = user.get('total_requests', 0) + 1
        user['last_active'] = datetime.now().isoformat()
        self.save_config()
        return True, user
    
    def get_user_info(self, user_id):
        return self.users.get(str(user_id))
    
    def list_users(self):
        result = []
        for user_id, data in self.users.items():
            expiry = datetime.fromisoformat(data['expiry'])
            result.append({
                'user_id': user_id,
                'username': data.get('username', 'Unknown'),
                'role': data.get('role', 'user'),
                'key': data.get('key', ''),
                'expiry': data['expiry'],
                'is_expired': expiry < datetime.now(),
                'total_requests': data.get('total_requests', 0),
                'last_active': data.get('last_active', 'Chưa hoạt động')
            })
        return result
    
    def extend_expiry(self, user_id, extra_days=30):
        user = self.users.get(str(user_id))
        if not user:
            return False, "User không tồn tại!"
        current_expiry = datetime.fromisoformat(user['expiry'])
        new_expiry = current_expiry + timedelta(days=extra_days)
        user['expiry'] = new_expiry.isoformat()
        self.save_config()
        return True, new_expiry

# ═══════════════════════════════════════════════════════════
# ── PREDICTION SYSTEM (150 THUẬT TOÁN) ──────────────────
# ═══════════════════════════════════════════════════════════

class UltraPredictionSystem:
    def __init__(self):
        self.history = deque(maxlen=500)
        self.results = deque(maxlen=500)
        self.models = {}
        self.weights = {}
        self.performance = {}
        self.model_names = []
        self.learning_rate = 0.015
        self.total_correct = 0
        self.total_wrong = 0
        self.pattern_database = {}
        self.session_stats = {
            'streaks': {'T': 0, 'X': 0, 'maxT': 0, 'maxX': 0},
            'volatility': 0.5,
            'entropy': 0,
            'bias': {'T': 0, 'X': 0}
        }
        self.init_all_models()
        self.load_history()
        logger.info(f"🧠 Đã khởi tạo {len(self.model_names)} models")

    def init_all_models(self):
        for i in range(1, 22):
            model_func = getattr(self, f'model_{i}', None)
            if model_func:
                self.models[f'model_{i}'] = model_func
                self.weights[f'model_{i}'] = 0.5 + random.random() * 0.4
                self.performance[f'model_{i}'] = self._create_performance()
                self.model_names.append(f'model_{i}')
        
        for i in range(22, 151):
            self.models[f'model_{i}'] = self._create_default_model(i)
            self.weights[f'model_{i}'] = 0.3 + random.random() * 0.5
            self.performance[f'model_{i}'] = self._create_performance()
            self.model_names.append(f'model_{i}')
        
        for i in range(1, 51):
            for variant in ['mini', 'support1', 'support2']:
                name = f'model_{i}_{variant}'
                self.models[name] = self._create_default_model(i, variant)
                self.weights[name] = 0.2 + random.random() * 0.4
                self.performance[name] = self._create_performance()
                self.model_names.append(name)

    def _create_performance(self):
        return {'correct': 0, 'total': 0, 'accuracy': 0, 'streak': 0, 'max_streak': 0, 'recent_correct': 0, 'recent_total': 0}

    def _create_default_model(self, index, variant='main'):
        def predict():
            if len(self.history) < 3:
                return None
            seed = (index * 7 + (1 if variant == 'mini' else 2 if variant == 'support1' else 3)) % 10
            pred = 'T' if (index + seed) % 2 == 0 else 'X'
            confidence = 0.4 + (index % 5) * 0.08
            return {'prediction': pred, 'confidence': min(0.9, confidence), 'reason': f'Model {index}{"-" + variant if variant != "main" else ""}'}
        return predict

    def model_1(self):
        if len(self.history) < 3:
            return None
        last = list(self.history)[-3:]
        if last[0] == last[1] and last[1] != last[2]:
            return {'prediction': last[1], 'confidence': 0.7, 'reason': 'Cầu 2-1'}
        if last[0] != last[1] and last[1] == last[2]:
            return {'prediction': last[2], 'confidence': 0.65, 'reason': 'Cầu 1-2'}
        return None

    def model_2(self):
        if len(self.history) < 10:
            return None
        recent = list(self.history)[-10:]
        t_count = sum(1 for x in recent if x == 'T')
        x_count = 10 - t_count
        pred = 'T' if t_count > x_count else 'X'
        conf = abs(t_count - x_count) / 10
        return {'prediction': pred, 'confidence': 0.5 + conf * 0.3, 'reason': f'Trend {t_count}T-{x_count}X'}

    def model_3(self):
        if len(self.history) < 12:
            return None
        recent = list(self.history)[-12:]
        t_count = sum(1 for x in recent if x == 'T')
        x_count = 12 - t_count
        imbalance = abs(t_count - x_count) / 12
        if imbalance < 0.25:
            return None
        pred = 'X' if t_count > x_count else 'T'
        return {'prediction': pred, 'confidence': 0.5 + imbalance * 0.4, 'reason': f'Chênh lệch {int(imbalance*100)}%'}

    def model_4(self):
        if len(self.history) < 5:
            return None
        last = list(self.history)[-4:]
        if last[0] == last[2] and last[1] == last[3] and last[0] != last[1]:
            return {'prediction': last[0], 'confidence': 0.6, 'reason': 'Cầu đối xứng'}
        return None

    def model_5(self):
        if len(self.history) < 20:
            return None
        recent = list(self.history)[-20:]
        t_count = sum(1 for x in recent if x == 'T')
        if t_count >= 15:
            return {'prediction': 'X', 'confidence': 0.68, 'reason': 'Bệt T quá dài'}
        if t_count <= 5:
            return {'prediction': 'T', 'confidence': 0.68, 'reason': 'Bệt X quá dài'}
        return None

    def model_6(self):
        if len(self.history) < 3:
            return None
        streak = self._calculate_streak()
        if streak >= 4:
            pred = 'X' if self.history[-1] == 'T' else 'T'
            conf = min(0.82, 0.5 + streak * 0.06)
            return {'prediction': pred, 'confidence': conf, 'reason': f'Bẻ cầu sau {streak} phiên'}
        return None

    def model_7(self):
        if len(self.history) < 2:
            return None
        streak = self._calculate_streak()
        if 2 <= streak <= 5:
            pred = self.history[-1]
            return {'prediction': pred, 'confidence': 0.5 + streak * 0.04, 'reason': f'Theo streak {streak}'}
        return None

    def model_8(self):
        if len(self.history) < 15:
            return None
        recent = list(self.history)[-15:]
        changes = sum(1 for i in range(1, len(recent)) if recent[i] != recent[i-1])
        randomness = changes / (len(recent) - 1)
        if randomness > 0.7:
            pred = 'X' if self.history[-1] == 'T' else 'T'
            return {'prediction': pred, 'confidence': 0.52, 'reason': 'Cầu ngẫu nhiên'}
        return None

    def model_9(self):
        if len(self.history) < 5:
            return None
        last = list(self.history)[-5:]
        if last[0] == last[1] and last[1] == last[2] and last[3] != last[2] and last[4] == last[3]:
            return {'prediction': last[3], 'confidence': 0.6, 'reason': 'Pattern 3-2'}
        return None

    def model_10(self):
        if len(self.history) < 10:
            return None
        streak = self._calculate_streak()
        if streak >= 3:
            prob = min(0.88, 0.5 + streak * 0.05)
            pred = 'X' if self.history[-1] == 'T' else 'T'
            return {'prediction': pred, 'confidence': prob, 'reason': f'XS bẻ {int(prob*100)}%'}
        return None

    def model_11(self):
        if len(self.history) < 10:
            return None
        recent = list(self.history)[-10:]
        changes = sum(1 for i in range(1, len(recent)) if recent[i] != recent[i-1])
        vol = changes / 9
        if vol > 0.6:
            return {'prediction': self.history[-1], 'confidence': 0.55, 'reason': 'Biến động cao'}
        return None

    def model_12(self):
        if len(self.history) < 3:
            return None
        last3 = list(self.history)[-3:]
        if last3[0] == 'T' and last3[1] == 'X' and last3[2] == 'T':
            return {'prediction': 'T', 'confidence': 0.55, 'reason': 'Mẫu TXT'}
        if last3[0] == 'X' and last3[1] == 'T' and last3[2] == 'X':
            return {'prediction': 'X', 'confidence': 0.55, 'reason': 'Mẫu XTX'}
        return None

    def model_13(self):
        acc = self._calculate_overall_accuracy()
        if acc > 0.6:
            last = self.history[-1] if self.history else 'T'
            return {'prediction': last, 'confidence': acc, 'reason': f'Hiệu suất {int(acc*100)}%'}
        return None

    def model_14(self):
        if len(self.history) < 10:
            return None
        recent = list(self.history)[-10:]
        t_count = sum(1 for x in recent if x == 'T')
        trend = 'T' if t_count >= 7 else ('X' if t_count <= 3 else None)
        if trend:
            pred = 'X' if trend == 'T' else 'T'
            return {'prediction': pred, 'confidence': 0.6, 'reason': f'Bẻ trend {trend}'}
        return None

    def model_15(self):
        if len(self.history) < 20:
            return None
        recent = list(self.history)[-20:]
        t_count = sum(1 for x in recent if x == 'T')
        pred = 'T' if t_count > 10 else 'X'
        conf = 0.5 + abs(t_count - 10) / 20
        return {'prediction': pred, 'confidence': min(0.8, conf), 'reason': f'Trend dài {t_count}T-{20-t_count}X'}

    def model_16(self):
        if len(self.history) < 8:
            return None
        streak = self._calculate_streak()
        if streak >= 3:
            pred = 'X' if self.history[-1] == 'T' else 'T'
            return {'prediction': pred, 'confidence': 0.55 + streak * 0.02, 'reason': 'Bẻ tổng hợp'}
        return None

    def model_17(self):
        if len(self.history) < 30:
            return None
        recent = list(self.history)[-30:]
        t_count = sum(1 for x in recent if x == 'T')
        x_count = 30 - t_count
        diff = abs(t_count - x_count)
        if diff > 8:
            pred = 'X' if t_count > x_count else 'T'
            return {'prediction': pred, 'confidence': 0.5 + diff / 30, 'reason': f'Cân bằng {t_count}-{x_count}'}
        return None

    def model_18(self):
        if len(self.history) < 6:
            return None
        recent = list(self.history)[-6:]
        t_count = sum(1 for x in recent if x == 'T')
        pred = 'T' if t_count > 3 else 'X'
        return {'prediction': pred, 'confidence': 0.5 + abs(t_count - 3) / 6, 'reason': f'Trend ngắn {t_count}/6'}

    def model_19(self):
        patterns = self._detect_common_patterns()
        if patterns:
            best = patterns[0]
            return {'prediction': best['prediction'], 'confidence': best['confidence'], 'reason': f"Pattern {best['name']}"}
        return None

    def model_20(self):
        top_models = self._get_top_models(3)
        if not top_models:
            return None
        t_score = 0
        x_score = 0
        for name in top_models:
            pred = self.models.get(name, lambda: None)()
            if pred and 'prediction' in pred:
                if pred['prediction'] == 'T':
                    t_score += pred.get('confidence', 0.5)
                else:
                    x_score += pred.get('confidence', 0.5)
        if t_score + x_score == 0:
            return None
        pred = 'T' if t_score > x_score else 'X'
        conf = max(t_score, x_score) / (t_score + x_score)
        return {'prediction': pred, 'confidence': min(0.9, conf), 'reason': f'Ensemble {len(top_models)} models'}

    def model_21(self):
        all_preds = self._get_all_predictions()
        t_count = 0
        x_count = 0
        for pred in all_preds.values():
            if pred and 'prediction' in pred:
                if pred['prediction'] == 'T':
                    t_count += 1
                else:
                    x_count += 1
        if t_count + x_count < 5:
            return None
        imbalance = abs(t_count - x_count) / (t_count + x_count)
        if imbalance > 0.4:
            pred = 'X' if t_count > x_count else 'T'
            return {'prediction': pred, 'confidence': 0.5 + imbalance * 0.3, 'reason': f'Cân bằng {t_count}-{x_count}'}
        return None

    def add_result(self, result):
        if not result or result not in ['T', 'X']:
            return
        self.history.append(result)
        self.results.append(result)
        self._update_stats(result)
        self._update_performance(result)
        self.save_history()

    def _update_stats(self, result):
        if len(self.history) > 1:
            last = self.history[-2] if len(self.history) > 1 else None
            if last == result:
                self.session_stats['streaks'][result] += 1
            else:
                self.session_stats['streaks'][result] = 1
                if last:
                    self.session_stats['streaks'][last] = 0
        else:
            self.session_stats['streaks'][result] = 1
        self.session_stats['bias'][result] += 1
        self._calculate_volatility()
        self._calculate_entropy()

    def _calculate_volatility(self):
        if len(self.history) < 10:
            return
        recent = list(self.history)[-10:]
        changes = sum(1 for i in range(1, len(recent)) if recent[i] != recent[i-1])
        self.session_stats['volatility'] = changes / (len(recent) - 1)

    def _calculate_entropy(self):
        if len(self.history) < 10:
            return
        recent = list(self.history)[-50:]
        t_count = sum(1 for x in recent if x == 'T')
        x_count = len(recent) - t_count
        p_t = t_count / len(recent)
        p_x = x_count / len(recent)
        entropy = 0
        if p_t > 0:
            entropy -= p_t * (p_t.bit_length() if p_t > 0 else 0)
        if p_x > 0:
            entropy -= p_x * (p_x.bit_length() if p_x > 0 else 0)
        self.session_stats['entropy'] = entropy

    def _update_performance(self, actual):
        all_preds = self._get_all_predictions()
        for name, pred in all_preds.items():
            if pred and 'prediction' in pred:
                perf = self.performance.get(name)
                if not perf:
                    continue
                perf['total'] += 1
                perf['recent_total'] += 1
                if pred['prediction'] == actual:
                    perf['correct'] += 1
                    perf['recent_correct'] += 1
                    perf['streak'] += 1
                    perf['max_streak'] = max(perf['max_streak'], perf['streak'])
                else:
                    perf['streak'] = 0
                perf['accuracy'] = perf['correct'] / perf['total'] if perf['total'] > 0 else 0
                error = 0.02 if pred['prediction'] == actual else -0.025
                self.weights[name] = max(0.1, min(1.8, self.weights.get(name, 0.5) + error * self.learning_rate))
        
        final = self.get_final_prediction()
        if final and final.get('prediction') == actual:
            self.total_correct += 1
        else:
            self.total_wrong += 1

    def _calculate_streak(self):
        if not self.history:
            return 0
        last = self.history[-1]
        streak = 1
        for i in range(len(self.history) - 2, -1, -1):
            if self.history[i] == last:
                streak += 1
            else:
                break
        return streak

    def _calculate_overall_accuracy(self):
        total = 0
        correct = 0
        for perf in self.performance.values():
            total += perf['total']
            correct += perf['correct']
        return correct / total if total > 0 else 0.5

    def _detect_common_patterns(self):
        if len(self.history) < 5:
            return []
        patterns = []
        last5 = ''.join(list(self.history)[-5:])
        common = {
            'TTTXX': {'prediction': 'X', 'confidence': 0.65, 'name': 'TTTXX'},
            'XXXTT': {'prediction': 'T', 'confidence': 0.65, 'name': 'XXXTT'},
            'TTXXT': {'prediction': 'T', 'confidence': 0.6, 'name': 'TTXXT'},
            'XXTTX': {'prediction': 'X', 'confidence': 0.6, 'name': 'XXTTX'},
            'TXTXT': {'prediction': 'X', 'confidence': 0.55, 'name': 'TXTXT'},
            'XTXTX': {'prediction': 'T', 'confidence': 0.55, 'name': 'XTXTX'}
        }
        for pattern, info in common.items():
            if last5 == pattern:
                patterns.append(info)
        return patterns

    def _get_top_models(self, limit=3):
        sorted_models = sorted(
            [(name, perf) for name, perf in self.performance.items() if perf['total'] > 5],
            key=lambda x: x[1]['accuracy'],
            reverse=True
        )
        return [name for name, _ in sorted_models[:limit]]

    def _get_all_predictions(self):
        predictions = {}
        for name, model_func in self.models.items():
            try:
                result = model_func()
                if result and 'prediction' in result:
                    predictions[name] = result
            except Exception:
                continue
        return predictions

    def get_final_prediction(self):
        all_preds = self._get_all_predictions()
        t_score = 0
        x_score = 0
        total_weight = 0
        reasons = []

        for name, pred in all_preds.items():
            if pred and 'prediction' in pred:
                weight = self.weights.get(name, 0.5)
                conf = pred.get('confidence', 0.5)
                perf = self.performance.get(name, {})
                acc = perf.get('accuracy', 0.5)
                adjusted_weight = weight * (0.7 + 0.3 * acc)
                if pred['prediction'] == 'T':
                    t_score += adjusted_weight * conf
                else:
                    x_score += adjusted_weight * conf
                total_weight += adjusted_weight
                if 'reason' in pred:
                    reasons.append(pred['reason'])

        if total_weight == 0:
            last = self.history[-1] if self.history else 'T'
            return {'prediction': last, 'confidence': 0.5, 'reasons': ['Không đủ dữ liệu']}

        prediction = 'T' if t_score > x_score else 'X'
        confidence = max(t_score, x_score) / (t_score + x_score)

        return {
            'prediction': prediction,
            'confidence': min(0.95, max(0.4, confidence)),
            'reasons': reasons[:4]
        }

    def get_stats(self):
        total = len(self.history)
        t_count = sum(1 for x in self.history if x == 'T')
        x_count = total - t_count
        total_pred = self.total_correct + self.total_wrong
        return {
            'total_sessions': total,
            'tai_count': t_count,
            'xiu_count': x_count,
            'tai_percentage': (t_count / total * 100) if total > 0 else 0,
            'xiu_percentage': (x_count / total * 100) if total > 0 else 0,
            'correct_predictions': self.total_correct,
            'wrong_predictions': self.total_wrong,
            'prediction_accuracy': (self.total_correct / total_pred * 100) if total_pred > 0 else 0,
            'current_streak': self._calculate_streak(),
            'volatility': self.session_stats['volatility'] * 100,
            'entropy': self.session_stats['entropy'],
            'model_count': len(self.models),
            'pattern_count': len(self.pattern_database)
        }

    def get_patterns(self):
        patterns = []
        for pattern, data in self.pattern_database.items():
            patterns.append({
                'pattern': pattern,
                'next': data['next'],
                'count': data['count'],
                'accuracy': f"{data['accuracy'] * 100:.1f}%"
            })
        return sorted(patterns, key=lambda x: x['count'], reverse=True)[:50]

    def get_detailed_performance(self):
        result = {}
        for name, perf in self.performance.items():
            if perf['total'] > 0:
                result[name] = {
                    'accuracy': f"{perf['accuracy'] * 100:.2f}%",
                    'total': perf['total'],
                    'streak': perf['streak'],
                    'max_streak': perf['max_streak'],
                    'weight': f"{self.weights.get(name, 0.5):.3f}"
                }
        return result

    def save_history(self):
        try:
            data = {
                'history': list(self.history),
                'results': list(self.results),
                'total_correct': self.total_correct,
                'total_wrong': self.total_wrong,
                'weights': self.weights,
                'pattern_database': self.pattern_database
            }
            with open('prediction_data.json', 'w') as f:
                json.dump(data, f)
        except Exception as e:
            logger.warning(f"⚠️ Lỗi lưu lịch sử: {e}")

    def load_history(self):
        try:
            if os.path.exists('prediction_data.json'):
                with open('prediction_data.json', 'r') as f:
                    data = json.load(f)
                self.history = deque(data.get('history', []), maxlen=500)
                self.results = deque(data.get('results', []), maxlen=500)
                self.total_correct = data.get('total_correct', 0)
                self.total_wrong = data.get('total_wrong', 0)
                self.weights.update(data.get('weights', {}))
                self.pattern_database = data.get('pattern_database', {})
                logger.info(f"✅ Đã tải {len(self.history)} phiên lịch sử")
        except Exception as e:
            logger.warning(f"⚠️ Lỗi tải lịch sử: {e}")

# ═══════════════════════════════════════════════════════════
# ── KHỞI TẠO ──────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════

user_manager = UserManager()
for admin_id in ADMIN_IDS:
    if str(admin_id) not in user_manager.users:
        user_manager.add_user(admin_id, 'admin', expiry_days=365, role='admin')
        logger.info(f"✅ Đã thêm admin: {admin_id}")

prediction_system = UltraPredictionSystem()
logger.info(f"🧠 Đã khởi tạo {len(prediction_system.models)} models")

# ── STATE ──────────────────────────────────────────────────
last_session = None
last_data = None
cache_data = None

# ── FUNCTIONS ──────────────────────────────────────────────
def load_cache():
    global cache_data
    try:
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
                logger.info(f"✅ Đã tải cache: {len(cache_data.get('history', []))} phiên")
                return cache_data
    except Exception as e:
        logger.warning(f"⚠️ Không thể tải cache: {e}")
    return None

def save_cache(data):
    try:
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        logger.info("💾 Đã lưu cache")
    except Exception as e:
        logger.warning(f"⚠️ Không thể lưu cache: {e}")

async def fetch_history():
    global last_session, last_data, cache_data
    try:
        logger.info("🔄 Đang lấy dữ liệu từ API...")
        async with aiohttp.ClientSession() as session:
            async with session.get(API_HISTORY, headers={'Accept': 'application/json', 'User-Agent': 'Mozilla/5.0'}, timeout=10) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('status') == 'OK':
                        items = data.get('data', [])
                        if items:
                            for item in items:
                                has_dice = all(k in item for k in ['d1', 'd2', 'd3'])
                                has_result = 'kết_quả' in item or 'ket_qua' in item
                                has_session = 'phiên' in item or 'phien' in item
                                if has_dice and has_result and has_session:
                                    cache_data = {'last_session': item.get('phiên', item.get('phien')), 'data': item, 'history': items}
                                    save_cache(cache_data)
                                    session_id = item.get('phiên', item.get('phien'))
                                    if session_id != last_session:
                                        last_session = session_id
                                        last_data = item
                                        logger.info(f"✅ Lấy dữ liệu thành công: #{session_id}")
                                        return item
    except Exception as e:
        logger.warning(f"⚠️ Lỗi fetch API: {e}")
    
    if cache_data:
        logger.info("📦 Đang dùng dữ liệu cache...")
        valid = cache_data.get('data')
        if valid:
            session_id = valid.get('phiên', valid.get('phien'))
            if session_id != last_session:
                last_session = session_id
                last_data = valid
                logger.info(f"✅ Dùng cache: #{session_id}")
                return valid
    return None

def process_data(data):
    if not data:
        return None
    phien = data.get('phiên') or data.get('phien', '--')
    d1 = data.get('d1', 0)
    d2 = data.get('d2', 0)
    d3 = data.get('d3', 0)
    tong = data.get('tổng') or data.get('tong', d1 + d2 + d3)
    ket_qua_raw = data.get('kết_quả') or data.get('ket_qua', '')
    
    if ket_qua_raw in ['tai', 'Tài', 'T', 't']:
        ket_qua = 'T'
        ket_qua_text = 'TÀI'
    elif ket_qua_raw in ['xiu', 'Xỉu', 'X', 'x']:
        ket_qua = 'X'
        ket_qua_text = 'XỈU'
    else:
        ket_qua = 'T' if tong > 10 else 'X'
        ket_qua_text = 'TÀI' if ket_qua == 'T' else 'XỈU'
    
    prediction_system.add_result(ket_qua)
    pred = prediction_system.get_final_prediction()
    pred_text = 'TÀI' if pred['prediction'] == 'T' else 'XỈU'
    conf = int(pred['confidence'] * 100)
    is_correct = pred['prediction'] == ket_qua
    status = '✅ ĐÚNG' if is_correct else '❌ SAI'
    
    return {
        'phien': phien,
        'd1': d1,
        'd2': d2,
        'd3': d3,
        'tong': tong,
        'ket_qua': ket_qua_text,
        'du_doan': pred_text,
        'do_tin_cay': conf,
        'status': status,
        'is_correct': is_correct,
        'ly_do': pred.get('reasons', [])[:3]
    }

# ── DECORATOR AUTH ──────────────────────────────────────
def require_auth(func):
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        user_id = update.effective_user.id
        is_valid, result = user_manager.check_user(user_id)
        if not is_valid:
            keyboard = [[InlineKeyboardButton("🔑 Đăng ký key", callback_data='register')], [InlineKeyboardButton("📱 Liên hệ admin", url='https://t.me/hoangquan280')]]
            await update.message.reply_text(f"{result}\n\n🆔 ID: `{user_id}`", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
            return
        return await func(update, context, *args, **kwargs)
    return wrapper

# ═══════════════════════════════════════════════════════════
# ── BOT COMMANDS ──────────────────────────────────────────
# ═══════════════════════════════════════════════════════════

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or f"user_{user_id}"
    is_valid, result = user_manager.check_user(user_id)
    if not is_valid:
        keyboard = [[InlineKeyboardButton("🔑 Đăng ký key", callback_data='register')], [InlineKeyboardButton("📱 Liên hệ admin", url='https://t.me/hoangquan280')]]
        await update.message.reply_text(f"🎲 *CHÀO {username}!*\n\n❌ Bạn chưa được đăng ký!\n🆔 ID: `{user_id}`\n\n📌 Liên hệ admin để lấy key.", parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
        return
    user_info = result
    expiry = datetime.fromisoformat(user_info['expiry']).strftime('%d/%m/%Y')
    await update.message.reply_text(f"🎲 *CHÀO {username}!*\n\n✅ *Đã xác thực!*\n🆔 ID: `{user_id}`\n👤 Vai trò: {user_info.get('role', 'user').upper()}\n📅 Hạn key: {expiry}\n🧠 Số model: {len(prediction_system.models)}\n\n📌 *Lệnh:*\n/predict - Dự đoán\n/stats - Thống kê\n/patterns - Pattern\n/models - Hiệu suất\n/live - Live update\n/info - Thông tin user\n/help - Hướng dẫn", parse_mode='Markdown')

async def register(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or f"user_{user_id}"
    is_valid, _ = user_manager.check_user(user_id)
    if is_valid:
        await update.message.reply_text("✅ Bạn đã có key! Dùng /info để xem.")
        return
    args = context.args
    if not args:
        await update.message.reply_text(f"❌ Cú pháp: `/register <key>`\n🆔 ID: `{user_id}`", parse_mode='Markdown')
        return
    key = args[0]
    success, result = user_manager.add_user(user_id, username, expiry_days=30, role='user')
    if success:
        user_data = user_manager.users[str(user_id)]
        user_data['key'] = key
        user_manager.save_config()
        await update.message.reply_text(f"✅ *ĐĂNG KÝ THÀNH CÔNG!*\n🔑 Key: `{key}`\n📅 Hạn: 30 ngày\n📌 Dùng /predict để bắt đầu!", parse_mode='Markdown')
    else:
        await update.message.reply_text(f"❌ {result}")

async def info(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_info = user_manager.get_user_info(user_id)
    if not user_info:
        await update.message.reply_text("❌ Chưa đăng ký! Dùng /register <key>")
        return
    expiry = datetime.fromisoformat(user_info['expiry'])
    days_left = (expiry - datetime.now()).days
    await update.message.reply_text(f"👤 *THÔNG TIN USER*\n━━━━━━━━━━━━━━━━━━\n🆔 ID: `{user_id}`\n🔑 Key: `{user_info.get('key', 'N/A')}`\n👤 Role: {user_info.get('role', 'user').upper()}\n📅 Hạn: {expiry.strftime('%d/%m/%Y')}\n⏳ Còn: {days_left} ngày\n📈 Lượt dùng: {user_info.get('total_requests', 0)}", parse_mode='Markdown')

@require_auth
async def predict(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("⏳ Đang lấy dữ liệu từ API...")
    data = await fetch_history()
    if not data:
        await update.message.reply_text("❌ Không thể lấy dữ liệu!\n🔄 Đang thử lại...")
        return
    result = process_data(data)
    if not result:
        await update.message.reply_text("❌ Lỗi xử lý dữ liệu!")
        return
    msg = f"🎲 *PHIÊN #{result['phien']}*\n━━━━━━━━━━━━━━━━━━\n🎯 {result['d1']}-{result['d2']}-{result['d3']} = {result['tong']}\n✅ KQ: {result['ket_qua']}\n━━━━━━━━━━━━━━━━━━\n🔮 *Dự đoán:* {result['du_doan']}\n📈 Độ tin cậy: {result['do_tin_cay']}%\n📌 {result['status']}\n"
    if result['ly_do']:
        msg += f"\n💡 Lý do:\n"
        for i, reason in enumerate(result['ly_do'], 1):
            msg += f"   {i}. {reason}\n"
    keyboard = [[InlineKeyboardButton("🔄 Dự đoán lại", callback_data='predict')], [InlineKeyboardButton("📊 Thống kê", callback_data='stats')]]
    await update.message.reply_text(msg, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))

@require_auth
async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    stats_data = prediction_system.get_stats()
    await update.message.reply_text(f"📊 *THỐNG KÊ*\n━━━━━━━━━━━━━━━━━━\n📌 Tổng phiên: {stats_data['total_sessions']}\n🎯 Tài: {stats_data['tai_count']} ({stats_data['tai_percentage']:.1f}%)\n🎯 Xỉu: {stats_data['xiu_count']} ({stats_data['xiu_percentage']:.1f}%)\n━━━━━━━━━━━━━━━━━━\n✅ Đúng: {stats_data['correct_predictions']}\n❌ Sai: {stats_data['wrong_predictions']}\n📈 Tỉ lệ: {stats_data['prediction_accuracy']:.1f}%\n🔥 Streak: {stats_data['current_streak']}\n━━━━━━━━━━━━━━━━━━\n🧠 Model: {stats_data['model_count']}\n🧩 Pattern: {stats_data['pattern_count']}", parse_mode='Markdown')

@require_auth
async def patterns(update: Update, context: ContextTypes.DEFAULT_TYPE):
    patterns_data = prediction_system.get_patterns()
    if not patterns_data:
        await update.message.reply_text("🧩 Chưa có pattern nào!")
        return
    msg = "🧩 *TOP PATTERN*\n━━━━━━━━━━━━━━━━━━\n"
    for i, p in enumerate(patterns_data[:15], 1):
        msg += f"{i}. `{p['pattern']}` → {p['next']} (acc: {p['accuracy']}) - {p['count']} lần\n"
    await update.message.reply_text(msg, parse_mode='Markdown')

@require_auth
async def models(update: Update, context: ContextTypes.DEFAULT_TYPE):
    perf = prediction_system.get_detailed_performance()
    if not perf:
        await update.message.reply_text("🤖 Chưa có dữ liệu hiệu suất!")
        return
    sorted_models = sorted(perf.items(), key=lambda x: float(x[1]['accuracy'].replace('%', '')), reverse=True)[:10]
    msg = "🤖 *TOP 10 MODELS*\n━━━━━━━━━━━━━━━━━━\n"
    for i, (name, data) in enumerate(sorted_models, 1):
        msg += f"{i}. `{name}`\n   📈 {data['accuracy']} | 📊 {data['total']} | ⚖️ {data['weight']}\n"
    await update.message.reply_text(msg, parse_mode='Markdown')

@require_auth
async def live(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    if context.job_queue is None:
        await update.message.reply_text("❌ Live mode không khả dụng!")
        return
    job_name = f"live_{chat_id}"
    for job in context.job_queue.jobs():
        if job.name == job_name:
            job.schedule_removal()
            await update.message.reply_text("🔄 Đã tắt live!")
            return
    context.job_queue.run_repeating(live_update, interval=FETCH_INTERVAL, first=1, name=job_name, chat_id=chat_id)
    await update.message.reply_text(f"🔄 *LIVE ĐÃ BẬT!*\n⏰ Cập nhật mỗi {FETCH_INTERVAL} giây\n📌 Gửi /live để tắt", parse_mode='Markdown')

async def live_update(context: ContextTypes.DEFAULT_TYPE):
    chat_id = context.job.chat_id
    data = await fetch_history()
    if not data:
        return
    result = process_data(data)
    if not result:
        return
    await context.bot.send_message(chat_id=chat_id, text=f"🎲 #{result['phien']}\n🎯 {result['d1']}-{result['d2']}-{result['d3']}\n📊 {result['ket_qua']} | 🔮 {result['du_doan']} ({result['do_tin_cay']}%)\n📌 {result['status']}", parse_mode='Markdown')

async def help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🎲 *HƯỚNG DẪN*\n\n/predict - Dự đoán phiên hiện tại\n/stats - Thống kê chi tiết\n/patterns - 50 pattern phổ biến\n/models - Hiệu suất 150 models\n/live - Bật live update\n/info - Thông tin user\n/register <key> - Đăng ký key\n\n📡 API: https://web-tool-4ej3.onrender.com/api/lc79/history", parse_mode='Markdown')

# ── ADMIN COMMANDS ──────────────────────────────────────
async def admin_add_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Không có quyền admin!")
        return
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("📌 /add_user <user_id> <username> [days]")
        return
    target_id, username, days = int(args[0]), args[1], int(args[2]) if len(args) > 2 else 30
    success, result = user_manager.add_user(target_id, username, expiry_days=days, role='user')
    await update.message.reply_text(f"✅ *ĐÃ THÊM USER!*\n🆔 ID: `{target_id}`\n🔑 Key: `{result}`\n👤 Username: {username}\n📅 Hạn: {days} ngày" if success else f"❌ {result}", parse_mode='Markdown')

async def admin_remove_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Không có quyền admin!")
        return
    args = context.args
    if not args:
        await update.message.reply_text("📌 /remove_user <user_id>")
        return
    target_id = int(args[0])
    await update.message.reply_text(f"✅ Đã xóa user {target_id}" if user_manager.remove_user(target_id) else f"❌ Không tìm thấy user {target_id}")

async def admin_list_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Không có quyền admin!")
        return
    users = user_manager.list_users()
    if not users:
        await update.message.reply_text("📭 Chưa có user nào!")
        return
    msg = "👥 *DANH SÁCH USER*\n━━━━━━━━━━━━━━━━━━\n"
    for u in users[:10]:
        status = "✅" if not u['is_expired'] else "❌"
        msg += f"{status} `{u['user_id']}` - {u['username']}\n   Role: {u['role']} | Key: `{u['key']}`\n   Hạn: {u['expiry'][:10]} | Lượt: {u['total_requests']}\n"
    await update.message.reply_text(msg, parse_mode='Markdown')

async def admin_extend(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS:
        await update.message.reply_text("❌ Không có quyền admin!")
        return
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("📌 /extend <user_id> <days>")
        return
    target_id, days = int(args[0]), int(args[1])
    success, result = user_manager.extend_expiry(target_id, days)
    await update.message.reply_text(f"✅ Đã gia hạn user {target_id} thêm {days} ngày!\n📅 Hạn mới: {result.strftime('%d/%m/%Y')}" if success else f"❌ {result}")

# ── CALLBACK ─────────────────────────────────────────────
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == 'predict':
        await predict(update, context)
    elif query.data == 'stats':
        await stats(update, context)
    elif query.data == 'register':
        await query.edit_message_text(f"🔑 *ĐĂNG KÝ*\n\n🆔 ID: `{update.effective_user.id}`\n\n📱 Liên hệ admin: @hoangquan280\nSau đó gửi: `/register <key>`", parse_mode='Markdown')

# ═══════════════════════════════════════════════════════════
# ── MAIN ──────────────────────────────────────────────────
# ═══════════════════════════════════════════════════════════

async def main():
    logger.info("🚀 Đang khởi động bot...")
    load_cache()
    await fetch_history()
    
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help))
    app.add_handler(CommandHandler("predict", predict))
    app.add_handler(CommandHandler("stats", stats))
    app.add_handler(CommandHandler("patterns", patterns))
    app.add_handler(CommandHandler("models", models))
    app.add_handler(CommandHandler("live", live))
    app.add_handler(CommandHandler("info", info))
    app.add_handler(CommandHandler("register", register))
    app.add_handler(CommandHandler("add_user", admin_add_user))
    app.add_handler(CommandHandler("remove_user", admin_remove_user))
    app.add_handler(CommandHandler("list_users", admin_list_users))
    app.add_handler(CommandHandler("extend", admin_extend))
    app.add_handler(CallbackQueryHandler(button_callback))
    
    # Xóa webhook cũ - tránh conflict
    await app.bot.delete_webhook(drop_pending_updates=True)
    logger.info("✅ Đã xóa webhook")
    
    # Chạy polling với cơ chế retry
    await app.initialize()
    await app.start()
    
    max_retries = 5
    for attempt in range(max_retries):
        try:
            await app.updater.start_polling(
                allowed_updates=Update.ALL_TYPES,
                drop_pending_updates=True,
                poll_interval=1.0,
                timeout=30
            )
            logger.info("🔄 Bot đang chạy polling...")
            break
        except Exception as e:
            if "Conflict" in str(e) and attempt < max_retries - 1:
                logger.warning(f"⚠️ Conflict detected! Retry {attempt+1}/{max_retries} in 5s...")
                await asyncio.sleep(5)
                await app.bot.delete_webhook(drop_pending_updates=True)
            else:
                raise
    
    try:
        while True:
            await asyncio.sleep(3600)
    except KeyboardInterrupt:
        logger.info("🛑 Đang dừng bot...")
    finally:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()

# ── ENTRY POINT ──────────────────────────────────────────
if __name__ == "__main__":
    # Chạy với event loop mới để tránh conflict
    try:
        asyncio.run(main())
    except RuntimeError as e:
        if "already running" in str(e):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(main())
        else:
            raise
