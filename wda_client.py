"""
WebDriverAgent HTTP Client
支持 WDA 的所有 API 端点

路由规则：
- 标记了 .withoutSession 的端点：直接用 /wda/xxx 访问
- 其他端点（默认 requiresSession=YES）：用 /session/{id}/wda/xxx 或 /session/{id}/xxx 访问
"""

import base64
import time
import requests
from typing import Optional, Dict, Any, List


class WDAClient:
    def __init__(self, base_url: str = "http://localhost:8100"):
        self.base_url = base_url.rstrip('/')
        self.session_id: Optional[str] = None
        self.timeout = 30
    
    def _request(self, method: str, path: str, **kwargs) -> Dict[str, Any]:
        """发送 HTTP 请求"""
        url = f"{self.base_url}{path}"
        kwargs.setdefault('timeout', self.timeout)
        response = requests.request(method, url, **kwargs)
        response.raise_for_status()
        return response.json()
    
    def _get(self, path: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        return self._request('GET', path, params=params)
    
    def _post(self, path: str, json: Optional[Dict] = None) -> Dict[str, Any]:
        return self._request('POST', path, json=json or {})
    
    def _delete(self, path: str) -> Dict[str, Any]:
        return self._request('DELETE', path)
    
    def _session_path(self, path: str) -> str:
        """构建带 session 前缀的路径（需要 session 的端点）"""
        if not self.session_id:
            raise ValueError("Session not created. Call create_session() first.")
        return f"/session/{self.session_id}{path}"
    
    # ========== Status (withoutSession) ==========
    
    def get_status(self) -> Dict[str, Any]:
        """GET /status - WDA 状态"""
        return self._get('/status')
    
    def get_healthcheck(self) -> Dict[str, Any]:
        """GET /wda/healthcheck - 健康检查 (withoutSession)"""
        return self._get('/wda/healthcheck')
    
    # ========== Session ==========
    
    def create_session(self, capabilities: Optional[Dict] = None) -> str:
        """POST /session - 创建会话"""
        body = {'capabilities': capabilities or {}}
        result = self._post('/session', body)
        self.session_id = result.get('sessionId') or result.get('value', {}).get('sessionId')
        return self.session_id
    
    def delete_session(self) -> None:
        """DELETE /session/:id - 删除会话"""
        if self.session_id:
            self._delete(self._session_path(''))
            self.session_id = None
    
    def get_session(self) -> Dict[str, Any]:
        """GET /session/:id - 获取会话信息"""
        return self._get(self._session_path(''))
    
    # ========== Screenshot ==========
    
    def get_screenshot(self) -> str:
        """GET /session/:id/screenshot - 截图 (base64)"""
        result = self._get(self._session_path('/screenshot'))
        return result.get('value', '')
    
    def get_element_screenshot(self, element_id: str) -> str:
        """GET /session/:id/element/:eid/screenshot - 元素截图 (base64)"""
        result = self._get(self._session_path(f'/element/{element_id}/screenshot'))
        return result.get('value', '')
    
    # ========== Page Source ==========
    
    def get_source(self) -> str:
        """GET /session/:id/source - 元素树 XML"""
        result = self._get(self._session_path('/source'))
        return result.get('value', '')
    
    def get_accessible_source(self) -> str:
        """GET /wda/accessibleSource - 可访问性源码 (withoutSession)"""
        result = self._get('/wda/accessibleSource')
        return result.get('value', '')
    
    # ========== Element Finding ==========
    
    def find_element(self, using: str, value: str) -> Optional[str]:
        """POST /session/:id/element - 查找元素"""
        body = {'using': using, 'value': value}
        try:
            result = self._post(self._session_path('/element'), body)
            return result.get('value', {}).get('ELEMENT')
        except:
            return None
    
    def find_elements(self, using: str, value: str) -> List[str]:
        """POST /session/:id/elements - 查找多个元素"""
        body = {'using': using, 'value': value}
        try:
            result = self._post(self._session_path('/elements'), body)
            elements = result.get('value', [])
            return [el.get('ELEMENT') for el in elements if el.get('ELEMENT')]
        except:
            return []
    
    def find_element_from_element(self, element_id: str, using: str, value: str) -> Optional[str]:
        """POST /session/:id/element/:eid/element - 从元素查找子元素"""
        body = {'using': using, 'value': value}
        try:
            result = self._post(self._session_path(f'/element/{element_id}/element'), body)
            return result.get('value', {}).get('ELEMENT')
        except:
            return None
    
    def find_elements_from_element(self, element_id: str, using: str, value: str) -> List[str]:
        """POST /session/:id/element/:eid/elements - 从元素查找多个子元素"""
        body = {'using': using, 'value': value}
        try:
            result = self._post(self._session_path(f'/element/{element_id}/elements'), body)
            elements = result.get('value', [])
            return [el.get('ELEMENT') for el in elements if el.get('ELEMENT')]
        except:
            return []
    
    def get_active_element(self) -> Optional[str]:
        """GET /session/:id/element/active - 获取当前活跃/聚焦元素"""
        try:
            result = self._get(self._session_path('/element/active'))
            return result.get('value', {}).get('ELEMENT')
        except:
            return None
    
    def get_visible_cells(self, element_id: str) -> List[str]:
        """GET /session/:id/wda/element/:eid/getVisibleCells - 获取可见 Cell"""
        try:
            result = self._get(self._session_path(f'/wda/element/{element_id}/getVisibleCells'))
            elements = result.get('value', [])
            return [el.get('ELEMENT') for el in elements if el.get('ELEMENT')]
        except:
            return []
    
    # ========== Element Properties ==========
    
    def get_element_text(self, element_id: str) -> str:
        """GET /session/:id/element/:eid/text"""
        result = self._get(self._session_path(f'/element/{element_id}/text'))
        return result.get('value', '')
    
    def get_element_attribute(self, element_id: str, name: str) -> Optional[str]:
        """GET /session/:id/element/:eid/attribute/:name"""
        result = self._get(self._session_path(f'/element/{element_id}/attribute/{name}'))
        return result.get('value')
    
    def is_element_displayed(self, element_id: str) -> bool:
        """GET /session/:id/element/:eid/displayed"""
        result = self._get(self._session_path(f'/element/{element_id}/displayed'))
        return result.get('value', False)
    
    def is_element_enabled(self, element_id: str) -> bool:
        """GET /session/:id/element/:eid/enabled"""
        result = self._get(self._session_path(f'/element/{element_id}/enabled'))
        return result.get('value', False)
    
    def is_element_selected(self, element_id: str) -> bool:
        """GET /session/:id/element/:eid/selected"""
        result = self._get(self._session_path(f'/element/{element_id}/selected'))
        return result.get('value', False)
    
    def get_element_name(self, element_id: str) -> str:
        """GET /session/:id/element/:eid/name"""
        result = self._get(self._session_path(f'/element/{element_id}/name'))
        return result.get('value', '')
    
    def get_element_rect(self, element_id: str) -> Dict[str, Any]:
        """GET /session/:id/element/:eid/rect"""
        result = self._get(self._session_path(f'/element/{element_id}/rect'))
        return result.get('value', {})
    
    def is_element_accessible(self, element_id: str) -> bool:
        """GET /session/:id/wda/element/:eid/accessible"""
        result = self._get(self._session_path(f'/wda/element/{element_id}/accessible'))
        return result.get('value', False)
    
    def is_element_accessibility_container(self, element_id: str) -> bool:
        """GET /session/:id/wda/element/:eid/accessibilityContainer"""
        result = self._get(self._session_path(f'/wda/element/{element_id}/accessibilityContainer'))
        return result.get('value', False)
    
    def is_element_focused(self, element_id: str) -> bool:
        """GET /session/:id/element/:eid/attribute/focused"""
        result = self._get(self._session_path(f'/element/{element_id}/attribute/focused'))
        return result.get('value', False)
    
    # ========== Element Interaction ==========
    
    def click_element(self, element_id: str) -> None:
        """POST /session/:id/element/:eid/click"""
        self._post(self._session_path(f'/element/{element_id}/click'))
    
    def click_element_relative(self, element_id: str, x: float = 0.5, y: float = 0.5) -> None:
        """POST /session/:id/element/:eid/click/relative - 相对坐标点击"""
        body = {'x': x, 'y': y}
        self._post(self._session_path(f'/element/{element_id}/click/relative'), body)
    
    def send_keys(self, element_id: str, text: str) -> None:
        """POST /session/:id/element/:eid/value"""
        body = {'value': list(text)}
        self._post(self._session_path(f'/element/{element_id}/value'), body)
    
    def keyboard_input(self, element_id: str, text: str) -> None:
        """POST /session/:id/wda/element/:eid/keyboardInput - 通过键盘输入"""
        body = {'value': list(text)}
        self._post(self._session_path(f'/wda/element/{element_id}/keyboardInput'), body)
    
    def clear_element(self, element_id: str) -> None:
        """POST /session/:id/element/:eid/clear"""
        self._post(self._session_path(f'/element/{element_id}/clear'))
    
    def focus_element(self, element_id: str) -> None:
        """POST /session/:id/wda/element/:eid/focuse - 聚焦元素"""
        self._post(self._session_path(f'/wda/element/{element_id}/focuse'))
    
    def select_pickerwheel(self, element_id: str, order: str, offset: int = 1) -> None:
        """POST /session/:id/wda/pickerwheel/:eid/select - 选择滚轮"""
        body = {'order': order, 'offset': offset}
        self._post(self._session_path(f'/wda/pickerwheel/{element_id}/select'), body)
    
    # ========== Coordinate Interaction (requires session) ==========
    
    def tap(self, x: int, y: int) -> None:
        """POST /session/:id/wda/tap - 点击坐标"""
        self._post(self._session_path('/wda/tap'), {'x': x, 'y': y})
    
    def swipe(self, from_x: int, from_y: int, to_x: int, to_y: int, duration: float = 1.0) -> None:
        """POST /session/:id/wda/swipe - 滑动"""
        body = {'fromX': from_x, 'fromY': from_y, 'toX': to_x, 'toY': to_y, 'duration': duration}
        self._post(self._session_path('/wda/swipe'), body)
    
    def pinch(self, from_x: int, from_y: int, to_x: int, to_y: int, duration: float = 1.0) -> None:
        """POST /session/:id/wda/pinch - 捏合"""
        body = {'fromX': from_x, 'fromY': from_y, 'toX': to_x, 'toY': to_y, 'duration': duration}
        self._post(self._session_path('/wda/pinch'), body)
    
    def rotate(self, from_x: int, from_y: int, to_x: int, to_y: int, duration: float = 1.0) -> None:
        """POST /session/:id/wda/rotate - 旋转"""
        body = {'fromX': from_x, 'fromY': from_y, 'toX': to_x, 'toY': to_y, 'duration': duration}
        self._post(self._session_path('/wda/rotate'), body)
    
    def double_tap(self, x: int, y: int) -> None:
        """POST /session/:id/wda/doubleTap - 双击坐标"""
        self._post(self._session_path('/wda/doubleTap'), {'x': x, 'y': y})
    
    def two_finger_tap(self, x: int, y: int) -> None:
        """POST /session/:id/wda/twoFingerTap - 双指点击"""
        self._post(self._session_path('/wda/twoFingerTap'), {'x': x, 'y': y})
    
    def touch_and_hold(self, x: int, y: int, duration: float = 1.0) -> None:
        """POST /session/:id/wda/touchAndHold - 长按坐标"""
        body = {'x': x, 'y': y, 'duration': duration}
        self._post(self._session_path('/wda/touchAndHold'), body)
    
    def scroll(self, direction: str = 'down', distance: float = 0.5) -> None:
        """POST /session/:id/wda/scroll - 滚动"""
        body = {'direction': direction, 'distance': distance}
        self._post(self._session_path('/wda/scroll'), body)
    
    def drag(self, from_x: int, from_y: int, to_x: int, to_y: int, duration: float = 1.0) -> None:
        """POST /session/:id/wda/dragfromtoforduration - 拖拽"""
        body = {'fromX': from_x, 'fromY': from_y, 'toX': to_x, 'toY': to_y, 'duration': duration}
        self._post(self._session_path('/wda/dragfromtoforduration'), body)
    
    def press_and_drag(self, from_x: int, from_y: int, to_x: int, to_y: int, velocity: float = 800.0) -> None:
        """POST /session/:id/wda/pressAndDragWithVelocity - 按下并拖拽"""
        body = {'fromX': from_x, 'fromY': from_y, 'toX': to_x, 'toY': to_y, 'velocity': velocity}
        self._post(self._session_path('/wda/pressAndDragWithVelocity'), body)
    
    def force_touch(self, x: int, y: int, pressure: float = 1.0, duration: float = 1.0) -> None:
        """POST /session/:id/wda/forceTouch - 3D Touch"""
        body = {'x': x, 'y': y, 'pressure': pressure, 'duration': duration}
        self._post(self._session_path('/wda/forceTouch'), body)
    
    def tap_with_number_of_taps(self, x: int, y: int, number_of_taps: int = 1, number_of_touches: int = 1) -> None:
        """POST /session/:id/wda/tapWithNumberOfTaps - 多次点击"""
        body = {'x': x, 'y': y, 'numberOfTaps': number_of_taps, 'numberOfTouches': number_of_touches}
        self._post(self._session_path('/wda/tapWithNumberOfTaps'), body)
    
    # ========== Element Gestures (requires session) ==========
    
    def swipe_element(self, element_id: str, direction: str, velocity: float = 1.0) -> None:
        """POST /session/:id/wda/element/:eid/swipe - 在元素上滑动"""
        body = {'direction': direction, 'velocity': velocity}
        self._post(self._session_path(f'/wda/element/{element_id}/swipe'), body)
    
    def pinch_element(self, element_id: str, scale: float, velocity: float = 1.0) -> None:
        """POST /session/:id/wda/element/:eid/pinch - 在元素上捏合"""
        body = {'scale': scale, 'velocity': velocity}
        self._post(self._session_path(f'/wda/element/{element_id}/pinch'), body)
    
    def rotate_element(self, element_id: str, rotation: float, duration: float = 1.0) -> None:
        """POST /session/:id/wda/element/:eid/rotate - 旋转元素"""
        body = {'rotation': rotation, 'duration': duration}
        self._post(self._session_path(f'/wda/element/{element_id}/rotate'), body)
    
    def double_tap_element(self, element_id: str) -> None:
        """POST /session/:id/wda/element/:eid/doubleTap - 双击元素"""
        self._post(self._session_path(f'/wda/element/{element_id}/doubleTap'))
    
    def two_finger_tap_element(self, element_id: str) -> None:
        """POST /session/:id/wda/element/:eid/twoFingerTap - 双指点击元素"""
        self._post(self._session_path(f'/wda/element/{element_id}/twoFingerTap'))
    
    def touch_and_hold_element(self, element_id: str, duration: float = 1.0) -> None:
        """POST /session/:id/wda/element/:eid/touchAndHold - 长按元素"""
        body = {'duration': duration}
        self._post(self._session_path(f'/wda/element/{element_id}/touchAndHold'), body)
    
    def scroll_element(self, element_id: str, direction: str = 'down', distance: float = 0.5) -> None:
        """POST /session/:id/wda/element/:eid/scroll - 在元素上滚动"""
        body = {'direction': direction, 'distance': distance}
        self._post(self._session_path(f'/wda/element/{element_id}/scroll'), body)
    
    def scroll_to_element(self, element_id: str, target_element_id: str) -> None:
        """POST /session/:id/wda/element/:eid/scrollTo - 滚动到指定元素"""
        body = {'toVisible': True}
        self._post(self._session_path(f'/wda/element/{element_id}/scrollTo'), body)
    
    def drag_element(self, element_id: str, to_x: int, to_y: int, duration: float = 1.0) -> None:
        """POST /session/:id/wda/element/:eid/dragfromtoforduration - 拖拽元素"""
        body = {'toX': to_x, 'toY': to_y, 'duration': duration}
        self._post(self._session_path(f'/wda/element/{element_id}/dragfromtoforduration'), body)
    
    def press_and_drag_element(self, element_id: str, to_x: int, to_y: int, velocity: float = 800.0) -> None:
        """POST /session/:id/wda/element/:eid/pressAndDragWithVelocity - 按下并拖拽元素"""
        body = {'toX': to_x, 'toY': to_y, 'velocity': velocity}
        self._post(self._session_path(f'/wda/element/{element_id}/pressAndDragWithVelocity'), body)
    
    def force_touch_element(self, element_id: str, pressure: float = 1.0, duration: float = 1.0) -> None:
        """POST /session/:id/wda/element/:eid/forceTouch - 3D Touch 元素"""
        body = {'pressure': pressure, 'duration': duration}
        self._post(self._session_path(f'/wda/element/{element_id}/forceTouch'), body)
    
    def tap_element(self, element_id: str) -> None:
        """POST /session/:id/wda/element/:eid/tap - 点击元素 (WDA 自定义)"""
        self._post(self._session_path(f'/wda/element/{element_id}/tap'))
    
    def tap_element_with_number_of_taps(self, element_id: str, number_of_taps: int = 1, number_of_touches: int = 1) -> None:
        """POST /session/:id/wda/element/:eid/tapWithNumberOfTaps - 多次点击元素"""
        body = {'numberOfTaps': number_of_taps, 'numberOfTouches': number_of_touches}
        self._post(self._session_path(f'/wda/element/{element_id}/tapWithNumberOfTaps'), body)
    
    # ========== Touch Perform (requires session) ==========
    
    def touch_perform(self, actions: List[Dict[str, Any]]) -> None:
        """POST /session/:id/wda/touch/perform - 执行手势 (Appium 格式)"""
        body = {'actions': actions}
        self._post(self._session_path('/wda/touch/perform'), body)
    
    def touch_multi_perform(self, actions: List[Dict[str, Any]]) -> None:
        """POST /session/:id/wda/touch/multi/perform - 多点触控"""
        body = {'actions': actions}
        self._post(self._session_path('/wda/touch/multi/perform'), body)
    
    def w3c_actions(self, actions: List[Dict[str, Any]]) -> None:
        """POST /session/:id/actions - W3C Actions API"""
        body = {'actions': actions}
        self._post(self._session_path('/actions'), body)
    
    # ========== App Management (requires session, in FBSessionCommands) ==========
    
    def launch_app(self, bundle_id: str) -> None:
        """POST /session/:id/wda/apps/launch"""
        body = {'bundleId': bundle_id}
        self._post(self._session_path('/wda/apps/launch'), body)
    
    def launch_unattached_app(self, bundle_id: str, arguments: Optional[List] = None, environment: Optional[Dict] = None) -> None:
        """POST /wda/apps/launchUnattached - 启动非关联应用 (withoutSession)"""
        body = {'bundleId': bundle_id}
        if arguments:
            body['arguments'] = arguments
        if environment:
            body['environment'] = environment
        self._post('/wda/apps/launchUnattached', body)
    
    def kill_app(self, bundle_id: str) -> None:
        """POST /wda/apps/kill - 关闭应用 (requires session via FBCustomCommands)"""
        body = {'bundleId': bundle_id}
        self._post('/wda/apps/kill', body)
    
    def activate_app(self, bundle_id: str) -> None:
        """POST /session/:id/wda/apps/activate"""
        body = {'bundleId': bundle_id}
        self._post(self._session_path('/wda/apps/activate'), body)
    
    def terminate_app(self, bundle_id: str) -> bool:
        """POST /session/:id/wda/apps/terminate"""
        body = {'bundleId': bundle_id}
        result = self._post(self._session_path('/wda/apps/terminate'), body)
        return result.get('value', False)
    
    def get_app_state(self, bundle_id: str) -> int:
        """POST /session/:id/wda/apps/state"""
        body = {'bundleId': bundle_id}
        result = self._post(self._session_path('/wda/apps/state'), body)
        return result.get('value', 0)
    
    def list_apps(self) -> List[Dict[str, Any]]:
        """GET /session/:id/wda/apps/list"""
        result = self._get(self._session_path('/wda/apps/list'))
        return result.get('value', [])
    
    # ========== Device Control ==========
    
    def press_home(self) -> None:
        """POST /wda/homescreen - 按 Home 键 (withoutSession)"""
        self._post('/wda/homescreen')
    
    def press_button(self, button_name: str) -> None:
        """POST /session/:id/wda/pressButton - 按系统按钮"""
        body = {'name': button_name}
        self._post(self._session_path('/wda/pressButton'), body)
    
    def deactivate_app(self, duration: float = 3.0) -> None:
        """POST /session/:id/wda/deactivateApp - 将 App 移到后台"""
        body = {'duration': duration}
        self._post(self._session_path('/wda/deactivateApp'), body)
    
    def lock_screen(self) -> None:
        """POST /wda/lock - 锁屏 (withoutSession)"""
        self._post('/wda/lock')
    
    def unlock_screen(self) -> None:
        """POST /wda/unlock - 解锁 (withoutSession)"""
        self._post('/wda/unlock')
    
    def is_locked(self) -> bool:
        """GET /wda/locked - 是否锁定 (withoutSession)"""
        result = self._get('/wda/locked')
        return result.get('value', False)
    
    # ========== Screen / Battery / Device Info ==========
    
    def get_screen_info(self) -> Dict[str, Any]:
        """GET /session/:id/wda/screen - 屏幕信息"""
        result = self._get(self._session_path('/wda/screen'))
        return result.get('value', {})
    
    def get_active_app_info(self) -> Dict[str, Any]:
        """GET /wda/activeAppInfo - 当前 App 信息 (withoutSession)"""
        result = self._get('/wda/activeAppInfo')
        return result.get('value', {})
    
    def get_battery_info(self) -> Dict[str, Any]:
        """GET /session/:id/wda/batteryInfo - 电池信息"""
        result = self._get(self._session_path('/wda/batteryInfo'))
        return result.get('value', {})
    
    def get_device_info(self) -> Dict[str, Any]:
        """GET /wda/device/info - 设备信息 (withoutSession)"""
        result = self._get('/wda/device/info')
        return result.get('value', {})
    
    def set_device_appearance(self, style: str) -> None:
        """POST /wda/device/appearance - 设置外观 (withoutSession, light/dark)"""
        body = {'style': style}
        self._post('/wda/device/appearance', body)
    
    def get_device_location(self) -> Dict[str, Any]:
        """GET /wda/device/location - 设备位置 (withoutSession)"""
        result = self._get('/wda/device/location')
        return result.get('value', {})
    
    def set_simulated_location(self, latitude: float, longitude: float) -> None:
        """POST /wda/simulatedLocation - 设置模拟位置 (withoutSession)"""
        body = {'latitude': latitude, 'longitude': longitude}
        self._post('/wda/simulatedLocation', body)
    
    def get_simulated_location(self) -> Dict[str, Any]:
        """GET /wda/simulatedLocation - 获取模拟位置 (withoutSession)"""
        result = self._get('/wda/simulatedLocation')
        return result.get('value', {})
    
    def clear_simulated_location(self) -> None:
        """DELETE /wda/simulatedLocation - 清除模拟位置 (withoutSession)"""
        self._delete('/wda/simulatedLocation')
    
    # ========== Orientation & Rotation ==========
    
    def get_orientation(self) -> str:
        """GET /session/:id/orientation"""
        result = self._get(self._session_path('/orientation'))
        return result.get('value', 'PORTRAIT')
    
    def set_orientation(self, orientation: str) -> None:
        """POST /session/:id/orientation"""
        body = {'orientation': orientation.upper()}
        self._post(self._session_path('/orientation'), body)
    
    def get_rotation(self) -> Dict[str, int]:
        """GET /session/:id/rotation"""
        result = self._get(self._session_path('/rotation'))
        return result.get('value', {})
    
    def set_rotation(self, x: int = 0, y: int = 0, z: int = 0) -> None:
        """POST /session/:id/rotation"""
        body = {'x': x, 'y': y, 'z': z}
        self._post(self._session_path('/rotation'), body)
    
    def get_window_size(self) -> Dict[str, Any]:
        """GET /session/:id/window/size"""
        result = self._get(self._session_path('/window/size'))
        return result.get('value', {})
    
    # ========== Alert ==========
    
    def get_alert_text(self) -> str:
        """GET /session/:id/alert/text"""
        result = self._get(self._session_path('/alert/text'))
        return result.get('value', '')
    
    def set_alert_text(self, text: str) -> None:
        """POST /session/:id/alert/text - 设置弹窗文本"""
        body = {'value': list(text)}
        self._post(self._session_path('/alert/text'), body)
    
    def accept_alert(self) -> None:
        """POST /alert/accept - 接受弹窗 (withoutSession)"""
        self._post('/alert/accept')
    
    def dismiss_alert(self) -> None:
        """POST /alert/dismiss - 关闭弹窗 (withoutSession)"""
        self._post('/alert/dismiss')
    
    def get_alert_buttons(self) -> List[str]:
        """GET /session/:id/wda/alert/buttons"""
        result = self._get(self._session_path('/wda/alert/buttons'))
        return result.get('value', [])
    
    def alert_action(self, button_label: Optional[str] = None) -> None:
        """POST /session/:id/wda/alertAction - 弹窗操作"""
        body = {}
        if button_label:
            body['name'] = button_label
        self._post(self._session_path('/wda/alertAction'), body)
    
    def clear_alert(self) -> None:
        """GET /wda/clearAlert - 清除弹窗 (withoutSession)"""
        self._get('/wda/clearAlert')
    
    # ========== Keyboard ==========
    
    def dismiss_keyboard(self) -> None:
        """POST /session/:id/wda/keyboard/dismiss"""
        self._post(self._session_path('/wda/keyboard/dismiss'))
    
    # ========== Clipboard ==========
    
    def get_clipboard(self) -> str:
        """POST /wda/getPasteboard - 获取剪贴板 (withoutSession, base64)"""
        result = self._post('/wda/getPasteboard')
        b64 = result.get('value', '')
        if b64:
            try:
                return base64.b64decode(b64).decode('utf-8')
            except:
                return b64
        return ''
    
    def set_clipboard(self, text: str) -> None:
        """POST /wda/setPasteboard - 设置剪贴板 (withoutSession)"""
        b64 = base64.b64encode(text.encode('utf-8')).decode('ascii')
        body = {'content': b64}
        self._post('/wda/setPasteboard', body)
    
    # ========== Keys ==========
    
    def send_keys(self, text: str) -> None:
        """POST /session/:id/wda/keys - 发送按键"""
        body = {'value': list(text)}
        self._post(self._session_path('/wda/keys'), body)
    
    # ========== Siri ==========
    
    def activate_siri(self, text: str) -> None:
        """POST /session/:id/wda/siri/activate - 激活 Siri"""
        body = {'text': text}
        self._post(self._session_path('/wda/siri/activate'), body)
    
    # ========== Accessibility ==========
    
    def perform_accessibility_audit(self, audit_types: Optional[List[str]] = None) -> Dict[str, Any]:
        """POST /session/:id/wda/performAccessibilityAudit - 可访问性审计"""
        body = {}
        if audit_types:
            body['auditTypes'] = audit_types
        result = self._post(self._session_path('/wda/performAccessibilityAudit'), body)
        return result.get('value', {})
    
    # ========== Touch ID ==========
    
    def set_touch_id(self, match: bool = True) -> None:
        """POST /session/:id/wda/touch_id - 模拟 Touch ID"""
        body = {'match': match}
        self._post(self._session_path('/wda/touch_id'), body)
    
    # ========== App Switcher ==========
    
    def activate_app_switcher(self) -> None:
        """GET /wda/activateAppSwitcher - 激活 App Switcher (withoutSession)"""
        self._get('/wda/activateAppSwitcher')
    
    # ========== Logs ==========
    
    def get_logs(self, log_type: str = 'syslog') -> List[Dict[str, Any]]:
        """POST /session/:id/wda/logs - 获取日志"""
        body = {'type': log_type}
        result = self._post(self._session_path('/wda/logs'), body)
        return result.get('value', [])
    
    def get_logs_without_session(self) -> List[Dict[str, Any]]:
        """GET /wda/logs - 获取日志 (withoutSession)"""
        result = self._get('/wda/logs')
        return result.get('value', [])
    
    # ========== Settings ==========
    
    def get_settings(self) -> Dict[str, Any]:
        """GET /session/:id/appium/settings"""
        result = self._get(self._session_path('/appium/settings'))
        return result.get('value', {})
    
    def update_settings(self, settings: Dict[str, Any]) -> None:
        """POST /session/:id/appium/settings"""
        body = {'settings': settings}
        self._post(self._session_path('/appium/settings'), body)
    
    # ========== Timeouts ==========
    
    def set_timeouts(self, implicit: Optional[int] = None, page_load: Optional[int] = None, script: Optional[int] = None) -> None:
        """POST /session/:id/timeouts"""
        body = {}
        if implicit is not None:
            body['implicit'] = implicit
        if page_load is not None:
            body['pageLoad'] = page_load
        if script is not None:
            body['script'] = script
        self._post(self._session_path('/timeouts'), body)
    
    # ========== Reset App Auth ==========
    
    def reset_app_auth(self) -> None:
        """POST /session/:id/wda/resetAppAuth - 重置 App 授权"""
        self._post(self._session_path('/wda/resetAppAuth'))
    
    # ========== IO HID Event ==========
    
    def perform_io_hid_event(self, page: int, usage: int, duration: float = 0.1) -> None:
        """POST /session/:id/wda/performIoHidEvent - 执行 HID 事件"""
        body = {'page': page, 'usage': usage, 'duration': duration}
        self._post(self._session_path('/wda/performIoHidEvent'), body)
    
    # ========== Utility ==========
    
    def wait(self, seconds: float) -> None:
        """等待指定秒数"""
        time.sleep(seconds)
    
    def close(self) -> None:
        """关闭连接"""
        if self.session_id:
            try:
                self.delete_session()
            except:
                pass
