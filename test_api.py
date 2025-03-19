import time
from pprint import pprint

import requests

# API基本URL
BASE_URL = "http://localhost:8000/api"


def test_health_check():
    """測試健康檢查端點"""
    url = f"{BASE_URL}/health-check"
    response = requests.get(url)

    print("\n--- 健康檢查測試 ---")
    print(f"狀態碼: {response.status_code}")
    try:
        pprint(response.json())
    except Exception:
        print(f"無法解析JSON響應: {response.text}")

    return response.status_code == 200


def register_user():
    """註冊新用戶"""
    url = f"{BASE_URL}/auth/register"
    data = {
        "username": "testuser",
        "email": "test@example.com",
        "password": "Secure123!",
        "first_name": "Test",
        "last_name": "User",
    }

    response = requests.post(url, json=data)

    print("\n--- 用戶註冊測試 ---")
    print(f"狀態碼: {response.status_code}")

    try:
        result = response.json()
        pprint(result)
        if response.status_code == 200:
            return result.get("access_token")
        else:
            print("註冊失敗，嘗試登入")
            return login_user()
    except Exception:
        print(f"無法解析JSON響應: {response.text}")
        print("註冊失敗，嘗試登入")
        return login_user()


def login_user():
    """用戶登入"""
    url = f"{BASE_URL}/auth/login"
    data = {"username": "testuser", "password": "Secure123!"}

    response = requests.post(url, json=data)

    print("\n--- 用戶登入測試 ---")
    print(f"狀態碼: {response.status_code}")

    try:
        result = response.json()
        pprint(result)
        if response.status_code == 200:
            return result.get("access_token")
        else:
            print(f"登入失敗: {response.text}")
            return None
    except Exception:
        print(f"無法解析JSON響應: {response.text}")
        return None


def get_user_profile(token):
    """獲取用戶資料"""
    url = f"{BASE_URL}/auth/user"
    headers = {"Authorization": f"Bearer {token}"}

    print("\n--- 獲取用戶資料測試 ---")
    print(f"使用令牌: {token[:15]}...")
    print(f"請求URL: {url}")

    response = requests.get(url, headers=headers)

    print(f"狀態碼: {response.status_code}")
    print(f"原始響應: {response.text}")

    try:
        data = response.json()
        pprint(data)
        return response.status_code == 200
    except Exception as e:
        print(f"無法解析JSON響應: {str(e)}")
        return False


def create_category(token):
    """創建任務分類"""
    url = f"{BASE_URL}/tasks/categories/"
    headers = {"Authorization": f"Bearer {token}"}
    data = {"name": "工作", "color_code": "#e53e3e"}

    response = requests.post(url, json=data, headers=headers)

    print("\n--- 創建任務分類測試 ---")
    print(f"狀態碼: {response.status_code}")
    print(f"原始響應: {response.text}")

    try:
        result = response.json()
        pprint(result)
        if response.status_code == 200:
            return result.get("id")
        else:
            return None
    except Exception as e:
        print(f"無法解析JSON響應: {str(e)}")
        return None


def create_task(token, category_id=None):
    """創建任務"""
    url = f"{BASE_URL}/tasks/"
    headers = {"Authorization": f"Bearer {token}"}
    data = {
        "title": "測試任務",
        "description": "這是一個測試任務的描述",
        "status": "pending",
        "priority": "high",
        "estimated_pomodoros": 3,
        "category_id": category_id,
        "tag_ids": [],
    }

    response = requests.post(url, json=data, headers=headers)

    print("\n--- 創建任務測試 ---")
    print(f"狀態碼: {response.status_code}")
    print(f"原始響應: {response.text}")

    try:
        result = response.json()
        pprint(result)
        if response.status_code == 200:
            return result.get("id")
        else:
            return None
    except Exception as e:
        print(f"無法解析JSON響應: {str(e)}")
        return None


def get_tasks(token):
    """獲取所有任務"""
    url = f"{BASE_URL}/tasks/"
    headers = {"Authorization": f"Bearer {token}"}

    response = requests.get(url, headers=headers)

    print("\n--- 獲取所有任務測試 ---")
    print(f"狀態碼: {response.status_code}")
    print(f"原始響應: {response.text}")

    try:
        pprint(response.json())
        return response.status_code == 200
    except Exception as e:
        print(f"無法解析JSON響應: {str(e)}")
        return False


def start_pomodoro(token, task_id=None):
    """開始番茄鐘"""
    url = f"{BASE_URL}/pomodoro/start"
    headers = {"Authorization": f"Bearer {token}"}
    data = {
        "task_id": task_id,
        "type": "work",
        "duration": 1500,  # 25分鐘
    }

    response = requests.post(url, json=data, headers=headers)

    print("\n--- 開始番茄鐘測試 ---")
    print(f"狀態碼: {response.status_code}")
    print(f"原始響應: {response.text}")

    try:
        result = response.json()
        pprint(result)
        if response.status_code == 200:
            return result.get("id")
        else:
            return None
    except Exception as e:
        print(f"無法解析JSON響應: {str(e)}")
        return None


def complete_pomodoro(token, session_id):
    """完成番茄鐘"""
    import datetime

    url = f"{BASE_URL}/pomodoro/{session_id}/complete"
    headers = {"Authorization": f"Bearer {token}"}
    data = {"end_time": datetime.datetime.now().isoformat(), "is_completed": True}

    response = requests.put(url, json=data, headers=headers)

    print("\n--- 完成番茄鐘測試 ---")
    print(f"狀態碼: {response.status_code}")
    print(f"原始響應: {response.text}")

    try:
        pprint(response.json())
        return response.status_code == 200
    except Exception as e:
        print(f"無法解析JSON響應: {str(e)}")
        return False


def get_analytics(token):
    """獲取分析數據"""
    url = f"{BASE_URL}/analytics/dashboard"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"days": 30}

    response = requests.get(url, headers=headers, params=params)

    print("\n--- 獲取分析數據測試 ---")
    print(f"狀態碼: {response.status_code}")
    print(f"原始響應長度: {len(response.text)} 字符")

    try:
        # 只打印部分數據，因為可能很長
        result = response.json()
        if "productivity_stats" in result:
            print("productivity_stats:")
            pprint(result.get("productivity_stats"))
        else:
            print("回應內容摘要:")
            print(response.text[:200] + "...")
        return response.status_code == 200
    except Exception as e:
        print(f"無法解析JSON響應: {str(e)}")
        print(f"原始響應: {response.text[:200]}...")
        return False


def run_tests():
    """執行所有測試"""
    results = {}

    # 1. 測試健康檢查
    results["health_check"] = test_health_check()
    if not results["health_check"]:
        print("健康檢查失敗，API可能沒有正確運行")
        return results

    # 2. 註冊/登入用戶
    token = register_user()
    results["authentication"] = token is not None

    if not results["authentication"]:
        print("無法獲取令牌，終止測試")
        return results

    print(f"\n使用令牌: {token[:15]}...")

    # 在繼續之前暫停一下
    print("等待 2 秒...")
    time.sleep(2)

    # 3. 獲取用戶資料
    results["get_user_profile"] = get_user_profile(token)

    # 暫停一下
    time.sleep(1)

    # 4. 創建任務分類
    category_id = create_category(token)
    results["create_category"] = category_id is not None

    # 暫停一下
    time.sleep(1)

    # 5. 創建任務
    task_id = create_task(token, category_id)
    results["create_task"] = task_id is not None

    # 暫停一下
    time.sleep(1)

    # 6. 獲取所有任務
    results["get_tasks"] = get_tasks(token)

    # 暫停一下
    time.sleep(1)

    # 7. 開始番茄鐘
    session_id = start_pomodoro(token, task_id)
    results["start_pomodoro"] = session_id is not None

    # 暫停一下
    time.sleep(1)

    if session_id:
        # 8. 完成番茄鐘
        results["complete_pomodoro"] = complete_pomodoro(token, session_id)
    else:
        results["complete_pomodoro"] = False

    # 暫停一下
    time.sleep(1)

    # 9. 獲取分析數據
    results["get_analytics"] = get_analytics(token)

    print("\n所有測試完成!")
    print("\n--- 測試結果摘要 ---")
    for test, passed in results.items():
        status = "✅ 通過" if passed else "❌ 失敗"
        print(f"{test}: {status}")

    return results


if __name__ == "__main__":
    run_tests()
