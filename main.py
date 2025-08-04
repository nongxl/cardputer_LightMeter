import M5
from M5 import Power, Lcd, Widgets
from hardware import MatrixKeyboard, I2C, Pin
from unit import DLightUnit
import math
import time

# --- 常量定义 ---
UP_KEY_STR = '.'
DOWN_KEY_STR = ';'

# --- 优化后的颜色方案 ---
COLOR_DEFAULT = 0xffffff  # 白色
COLOR_FOCUSED = 0x33ff33  # 绿色 (焦点)
COLOR_INVALID = 0xff0000  # 红色 (无效选项 - 焦点)
COLOR_BACKGROUND = 0x000000  # 黑色
COLOR_TITLE_BG = 0x0000FF  # 标题背景色
COLOR_GRADIENT_1 = 0xCCCCCC  # 渐变色1 (亮灰色)
COLOR_GRADIENT_2 = 0x555555  # 渐变色2 (暗灰色)
# [新增] 无效选项的渐变色
COLOR_INVALID_GRADIENT_1 = 0xCC3333  # 无效渐变1 (暗红色)
COLOR_INVALID_GRADIENT_2 = 0x883333  # 无效渐变2 (更暗的红色)

PARAMETER_LIST_SIZE = 5  # 参数选择列表显示的行数，必须为奇数
LIST_ITEM_HEIGHT = 20  # 列表项的高度


# --- 应用程序类 ---
class LightMeterApp:
    def __init__(self):
        # --- 状态变量 ---
        self.current_mode = 'i'
        self.priority_mode = 'A'
        self.last_lux_value = 0

        # --- 动画状态变量 ---
        self.is_animating = False
        self.anim_duration = 120  # 动画时长 (毫秒)
        self.anim_start_time = 0
        self.anim_start_y = 0.0
        self.anim_target_y = 0.0
        self.anim_current_y = 0.0

        # --- 预设值 ---
        self.iso_values = [50, 100, 200, 400, 800, 1000, 1200, 1600, 3200, 6400]
        self.aperture_values = [0.95, 1.0, 1.2, 1.4, 1.8, 2.0, 2.2, 2.8, 4, 5.6, 8, 11, 16, 22]
        self.shutter_values = ["30s", "15s", "8s", "4s", "2s", "1s", "1/2", "1/4", "1/8", "1/15", "1/30", "1/60",
                               "1/125", "1/250", "1/500", "1/1000", "1/2000", "1/4000"]

        # --- 当前预览值的索引 ---
        self.preview_indices = {'ISO': 1, 'Aperture': 4, 'Shutter': 11}

        # --- 硬件和界面元素 ---
        self.kb = None
        self.i2c0 = None
        self.dlight_0 = None
        self.ui_elements = {}
        self.param_list_canvas = None  # 用于动画的离屏画布

    # --- 辅助函数 ---
    def _shutter_to_float(self, shutter_str):
        clean_str = shutter_str.strip().rstrip('s')
        if "/" in clean_str:
            parts = clean_str.split('/')
            return float(parts[0]) / float(parts[1])
        else:
            return float(clean_str)

    # --- 计算逻辑 ---
    def _compute_aperture(self, ev, iso, shutter_speed):
        ev_corrected = ev - math.log2(iso / 100)
        f_number_sq = (2 ** ev_corrected) * shutter_speed
        return math.sqrt(f_number_sq) if f_number_sq > 0 else 0

    def _compute_shutter_speed(self, ev, iso, aperture):
        ev_corrected = ev - math.log2(iso / 100)
        denominator = (2 ** ev_corrected)
        return (aperture ** 2) / denominator if denominator != 0 else 0

    # --- 检查选项有效性的辅助函数 ---
    def _is_choice_valid(self, param_key, choice_idx):
        # ISO值永远不会被标记为无效
        if param_key == 'ISO':
            return True

        if not self.dlight_0: return True
        try:
            lux = self.dlight_0.get_lux()
            ev = math.log2(lux / 2.5) if lux > 0 else -100

            # 获取基础参数用于计算
            iso = self.iso_values[self.preview_indices['ISO']]

            # 在光圈优先模式下，我们正在测试一个光圈选项
            if param_key == 'Aperture':
                aperture_to_test = self.aperture_values[choice_idx]
                shutter_float_result = self._compute_shutter_speed(ev, iso, aperture_to_test)
                return self._shutter_to_float(
                    self.shutter_values[-1]) <= shutter_float_result <= self._shutter_to_float(self.shutter_values[0])

            # 在快门优先模式下，我们正在测试一个快门选项
            elif param_key == 'Shutter':
                shutter_to_test_str = self.shutter_values[choice_idx]
                shutter_float_to_test = self._shutter_to_float(shutter_to_test_str)
                aperture_float_result = self._compute_aperture(ev, iso, shutter_float_to_test)
                return self.aperture_values[0] <= aperture_float_result <= self.aperture_values[-1]

        except (ValueError, ZeroDivisionError, OSError):
            return False
        return True

    # --- 界面更新与核心逻辑 ---
    def _update_parameter_colors(self):
        """根据当前模式，更新左侧标签的颜色以示高亮"""
        self.ui_elements['iso_text_label'].setColor(COLOR_DEFAULT, COLOR_BACKGROUND)
        self.ui_elements['aperture_text_label'].setColor(COLOR_DEFAULT, COLOR_BACKGROUND)
        self.ui_elements['shutter_text_label'].setColor(COLOR_DEFAULT, COLOR_BACKGROUND)
        mode_map = {'i': 'iso', 'a': 'aperture', 's': 'shutter'}
        focus_label = self.ui_elements[f"{mode_map[self.current_mode]}_text_label"]
        focus_label.setColor(COLOR_FOCUSED, COLOR_BACKGROUND)

    def _draw_parameter_list(self):
        """在离屏画布上绘制参数列表，并推送到屏幕，实现无闪烁动画"""
        self.param_list_canvas.fillScreen(COLOR_BACKGROUND)
        self.param_list_canvas.setFont(Widgets.FONTS.DejaVu18)

        font_h = 18

        mode_map = {'i': 'ISO', 'a': 'Aperture', 's': 'Shutter'}
        param_key = mode_map[self.current_mode]
        values_list = getattr(self, f"{param_key.lower()}_values")
        current_idx = self.preview_indices[param_key]
        center_list_idx = PARAMETER_LIST_SIZE // 2

        for i in range(-1, PARAMETER_LIST_SIZE + 1):
            data_idx = current_idx + (i - center_list_idx)
            if 0 <= data_idx < len(values_list):
                value = values_list[data_idx]
                prefix = "f/" if param_key == 'Aperture' else ""
                text_to_draw = f"{prefix}{value}"
                draw_y = int((i * LIST_ITEM_HEIGHT) + self.anim_current_y)

                text_w = self.param_list_canvas.textWidth(text_to_draw)
                canvas_w = self.param_list_canvas.width()
                text_x = (canvas_w - text_w) // 2
                text_y_offset = (LIST_ITEM_HEIGHT - font_h) // 2
                centered_text_y = draw_y + text_y_offset

                distance_from_center = abs(i - center_list_idx)

                # --- [核心逻辑重构] ---
                # 1. 决定使用哪个颜色渐变方案
                is_valid = self._is_choice_valid(param_key, data_idx)

                if is_valid:
                    # 对于有效选项，使用绿色/灰色渐变
                    if distance_from_center == 0:
                        text_color = COLOR_FOCUSED
                    elif distance_from_center == 1:
                        text_color = COLOR_GRADIENT_1
                    else:  # distance >= 2
                        text_color = COLOR_GRADIENT_2
                else:
                    # 对于无效选项，使用新的红色渐变
                    if distance_from_center == 0:
                        text_color = COLOR_INVALID
                    elif distance_from_center == 1:
                        text_color = COLOR_INVALID_GRADIENT_1
                    else:  # distance >= 2
                        text_color = COLOR_INVALID_GRADIENT_2

                # 2. 独立判断是否绘制外框 (只要是中间项就绘制)
                if distance_from_center == 0:
                    box_color = COLOR_FOCUSED
                    box_padding_x = 6
                    box_padding_y = 2
                    thickness = 2

                    box_x = text_x - box_padding_x
                    box_y = centered_text_y - box_padding_y
                    box_w = text_w + (2 * box_padding_x)
                    box_h = font_h + (2 * box_padding_y)

                    for t in range(thickness):
                        top_y = box_y + t
                        bottom_y = box_y + box_h - 1 - t
                        if top_y >= bottom_y and t > 0:
                            break
                        self.param_list_canvas.drawLine(box_x, top_y, box_x + box_w, top_y, box_color)
                        self.param_list_canvas.drawLine(box_x, bottom_y, box_x + box_w, bottom_y, box_color)

                # 3. 最后，使用计算出的颜色绘制文本
                self.param_list_canvas.setTextColor(text_color, COLOR_BACKGROUND)
                self.param_list_canvas.drawString(text_to_draw, text_x, centered_text_y)

        canvas_pos = self.ui_elements['param_list_canvas_pos']
        self.param_list_canvas.push(canvas_pos[0], canvas_pos[1])

    def _update_and_recalculate(self):
        """根据传感器数据和当前设置，计算并更新左侧的数值显示"""
        if not self.is_animating:
            self._draw_parameter_list()

        if not self.dlight_0: return
        try:
            lux = self.dlight_0.get_lux()
            ev = math.log2(lux / 2.5) if lux > 0 else -100
            iso = self.iso_values[self.preview_indices['ISO']]
            aperture = self.aperture_values[self.preview_indices['Aperture']]
            shutter_str = self.shutter_values[self.preview_indices['Shutter']]

            # 更新ISO值，永远是默认颜色
            self.ui_elements['iso_value_label'].setText(str(iso))
            self.ui_elements['iso_value_label'].setColor(COLOR_DEFAULT, COLOR_BACKGROUND)

            # 重置光圈和快门标签颜色为默认
            self.ui_elements['aperture_value_label'].setColor(COLOR_DEFAULT, COLOR_BACKGROUND)
            self.ui_elements['shutter_value_label'].setColor(COLOR_DEFAULT, COLOR_BACKGROUND)

            if self.priority_mode == 'A':  # 光圈优先
                self.ui_elements['aperture_value_label'].setText(f"f/{aperture}")

                shutter_float_theoretical = self._compute_shutter_speed(ev, iso, aperture)

                min_shutter_val = self._shutter_to_float(self.shutter_values[-1])
                max_shutter_val = self._shutter_to_float(self.shutter_values[0])

                is_out_of_bounds = shutter_float_theoretical < min_shutter_val or shutter_float_theoretical > max_shutter_val

                if is_out_of_bounds:
                    # 如果超出范围，强制显示边界值并标红
                    closest_shutter = self.shutter_values[-1] if shutter_float_theoretical < min_shutter_val else \
                    self.shutter_values[0]
                    self.ui_elements['shutter_value_label'].setColor(COLOR_INVALID, COLOR_BACKGROUND)
                else:
                    # 如果在范围内，找到最接近的可用值
                    closest_shutter = min(self.shutter_values,
                                          key=lambda s: abs(self._shutter_to_float(s) - shutter_float_theoretical))

                self.ui_elements['shutter_value_label'].setText(str(closest_shutter))

            elif self.priority_mode == 'S':  # 快门优先
                self.ui_elements['shutter_value_label'].setText(str(shutter_str))

                shutter_float = self._shutter_to_float(shutter_str)
                aperture_float_theoretical = self._compute_aperture(ev, iso, shutter_float)

                min_aperture_val = self.aperture_values[0]
                max_aperture_val = self.aperture_values[-1]

                is_out_of_bounds = aperture_float_theoretical < min_aperture_val or aperture_float_theoretical > max_aperture_val

                if is_out_of_bounds:
                    # 如果超出范围，强制显示边界值并标红
                    closest_aperture = min_aperture_val if aperture_float_theoretical < min_aperture_val else max_aperture_val
                    self.ui_elements['aperture_value_label'].setColor(COLOR_INVALID, COLOR_BACKGROUND)
                else:
                    # 如果在范围内，找到最接近的可用值
                    closest_aperture = min(self.aperture_values, key=lambda a: abs(a - aperture_float_theoretical))

                self.ui_elements['aperture_value_label'].setText(f"f/{closest_aperture:g}")

        except (ValueError, ZeroDivisionError, OSError) as e:
            print(f"Calculation error: {e}")

    # --- 事件处理 ---
    def kb_pressed_event(self, kb_event):
        if self.is_animating: return
        key_str = self.kb.get_string()

        if key_str in ['i', 'a', 's']:
            self.current_mode = key_str
            if key_str == 'a':
                self.priority_mode = 'A'
            elif key_str == 's':
                self.priority_mode = 'S'
            self._update_parameter_colors()
            self._update_and_recalculate()

        elif key_str in [UP_KEY_STR, DOWN_KEY_STR]:
            mode_map = {'i': 'ISO', 'a': 'Aperture', 's': 'Shutter'}
            param_key = mode_map[self.current_mode]
            current_idx = self.preview_indices[param_key]
            values_list = getattr(self, f"{param_key.lower()}_values")
            direction = 1 if key_str == UP_KEY_STR else -1
            next_idx = current_idx + direction

            # 关键：不再检查_is_choice_valid来限制选择，用户永远可以滚动
            if 0 <= next_idx < len(values_list):
                self.preview_indices[param_key] = next_idx
                self.is_animating = True
                self.anim_start_time = time.ticks_ms()
                self.anim_start_y = self.anim_current_y
                self.anim_target_y = self.anim_current_y - (direction * LIST_ITEM_HEIGHT)
                self._update_and_recalculate()

    # --- 私有初始化方法 ---
    def _init_hardware(self):
        """初始化键盘和I2C传感器"""
        self.kb = MatrixKeyboard()
        self.kb.set_callback(self.kb_pressed_event)
        self.i2c0 = I2C(0, scl=Pin(1), sda=Pin(2), freq=100000)
        try:
            self.dlight_0 = DLightUnit(self.i2c0)
            print("DLight Unit initialized successfully.")
        except OSError as e:
            self.dlight_0 = None
            print(f"Failed to initialize DLight Unit: {e}")

    def _init_ui(self):
        """初始化所有UI元素，包括左侧的Widgets和右侧的Canvas"""
        Widgets.fillScreen(COLOR_BACKGROUND)

        # --- 全局统一使用DejaVu24字体，并精调布局 ---字体大小支持12/18/24/40/56/72
        UNIFIED_FONT = Widgets.FONTS.DejaVu24

        # --- 顶部面板 ---
        self.ui_elements['title'] = Widgets.Title("LightMeter", 3, COLOR_DEFAULT, COLOR_TITLE_BG, UNIFIED_FONT)
        self.ui_elements['battary_label'] = Widgets.Label("B:", 188, 1, 1.0, COLOR_DEFAULT, COLOR_BACKGROUND,
                                                          UNIFIED_FONT)

        # --- 左侧面板 (使用 Widgets) ---
        # DejaVu24字体下最合适的坐标
        lux_y, iso_y, apert_y, speed_y = 28, 54, 82, 110
        label_x, value_x = 8, 82

        Widgets.Label("LUX:", label_x, lux_y, 1.0, COLOR_DEFAULT, COLOR_BACKGROUND, UNIFIED_FONT)
        self.ui_elements['lux_value_label'] = Widgets.Label("N/A", value_x, lux_y, 1.0, COLOR_DEFAULT, COLOR_BACKGROUND,
                                                            UNIFIED_FONT)

        self.ui_elements['iso_text_label'] = Widgets.Label("ISO:", label_x, iso_y, 1.0, COLOR_DEFAULT, COLOR_BACKGROUND,
                                                           UNIFIED_FONT)
        self.ui_elements['iso_value_label'] = Widgets.Label("100", value_x, iso_y, 1.0, COLOR_DEFAULT, COLOR_BACKGROUND,
                                                            UNIFIED_FONT)

        self.ui_elements['aperture_text_label'] = Widgets.Label("APER:", label_x, apert_y, 1.0, COLOR_DEFAULT,
                                                                COLOR_BACKGROUND, UNIFIED_FONT)
        self.ui_elements['aperture_value_label'] = Widgets.Label("f/2.8", value_x, apert_y, 1.0, COLOR_DEFAULT,
                                                                 COLOR_BACKGROUND, UNIFIED_FONT)

        self.ui_elements['shutter_text_label'] = Widgets.Label("SSPD:", label_x, speed_y, 1.0, COLOR_DEFAULT,
                                                               COLOR_BACKGROUND, UNIFIED_FONT)
        self.ui_elements['shutter_value_label'] = Widgets.Label("1/125", value_x, speed_y, 1.0, COLOR_DEFAULT,
                                                                COLOR_BACKGROUND, UNIFIED_FONT)

        # --- 右侧面板 (使用 Canvas) ---
        list_x, list_y = 172, 40
        list_w, list_h = 72, (PARAMETER_LIST_SIZE * LIST_ITEM_HEIGHT)
        # 关键：在可靠的内部SRAM中创建画布
        self.param_list_canvas = Lcd.newCanvas(list_w, list_h, 16, False)
        self.ui_elements['param_list_canvas_pos'] = (list_x, list_y)

    # --- 主流程 ---
    def setup(self):
        M5.begin()
        Lcd.setBrightness(25)
        self._init_hardware()
        self._init_ui()
        self._update_parameter_colors()
        self._update_and_recalculate()

    def loop(self):
        M5.update()  # 必须保留，它驱动Widgets和系统事件
        self.kb.tick()

        if self.is_animating:
            elapsed = time.ticks_diff(time.ticks_ms(), self.anim_start_time)
            if elapsed >= self.anim_duration:
                self.is_animating = False
                self.anim_current_y = 0
                self.anim_start_y = 0
                self.anim_target_y = 0
                self._update_and_recalculate()
            else:
                progress = elapsed / self.anim_duration
                self.anim_current_y = self.anim_start_y + (self.anim_target_y - self.anim_start_y) * progress
                self._draw_parameter_list()
        else:
            # 非动画状态下的常规更新
            self.ui_elements['battary_label'].setText(str(Power.getBatteryLevel()))
            if self.dlight_0:
                try:
                    current_lux = self.dlight_0.get_lux()
                    # 增加一个小的阈值避免过于频繁的更新
                    if abs(current_lux - self.last_lux_value) > 1:
                        self.last_lux_value = current_lux
                        self.ui_elements['lux_value_label'].setText(str(int(self.last_lux_value)))
                        self._update_and_recalculate()
                except OSError:
                    self.ui_elements['lux_value_label'].setText("Error")

        time.sleep_ms(20)


# --- 程序入口 ---
if __name__ == '__main__':
    app = LightMeterApp()
    try:
        app.setup()
        while True:
            app.loop()
    except (Exception, KeyboardInterrupt) as e:
        try:
            from utility import print_error_msg

            print_error_msg(e)
        except ImportError:
            print("Firmware error or missing utility module.")
            print(e)