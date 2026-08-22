import pygame
import math
import re

pygame.init()


####screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
####width, height = screen.get_size()

width, height = pygame.display.Info().current_w, pygame.display.Info().current_h - 80
screen = pygame.display.set_mode((width, height))
pygame.display.set_caption("3D Orbit Test")



clock = pygame.time.Clock()

#Fonts

_font_cache = {}

def widen_digits(text):
    return re.sub(r'\d', '8', text)

def get_font(size):
    if size not in _font_cache:
        _font_cache[size] = pygame.font.SysFont(None, size)
    return _font_cache[size]

def get_uniform_font(texts, max_width, start_size=28, min_size=10, step=2):
    size = start_size
    while size > min_size:
        f = get_font(size)
        if all(f.size(t)[0] <= max_width for t in texts):
            return f
        size -= step
    return get_font(min_size)


font = get_font(28)


bodies = []
sliders = []
menu_sliders = []
menus = []

TRAIL_DISPLAY_LENGTH = 1000


class OrbitingBody:
    def __init__(self, name, primary, x, y, z, vx, vy, vz, mass, color, trail_color, radius_scale):
        self.name = name

        self.primary = primary

        self.x = x
        self.y = y
        self.z = z

        self.vx = vx
        self.vy = vy
        self.vz = vz

        self.ax = 0
        self.ay = 0
        self.az = 0

        self.mass = mass
        self.color = color
        self.radius_scale = radius_scale

        self.trail = []
        self.trail_start_index = 0
        self.trail_view_end = 0

        self.trail_fader = 1
        self.trail_min_distance = 0.001
        self.trail_color = trail_color

        self.initial_state = (x, y, z, vx, vy, vz, 0, 0, 0)

        self.screen_point = None

        bodies.append(self)

        if self.primary is None:
            stars.append(self)
        elif self.primary.primary is None:
            planets.append(self)
        elif self.primary.primary.primary is None:
            moons.append(self)

    def set_state(self, x, y, z, vx, vy, vz):
        self.x = x
        self.y = y
        self.z = z
        self.vx = vx
        self.vy = vy
        self.vz = vz

    def reset_initial_state(self):
        x, y, z, vx, vy, vz, ax, ay, az = self.initial_state

        self.set_state(x, y, z, vx, vy, vz)
        self.ax = ax
        self.ay = ay
        self.az = az

        self.trail.clear()
        self.trail_start_index = 0
        self.trail_view_end = 0

    def update_trail(self):
        """Called while moving forward in time."""
        if self.trail_view_end == 0:
            self.trail.append((self.x, self.y, self.z))
            self.trail_view_end = 1
            return

        last_trail_x, last_trail_y, last_trail_z = self.trail[self.trail_view_end - 1]

        dx = self.x - last_trail_x
        dy = self.y - last_trail_y
        dz = self.z - last_trail_z

        distance = math.sqrt(dx * dx + dy * dy + dz * dz)

        if distance > self.trail_min_distance:
            if self.trail_view_end < len(self.trail):
                del self.trail[self.trail_view_end:]

            self.trail.append((self.x, self.y, self.z))
            self.trail_view_end += 1

            if (self.trail_view_end - self.trail_start_index) > TRAIL_DISPLAY_LENGTH:
                self.trail_start_index += 1

    def rewind_trail(self):
        """Called while moving backward in time."""

        if self.trail_view_end < 2:
            return

        prev_x, prev_y, prev_z = self.trail[self.trail_view_end - 2]

        dx = self.x - prev_x
        dy = self.y - prev_y
        dz = self.z - prev_z

        distance = math.sqrt(dx * dx + dy * dy + dz * dz)

        if distance < self.trail_min_distance:
            self.trail_view_end -= 1

            if self.trail_start_index > 0:
                self.trail_start_index -= 1

    def draw_trail(self):
        window_length = self.trail_view_end - self.trail_start_index

        if window_length > 1:
            for i in range(self.trail_start_index + 1, self.trail_view_end):
                x1, y1, z1 = self.trail[i - 1]
                x2, y2, z2 = self.trail[i]

                p1 = project_point(
                    x1, y1, z1,
                    cam_x, cam_y, cam_z,
                    cam_fx, cam_fy, cam_fz,
                    cam_rx, cam_ry, cam_rz,
                    cam_up_x, cam_up_y, cam_up_z,
                    focal_length, width, height
                )

                p2 = project_point(
                    x2, y2, z2,
                    cam_x, cam_y, cam_z,
                    cam_fx, cam_fy, cam_fz,
                    cam_rx, cam_ry, cam_rz,
                    cam_up_x, cam_up_y, cam_up_z,
                    focal_length, width, height
                )

                if p1 is not None and p2 is not None:

                    if self is body_selected:
                        true_trail_color = self.trail_color
                    else:
                        true_trail_color = (
                            self.trail_color[0] // 2,
                            self.trail_color[1] // 2,
                            self.trail_color[2] // 2
                        )

                    t = (i - self.trail_start_index) / window_length
                    brightness = t ** self.trail_fader
                    drawn_trail_color = (
                        int(true_trail_color[0] * brightness),
                        int(true_trail_color[1] * brightness),
                        int(true_trail_color[2] * brightness),
                    )
                    pygame.draw.line(screen, drawn_trail_color, (p1[0], p1[1]), (p2[0], p2[1]), 2)

    def draw(self):
        body_point = project_point(
            self.x, self.y, self.z,
            cam_x, cam_y, cam_z,
            cam_fx, cam_fy, cam_fz,
            cam_rx, cam_ry, cam_rz,
            cam_up_x, cam_up_y, cam_up_z,
            focal_length, width, height
        )

        if body_point is None:
            return None

        sx, sy, depth = body_point
        base_radius = max(2.0, (self.radius_scale / depth))

        glow_surface = pygame.Surface((width, height), pygame.SRCALPHA)

        for i in range(8, 0, -1):

            glow_radius = base_radius * (1 + i / 12)

            alpha = int(180 * (i / 16))

            pygame.draw.circle(
                glow_surface,
                (*self.color, alpha),
                (sx, sy),
                int(glow_radius)
            )

        screen.blit(glow_surface, (0, 0))

        pygame.draw.circle(screen, self.color, (sx, sy), base_radius)

        return body_point

    def __str__(self):
        return self.name

class Slider:

    def __init__(self, slider_width, slider_height, min_value, max_value, initial_value,
                 track_color, knob_color_active, knob_color_inactive,
                 knob_radius, label, value_type, decimal_places, is_multiplier_slider,
                 is_logarithmic_slider, is_hidden, is_menu_slider):

        self.gap_space = 50

        self.slider_width = slider_width
        self.slider_height = slider_height
        self.x = width - 300
        self.y = self.gap_space + (self.gap_space + self.slider_height)*len(sliders)

        self.min_value = min_value
        self.max_value = max_value
        self.value = initial_value

        self.track_color = track_color
        self.knob_color_active = knob_color_active
        self.knob_color_inactive = knob_color_inactive
        self.knob_radius = knob_radius
        self.hidden_color = (60, 60, 60)

        self.label = label
        self.value_type = value_type
        self.decimal_places = decimal_places

        self.is_multiplier_slider = is_multiplier_slider
        self.is_logarithmic_slider = is_logarithmic_slider
        self.is_hidden = is_hidden

        self.is_menu_slider = is_menu_slider

        self.dragging = False
        self.click_margin = 15

        sliders.append(self)
        if self.is_menu_slider:
            menu_sliders.append(self)


    def value_to_slider(self):
        if self.is_logarithmic_slider:
            log_max = math.log(self.max_value)
            log_min = math.log(self.min_value)
            log_value = math.log(self.value)
            range_frac = (log_value - log_min) / (log_max - log_min)
        else:
            range_frac = (self.value - self.min_value) / (self.max_value - self.min_value)

        range_frac = max(0, min(1, range_frac))
        return self.x + self.slider_width * range_frac

    def slider_to_value(self, mouse_x):
        pixel_frac = (mouse_x - self.x) / self.slider_width
        pixel_frac = max(0, min(1, pixel_frac))



        if self.is_logarithmic_slider:
            log_min = math.log(self.min_value)
            log_max = math.log(self.max_value)
            return self.value_type(math.exp(log_min + pixel_frac * (log_max - log_min)))
        else:
            return self.value_type(self.min_value + pixel_frac * (self.max_value - self.min_value))


    def draw(self, new_x=None, new_y=None):
        if new_x is not None:
            self.x = new_x
        if new_y is not None:
            self.y = new_y

        pygame.draw.rect(
            screen,
            self.hidden_color if self.is_hidden else self.track_color,
            (self.x, self.y - self.slider_height // 2, self.slider_width, self.slider_height)
        )

        knob_x = self.value_to_slider()

        drawn_knob_color = None
        if self.is_hidden:
            drawn_knob_color = self.hidden_color
        elif self.dragging:
            drawn_knob_color = self.knob_color_active
        else:
            drawn_knob_color = self.knob_color_inactive

        pygame.draw.circle(
            screen,
            drawn_knob_color,
            (knob_x, self.y),
            self.knob_radius
        )

        if self.is_multiplier_slider:
            drawn_surface = font.render(
                f"{self.label} {self.value:.{self.decimal_places}f}x",
                True,
                self.hidden_color if self.is_hidden else (255, 255, 255)
            )
        else:
            drawn_surface = font.render(
                f"{self.label} {self.value:.{self.decimal_places}f}",
                True,
                self.hidden_color if self.is_hidden else (255, 255, 255)
            )

        screen.blit(drawn_surface, (self.x, self.y + 18))


    def handle_event(self, event, new_x=None, new_y=None):
        if new_x is not None:
            self.x = new_x
        if new_y is not None:
            self.y = new_y

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos

            if self.x <= mx <= self.x + self.slider_width and abs(my - self.y) < self.click_margin:
                self.value = self.slider_to_value(mx)
                self.dragging = True

        if event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            self.dragging = False

        if event.type == pygame.MOUSEMOTION:
            if self.dragging:
                mx, my = event.pos
                self.value = self.slider_to_value(mx)

class ExpandableMenu:
    def __init__(self, list_objects, *, menu_x=None, menu_y=None, second_list_objects=None,
                 menu_w=300, menu_clickable=False, mode_selection_needed=False, mode_1=None,
                 mode_2=None, option_height=30, max_visible_list_length=5, mixed_type_list=False, is_hidden=False):

        self.menu_clickable = menu_clickable
        self.mode_selection_needed = mode_selection_needed
        self.mode_1 = mode_1
        self.mode_2 = mode_2
        self.mode_1_pressed = True
        self.mode_2_pressed = False

        # Set dimensions / position
        gap_space = 10
        total_width = 0
        for menu in menus:
            total_width += menu.menu_w
        total_width += gap_space*(len(menus) + 1)

        if menu_y is None:
            self.menu_y = height - 45
        else:
            self.menu_y = menu_y

        if menu_x is None:
            self.menu_x = total_width
        else:
            self.menu_x = menu_x

        self.menu_h = 45
        self.menu_w = menu_w


        self.option_height = option_height
        self.max_visible_list_length = max_visible_list_length

        self.list_objects = list_objects
        self.second_list_objects = second_list_objects
        self.mixed_type_list = mixed_type_list
        self.first_visible_item = 0
        self.visible_list_length = min(len(self.list_objects), max_visible_list_length)

        self.menu_open = False
        self.menu_rect = pygame.Rect(self.menu_x, self.menu_y, self.menu_w, self.menu_h)

        self.option_clicked = False

        self.active_submenu = None

        self.is_hidden = is_hidden

        menus.append(self)

    def get_active_list(self):
        if self.second_list_objects is not None and not self.mode_1_pressed:
            return self.second_list_objects
        return self.list_objects

    def set_list(self, new_list):
        self.list_objects = new_list
        self.visible_list_length = min(len(new_list), self.max_visible_list_length)
        max_first = max(0, len(new_list) - self.visible_list_length)
        self.first_visible_item = min(self.first_visible_item, max_first)

    def draw_scrollbar(self, active_list):
        if len(active_list) <= self.visible_list_length:
            return

        total_h = self.visible_list_length * self.option_height
        top_y = self.menu_y - total_h

        bar_w = 10
        bar_x = self.menu_x + self.menu_w - bar_w

        thumb_h = total_h * self.visible_list_length / len(active_list)
        max_first = len(active_list) - self.visible_list_length

        scroll_frac = self.first_visible_item / max_first
        thumb_y = top_y + scroll_frac * (total_h - thumb_h)

        pygame.draw.rect(screen, (60, 60, 60), (bar_x, top_y, bar_w, total_h))
        pygame.draw.rect(screen, (200, 200, 200), (bar_x, thumb_y, bar_w, thumb_h))

    def clamp_to_screen(self, extra_bottom=0):
        rows = self.visible_list_length + (1 if self.mode_selection_needed else 0)

        top_y = self.menu_y - rows * self.option_height
        bottom_y = self.menu_y + self.menu_h + extra_bottom

        if top_y < 0:
            self.menu_y += -top_y

        if bottom_y > height:
            self.menu_y -= bottom_y - height

        self.menu_x = max(0, min(self.menu_x, width - self.menu_w))
        self.menu_rect.topleft = (self.menu_x, self.menu_y)

    def draw_menu(self, title, list_objects, new_x=None, new_y=None):
        if new_x is not None:
            self.menu_x = new_x
        if new_y is not None:
            self.menu_y = new_y

        self.menu_rect.topleft = (self.menu_x, self.menu_y)

        active_list = self.get_active_list()

        self.visible_list_length = min(len(active_list), self.max_visible_list_length)

        max_first = max(0, len(active_list) - self.visible_list_length)
        self.first_visible_item = min(self.first_visible_item, max_first)

        available_width = self.menu_w - 6

        if self.mixed_type_list:
            visible_rows = [
                list_objects[self.visible_list_length + self.first_visible_item - (i + 1)]
                for i in range(self.visible_list_length)
            ]
            row_texts = [widen_digits(str(item)) for kind, item in visible_rows if kind == "text"]
        else:
            visible_rows = [
                str(list_objects[self.visible_list_length + self.first_visible_item - (i + 1)])
                for i in range(self.visible_list_length)
            ]
            row_texts = [widen_digits(r) for r in visible_rows]

        title_font = get_uniform_font([title], available_width)

        if self.mode_selection_needed:
            row_texts += [str(self.mode_1), str(self.mode_2)]
        rows_font = get_uniform_font(row_texts, available_width)

        pygame.draw.rect(screen, (80, 80, 80) if self.is_hidden else (220, 220, 220), self.menu_rect, 1)
        menu_title = title_font.render(f"{title}", True, (90, 90, 90) if self.is_hidden else (255, 255, 255))
        screen.blit(menu_title, (self.menu_x + 3, self.menu_y + 3))

        if self.menu_open:
            if self.mode_selection_needed:
                mode_1_rect = pygame.Rect(self.menu_x, self.menu_y - self.option_height, self.menu_w // 2, self.option_height)
                mode_2_rect = pygame.Rect(self.menu_x + self.menu_w // 2, self.menu_y - self.option_height, self.menu_w // 2, self.option_height)

                active_rect_color = (255, 0, 0)
                inactive_rect_color = (220, 220, 220)

                if self.mode_1_pressed:
                    pygame.draw.rect(screen, active_rect_color, mode_1_rect, 3)
                    pygame.draw.rect(screen, inactive_rect_color, mode_2_rect, 1)
                else:
                    pygame.draw.rect(screen, active_rect_color, mode_2_rect, 3)
                    pygame.draw.rect(screen, inactive_rect_color, mode_1_rect, 1)

                mode_1_title = rows_font.render(f"{self.mode_1}", True, active_rect_color if self.mode_1_pressed else inactive_rect_color)
                mode_2_title = rows_font.render(f"{self.mode_2}", True, active_rect_color if self.mode_2_pressed else inactive_rect_color)
                screen.blit(mode_1_title, (self.menu_x + 3, self.menu_y - self.option_height + 3))
                screen.blit(mode_2_title, (self.menu_x + self.menu_w // 2 + 3, self.menu_y - self.option_height + 3))

            for i, row in enumerate(visible_rows):
                option_y_pos = self.menu_y - self.option_height * (i + 1) if not self.mode_selection_needed else self.menu_y - self.option_height * (i + 2)
                option_rect = pygame.Rect(
                    self.menu_x, option_y_pos,
                    self.menu_w, self.option_height
                )

                pygame.draw.rect(screen, (200, 200, 200), option_rect, 1)

                if self.mixed_type_list:
                    kind, item = row

                    if kind == "text":
                        label = rows_font.render(str(item), True, (255, 255, 255))
                        screen.blit(label, (self.menu_x + 3, option_y_pos + 3))

                    elif kind == "slider":
                        item.draw(self.menu_x + 3, option_y_pos + self.option_height // 2)

                    elif kind == "input":
                        item.draw(self.menu_x + 3, option_y_pos + 5)

                    elif kind == "name_input":
                        item.draw(self.menu_x + 3, option_y_pos + 5)

                    elif kind == "submenu":
                        label, submenu = item


                        text = rows_font.render(f"{label} >", True, (255, 255, 255))
                        screen.blit(text, (self.menu_x + 3, option_y_pos + 3))

                        if self.active_submenu is submenu:
                            submenu.menu_x = self.menu_x + self.menu_w + 5
                            submenu.menu_y = option_y_pos + self.option_height

                            submenu.clamp_to_screen()
                            submenu.draw_menu(label, submenu.list_objects)
                else:
                    label = rows_font.render(row, True, (255, 255, 255))
                    screen.blit(label, (self.menu_x + 3, option_y_pos + 3))

            self.draw_scrollbar(active_list)

    def handle_event(self, event, new_x=None, new_y=None):
        if self.is_hidden:
            return

        if new_x is not None:
            self.menu_x = new_x
        if new_y is not None:
            self.menu_y = new_y

        self.menu_rect.topleft = (self.menu_x, self.menu_y)

        active_list = self.get_active_list()

        if self.active_submenu is not None:
            submenu_output = self.active_submenu.handle_event(event)

            if submenu_output is not None:
                return ("submenu", self.active_submenu, submenu_output)

        if self.mixed_type_list and self.menu_open:
            for i in range(self.visible_list_length):
                item_index = self.visible_list_length + self.first_visible_item - i - 1
                option_y_pos = self.menu_y - self.option_height * (i + (2 if self.mode_selection_needed else 1))

                kind, item = active_list[item_index]

                if kind == "slider":
                    item.handle_event(event, self.menu_x + 3, option_y_pos + self.option_height // 2)

                elif kind == "input":
                    item.handle_event(event, self.menu_x + 3, option_y_pos + 5)

                elif kind == "name_input":
                    item.handle_event(event, self.menu_x + 3, option_y_pos + 5)

                elif kind == "submenu":
                    label, submenu = item

                    row_rect = pygame.Rect(
                        self.menu_x,
                        option_y_pos,
                        self.menu_w,
                        self.option_height
                    )

                    if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        if row_rect.collidepoint(event.pos):
                            if self.active_submenu is submenu:
                                self.active_submenu = None
                                submenu.menu_open = False
                            else:
                                self.active_submenu = submenu
                                submenu.menu_open = True

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos

            if self.menu_x <= mx <= self.menu_x + self.menu_w:

                if height >= my >= self.menu_y:
                    self.menu_open = not self.menu_open
                    return

                if self.menu_clickable:
                    self.option_clicked = False

                    if self.menu_open:
                        if self.mode_selection_needed:
                            if self.menu_y >= my >= self.menu_y - self.option_height:
                                if self.menu_x <= mx <= self.menu_x + self.menu_w // 2:
                                    self.mode_1_pressed = True
                                    self.mode_2_pressed = False
                                    return True
                                else:
                                    self.mode_1_pressed = False
                                    self.mode_2_pressed = True
                                    return False

                        if not self.mixed_type_list:
                            for i in range(self.visible_list_length):
                                item_index = self.visible_list_length + self.first_visible_item - (i+1)
                                if self.mode_selection_needed:
                                    option_y_pos = self.menu_y - self.option_height * (i + 2)
                                else:
                                    option_y_pos = self.menu_y - self.option_height * (i + 1)

                                if option_y_pos <= my <= option_y_pos + self.option_height:
                                    self.option_clicked = True
                                    return item_index

        if event.type == pygame.MOUSEWHEEL:
            mx, my = pygame.mouse.get_pos()

            if self.menu_open:
                if self.mode_selection_needed:
                    lower_bound = self.menu_y - self.option_height
                    upper_bound = self.menu_y - self.option_height * (self.visible_list_length + 1)
                else:
                    lower_bound = self.menu_y
                    upper_bound = self.menu_y - self.option_height * self.visible_list_length
                if self.menu_x <= mx <= self.menu_x + self.menu_w and upper_bound <= my <= lower_bound:
                    self.first_visible_item -= event.y
                    max_first = max(0, len(active_list) - self.visible_list_length)
                    self.first_visible_item = max(0, min(self.first_visible_item, max_first))


class TextInputBox:
    def __init__(self, width, height, label, initial_value="", max_digits=15, min_value=None, max_value=None):
        self.width = width
        self.height = height
        self.label = label
        self.x = self.y = 0
        self.text_buffer = str(initial_value)
        self.is_focused = False
        self.committed_value = float(initial_value)
        self.max_digits = max_digits
        self.min_value = min_value
        self.max_value = max_value

    def set_value(self, value):
        self.committed_value = float(value)
        self.text_buffer = f"{self.committed_value:.15g}"

    def commit(self):
        try:
            value = float(self.text_buffer)
            if self.min_value is not None:
                value = max(self.min_value, value)
            if self.max_value is not None:
                value = min(self.max_value, value)
            self.set_value(value)
        except ValueError:
            self.text_buffer = f"{self.committed_value:.15g}"
        self.is_focused = False

    def draw(self, new_x=None, new_y=None):
        if new_x is not None: self.x = new_x
        if new_y is not None: self.y = new_y

        label_surface = font.render(f"{self.label}: ", True, (255, 255, 255))
        box_x = self.x + label_surface.get_width()
        rect = pygame.Rect(box_x, self.y, self.width, self.height)
        border_color = (255, 0, 0) if self.is_focused else (200, 200, 200)

        screen.blit(label_surface, (self.x, self.y + self.height // 2 - label_surface.get_height() // 2))
        pygame.draw.rect(screen, border_color, rect, 2)

        cursor = "|" if self.is_focused and (pygame.time.get_ticks() // 500) % 2 == 0 else ""
        shown_text = self.text_buffer + cursor
        text_font = get_uniform_font([widen_digits(shown_text)], self.width - 8, start_size=28, min_size=12)
        text_surface = text_font.render(shown_text, True, (255, 255, 255))
        screen.blit(text_surface, (box_x + 4, self.y + self.height // 2 - text_surface.get_height() // 2))

    def handle_event(self, event, new_x=None, new_y=None):
        if new_x is not None: self.x = new_x
        if new_y is not None: self.y = new_y

        label_width = font.size(f"{self.label}: ")[0]
        rect = pygame.Rect(self.x + label_width, self.y, self.width, self.height)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            was_focused = self.is_focused
            self.is_focused = rect.collidepoint(event.pos)
            if was_focused and not self.is_focused:
                self.commit()

        if self.is_focused and event.type == pygame.KEYDOWN:
            if event.key == pygame.K_RETURN:
                self.commit()
            elif event.key == pygame.K_BACKSPACE:
                self.text_buffer = self.text_buffer[:-1]
            elif event.unicode in "0123456789.eE+-":
                digit_count = sum(char.isdigit() for char in self.text_buffer)
                if not event.unicode.isdigit() or digit_count < self.max_digits:
                    self.text_buffer += event.unicode


class NameInputBox:
    def __init__(self, width, height, label, initial_value=""):
        self.width = width
        self.height = height
        self.label = label
        self.x = self.y = 0
        self.text_buffer = initial_value
        self.is_focused = False

    def draw(self, new_x=None, new_y=None):
        if new_x is not None: self.x = new_x
        if new_y is not None: self.y = new_y

        label_surface = font.render(f"{self.label}: ", True, (255, 255, 255))
        box_x = self.x + label_surface.get_width()

        pygame.draw.rect(
            screen,
            (255, 0, 0) if self.is_focused else (200, 200, 200),
            (box_x, self.y, self.width, self.height),
            2
        )

        cursor = "|" if self.is_focused and (pygame.time.get_ticks() // 500) % 2 == 0 else ""
        text_surface = font.render(self.text_buffer + cursor, True, (255, 255, 255))

        screen.blit(label_surface, (self.x, self.y))
        screen.blit(text_surface, (box_x + 4, self.y))

    def handle_event(self, event, new_x=None, new_y=None):
        if new_x is not None: self.x = new_x
        if new_y is not None: self.y = new_y

        label_width = font.size(f"{self.label}: ")[0]
        rect = pygame.Rect(self.x + label_width, self.y, self.width, self.height)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            self.is_focused = rect.collidepoint(event.pos)

        if self.is_focused and event.type == pygame.KEYDOWN:
            if event.key == pygame.K_BACKSPACE:
                self.text_buffer = self.text_buffer[:-1]

            elif event.key == pygame.K_RETURN:
                self.is_focused = False

            elif event.unicode.isprintable() and len(self.text_buffer) < 20:
                self.text_buffer += event.unicode

class Button:
    def __init__(self, width, height, text):
        self.width = width
        self.height = height
        self.text = text
        self.x = self.y = 0

    def draw(self, x, y):
        self.x, self.y = x, y
        rect = pygame.Rect(x, y, self.width, self.height)

        pygame.draw.rect(screen, (200, 200, 200), rect, 2)

        text_surface = font.render(self.text, True, (255, 255, 255))
        screen.blit(text_surface, (
            x + self.width / 2 - text_surface.get_width() / 2,
            y + self.height / 2 - text_surface.get_height() / 2
        ))

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            return pygame.Rect(self.x, self.y, self.width, self.height).collidepoint(event.pos)

        return False

G = 4 * (math.pi ** 2)

# Calculate distance function
def calculate_distance(body_1, body_2):
    dx = body_1.x - body_2.x
    dy = body_1.y - body_2.y
    dz = body_1.z - body_2.z

    distance = math.sqrt(dx**2+dy**2+dz**2)

    return distance

# Decide if all the bodies in the system can be seen on screen
def all_bodies_in_view(margin=10):
    for body in bodies:
        if body.screen_point is None:
            return False

        sx, sy, _ = body.screen_point
        if not (margin <= sx <= width - margin and
                margin <= sy <= height - margin):
            return False

    return True

# Find the closest body
def find_closest_body(main_body, skipped_bodies=None):
    smallest_distance = float('inf')
    closest_body = None

    for body in bodies:
        if skipped_bodies is not None:
            if body in skipped_bodies:
                continue

        if body is not main_body:

            distance = calculate_distance(main_body, body)

            if distance < smallest_distance:
                smallest_distance = distance
                closest_body = body


    return closest_body, smallest_distance

def find_closest_body_to_point(px, py, pz):
    closest_body = None
    smallest_distance = None

    for body in bodies:
        dx = body.x - px
        dy = body.y - py
        dz = body.z - pz
        distance = math.sqrt(dx**2 + dy**2 + dz**2)

        if smallest_distance is None or distance < smallest_distance:
            closest_body = body
            smallest_distance = distance

    return closest_body, smallest_distance

def calculate_orbital_period(body):
    if body.primary is None:
        return None
    radius = calculate_distance(body, body.primary)
    orbital_period = math.sqrt(radius**3/body.primary.mass)

    return orbital_period

def calculate_speed(body):
    body_speed = math.sqrt(body.vx**2 + body.vy**2 + body.vz**2)
    return body_speed

def find_greatest_accel():
    greatest_accel = None

    for body in bodies:
        accel_mag = math.sqrt(body.ax**2+body.ay**2+body.az**2)

        if greatest_accel is None:
            greatest_accel = accel_mag

        if accel_mag > greatest_accel:
            greatest_accel = accel_mag

    return greatest_accel

def calculate_center_of_mass(list_of_bodies):
    total_mass = 0
    total_x_vec = 0
    total_y_vec = 0
    total_z_vec = 0
    for body in list_of_bodies:
        total_x_vec += body.x * body.mass
        total_y_vec += body.y * body.mass
        total_z_vec += body.z * body.mass

        total_mass += body.mass

    center_of_mass_x = total_x_vec / total_mass
    center_of_mass_y = total_y_vec / total_mass
    center_of_mass_z = total_z_vec / total_mass

    return center_of_mass_x, center_of_mass_y, center_of_mass_z

earth_mass = 0.00000300343
moon_mass = 0.000000036946227

moon_earth_distance = 0.00257

energy_to_joules = 4.4685e37

verlet_total_energy = []
euler_total_energy = []
time_data = []
sim_time = 0

# Camera orbit settings
R = 2.5
theta = 0.0
phi = 0.4
focal_length = width

world_up_x = 0
world_up_y = 1
world_up_z = 0

# Velocity/Accel vectors
velocity_scale = 0.01 * R
acceleration_scale = 0.002 * R
a0 = 5

def clamp_va_vectors():
    global velocity_scale, acceleration_scale
    velocity_scale = min(0.3, velocity_scale)
    acceleration_scale = min(0.06, acceleration_scale)

clamp_va_vectors()

if len(bodies) == 2:
    system_text = "2 body system"
    # Initial system label without integrator swap
    system_label = "2 body system | Verlet"
else:
    system_text = "N-body system"
    # Initial system label without integrator swap
    system_label = "N-body system | Verlet"

def create_circular_orbit(name, central_body, radius, mass, color, trail_color, radius_scale):

    orbital_speed = math.sqrt(G * (central_body.mass + mass) / radius)

    body = OrbitingBody(
        name,

        central_body,

        central_body.x + radius,
        central_body.y,
        central_body.z,

        central_body.vx,
        central_body.vy - orbital_speed,
        central_body.vz,

        mass,
        color,
        trail_color,
        radius_scale
    )

    body.name = name
    return body

# Sublists, body types
stars = []
planets = []
moons = []

# Sun (central body)
Sun = OrbitingBody(
    "Sun", None, 0, 0, 0,
    0.0, 0.0, 0.0,
    1.0,
    (255, 220, 100), (255, 220, 100),
    25
)


# Sun-Centric bodies
Earth = create_circular_orbit("Earth", Sun, 1, earth_mass, (40, 157, 140), (40, 157, 140), 0.15)


# Moons
Moon = create_circular_orbit("Moon", Earth, 0.00257, moon_mass, (220, 220, 220), (180, 180, 180), 0.05)



SAFETY_FRACTION = 0.15  # how much of the real gap a body's exaggerated size may occupy
TARGET_SCALE = 10
R_typical = 2.5

def assign_radius_scales(list_bodies=bodies):
    for body in list_bodies:
        _, closest_distance = find_closest_body(body)
        safety_radius_scale = SAFETY_FRACTION * focal_length * closest_distance
        desired_radius_scale = TARGET_SCALE * (body.mass ** (1/3)) * R_typical
        body.radius_scale = min(safety_radius_scale, desired_radius_scale)


assign_radius_scales()

def find_suitable_dt():
    smallest_orbital_period = None

    for body in bodies:
        if body.primary is None:
            continue

        distance_to_primary = calculate_distance(body, body.primary)
        orbital_period_years = math.sqrt(distance_to_primary**3/body.primary.mass)

        if smallest_orbital_period is None:
            smallest_orbital_period = orbital_period_years

        if orbital_period_years < smallest_orbital_period:
            smallest_orbital_period = orbital_period_years

    return smallest_orbital_period / 250

dt = find_suitable_dt()

dt_lower_limit = dt/10
dt_upper_limit = dt*10

substeps = 1000


bodies.sort(key=lambda body: body.mass)
body_selected = Earth
camera_target = Sun


max_energy_error = 0
baseline_total_energy = None
energy_error_label = None
SAFETY_MARGIN = 3
energy_spike_threshold = 0.01
previous_total_energy = None

selecting_camera_target = False
camera_target_is_com = False
camera_target_is_origin = False
body_mode_selected = True

show_stats = False









# Menus

# Body camera menu
bodies_and_com_list = ["Origin", "CoM"] + bodies
body_camera_menu = ExpandableMenu(bodies, second_list_objects=bodies_and_com_list, menu_w=300,  menu_clickable=True,
                                  mode_selection_needed=True, mode_1="Body", mode_2="Camera",
                                  option_height=35, max_visible_list_length=10
                                  )
# Keybinds menu
keybinds = ["A/D: Pan Camera", "W/S: Pitch Camera", "B: Place body", "9: Switch Integrators",
            "E/Q: Zoom In/Out", "C: Cinematic Mode", "J: Reset Camera Zoom", "M: Show stats", "P: Pause",
            "Arrow Keys: Rewind / Simulate", "V: Toggle Vectors",
            "T: Select Camera Target", "1: Load Earth-Moon-Sun", "2: Load Inner Solar System",
            "3: Load Solar System", "4: Load Binary Star System", "5: Load Empty System"]
keybinds_menu = ExpandableMenu(keybinds, menu_w=300, option_height=35, max_visible_list_length=5)

DISTANCE_UNITS = {
    "AU" : {
        "factor": 1,
        "min_value": 0.1,
        "precision": 2
    },
    "Million km" : {
        "factor": 149.5978707,
        "min_value": 1,
        "precision": 2
    },
    "Million miles" : {
        "factor": 92.955807,
        "min_value": 1,
        "precision": 2
    },
    "Km" : {
        "factor": 149_597_870.7,
        "min_value": 0,
        "precision": 2
    },
    "Miles" : {
        "factor": 92_955_807,
        "min_value": 0,
        "precision": 2
    }
}

SPEED_UNITS = {
    "km/s": {
        "factor": 4.740470464,
        "precision": 2
    },

    "m/s": {
        "factor": 4740.470464,
        "precision": 0
    },

    "km/h": {
        "factor": 17_065.69367,
        "precision": 0
    },

    "mph": {
        "factor": 10_603.98413,
        "precision": 0
    }
}

def format_distance(distance_au):
    for label, unit in DISTANCE_UNITS.items():

        converted_distance = distance_au * unit["factor"]

        if converted_distance >= unit["min_value"]:
            return (
                f"{converted_distance:,.{unit['precision']}f} {label}"
            )

def format_speed(speed_au_per_year, preferred_unit="km/s"):
    unit = SPEED_UNITS[preferred_unit]

    converted_speed = speed_au_per_year * unit["factor"]
    return (
        f"{converted_speed:,.{unit['precision']}f} {preferred_unit}"
    )

def acquire_body_info(inspected_body):
    body_information = []

    body_information.append(f"Name: {inspected_body.name}")
    body_information.append(f"Mass: {inspected_body.mass}")

    # Closest body, and the distance to such body
    closest_body, distance_to_closest_body = find_closest_body(inspected_body)
    distance_to_closest_body = format_distance(distance_to_closest_body)
    body_information.append(f"Closest Body: {closest_body}, {distance_to_closest_body}")

    # Body speed
    body_speed = calculate_speed(inspected_body)
    body_speed = format_speed(body_speed)
    body_information.append(f"Speed: {body_speed}")

    # If the body does not have a primary, do not perform primary-related calculations.
    if inspected_body.primary is not None:
        body_orbital_period = calculate_orbital_period(inspected_body)
        body_information.append(f"Orbital Period: {body_orbital_period:.2f} Years")

        distance_to_primary = calculate_distance(inspected_body, inspected_body.primary)
        hill_sphere_radius = distance_to_primary * math.cbrt(inspected_body.mass / (3 * inspected_body.primary.mass))

        distance_to_primary = format_distance(distance_to_primary)
        body_information.append(f"Primary: {inspected_body.primary}, {distance_to_primary}")


        hill_sphere_radius = format_distance(hill_sphere_radius)
        body_information.append(f"Hill Sphere Radius: {hill_sphere_radius}")
    else:
        body_information.append("Orbital period: N/A")
        body_information.append("Primary: N/A")



    return body_information

# Body info menu
body_information = acquire_body_info(body_selected)

body_info_menu = ExpandableMenu(body_information, menu_x = width - 430, menu_w=400, option_height=35, max_visible_list_length=5)

# More settings menu (User body placement)
body_settings_list = []
more_settings_menu = ExpandableMenu(body_settings_list, menu_w=300, option_height=75, max_visible_list_length=3, mixed_type_list=True)

coplanar_bodies = [body for body in bodies if body.primary is not None]
coplanar_body_menu = ExpandableMenu(coplanar_bodies, menu_w=200, menu_clickable=True, option_height=35, max_visible_list_length=6)
coplanar_body_menu.menu_open = False

body_settings_list.append(("submenu", ("Coplanar with", coplanar_body_menu)))



def find_settings_menu_x(body_x, velocity_end_x, menu, gap=30):
    left_x = body_x - menu.menu_w - gap
    right_x = body_x + gap

    velocity_goes_right = velocity_end_x >= body_x
    preferred_x = left_x if velocity_goes_right else right_x
    fallback_x = right_x if velocity_goes_right else left_x

    def fits(x):
        return 0 <= x and x + menu.menu_w <= width

    if fits(preferred_x):
        return preferred_x
    if fits(fallback_x):
        return fallback_x

    return max(0, min(preferred_x, width - menu.menu_w))

# More settings menu done button
done_button = Button(300, 35, "Done")


# Sliders
dt_slider = Slider(
    220, 6,
    dt_lower_limit, dt_upper_limit, dt,
    (160, 160, 160),
    (255, 0, 0),
    (200, 200, 200),
    10,
    "dt:",
    float,
    3,
    False,
    False,
    False,
    False
)

substeps_slider = Slider(
    220, 6,
    10, 1000, 500,
    (160, 160, 160),
    (0, 0, 255),
    (200, 200, 200),
    10,
    "Substeps:",
    int,
    0,
    False,
    False,
    False,
    False
)

zoom_strength_slider = Slider(
    220, 6,
    1, 100, 1,
    (160, 160, 160),
    (0, 0, 255),
    (200, 200, 200),
    10,
    "Zoom strength:",
    float,
    2,
    True,
    True,
    False,
    False
)

paused_simulating_speed_slider = Slider(
    220, 6,
    1, 100, 1,
    (160, 160, 160),
    (0, 0, 255),
    (200, 200, 200),
    10,
    "Paused simulating speed:",
    float,
    2,
    True,
    True,
    True,
    False
)

#  SETTINGS MENU SLIDERS
MAX_BODY_MASS = 100.0
mass_input_box = TextInputBox(85, 30, "Mass (Solar Masses)", 0.0001, max_digits=15, min_value=0, max_value=MAX_BODY_MASS)
body_settings_list.append(("input", mass_input_box))

# Add later to index 0
name_input_box = NameInputBox(120, 30, "Name", "")

# Append this later if applicable
distance_input_box = TextInputBox(85, 30, "Distance to Primary (AU)", 1, max_digits=15, min_value=0)

red_color_slider = Slider(
    more_settings_menu.menu_w - 4, 6,
    0, 255, 255,
    (160, 160, 160),
    (0, 0, 255),
    (200, 200, 200),
    10,
    "Body Red:",
    int,
    0,
    False,
    False,
    False,
    True
)

body_settings_list.append(("slider", red_color_slider))

green_color_slider = Slider(
    more_settings_menu.menu_w - 4, 6,
    0, 255, 255,
    (160, 160, 160),
    (0, 0, 255),
    (200, 200, 200),
    10,
    "Body Green:",
    int,
    0,
    False,
    False,
    False,
    True
)

body_settings_list.append(("slider", green_color_slider))

blue_color_slider = Slider(
    more_settings_menu.menu_w - 4, 6,
    0, 255, 255,
    (160, 160, 160),
    (0, 0, 255),
    (200, 200, 200),
    10,
    "Body Blue:",
    int,
    0,
    False,
    False,
    False,
    True
)

body_settings_list.append(("slider", blue_color_slider))

red_trail_color_slider = Slider(
    more_settings_menu.menu_w - 4, 6,
    0, 255, 255,
    (160, 160, 160),
    (0, 0, 255),
    (200, 200, 200),
    10,
    "Trail Red:",
    int,
    0,
    False,
    False,
    False,
    True
)

body_settings_list.append(("slider", red_trail_color_slider))

green_trail_color_slider = Slider(
    more_settings_menu.menu_w - 4, 6,
    0, 255, 255,
    (160, 160, 160),
    (0, 0, 255),
    (200, 200, 200),
    10,
    "Trail Green:",
    int,
    0,
    False,
    False,
    False,
    True
)

body_settings_list.append(("slider", green_trail_color_slider))

blue_trail_color_slider = Slider(
    more_settings_menu.menu_w - 4, 6,
    0, 255, 255,
    (160, 160, 160),
    (0, 0, 255),
    (200, 200, 200),
    10,
    "Trail Blue:",
    int,
    0,
    False,
    False,
    False,
    True
)

body_settings_list.append(("slider", blue_trail_color_slider))

original_body_settings_list = body_settings_list.copy()




# If the user clicks on a body, make it the body selected.

def handle_body_click_event(event):
    global body_selected
    global camera_target
    global selecting_camera_target
    global paused

    if event.type == pygame.KEYDOWN and not typing_in_input:
        if event.key == pygame.K_t:
            selecting_camera_target = not selecting_camera_target
            paused = selecting_camera_target
    if event.type == pygame.MOUSEBUTTONDOWN:
        mx, my = event.pos

        for body in bodies:
            if body.screen_point is None:
                continue
            sx, sy, depth = body.screen_point

            dx = mx - sx
            dy = my - sy

            if math.sqrt(dx**2+dy**2) < 10:
                if selecting_camera_target:
                    camera_target = body
                    selecting_camera_target = False
                    paused = False
                else:
                    body_selected = body
                    camera_target = body
                break

# Take a 3D coordinate and turn it into 2D screen coordinates with a depth measurement
def project_point(
        px, py, pz,
        cam_x, cam_y, cam_z,
        cam_fx, cam_fy, cam_fz,
        cam_rx, cam_ry, cam_rz,
        cam_up_x, cam_up_y, cam_up_z,
        focal_length,
        width, height
):
    point_dx = px - cam_x
    point_dy = py - cam_y
    point_dz = pz - cam_z

    x_cam = point_dx * cam_rx + point_dy * cam_ry + point_dz * cam_rz
    y_cam = point_dx * cam_up_x + point_dy * cam_up_y + point_dz * cam_up_z
    z_cam = point_dx * cam_fx + point_dy * cam_fy + point_dz * cam_fz

    if z_cam <= 0.01:
        return None

    sx = width / 2 + focal_length * (x_cam / z_cam)
    sy = height / 2 - focal_length * (y_cam / z_cam)

    return int(sx), int(sy), z_cam

# Inverse of project point
def convert_mouse_to_3D():

    mx, my = pygame.mouse.get_pos()
    x_local = (mx - width / 2) / focal_length
    y_local = (height / 2 - my) / focal_length
    z_local = 1

    # Add more options later. If user inputs a plane distance, or if they select a body for this new body to be coplanar with.
    # copied_body = body_selected
    # dx = copied_body.x - cam_x
    # dy = copied_body.y - cam_y
    # dz = copied_body.z - cam_z

    # Dot the vector from the camera to the copied body with the camera's forward vector to determine the plane distance
    # plane_distance = dx * cam_fx + dy * cam_fy + dz * cam_fz


    plane_distance = R


    world_dir_x = x_local * cam_rx + y_local * cam_up_x + z_local * cam_fx
    world_dir_y = x_local * cam_ry + y_local * cam_up_y + z_local * cam_fy
    world_dir_z = x_local * cam_rz + y_local * cam_up_z + z_local * cam_fz

    # Find how much the world direction vector lies in the camera's forward vector's direction with a dot product
    world_dir_forward = world_dir_x * cam_fx + world_dir_y * cam_fy + world_dir_z * cam_fz

    steps_to_plane = plane_distance / world_dir_forward

    hit_x = cam_x + steps_to_plane * world_dir_x
    hit_y = cam_y + steps_to_plane * world_dir_y
    hit_z = cam_z + steps_to_plane * world_dir_z

    return hit_x, hit_y, hit_z

def snap_camera_to_orbital_plane(body):
    global theta, phi, camera_target, camera_target_is_com

    if body.primary is None:
        return False

    h = find_h_vector(body)
    if h is None:
        return False

    hx, hy, hz = h
    h_mag = math.sqrt(hx**2 + hy**2 + hz**2)

    if h_mag == 0:
        return False

    hx /= h_mag
    hy /= h_mag
    hz /= h_mag

    # Choose whichever side of the plane is closer to current view
    if cam_fx * hx + cam_fy * hy + cam_fz * hz < 0:
        hx, hy, hz = -hx, -hy, -hz

    # Camera radial direction is opposite camera-forward direction
    phi = math.asin(max(-1, min(1, -hy)))
    theta = math.atan2(-hz, -hx)

    # Center camera on a point contained in the orbital plane
    camera_target = body.primary
    camera_target_is_com = False

    return True



# Find the vector normal to the placed body's orbital plane.
def find_h_vector(body):
    if body.primary is None:
        return None

    rx = body.x - body.primary.x
    ry = body.y - body.primary.y
    rz = body.z - body.primary.z

    vx = body.vx - body.primary.vx
    vy = body.vy - body.primary.vy
    vz = body.vz - body.primary.vz

    hx = ry * vz - rz * vy
    hy = rz * vx - rx * vz
    hz = rx * vy - ry * vx

    return hx, hy, hz

def prepare_body_settings():
    global placed_body_primary, placed_radial_x, placed_radial_y, placed_radial_z
    global placed_body_dist_to_primary, body_settings_list

    placed_body_primary = define_primary(placed_body_x, placed_body_y, placed_body_z)

    coplanar_bodies.clear()
    coplanar_bodies.extend(body for body in bodies if body.primary is not None)
    coplanar_body_menu.set_list(coplanar_bodies)

    body_settings_list = original_body_settings_list.copy()

    if placed_body_primary is not None:
        dx = placed_body_x - placed_body_primary.x
        dy = placed_body_y - placed_body_primary.y
        dz = placed_body_z - placed_body_primary.z
        placed_body_dist_to_primary = math.sqrt(dx**2 + dy**2 + dz**2)

        if placed_body_dist_to_primary > 0:
            placed_radial_x = dx / placed_body_dist_to_primary
            placed_radial_y = dy / placed_body_dist_to_primary
            placed_radial_z = dz / placed_body_dist_to_primary
        else:
            placed_radial_x, placed_radial_y, placed_radial_z = 1, 0, 0

        distance_input_box.set_value(placed_body_dist_to_primary)
        body_settings_list.insert(0, ("input", distance_input_box))
        body_settings_list.insert(0, ("text", f"Primary: {placed_body_primary.name}"))
    else:
        placed_body_dist_to_primary = None
        body_settings_list.insert(0, ("text", "Primary: None"))

    body_settings_list.insert(0, ("name_input", name_input_box))

    more_settings_menu.set_list(body_settings_list)


def update_placed_body_distance():
    global placed_body_x, placed_body_y, placed_body_z, placed_body_dist_to_primary
    global camera_target, camera_target_is_com, R

    if placed_body_primary is None:
        return

    new_distance = distance_input_box.committed_value

    if placed_body_primary.primary is not None:
        hill_radius = calculate_distance(
            placed_body_primary,
            placed_body_primary.primary
        ) * math.cbrt(
            placed_body_primary.mass / (3 * placed_body_primary.primary.mass)
        )

        new_distance = min(new_distance, 0.4 * hill_radius)
        distance_input_box.set_value(new_distance)

    if new_distance == placed_body_dist_to_primary:
        return

    placed_body_dist_to_primary = new_distance
    placed_body_x = placed_body_primary.x + placed_radial_x * new_distance
    placed_body_y = placed_body_primary.y + placed_radial_y * new_distance
    placed_body_z = placed_body_primary.z + placed_radial_z * new_distance

    camera_target = placed_body_primary
    camera_target_is_com = False
    R = max(0.001, new_distance * 2.5)


def handle_body_placement_click():
    global dragging_velocity_vector, settings_under_review
    global screen_body_mx, screen_body_my, screen_v_end_mx, screen_v_end_my
    global placed_body_x, placed_body_y, placed_body_z
    global placed_body_vx, placed_body_vy, placed_body_vz

    if not dragging_velocity_vector and not settings_under_review:
        screen_body_mx, screen_body_my = pygame.mouse.get_pos()
        placed_body_x, placed_body_y, placed_body_z = convert_mouse_to_3D()
        dragging_velocity_vector = True
        return

    if dragging_velocity_vector:
        placed_v_end_x, placed_v_end_y, placed_v_end_z = convert_mouse_to_3D()
        screen_v_end_mx, screen_v_end_my = pygame.mouse.get_pos()

        placed_body_vx = (placed_v_end_x - placed_body_x) * DRAGGED_VELOCITY_FACTOR
        placed_body_vy = (placed_v_end_y - placed_body_y) * DRAGGED_VELOCITY_FACTOR
        placed_body_vz = (placed_v_end_z - placed_body_z) * DRAGGED_VELOCITY_FACTOR

        dragging_velocity_vector = False
        settings_under_review = True
        more_settings_menu.menu_open = True

        prepare_body_settings()

        more_settings_menu.menu_x = find_settings_menu_x(screen_body_mx, screen_v_end_mx, more_settings_menu)
        more_settings_menu.menu_y = screen_body_my
        more_settings_menu.clamp_to_screen(extra_bottom=done_button.height + 5)


def draw_body_placement():
    global screen_body_mx, screen_body_my

    mouse_circ_radius = max(2.0, 0.25 / R)

    if not dragging_velocity_vector and not settings_under_review:
        moving_mx, moving_my = pygame.mouse.get_pos()
        pygame.draw.circle(screen, (255, 255, 255), (moving_mx, moving_my), mouse_circ_radius)

    elif dragging_velocity_vector:
        pygame.draw.circle(screen, (255, 255, 255), (screen_body_mx, screen_body_my), mouse_circ_radius)
        screen_v_end_mx, screen_v_end_my = pygame.mouse.get_pos()
        pygame.draw.line(screen, (0, 255, 0), (screen_body_mx, screen_body_my), (screen_v_end_mx, screen_v_end_my), 3)

    elif settings_under_review:
        body_screen_point = project_point(
            placed_body_x, placed_body_y, placed_body_z,
            cam_x, cam_y, cam_z,
            cam_fx, cam_fy, cam_fz,
            cam_rx, cam_ry, cam_rz,
            cam_up_x, cam_up_y, cam_up_z,
            focal_length, width, height
        )

        velocity_end_x = placed_body_x + placed_body_vx / DRAGGED_VELOCITY_FACTOR
        velocity_end_y = placed_body_y + placed_body_vy / DRAGGED_VELOCITY_FACTOR
        velocity_end_z = placed_body_z + placed_body_vz / DRAGGED_VELOCITY_FACTOR
        velocity_screen_point = project_point(
            velocity_end_x, velocity_end_y, velocity_end_z,
            cam_x, cam_y, cam_z,
            cam_fx, cam_fy, cam_fz,
            cam_rx, cam_ry, cam_rz,
            cam_up_x, cam_up_y, cam_up_z,
            focal_length, width, height
        )

        if body_screen_point is not None:
            screen_body_mx, screen_body_my, _ = body_screen_point
            pygame.draw.circle(screen, (255, 255, 255), (screen_body_mx, screen_body_my), mouse_circ_radius)

        if body_screen_point is not None and velocity_screen_point is not None:
            pygame.draw.line(screen, (0, 255, 0), body_screen_point[:2], velocity_screen_point[:2], 3)

        more_settings_menu.clamp_to_screen(extra_bottom=done_button.height + 5)
        more_settings_menu.draw_menu("More settings...", more_settings_menu.list_objects)
        done_button.draw(more_settings_menu.menu_x, more_settings_menu.menu_y + more_settings_menu.menu_h + 5)


def finish_body_placement():
    global settings_under_review, placing_body, vectors_toggled, paused

    mass_input_box.commit()
    if placed_body_primary is not None:
        distance_input_box.commit()
        update_placed_body_distance()

    placed_body_color = (red_color_slider.value, green_color_slider.value, blue_color_slider.value)
    placed_body_trail_color = (red_trail_color_slider.value, green_trail_color_slider.value, blue_trail_color_slider.value)

    body_name = name_input_box.text_buffer.strip() or "Unnamed"

    new_body = OrbitingBody(
        body_name, placed_body_primary,
        placed_body_x, placed_body_y, placed_body_z,
        placed_body_vx, placed_body_vy, placed_body_vz,
        mass_input_box.committed_value,
        placed_body_color,
        placed_body_trail_color,
        25
    )
    update_camera_target_list()

    assign_radius_scales([new_body])

    settings_under_review = False
    placing_body = False
    more_settings_menu.menu_open = False
    more_settings_menu.active_submenu = None
    coplanar_body_menu.menu_open = False
    vectors_toggled = True
    paused = False
    name_input_box.is_focused = False
    mass_input_box.is_focused = False
    distance_input_box.is_focused = False


def define_primary(x, y, z):
    print(f"{stars}")
    print(f"{planets}")
    print(f"{moons}")

    if not stars:
        return None

    for moon in moons:

        if moon.primary is None:
            continue

        dx = moon.x - x
        dy = moon.y - y
        dz = moon.z - z

        dist_squared = dx**2 + dy**2 + dz**2

        moon_radius_x = moon.primary.x - moon.x
        moon_radius_y = moon.primary.y - moon.y
        moon_radius_z = moon.primary.z - moon.z
        moon_primary_distance = math.sqrt(moon_radius_x**2 + moon_radius_y**2 + moon_radius_z**2)

        moon_hill_sphere_radius = moon_primary_distance * math.cbrt(moon.mass / (3*moon.primary.mass))

        if dist_squared < moon_hill_sphere_radius**2:
            return moon

    for planet in planets:

        if planet.primary is None:
            continue

        dx = planet.x - x
        dy = planet.y - y
        dz = planet.z - z

        dist_squared = dx**2 + dy**2 + dz**2

        planet_radius_x = planet.primary.x - planet.x
        planet_radius_y = planet.primary.y - planet.y
        planet_radius_z = planet.primary.z - planet.z
        planet_primary_distance = math.sqrt(planet_radius_x**2 + planet_radius_y**2 + planet_radius_z**2)

        planet_hill_sphere_radius = planet_primary_distance * math.cbrt(planet.mass / (3*planet.primary.mass))

        if dist_squared < planet_hill_sphere_radius**2:
            return planet

    if len(stars) == 1:
        return stars[0]

    confirmed_star_primaries = []
    most_influential_star = None
    greatest_accel = -1


    for star in stars:
        dx = star.x - x
        dy = star.y - y
        dz = star.z - z

        dist_squared = dx**2 + dy**2 + dz**2

        if dist_squared == 0:
            return star

        accel = star.mass / dist_squared
        if accel > greatest_accel:
            greatest_accel = accel
            most_influential_star = star


        if len(stars) == 2:
            other_star = stars[0] if stars[1] is star else stars[1]

            separation = calculate_distance(star, other_star)
            star_total_mass = star.mass + other_star.mass

            hill_radius = separation * math.cbrt(star.mass / (3 * star_total_mass))


            if dist_squared < hill_radius**2:
                confirmed_star_primaries.append(star)


    if len(confirmed_star_primaries) == 1:
        return confirmed_star_primaries[0]

    return most_influential_star







#Reset the entire system to where it was before.
def reset_system():
    global baseline_total_energy, max_energy_error, sim_time

    for body in bodies:
        body.reset_initial_state()

    baseline_total_energy = None
    max_energy_error = 0

    sim_time = 0

# Can the simulation continue rewinding? (Is the time metric above 0?)
def can_rewind_system():
    if sim_time <= 0:
        return False
    return True

def update_camera_target_list():
    bodies_and_com_list.clear()
    bodies_and_com_list.append("Origin")

    if sum(body.mass for body in bodies) > 0:
        bodies_and_com_list.append("CoM")

    bodies_and_com_list.extend(bodies)

def load_system(system_num):
    global baseline_total_energy, max_energy_error, sim_time, body_selected, camera_target, camera_target_is_com, camera_target_is_origin

    baseline_total_energy = None
    max_energy_error = 0

    sim_time = 0

    # Solar system planet masses
    mercury_mass = 0.00000017
    venus_mass =  0.00000245
    mars_mass = 0.00000032
    jupiter_mass = 0.00095446
    saturn_mass = 0.00028564
    uranus_mass = 0.0000436568
    neptune_mass =  0.0000515034

    # Solar system planet distances
    mercury_radius = 0.39
    venus_radius = 0.72
    mars_radius = 1.52
    jupiter_radius = 5.20
    saturn_radius = 9.58
    uranus_radius = 19.19
    neptune_radius = 30.07

    #Moon to planet distances
    deimos_mars_radius = 0.0001568
    phobos_mars_radius = 0.0000627
    io_jupiter_radius = 0.002818890
    europa_jupiter_radius = 0.004484690
    ganymede_jupiter_radius = 0.007155182
    callisto_jupiter_radius = 0.012585072


    #Moon masses:
    deimos_mass = 0.000000000000000742
    phobos_mass = 0.00000000000000536

    io_mass = 0.00000004491845
    europa_mass = 0.00000002413916
    ganymede_mass = 0.00000007452463
    callisto_mass = 0.00000005410693


    if system_num == 1:
        # Load Earth/Moon/Sun system

        bodies.clear()
        stars.clear()
        planets.clear()
        moons.clear()

        Sun = OrbitingBody(
            "Sun", None, 0, 0, 0,
            0.0, 0.0, 0.0,
            1.0,
            (255, 220, 100), (255, 220, 100),
            25
        )

        Earth = create_circular_orbit("Earth", Sun, 1, earth_mass, (40, 157, 140), (40, 157, 140), 15)

        Moon = create_circular_orbit("Moon", Earth, moon_earth_distance, moon_mass, (220, 220, 220), (180, 180, 180), 6)

        assign_radius_scales()

        update_camera_target_list()

        body_selected = Earth
        camera_target = Sun

    if system_num == 2:
        # Load inner solar system, major moons included
        bodies.clear()
        stars.clear()
        planets.clear()
        moons.clear()

        Sun = OrbitingBody(
            "Sun", None, 0, 0, 0,
            0.0, 0.0, 0.0,
            1.0,
            (255, 220, 100), (255, 220, 100),
            25
        )

        # Planets

        Mercury = create_circular_orbit("Mercury", Sun, mercury_radius, mercury_mass, (183, 184, 185), (183, 184, 185), 10)
        Venus = create_circular_orbit("Venus", Sun, venus_radius, venus_mass, (255, 198, 73), (255, 198, 73), 13)
        Earth = create_circular_orbit("Earth", Sun, 1, earth_mass, (40, 157, 140), (40, 157, 140), 15)
        Mars = create_circular_orbit("Mars", Sun, mars_radius, mars_mass, (173, 98, 66), (173, 98, 66), 14)

        # Moons
        Moon = create_circular_orbit("Moon", Earth, moon_earth_distance, moon_mass, (220, 220, 220), (180, 180, 180), 6)

        assign_radius_scales()
        for body in bodies:
            print(f"{body.radius_scale}")

        update_camera_target_list()

        body_selected = Earth
        camera_target = Sun

    if system_num == 3:
        # Load entire solar system, major moons included
        bodies.clear()
        stars.clear()
        planets.clear()
        moons.clear()

        Sun = OrbitingBody(
            "Sun", None, 0, 0, 0,
            0.0, 0.0, 0.0,
            1.0,
            (255, 220, 100), (255, 220, 100),
            25
        )

        Mercury = create_circular_orbit("Mercury", Sun, mercury_radius, mercury_mass, (183, 184, 185), (183, 184, 185), 10)
        Venus = create_circular_orbit("Venus", Sun, venus_radius, venus_mass, (255, 198, 73), (255, 198, 73), 13)
        Earth = create_circular_orbit("Earth", Sun, 1, earth_mass, (40, 157, 140), (40, 157, 140), 15)
        Mars = create_circular_orbit("Mars", Sun, mars_radius, mars_mass, (173, 98, 66), (173, 98, 66), 14)
        Jupiter = create_circular_orbit("Jupiter", Sun, jupiter_radius, jupiter_mass, (227, 220, 203), (227, 220, 203), 22)
        Saturn = create_circular_orbit("Saturn", Sun, saturn_radius, saturn_mass, (234, 214, 184), (234, 214, 184), 1800)
        Uranus = create_circular_orbit("Uranus", Sun, uranus_radius, uranus_mass, (172, 229, 238), (172, 229, 238), 1500)
        Neptune = create_circular_orbit("Neptune", Sun, neptune_radius, neptune_mass, (124, 183, 187), (124, 183, 187), 1500)


        assign_radius_scales()

        update_camera_target_list()

        body_selected = Earth
        camera_target = Sun

    if system_num == 4:
        # Load binary star system
        bodies.clear()
        stars.clear()
        planets.clear()
        moons.clear()

        Star_1 = OrbitingBody("Star 1", None, 0.0, 0.0, 0.0,
                              0.0, 3.0, 0.0,
                              1.0, (255, 220, 100),
                              (255, 0, 0), 25)


        Star_2 = OrbitingBody("Star 2", None, 1.0, 0.0, 0.0,
                              0.0, -3.0, 0.0,
                              1.0, (255, 220, 100),
                              (200, 200, 100), 25)


        assign_radius_scales()

        update_camera_target_list()

        body_selected = Star_2
        camera_target_is_origin = False
        camera_target_is_com = True

    if system_num == 5:
        bodies.clear()
        stars.clear()
        planets.clear()
        moons.clear()

        update_camera_target_list()

        body_selected = None
        camera_target = None

        camera_target_is_com = False
        camera_target_is_origin = True




def compute_acceleration_at(body, x, y, z, positions):
    ax = ay = az = 0

    for other in bodies:
        if other is body:
            continue

        ox, oy, oz = positions[other]

        dx = ox - x
        dy = oy - y
        dz = oz - z

        r2 = dx**2 + dy**2 + dz**2

        if r2 < 1e-12:
            continue
        r = math.sqrt(r2)

        a_mag = G * other.mass / r2

        ax += a_mag * dx / r
        ay += a_mag * dy / r
        az += a_mag * dz / r

    return ax, ay, az


def verlet_nbody_step(bodies, sub_dt):
    global sim_time

    old_positions = {
        body: (body.x, body.y, body.z)
        for body in bodies
    }

    old_accels = {}
    for body in bodies:
        old_accels[body] = compute_acceleration_at(body, body.x, body.y, body.z, old_positions)

    new_positions = {}
    for body in bodies:
        ax, ay, az = old_accels[body]

        x_new = body.x + body.vx * sub_dt + 0.5 * ax * sub_dt ** 2
        y_new = body.y + body.vy * sub_dt + 0.5 * ay * sub_dt ** 2
        z_new = body.z + body.vz * sub_dt + 0.5 * az * sub_dt ** 2

        new_positions[body] = x_new, y_new, z_new

    new_accels = {}
    for body in bodies:
        x_new, y_new, z_new = new_positions[body]
        new_accels[body] = compute_acceleration_at(body, x_new, y_new, z_new, new_positions)

    for body in bodies:
        ax_old, ay_old, az_old = old_accels[body]
        ax_new, ay_new, az_new = new_accels[body]

        x_new, y_new, z_new = new_positions[body]

        vx_new = body.vx + 0.5 * (ax_old + ax_new) * sub_dt
        vy_new = body.vy + 0.5 * (ay_old + ay_new) * sub_dt
        vz_new = body.vz + 0.5 * (az_old + az_new) * sub_dt

        body.ax = ax_new
        body.ay = ay_new
        body.az = az_new

        body.set_state(x_new, y_new, z_new, vx_new, vy_new, vz_new)

        if sub_dt > 0:
            body.update_trail()
        elif sub_dt < 0:
            body.rewind_trail()

    sim_time += sub_dt


def euler_nbody_step(bodies, sub_dt):
    global sim_time

    old_positions = {
        body: (body.x, body.y, body.z)
        for body in bodies
    }

    old_accels = {}
    for body in bodies:
        old_accels[body] = compute_acceleration_at(body, body.x, body.y, body.z, old_positions)

    for body in bodies:
        ax, ay, az = old_accels[body]

        vx_new = body.vx + ax * sub_dt
        vy_new = body.vy + ay * sub_dt
        vz_new = body.vz + az * sub_dt

        x_new = body.x + body.vx * sub_dt
        y_new = body.y + body.vy * sub_dt
        z_new = body.z + body.vz * sub_dt

        body.ax = ax
        body.ay = ay
        body.az = az

        body.set_state(x_new, y_new, z_new, vx_new, vy_new, vz_new)

        if sub_dt > 0:
            body.update_trail()
        elif sub_dt < 0:
            body.rewind_trail()

    sim_time += sub_dt





background = pygame.image.load("nasa_starscape.png").convert_alpha()
background = pygame.transform.scale(background, (width, height))

use_verlet = True
paused = False
cinematic_mode = False
vectors_toggled = True

placing_body = False
dragging_velocity_vector = False
DRAGGED_VELOCITY_FACTOR = 50.0
settings_under_review = False
coplanar_body = None
placed_body_primary = None
placed_radial_x = placed_radial_y = placed_radial_z = 0
placed_body_dist_to_primary = None
show_distance_box = True



running = True
while running:
    clock.tick(60)


    substeps = substeps_slider.value
    dt = dt_slider.value


    if not placing_body:
        dragging_velocity_vector = False
        settings_under_review = False
    else:
        paused = True

    if dragging_velocity_vector:
        settings_under_review = False

    if settings_under_review:
        dragging_velocity_vector = False


    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

        typing_in_input = (
                name_input_box.is_focused
                or mass_input_box.is_focused
                or distance_input_box.is_focused
        )


        if event.type == pygame.KEYDOWN and not typing_in_input:

            if event.key == pygame.K_9:
                use_verlet = not use_verlet
                reset_system()
                system_label = f"{system_text} | {'Verlet' if use_verlet else 'Euler'}"

            if event.key == pygame.K_c:
                cinematic_mode = not cinematic_mode

            if event.key == pygame.K_v:
                vectors_toggled = not vectors_toggled

            if event.key == pygame.K_p:
                paused = not paused

            if event.key == pygame.K_m:
                show_stats = not show_stats

            if event.key == pygame.K_b:
                placing_body = not placing_body

            if event.key == pygame.K_j:
                R = 2.5

            if event.key == pygame.K_1:
                if not placing_body:
                    load_system(1)
            if event.key == pygame.K_2:
                if not placing_body:
                    load_system(2)
            if event.key == pygame.K_3:
                if not placing_body:
                    load_system(3)
            if event.key == pygame.K_4:
                if not placing_body:
                    load_system(4)
            if event.key == pygame.K_5:
                if not placing_body:
                    load_system(5)


        # Placing body
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if placing_body:
                vectors_toggled = False
                handle_body_placement_click()
            else:
                dragging_velocity_vector = False

        if settings_under_review:
            settings_output = more_settings_menu.handle_event(event)
            update_placed_body_distance()

            if settings_output is not None:
                kind, submenu, selected_index = settings_output

                if kind == "submenu" and submenu is coplanar_body_menu:
                    coplanar_body = coplanar_bodies[selected_index]

                    if snap_camera_to_orbital_plane(coplanar_body):
                        settings_under_review = False
                        more_settings_menu.menu_open = False
                        more_settings_menu.active_submenu = None
                        coplanar_body_menu.menu_open = False
                        dragging_velocity_vector = False
                        placing_body = True

            if done_button.handle_event(event):
                finish_body_placement()


        for slider in sliders:
            if slider in menu_sliders:
                continue
            if not slider.is_hidden:
                slider.handle_event(event)


        handle_body_click_event(event)

        keybinds_menu.handle_event(event)
        body_info_menu.handle_event(event)







        body_menu_output = body_camera_menu.handle_event(event)



        if body_menu_output is not None:
            # If the function returns True, body mode is selected
            if body_menu_output is True:
                body_mode_selected = True
            # If the function returns False, camera mode is selected
            elif body_menu_output is False:
                body_mode_selected = False
            else:

                # Use the returned index to correspond to a body. If the index is 0, the CoM has been selected as a camera target.
                if body_mode_selected:
                    body_selected = bodies[body_menu_output]
                    camera_target = bodies[body_menu_output]
                    camera_target_is_com = False
                    camera_target_is_origin = False

                else:
                    selected_target = bodies_and_com_list[body_menu_output]

                    if selected_target == "Origin":
                        camera_target_is_origin = True
                        camera_target_is_com = False

                    elif selected_target == "CoM":
                        camera_target_is_com = True
                        camera_target_is_origin = False

                    else:
                        camera_target = selected_target
                        camera_target_is_com = False
                        camera_target_is_origin = False

    # Camera controls
    keys = pygame.key.get_pressed()

    if not name_input_box.is_focused:
        if keys[pygame.K_a]:
            theta -= 0.02
        if keys[pygame.K_d]:
            theta += 0.02
        if keys[pygame.K_w]:
            phi += 0.02
        if keys[pygame.K_s]:
            phi -= 0.02
        if keys[pygame.K_q]:
            R += zoom_strength_slider.value / 20
        if keys[pygame.K_e]:
            R -= zoom_strength_slider.value / 20

    sub_dt = dt / substeps
    step_fn = verlet_nbody_step if use_verlet else euler_nbody_step

    if paused:
        direction = 0

        if keys[pygame.K_RIGHT]:
            direction = 1
        if keys[pygame.K_LEFT]:
            direction = -1

        if direction != 0 and body_selected is not None:
            accel_mag = math.sqrt(body_selected.ax**2+body_selected.ay**2+body_selected.az**2)

            target_time_advance = 0.005 * paused_simulating_speed_slider.value
            number_timesteps = (20 + 200 * accel_mag) * paused_simulating_speed_slider.value
            number_timesteps = max(10, min(500, number_timesteps))
            adaptive_sub_dt = direction * target_time_advance / number_timesteps

            for i in range(int(number_timesteps)):
                if adaptive_sub_dt < 0 and not can_rewind_system():
                    break

                step_fn(bodies, adaptive_sub_dt)



    phi = max(-1.55, min(1.55, phi))
    R = max(0.1, R)

    # Recalibrate Accel/Velocity vectors scaling
    clamp_va_vectors()


    if camera_target_is_origin:
        target_x, target_y, target_z = 0, 0, 0

    elif camera_target_is_com:
        target_x, target_y, target_z = calculate_center_of_mass(bodies)

    else:
        target_x = camera_target.x
        target_y = camera_target.y
        target_z = camera_target.z

    # Camera position on hemisphere/sphere
    cam_x = target_x + R * math.cos(phi) * math.cos(theta)
    cam_y = target_y + R * math.sin(phi)
    cam_z = target_z + R * math.cos(phi) * math.sin(theta)

    # Camera forward: camera -> center
    cam_fx = target_x - cam_x
    cam_fy = target_y - cam_y
    cam_fz = target_z - cam_z

    cam_f_mag = math.sqrt(cam_fx * cam_fx + cam_fy * cam_fy + cam_fz * cam_fz)

    cam_fx /= cam_f_mag
    cam_fy /= cam_f_mag
    cam_fz /= cam_f_mag

    # Camera right = forward x world_up
    cam_rx = cam_fz * world_up_y - cam_fy * world_up_z
    cam_ry = cam_fx * world_up_z - cam_fz * world_up_x
    cam_rz = cam_fy * world_up_x - cam_fx * world_up_y

    cam_r_mag = math.sqrt(cam_rx * cam_rx + cam_ry * cam_ry + cam_rz * cam_rz)

    cam_rx /= cam_r_mag
    cam_ry /= cam_r_mag
    cam_rz /= cam_r_mag

    # Camera up = right x forward
    cam_up_x = cam_ry * cam_fz - cam_rz * cam_fy
    cam_up_y = cam_rz * cam_fx - cam_rx * cam_fz
    cam_up_z = cam_rx * cam_fy - cam_ry * cam_fx



    # Physics
    for _ in range(substeps):
        if not paused:
            step_fn(bodies, sub_dt)

    if body_selected is not None:
        ax = body_selected.ax
        ay = body_selected.ay
        az = body_selected.az

        # Acceleration display scaling
        a_mag = math.sqrt(ax * ax + ay * ay + az * az)

        if a_mag != 0:
            if a_mag <= a0:
                display_length = acceleration_scale * a_mag
            else:
                display_length = acceleration_scale * a0 * math.sqrt(a_mag / a0)

            ax_display = display_length * (ax / a_mag)
            ay_display = display_length * (ay / a_mag)
            az_display = display_length * (az / a_mag)
        else:
            ax_display = ay_display = az_display = 0.0

    # N-body Energy
    kinetic_energy = 0.0
    for body in bodies:
        body_speed2 = body.vx**2+body.vy**2+body.vz**2
        kinetic_energy += 0.5*body.mass*body_speed2

    # Format KE
    kinetic_energy *= energy_to_joules



    potential_energy = 0.0
    for i in range(len(bodies)):
        for j in range(i+1, len(bodies)):
            body1 = bodies[i]
            body2 = bodies[j]

            radius = calculate_distance(body1, body2)

            if radius != 0:
                potential_energy += (-G*body2.mass*body1.mass)/radius

    potential_energy *= energy_to_joules

    total_energy = kinetic_energy + potential_energy



    if previous_total_energy is None:
        previous_total_energy = total_energy

    if total_energy != 0:
        relative_energy_change = abs(total_energy - previous_total_energy) / abs(total_energy)
    else:
        relative_energy_change = None

    if baseline_total_energy is None and relative_energy_change is not None and relative_energy_change < energy_spike_threshold:
        baseline_total_energy = total_energy

    previous_total_energy = total_energy


    energy_baseline_ready = baseline_total_energy is not None

    if energy_baseline_ready:
        total_energy_error = baseline_total_energy - total_energy
        relative_error_percent = 100 * (total_energy_error / baseline_total_energy)
        max_energy_error = max(max_energy_error, abs(total_energy_error))
    else:
        total_energy_error = None

    # Draw
    screen.fill((0, 0, 0))

    # Background
    screen.blit(background, (0,0))

    dark_overlay = pygame.Surface((width, height))
    dark_overlay.fill((0, 0, 0))
    dark_overlay.set_alpha(195)

    screen.blit(background, (0, 0))
    screen.blit(dark_overlay, (0, 0))

    if body_selected is not None:
        body_point = body_selected.draw()


    if placing_body:
        draw_body_placement()
    else:
        dragging_velocity_vector = False





    # Slider hidden conditions
    if paused:
        paused_simulating_speed_slider.is_hidden = False
    else:
        paused_simulating_speed_slider.is_hidden = True

    if not cinematic_mode:
        # Sliders

        for slider in sliders:
            if slider in menu_sliders:
                continue
            slider.draw()

        # Labels


        label_surface = font.render(system_label, True, (255, 255, 255))
        # Use later for togglable comparison # distance_surface = font.render(f"Distance: {radius:.2f}", True, (255, 255, 255))

        ke_surface = font.render(f"Kinetic Energy: {kinetic_energy:.4e} Joules", True, (255, 255, 255))
        pe_surface = font.render(f"Potential Energy: {potential_energy:.4e} Joules", True, (255, 255, 255))
        te_surface = font.render(f"Total Energy: {total_energy:.4e} Joules", True, (255, 255, 255))

        if total_energy_error is None:
            eer_surface = font.render(f"Baseline not trusted", True, (255, 255, 255))
            relative_er_surface = font.render(f"Relative Error: --", True, (255, 255, 255))
            maxeer_surface = font.render(f"Max Energy Error: --", True, (255, 255, 255))
        else:
            eer_surface = font.render(f"Energy Error: {total_energy_error:.5e} Joules", True, (255, 255, 255))
            relative_er_surface = font.render(f"Relative Error: {relative_error_percent:.3e}%", True, (255, 255, 255))
            maxeer_surface = font.render(f"Max Energy Error: {max_energy_error:.5e} Joules", True, (255, 255, 255))



        screen.blit(label_surface, (20, 20))

        if show_stats:

            screen.blit(ke_surface, (20, 80))
            screen.blit(pe_surface, (20, 110))
            screen.blit(te_surface, (20, 140))
            screen.blit(eer_surface, (20, 200))
            screen.blit(relative_er_surface, (20, 230))
            screen.blit(maxeer_surface, (20, 260))



        # Draw menus
        camera_target_label = camera_target
        if camera_target_is_com:
            camera_target_label = "Center of Mass"
        elif camera_target_is_origin:
            camera_target_label = "Origin"

        body_menu_title = f"Body: {body_selected}, Camera: {camera_target_label}"
        if body_camera_menu.mode_1_pressed:
            body_camera_menu.draw_menu(body_menu_title, bodies)
        else:
            body_camera_menu.draw_menu(body_menu_title, bodies_and_com_list)

        keybinds_menu_title = "Keybinds"
        keybinds_menu.draw_menu(keybinds_menu_title, keybinds)

        if body_selected is not None:
            body_information = acquire_body_info(body_selected)
        else:
            body_information = ["No body selected"]

        body_info_menu.set_list(body_information)
        body_info_menu.draw_menu(
            "Body Info",
            body_info_menu.list_objects
        )


    # Trail and body
    for body in bodies:
        body.draw_trail()

    # Acceleration / Velocity vectors

    # Velocity vector
    if vectors_toggled and body_selected is not None:
        v_end = project_point(
            body_selected.x + body_selected.vx * velocity_scale,
            body_selected.y + body_selected.vy * velocity_scale,
            body_selected.z + body_selected.vz * velocity_scale,
            cam_x, cam_y, cam_z,
            cam_fx, cam_fy, cam_fz,
            cam_rx, cam_ry, cam_rz,
            cam_up_x, cam_up_y, cam_up_z,
            focal_length, width, height
        )

        if body_point is not None and v_end is not None:
            pygame.draw.line(
                screen,
                (0, 255, 0),
                (body_point[0], body_point[1]),
                (v_end[0], v_end[1]),
                3
            )

        # Acceleration vector
        a_end = project_point(
            body_selected.x + ax_display,
            body_selected.y + ay_display,
            body_selected.z + az_display,
            cam_x, cam_y, cam_z,
            cam_fx, cam_fy, cam_fz,
            cam_rx, cam_ry, cam_rz,
            cam_up_x, cam_up_y, cam_up_z,
            focal_length, width, height
        )

        if body_point is not None and a_end is not None:
            pygame.draw.line(
                screen,
                (255, 255, 0),
                (body_point[0], body_point[1]),
                (a_end[0], a_end[1]),
                3
            )

    sct_surface = font.render("Selecting camera target - CLICK A BODY", True, (255, 255, 255))
    if selecting_camera_target:
        screen.blit(sct_surface, (200, 550))

    body_warning_surface = font.render("WARNING: Simulating 15+ bodies is not recommended", True, (255, 0, 0))
    if len(bodies) >= 15:
        screen.blit(body_warning_surface, (40, 40))


    # Draw bodies
    if body_selected is not None:
        body_selected.screen_point = body_point

    if not all_bodies_in_view():
        not_all_in_view_warning = font.render(
            "Zoom out to see other bodies",
            True,
            (255, 0, 0)
        )

        screen.blit(
            not_all_in_view_warning,
            (20, 50)
        )

    if len(bodies) == 0:
        place_a_body_warning = font.render(
            "Press B to place a body...",
            True,
            (255, 0, 0)
        )

        screen.blit(
            place_a_body_warning,
            (width / 3, 50)
        )

    for body in bodies:
        if body == body_selected:
            continue
        body.screen_point = body.draw()

    pygame.display.flip()

pygame.quit()
