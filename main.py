import M5
from M5 import Widgets, Power
from hardware import MatrixKeyboard, I2C, Pin
from unit import DLightUnit
import math
import time

# --- �������� ---
UP_KEY_STR = '.'
DOWN_KEY_STR = ';'

COLOR_DEFAULT = 0xffffff  # ��ɫ
COLOR_FOCUSED = 0x33ff33  # ��ɫ
COLOR_INVALID = 0xff0000  # ��ɫ (������Чѡ��)
COLOR_BACKGROUND = 0x000000
PARAMETER_LIST_SIZE = 5  # ����ѡ���б���ʾ������������Ϊ����


# --- Ӧ�ó����� ---
class LightMeterApp:
    def __init__(self):
        # --- ״̬���� ---
        self.current_mode = 'i'  # 'i', 'a', 's'
        self.priority_mode = 'A'  # 'A' for Aperture, 'S' for Shutter
        self.last_lux_value = 0

        # --- Ԥ��ֵ ---
        self.iso_values = [50, 100, 200, 400, 800, 1000, 1200, 1600, 3200, 6400]
        self.aperture_values = [0.95, 1.0, 1.4, 2.0, 2.8, 4.0, 5.6, 8.0, 11.0, 16.0, 22.0]
        self.shutter_values = ["30s", "15s", "8s", "4s", "2s", "1s", "1/2", "1/4", "1/8", "1/15", "1/30", "1/60",
                               "1/125",
                               "1/250", "1/500", "1/1000", "1/2000", "1/4000"]

        # --- ��ǰԤ��ֵ������ ---
        self.preview_indices = {'ISO': 1, 'Aperture': 4, 'Shutter': 11}

        # --- Ӳ���ͽ���Ԫ�� ---
        self.kb = None
        self.i2c0 = None
        self.dlight_0 = None
        self.ui_elements = {}

    # --- �������� ---
    def _shutter_to_float(self, shutter_str):
        """�������ַ������� '1/125'��'30s'��ת��Ϊ������"""
        clean_str = shutter_str.strip().rstrip('s')
        if "/" in clean_str:
            parts = clean_str.split('/')
            return float(parts[0]) / float(parts[1])
        else:
            return float(clean_str)

    # --- �����߼� ---
    def _compute_aperture(self, ev, iso, shutter_speed):
        ev_corrected = ev - math.log2(iso / 100)
        f_number_sq = (2 ** ev_corrected) * shutter_speed
        return math.sqrt(f_number_sq) if f_number_sq > 0 else 0

    def _compute_shutter_speed(self, ev, iso, aperture):
        ev_corrected = ev - math.log2(iso / 100)
        denominator = (2 ** ev_corrected)
        return (aperture ** 2) / denominator if denominator != 0 else 0

    # --- ����: ���ѡ����Ч�Եĸ������� ---
    def _is_choice_valid(self, param_key, choice_idx):
        """
        Ԥ���㲢��������ѡ�������Ƿ�ᵼ��һ����Ч�Ľ����
        """
        try:
            lux = self.dlight_0.get_lux()
            ev = math.log2(lux / 2.5) if lux > 0 else -100

            # ��ȡ��ǰ״̬�ĸ���
            iso = self.iso_values[self.preview_indices['ISO']]
            aperture = self.aperture_values[self.preview_indices['Aperture']]
            shutter_str = self.shutter_values[self.preview_indices['Shutter']]

            # �ô�����ֵ�滻��ǰֵ
            if param_key == 'ISO':
                iso = self.iso_values[choice_idx]
            elif param_key == 'Aperture':
                aperture = self.aperture_values[choice_idx]
            elif param_key == 'Shutter':
                shutter_str = self.shutter_values[choice_idx]

            # ִ��Ԥ����
            if self.priority_mode == 'A':
                shutter_float = self._compute_shutter_speed(ev, iso, aperture)
                return self._shutter_to_float(self.shutter_values[-1]) <= shutter_float <= self._shutter_to_float(
                    self.shutter_values[0])
            elif self.priority_mode == 'S':
                shutter_float = self._shutter_to_float(shutter_str)
                aperture_float = self._compute_aperture(ev, iso, shutter_float)
                return self.aperture_values[0] <= aperture_float <= self.aperture_values[-1]

        except (ValueError, ZeroDivisionError, OSError):
            return False  # ���������Ϊ��Ч
        return True # Ĭ����Ч

    # --- �������������߼� ---
    def _update_parameter_colors(self):
        """���ݵ�ǰ���������������ǩ��ɫ"""
        self.ui_elements['iso_text_label'].setColor(COLOR_DEFAULT, COLOR_BACKGROUND)
        self.ui_elements['aperture_text_label'].setColor(COLOR_DEFAULT, COLOR_BACKGROUND)
        self.ui_elements['shutter_text_label'].setColor(COLOR_DEFAULT, COLOR_BACKGROUND)

        mode_map = {'i': 'iso', 'a': 'aperture', 's': 'shutter'}
        focus_label = self.ui_elements[f"{mode_map[self.current_mode]}_text_label"]
        focus_label.setColor(COLOR_FOCUSED, COLOR_BACKGROUND)

    def _update_parameter_list_display(self):
        """�����Ҳ�Ĳ���ѡ���б���Ϊ��Чѡ����"""
        mode_map = {'i': 'ISO', 'a': 'Aperture', 's': 'Shutter'}
        param_key = mode_map[self.current_mode]
        values_list = getattr(self, f"{param_key.lower()}_values")
        current_idx = self.preview_indices[param_key]

        center_list_idx = PARAMETER_LIST_SIZE // 2

        for i in range(PARAMETER_LIST_SIZE):
            label = self.ui_elements['param_list_labels'][i]
            data_idx = current_idx + (i - center_list_idx)

            if 0 <= data_idx < len(values_list):
                value = values_list[data_idx]
                prefix = "f/" if param_key == 'Aperture' else ""
                label.setText(f"{prefix}{value}")

                # --- �����޸ģ�������ɫ ---
                if i == center_list_idx:
                    label.setColor(COLOR_FOCUSED, COLOR_BACKGROUND)
                elif self._is_choice_valid(param_key, data_idx):
                    label.setColor(COLOR_DEFAULT, COLOR_BACKGROUND)
                else:
                    label.setColor(COLOR_INVALID, COLOR_BACKGROUND)
            else:
                label.setText("")

    def _update_and_recalculate(self):
        """
        ���ĺ��������ݵ�ǰ����ģʽ��ʹ���������������Ԥ��ֵ��
        �������������������������UI��ʾ��
        """
        try:
            # �����ȸ����Ҳ��б���Ϊ��������Ҫ��ʾ��Ч��
            self._update_parameter_list_display()

            lux = self.dlight_0.get_lux()
            ev = math.log2(lux / 2.5) if lux > 0 else -100

            iso = self.iso_values[self.preview_indices['ISO']]
            aperture = self.aperture_values[self.preview_indices['Aperture']]
            shutter_str = self.shutter_values[self.preview_indices['Shutter']]

            # ���ü���������ɫΪĬ�ϰ�ɫ
            self.ui_elements['iso_value_label'].setText(str(iso))
            self.ui_elements['aperture_value_label'].setColor(COLOR_DEFAULT, COLOR_BACKGROUND)
            self.ui_elements['shutter_value_label'].setColor(COLOR_DEFAULT, COLOR_BACKGROUND)

            if self.priority_mode == 'A':
                self.ui_elements['aperture_value_label'].setText(f"f/{aperture}")
                shutter_float = self._compute_shutter_speed(ev, iso, aperture)
                closest_shutter = min(self.shutter_values, key=lambda s: abs(self._shutter_to_float(s) - shutter_float))
                self.ui_elements['shutter_value_label'].setText(str(closest_shutter))
                self.preview_indices['Shutter'] = self.shutter_values.index(closest_shutter)

            elif self.priority_mode == 'S':
                self.ui_elements['shutter_value_label'].setText(str(shutter_str))
                shutter_float = self._shutter_to_float(shutter_str)
                aperture_float = self._compute_aperture(ev, iso, shutter_float)
                closest_aperture = min(self.aperture_values, key=lambda a: abs(a - aperture_float))
                self.ui_elements['aperture_value_label'].setText(f"f/{closest_aperture}")
                self.preview_indices['Aperture'] = self.aperture_values.index(closest_aperture)

        except (ValueError, ZeroDivisionError, OSError) as e:
            print(e)

    # --- �¼����� ---
    def kb_pressed_event(self, kb_event):
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

            next_idx = current_idx
            if key_str == UP_KEY_STR:
                if current_idx < len(values_list) - 1:
                    next_idx = current_idx + 1
            elif key_str == DOWN_KEY_STR:
                if current_idx > 0:
                    next_idx = current_idx - 1

            # ֻ�е�Ŀ�������͵�ǰ��ͬ����Ŀ������Ч��ʱ�򣬲��ƶ�
            if next_idx != current_idx and self._is_choice_valid(param_key, next_idx):
                self.preview_indices[param_key] = next_idx
                self._update_and_recalculate()

    # --- ������ ---
    def setup(self):
        M5.begin()
        Widgets.setBrightness(25)
        Widgets.fillScreen(COLOR_BACKGROUND)

        # ��ʼ��Ӳ��
        self.kb = MatrixKeyboard()
        self.kb.set_callback(self.kb_pressed_event)
        self.i2c0 = I2C(0, scl=Pin(1), sda=Pin(2), freq=100000)
        self.dlight_0 = DLightUnit(self.i2c0)

        # ��ʼ��UI�������ֵ�
        self.ui_elements['title'] = Widgets.Title("LightMeter", 3, COLOR_DEFAULT, 0x0000FF, Widgets.FONTS.DejaVu18)
        self.ui_elements['battary_label'] = Widgets.Label("B:", 204, 2, 1.0, COLOR_DEFAULT, COLOR_BACKGROUND,
                                                          Widgets.FONTS.DejaVu18)
        self.ui_elements['lux_value_label'] = Widgets.Label("LUX", 80, 21, 1.0, COLOR_DEFAULT, COLOR_BACKGROUND,
                                                            Widgets.FONTS.DejaVu18)
        self.ui_elements['iso_value_label'] = Widgets.Label("ISO", 80, 52, 1.0, COLOR_DEFAULT, COLOR_BACKGROUND,
                                                            Widgets.FONTS.DejaVu18)
        self.ui_elements['aperture_value_label'] = Widgets.Label("A", 80, 78, 1.0, COLOR_DEFAULT, COLOR_BACKGROUND,
                                                                 Widgets.FONTS.DejaVu18)
        self.ui_elements['shutter_value_label'] = Widgets.Label("S", 80, 106, 1.0, COLOR_DEFAULT, COLOR_BACKGROUND,
                                                                Widgets.FONTS.DejaVu18)

        label_x_pos = 10
        self.ui_elements['iso_text_label'] = Widgets.Label("ISO:", label_x_pos, 50, 1.0, COLOR_DEFAULT,
                                                           COLOR_BACKGROUND,
                                                           Widgets.FONTS.DejaVu18)
        self.ui_elements['aperture_text_label'] = Widgets.Label("APERT:", label_x_pos, 77, 1.0, COLOR_DEFAULT,
                                                                COLOR_BACKGROUND,
                                                                Widgets.FONTS.DejaVu18)
        self.ui_elements['shutter_text_label'] = Widgets.Label("SPEED:", label_x_pos, 107, 1.0, COLOR_DEFAULT,
                                                               COLOR_BACKGROUND,
                                                               Widgets.FONTS.DejaVu18)

        Widgets.Label("LUX:", 12, 22, 1.0, COLOR_DEFAULT, COLOR_BACKGROUND, Widgets.FONTS.DejaVu18)

        # �����Ҳ�Ĳ���ѡ���б�
        self.ui_elements['param_list_labels'] = []
        for i in range(PARAMETER_LIST_SIZE):
            y_pos = 40 + i * 20
            label = Widgets.Label("", 168, y_pos, 1.0, COLOR_DEFAULT, COLOR_BACKGROUND, Widgets.FONTS.DejaVu18)
            self.ui_elements['param_list_labels'].append(label)

        # ���ó�ʼ״̬�����е�һ�μ���
        self._update_parameter_colors()
        self._update_and_recalculate()

    def loop(self):
        M5.update()
        self.kb.tick()

        self.ui_elements['battary_label'].setText(str(Power.getBatteryLevel()))
        if self.dlight_0:
            try:
                current_lux = self.dlight_0.get_lux()
                if int(current_lux) != int(self.last_lux_value):
                    self.last_lux_value = current_lux
                    self.ui_elements['lux_value_label'].setText(str(int(self.last_lux_value)))
                    self._update_and_recalculate()
            except OSError:
                pass

        time.sleep_ms(20)


# --- ������� ---
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