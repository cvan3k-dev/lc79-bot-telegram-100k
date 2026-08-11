import json
import os
from datetime import datetime, timedelta

# ── CONFIG ──────────────────────────────────────────────
CONFIG_FILE = 'users_config.json'
ADMIN_IDS = [5888859004]  # Thay bằng ID Telegram của bạn

# ── USER MANAGEMENT ─────────────────────────────────────
class UserManager:
    def __init__(self):
        self.users = {}
        self.load_config()
    
    def load_config(self):
        """Tải cấu hình user từ file"""
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    self.users = json.load(f)
                print(f"✅ Đã tải {len(self.users)} users")
            else:
                self.users = {}
                self.save_config()
        except Exception as e:
            print(f"⚠️ Lỗi tải config: {e}")
            self.users = {}
    
    def save_config(self):
        """Lưu cấu hình user vào file"""
        try:
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.users, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️ Lỗi lưu config: {e}")
    
    def add_user(self, user_id, username, expiry_days=30, role='user'):
        """Thêm user mới với key và thời hạn"""
        if str(user_id) in self.users:
            return False, "User đã tồn tại!"
        
        # Tạo key ngẫu nhiên
        import hashlib
        import time
        key_raw = f"{user_id}_{username}_{time.time()}"
        key = hashlib.sha256(key_raw.encode()).hexdigest()[:16]
        
        expiry = (datetime.now() + timedelta(days=expiry_days)).isoformat()
        
        self.users[str(user_id)] = {
            'user_id': user_id,
            'username': username,
            'key': key,
            'role': role,  # admin, vip, user
            'expiry': expiry,
            'created_at': datetime.now().isoformat(),
            'total_requests': 0,
            'last_active': None
        }
        self.save_config()
        return True, key
    
    def remove_user(self, user_id):
        """Xóa user"""
        if str(user_id) in self.users:
            del self.users[str(user_id)]
            self.save_config()
            return True
        return False
    
    def check_user(self, user_id, key=None):
        """Kiểm tra quyền user"""
        user_id = str(user_id)
        
        if user_id not in self.users:
            return False, "❌ User chưa được đăng ký! Liên hệ admin @hoangquan280"
        
        user = self.users[user_id]
        
        # Kiểm tra key nếu có
        if key and user.get('key') != key:
            return False, "❌ Key không hợp lệ!"
        
        # Kiểm tra thời hạn
        expiry = datetime.fromisoformat(user['expiry'])
        if expiry < datetime.now():
            return False, f"❌ Key đã hết hạn! ({expiry.strftime('%d/%m/%Y')})"
        
        # Cập nhật hoạt động
        user['total_requests'] = user.get('total_requests', 0) + 1
        user['last_active'] = datetime.now().isoformat()
        self.save_config()
        
        return True, user
    
    def get_user_info(self, user_id):
        """Lấy thông tin user"""
        return self.users.get(str(user_id))
    
    def list_users(self):
        """Danh sách tất cả user"""
        result = []
        for user_id, data in self.users.items():
            expiry = datetime.fromisoformat(data['expiry'])
            is_expired = expiry < datetime.now()
            result.append({
                'user_id': user_id,
                'username': data.get('username', 'Unknown'),
                'role': data.get('role', 'user'),
                'key': data.get('key', ''),
                'expiry': data['expiry'],
                'is_expired': is_expired,
                'total_requests': data.get('total_requests', 0),
                'last_active': data.get('last_active', 'Chưa hoạt động')
            })
        return result
    
    def extend_expiry(self, user_id, extra_days=30):
        """Gia hạn key"""
        user = self.users.get(str(user_id))
        if not user:
            return False, "User không tồn tại!"
        
        current_expiry = datetime.fromisoformat(user['expiry'])
        new_expiry = current_expiry + timedelta(days=extra_days)
        user['expiry'] = new_expiry.isoformat()
        self.save_config()
        return True, new_expiry

# ── KHỞI TẠO ──────────────────────────────────────────────
user_manager = UserManager()

# Thêm admin mặc định nếu chưa có
for admin_id in ADMIN_IDS:
    if str(admin_id) not in user_manager.users:
        user_manager.add_user(admin_id, 'admin', expiry_days=365, role='admin')
        print(f"✅ Đã thêm admin: {admin_id}")
