import json
import os
from datetime import date

class QuotaTracker:
    def __init__(self, quota_file="daily_quota.json", max_daily=250):
        self.quota_file = quota_file
        self.max_daily = max_daily
        self.load_quota()
    
    def load_quota(self):
        """Load daily quota from file"""
        if os.path.exists(self.quota_file):
            try:
                with open(self.quota_file, 'r') as f:
                    data = json.load(f)
                    today = str(date.today())
                    if data.get('date') == today:
                        self.used_today = data.get('used', 0)
                    else:
                        self.used_today = 0
                        self.save_quota()  # Reset for new day
            except Exception:
                self.used_today = 0
        else:
            self.used_today = 0
    
    def save_quota(self):
        """Save current quota usage"""
        data = {
            'date': str(date.today()),
            'used': self.used_today
        }
        with open(self.quota_file, 'w') as f:
            json.dump(data, f)
    
    def can_process(self, count=1):
        """Check if we can process more requests"""
        return (self.used_today + count) <= self.max_daily
    
    def add_usage(self, count=1):
        """Add to usage count"""
        self.used_today += count
        self.save_quota()
    
    def get_remaining(self):
        """Get remaining quota for today"""
        return max(0, self.max_daily - self.used_today)
    
    def get_status(self):
        """Get current quota status"""
        return {
            'used': self.used_today,
            'max': self.max_daily,
            'remaining': self.get_remaining(),
            'date': str(date.today())
        }