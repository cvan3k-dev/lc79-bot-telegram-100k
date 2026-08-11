import random
import json
import os
from collections import deque
from datetime import datetime

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
        print(f"🧠 Đã khởi tạo {len(self.model_names)} models (bao gồm biến thể)")

    # ── KHỞI TẠO 150 MODELS ─────────────────────────────
    def init_all_models(self):
        # Định nghĩa 21 models cơ bản
        for i in range(1, 22):
            model_func = getattr(self, f'model_{i}', None)
            if model_func:
                self.models[f'model_{i}'] = model_func
                self.weights[f'model_{i}'] = 0.5 + random.random() * 0.4
                self.performance[f'model_{i}'] = self._create_performance()
                self.model_names.append(f'model_{i}')
        
        # Tạo thêm 129 models mở rộng (tổng 150)
        for i in range(22, 151):
            self.models[f'model_{i}'] = self._create_default_model(i)
            self.weights[f'model_{i}'] = 0.3 + random.random() * 0.5
            self.performance[f'model_{i}'] = self._create_performance()
            self.model_names.append(f'model_{i}')
        
        # Thêm các biến thể mini và support
        for i in range(1, 51):
            for variant in ['mini', 'support1', 'support2']:
                name = f'model_{i}_{variant}'
                self.models[name] = self._create_default_model(i, variant)
                self.weights[name] = 0.2 + random.random() * 0.4
                self.performance[name] = self._create_performance()
                self.model_names.append(name)

    def _create_performance(self):
        return {
            'correct': 0,
            'total': 0,
            'accuracy': 0,
            'streak': 0,
            'max_streak': 0,
            'recent_correct': 0,
            'recent_total': 0
        }

    def _create_default_model(self, index, variant='main'):
        def predict():
            if len(self.history) < 3:
                return None
            last = self.history[-1] if self.history else 'T'
            # Tạo dự đoán ngẫu nhiên có trọng số dựa trên index
            seed = (index * 7 + (1 if variant == 'mini' else 2 if variant == 'support1' else 3)) % 10
            pred = 'T' if (index + seed) % 2 == 0 else 'X'
            confidence = 0.4 + (index % 5) * 0.08
            return {
                'prediction': pred,
                'confidence': min(0.9, confidence),
                'reason': f'Model {index}{"-" + variant if variant != "main" else ""}'
            }
        return predict

    # ── 21 MODELS CÓ SẴN ──────────────────────────────────
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
        return {
            'prediction': pred,
            'confidence': 0.5 + conf * 0.3,
            'reason': f'Trend {t_count}T-{x_count}X'
        }

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
        return {
            'prediction': pred,
            'confidence': 0.5 + imbalance * 0.4,
            'reason': f'Chênh lệch {int(imbalance*100)}%'
        }

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
            return {
                'prediction': pred,
                'confidence': conf,
                'reason': f'Bẻ cầu sau {streak} phiên'
            }
        return None

    def model_7(self):
        if len(self.history) < 2:
            return None
        streak = self._calculate_streak()
        if 2 <= streak <= 5:
            pred = self.history[-1]
            return {
                'prediction': pred,
                'confidence': 0.5 + streak * 0.04,
                'reason': f'Theo streak {streak}'
            }
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
            return {
                'prediction': pred,
                'confidence': prob,
                'reason': f'XS bẻ {int(prob*100)}%'
            }
        return None

    def model_11(self):
        if len(self.history) < 10:
            return None
        recent = list(self.history)[-10:]
        changes = sum(1 for i in range(1, len(recent)) if recent[i] != recent[i-1])
        vol = changes / 9
        if vol > 0.6:
            return {
                'prediction': self.history[-1],
                'confidence': 0.55,
                'reason': 'Biến động cao'
            }
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
            return {
                'prediction': last,
                'confidence': acc,
                'reason': f'Hiệu suất {int(acc*100)}%'
            }
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
        return {
            'prediction': pred,
            'confidence': min(0.8, conf),
            'reason': f'Trend dài {t_count}T-{20-t_count}X'
        }

    def model_16(self):
        if len(self.history) < 8:
            return None
        streak = self._calculate_streak()
        if streak >= 3:
            pred = 'X' if self.history[-1] == 'T' else 'T'
            return {
                'prediction': pred,
                'confidence': 0.55 + streak * 0.02,
                'reason': 'Bẻ tổng hợp'
            }
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
            return {
                'prediction': pred,
                'confidence': 0.5 + diff / 30,
                'reason': f'Cân bằng {t_count}-{x_count}'
            }
        return None

    def model_18(self):
        if len(self.history) < 6:
            return None
        recent = list(self.history)[-6:]
        t_count = sum(1 for x in recent if x == 'T')
        pred = 'T' if t_count > 3 else 'X'
        return {
            'prediction': pred,
            'confidence': 0.5 + abs(t_count - 3) / 6,
            'reason': f'Trend ngắn {t_count}/6'
        }

    def model_19(self):
        patterns = self._detect_common_patterns()
        if patterns:
            best = patterns[0]
            return {
                'prediction': best['prediction'],
                'confidence': best['confidence'],
                'reason': f"Pattern {best['name']}"
            }
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
        return {
            'prediction': pred,
            'confidence': min(0.9, conf),
            'reason': f'Ensemble {len(top_models)} models'
        }

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
            return {
                'prediction': pred,
                'confidence': 0.5 + imbalance * 0.3,
                'reason': f'Cân bằng {t_count}-{x_count}'
            }
        return None

    # ── CORE FUNCTIONS ────────────────────────────────────
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
                
                # Cập nhật trọng số
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
            print(f"⚠️ Lỗi lưu lịch sử: {e}")

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
                print(f"✅ Đã tải {len(self.history)} phiên lịch sử")
        except Exception as e:
            print(f"⚠️ Lỗi tải lịch sử: {e}")
