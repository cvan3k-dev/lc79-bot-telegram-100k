import math
from collections import defaultdict

class UltraDicePredictionSystem:
    def __init__(self):
        self.history = []
        self.models = {}
        self.weights = {}
        self.performance = {}
        self.max_history_size = 50
        
        self.session_stats = {
            'streaks': {'T': 0, 'X': 0, 'maxT': 0, 'maxX': 0},
            'volatility': 0.5,
            'entropy': 0,
            'bias': {'T': 0, 'X': 0},
            'predictions': {'total': 0, 'correct': 0, 'accuracy': 0}
        }
        
        self.init_all_models()

    def init_all_models(self):
        for i in range(1, 22):
            model_name = f'model{i}'
            self.models[model_name] = getattr(self, model_name, self._default_model)
            self.weights[model_name] = 1.0
            self.performance[model_name] = {
                'correct': 0, 'total': 0, 'accuracy': 0, 'streak': 0
            }

    def _default_model(self):
        return None

    def add_result(self, result):
        self.history.append(result)
        if len(self.history) > self.max_history_size:
            self.history.pop(0)
        self._update_stats(result)

    def _update_stats(self, result):
        if len(self.history) > 1:
            last = self.history[-2]
            if result == last:
                self.session_stats['streaks'][result] += 1
            else:
                self.session_stats['streaks'][result] = 1
                self.session_stats['streaks'][last] = 0
        else:
            self.session_stats['streaks'][result] = 1
        
        self.session_stats['bias'][result] += 1
        self._calculate_volatility()
        self._calculate_entropy()

    def _calculate_volatility(self):
        if len(self.history) < 10:
            return
        recent = self.history[-10:]
        changes = sum(1 for i in range(1, len(recent)) if recent[i] != recent[i-1])
        self.session_stats['volatility'] = changes / (len(recent) - 1)

    def _calculate_entropy(self):
        if len(self.history) < 10:
            return
        recent = self.history[-50:]
        t_count = recent.count('T')
        x_count = recent.count('X')
        total = len(recent)
        pT = t_count / total
        pX = x_count / total
        entropy = 0
        if pT > 0:
            entropy -= pT * math.log2(pT)
        if pX > 0:
            entropy -= pX * math.log2(pX)
        self.session_stats['entropy'] = entropy

    # ===== MODELS 1-21 =====
    
    def model1(self):
        patterns = self._detect_basic_patterns()
        if not patterns:
            return None
        return {
            'prediction': patterns[0]['prediction'],
            'confidence': 0.7,
            'reason': f"Pattern {patterns[0]['name']}"
        }

    def model2(self):
        short_term = self._analyze_trend(10)
        long_term = self._analyze_trend(30)
        if short_term['strength'] > long_term['strength']:
            return {
                'prediction': short_term['direction'],
                'confidence': short_term['strength'],
                'reason': 'Trend ngắn hạn'
            }
        return {
            'prediction': long_term['direction'],
            'confidence': long_term['strength'],
            'reason': 'Trend dài hạn'
        }

    def model3(self):
        analysis = self._analyze_imbalance(12)
        if analysis['imbalance'] < 0.4:
            return None
        return {
            'prediction': analysis['prediction'],
            'confidence': analysis['imbalance'] * 0.8,
            'reason': 'Chênh lệch cao'
        }

    def model4(self):
        analysis = self._analyze_short_term_pattern(6)
        if analysis['confidence'] < 0.6:
            return None
        return {
            'prediction': analysis['prediction'],
            'confidence': analysis['confidence'],
            'reason': 'Cầu ngắn hạn'
        }

    def model5(self):
        predictions = self.get_all_predictions()
        t_count = sum(1 for p in predictions.values() if p and p.get('prediction') == 'T')
        x_count = sum(1 for p in predictions.values() if p and p.get('prediction') == 'X')
        total = t_count + x_count
        if total < 5:
            return None
        imbalance = abs(t_count - x_count) / total
        if imbalance > 0.6:
            return {
                'prediction': 'X' if t_count > x_count else 'T',
                'confidence': imbalance * 0.9,
                'reason': 'Cân bằng dự đoán'
            }
        return None

    def model6(self):
        streak = self._calculate_current_streak()
        break_prob = self._calculate_break_probability()
        if streak >= 5 and break_prob > 0.7:
            return {
                'prediction': 'X' if self.history[-1] == 'T' else 'T',
                'confidence': break_prob * 0.8,
                'reason': f'Bẻ cầu streak {streak}'
            }
        return {
            'prediction': self.history[-1] if self.history else 'T',
            'confidence': 0.6,
            'reason': 'Tiếp streak'
        }

    def model7(self):
        return None

    def model8(self):
        randomness = self._measure_randomness(30)
        if randomness > 0.7:
            return {
                'prediction': None,
                'confidence': 0,
                'reason': f'Cầu xấu - ngẫu nhiên {round(randomness*100)}%'
            }
        return None

    def model9(self):
        return None

    def model10(self):
        break_prob = self._calculate_break_probability()
        return {
            'prediction': None,
            'confidence': break_prob,
            'reason': f'Xác suất bẻ cầu: {round(break_prob*100)}%'
        }

    def model11(self):
        volatility = self._analyze_volatility()
        return {
            'prediction': self.history[-1] if self.history else 'T',
            'confidence': 0.5 + (1 - volatility['value']) * 0.3,
            'reason': f"Biến động {volatility['level']}"
        }

    def model12(self):
        short_patterns = self._detect_short_patterns(8)
        if not short_patterns:
            return None
        return {
            'prediction': short_patterns[0]['prediction'],
            'confidence': 0.65,
            'reason': f"Mẫu ngắn: {short_patterns[0]['pattern']}"
        }

    def model13(self):
        return None

    def model14(self):
        trend_break = self._calculate_trend_break_probability()
        return {
            'prediction': trend_break['prediction'],
            'confidence': trend_break['probability'],
            'reason': f"Bẻ trend {round(trend_break['probability']*100)}%"
        }

    def model15(self):
        trend = self._analyze_trend(10)
        return {
            'prediction': trend['direction'],
            'confidence': trend['strength'],
            'reason': f"Theo trend {trend['direction']}"
        }

    def model16(self):
        break_prob = self._calculate_comprehensive_break_probability()
        return {
            'prediction': break_prob['prediction'],
            'confidence': break_prob['probability'],
            'reason': f"Bẻ tổng hợp {round(break_prob['probability']*100)}%"
        }

    def model17(self):
        return None

    def model18(self):
        short_trend = self._analyze_short_term_trend(6)
        return {
            'prediction': short_trend['prediction'],
            'confidence': short_trend['confidence'],
            'reason': f"Xu hướng ngắn: {short_trend['direction']}"
        }

    def model19(self):
        popular_trends = self._identify_popular_trends()
        if not popular_trends:
            return None
        return {
            'prediction': popular_trends[0]['prediction'],
            'confidence': popular_trends[0]['confidence'],
            'reason': f"Xu hướng phổ biến: {popular_trends[0]['pattern']}"
        }

    def model20(self):
        top_models = self._get_top_performing_models(3)
        if not top_models:
            return None
        t_score = 0
        x_score = 0
        for model in top_models:
            pred = self.models[model['name']]()
            if pred and pred.get('prediction'):
                if pred['prediction'] == 'T':
                    t_score += pred['confidence']
                else:
                    x_score += pred['confidence']
        return {
            'prediction': 'T' if t_score > x_score else 'X',
            'confidence': max(t_score, x_score) / (t_score + x_score) if (t_score + x_score) > 0 else 0.5,
            'reason': f"Ensemble top {len(top_models)} models"
        }

    def model21(self):
        global_imbalance = self._measure_global_imbalance()
        if global_imbalance > 0.4:
            balanced = self._global_balancing()
            return {
                'prediction': balanced['prediction'],
                'confidence': balanced['confidence'],
                'reason': f"Cân bằng tổng thể {round(global_imbalance*100)}%"
            }
        return None

    # ===== UTILITY FUNCTIONS =====

    def _analyze_trend(self, period):
        if len(self.history) < period:
            return {'direction': 'T', 'strength': 0.5}
        segment = self.history[-period:]
        t_count = segment.count('T')
        x_count = segment.count('X')
        direction = 'T' if t_count > x_count else 'X'
        strength = abs(t_count - x_count) / period
        return {'direction': direction, 'strength': strength}

    def _analyze_imbalance(self, period):
        if len(self.history) < period:
            return {'imbalance': 0, 'prediction': 'T'}
        segment = self.history[-period:]
        t_count = segment.count('T')
        x_count = segment.count('X')
        imbalance = abs(t_count - x_count) / period
        prediction = 'X' if t_count > x_count else 'T'
        return {'imbalance': imbalance, 'prediction': prediction}

    def _analyze_short_term_pattern(self, period):
        if len(self.history) < period:
            return {'prediction': 'T', 'confidence': 0.5}
        last = self.history[-1]
        return {'prediction': last, 'confidence': 0.6}

    def _calculate_current_streak(self):
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

    def _calculate_break_probability(self):
        if len(self.history) < 10:
            return 0.5
        streak = self._calculate_current_streak()
        if streak >= 7:
            return 0.8
        if streak >= 5:
            return 0.7
        if streak >= 4:
            return 0.6
        return 0.5

    def _measure_randomness(self, period):
        if len(self.history) < period:
            return 0.5
        segment = self.history[-period:]
        changes = sum(1 for i in range(1, len(segment)) if segment[i] != segment[i-1])
        return changes / (len(segment) - 1)

    def _analyze_volatility(self):
        value = self.session_stats['volatility']
        level = 'medium'
        if value < 0.3:
            level = 'low'
        elif value > 0.7:
            level = 'high'
        return {'level': level, 'value': value}

    def _detect_basic_patterns(self):
        patterns = []
        basic_patterns = {
            '1-1': {'pattern': ['T', 'X', 'T', 'X'], 'prediction': 'T'},
            '1-2-1': {'pattern': ['T', 'X', 'X', 'T'], 'prediction': 'X'},
            '2-1-2': {'pattern': ['T', 'T', 'X', 'T', 'T'], 'prediction': 'X'},
            '3-1': {'pattern': ['T', 'T', 'T', 'X'], 'prediction': 'T'},
            '1-3': {'pattern': ['T', 'X', 'X', 'X'], 'prediction': 'T'}
        }
        for name, info in basic_patterns.items():
            if len(self.history) >= len(info['pattern']):
                last_segment = self.history[-(len(info['pattern']) - 1):]
                pattern_without_last = info['pattern'][:-1]
                if last_segment == pattern_without_last:
                    patterns.append({
                        'name': name,
                        'prediction': info['prediction']
                    })
        return patterns

    def _detect_short_patterns(self, length):
        if len(self.history) < 3:
            return []
        patterns = []
        last3 = '-'.join(self.history[-3:])
        if last3 in ['T-X-T', 'X-T-X']:
            patterns.append({
                'pattern': last3,
                'prediction': 'X' if last3[-1] == 'T' else 'T'
            })
        return patterns

    def _identify_popular_trends(self):
        if len(self.history) < 10:
            return []
        trends = []
        recent = self.history[-10:]
        t_count = recent.count('T')
        if t_count > 7:
            trends.append({'pattern': 'T nhiều', 'prediction': 'T', 'confidence': 0.7})
        elif t_count < 3:
            trends.append({'pattern': 'X nhiều', 'prediction': 'X', 'confidence': 0.7})
        return trends

    def _calculate_trend_break_probability(self):
        trend = self._analyze_trend(10)
        return {
            'probability': 0.5,
            'prediction': 'X' if trend['direction'] == 'T' else 'T'
        }

    def _calculate_comprehensive_break_probability(self):
        return {
            'probability': 0.5,
            'prediction': 'X' if self.history and self.history[-1] == 'T' else 'T'
        }

    def _analyze_short_term_trend(self, period):
        trend = self._analyze_trend(period)
        return {
            'direction': trend['direction'],
            'prediction': trend['direction'],
            'confidence': trend['strength']
        }

    def _get_top_performing_models(self, limit=3):
        sorted_models = sorted(
            [(name, perf) for name, perf in self.performance.items() if perf['total'] > 0],
            key=lambda x: x[1]['accuracy'],
            reverse=True
        )[:limit]
        return [{'name': name} for name, _ in sorted_models]

    def _measure_global_imbalance(self):
        if not self.history:
            return 0
        t_count = self.history.count('T')
        x_count = self.history.count('X')
        return abs(t_count - x_count) / len(self.history)

    def _global_balancing(self):
        return {
            'prediction': self.history[-1] if self.history else 'T',
            'confidence': 0.5
        }

    def get_all_predictions(self):
        predictions = {}
        for name, model_func in self.models.items():
            try:
                predictions[name] = model_func()
            except:
                pass
        return predictions

    def get_final_prediction(self):
        predictions = self.get_all_predictions()
        t_score = 0
        x_score = 0
        total_weight = 0
        reasons = []
        
        for model, pred in predictions.items():
            if pred and pred.get('prediction'):
                weight = self.weights.get(model, 1.0)
                if pred['prediction'] == 'T':
                    t_score += weight * pred.get('confidence', 0.5)
                else:
                    x_score += weight * pred.get('confidence', 0.5)
                total_weight += weight
                if pred.get('reason'):
                    reasons.append(f"{model}: {pred['reason']}")
        
        if total_weight == 0:
            return {
                'prediction': self.history[-1] if self.history else 'T',
                'confidence': 0.5,
                'reasons': ['Không đủ dữ liệu']
            }
        
        prediction = 'T' if t_score > x_score else 'X'
        confidence = max(t_score, x_score) / (t_score + x_score) if (t_score + x_score) > 0 else 0.5
        confidence = min(0.95, max(0.5, confidence))
        
        return {
            'prediction': prediction,
            'confidence': confidence,
            'reasons': reasons[:3]
        }

    def update_performance(self, actual_result):
        predictions = self.get_all_predictions()
        for model, pred in predictions.items():
            if pred and pred.get('prediction'):
                perf = self.performance.get(model)
                if not perf:
                    continue
                perf['total'] += 1
                if pred['prediction'] == actual_result:
                    perf['correct'] += 1
                    perf['streak'] += 1
                else:
                    perf['streak'] = 0
                perf['accuracy'] = perf['correct'] / perf['total'] if perf['total'] > 0 else 0
        
        self.session_stats['predictions']['total'] += 1
        if self.get_final_prediction()['prediction'] == actual_result:
            self.session_stats['predictions']['correct'] += 1
        
        total = self.session_stats['predictions']['total']
        correct = self.session_stats['predictions']['correct']
        self.session_stats['predictions']['accuracy'] = correct / total if total > 0 else 0
