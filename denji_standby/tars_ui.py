"""
TARS UI Engine - Geometric cube-inspired interface for Denji
Renders technical, clean geometric layouts in curses
"""

import curses
from typing import Tuple, Callable, Any

class TARSUIRenderer:
    """Renders TARS-inspired geometric UI segments"""
    
    def __init__(self, color_pair_mapping: dict):
        """
        color_pair_mapping: dict of {name: curses_pair} for colors
        e.g., {P_HIGH: 3, P_DIM: 1, P_CYAN: 8, P_PINK: 9, ...}
        """
        self.colors = color_pair_mapping
        
    def draw_segment_box(self, win, y: int, x: int, h: int, w: int, 
                         label: str = "", data: str = "", 
                         color=None, border_thick=False):
        """Draw a TARS-style geometric segment with optional border"""
        if color is None:
            color = self.colors.get('P_DIM', 0)
        
        # Corner characters
        if border_thick:
            tl, tr, bl, br = "╔", "╗", "╚", "╝"
            h_line, v_line = "═", "║"
        else:
            tl, tr, bl, br = "┌", "┐", "└", "┘"
            h_line, v_line = "─", "│"
        
        try:
            # Draw corners
            if y < win.getmaxyx()[0] and x < win.getmaxyx()[1]:
                curses.init_pair(99, color, -1)
                win.addch(y, x, ord(tl), curses.color_pair(99))
                if x + w - 1 < win.getmaxyx()[1]:
                    win.addch(y, x + w - 1, ord(tr), curses.color_pair(99))
                if y + h - 1 < win.getmaxyx()[0]:
                    win.addch(y + h - 1, x, ord(bl), curses.color_pair(99))
                    if x + w - 1 < win.getmaxyx()[1]:
                        win.addch(y + h - 1, x + w - 1, ord(br), curses.color_pair(99))
                
                # Draw horizontal lines
                for i in range(1, w - 1):
                    if x + i < win.getmaxyx()[1]:
                        win.addch(y, x + i, ord(h_line), curses.color_pair(99))
                        if y + h - 1 < win.getmaxyx()[0]:
                            win.addch(y + h - 1, x + i, ord(h_line), curses.color_pair(99))
                
                # Draw vertical lines
                for i in range(1, h - 1):
                    if y + i < win.getmaxyx()[0]:
                        win.addch(y + i, x, ord(v_line), curses.color_pair(99))
                        if x + w - 1 < win.getmaxyx()[1]:
                            win.addch(y + i, x + w - 1, ord(v_line), curses.color_pair(99))
        except curses.error:
            pass
        
        # Draw label if provided
        if label and y + 1 < win.getmaxyx()[0] and x + 2 < win.getmaxyx()[1]:
            label_str = f" {label} "
            try:
                win.addstr(y + 1, x + 2, label_str[:w-4], curses.color_pair(color))
            except curses.error:
                pass
        
        # Draw data if provided
        if data:
            lines = data.split('\n')
            for i, line in enumerate(lines):
                data_y = y + 2 + i
                if data_y + 1 < win.getmaxyx()[0] - 1 and x + 2 < win.getmaxyx()[1]:
                    try:
                        win.addstr(data_y, x + 2, line[:w-4], curses.color_pair(color))
                    except curses.error:
                        pass

    def draw_percentage_bar(self, win, y: int, x: int, width: int, 
                           percent: float, label: str = "", 
                           bar_color=None, label_color=None, show_percent=True):
        """Draw a TARS-style percentage bar with label"""
        if bar_color is None:
            bar_color = self.colors.get('P_CYAN', 0)
        if label_color is None:
            label_color = self.colors.get('P_DIM', 0)
        
        percent = max(0, min(100, percent))
        filled = int((width - 2) * percent / 100)
        
        bar_str = "█" * filled + "░" * (width - 2 - filled)
        bar_display = f"[{bar_str}]"
        
        try:
            if label:
                label_str = f"{label}: "
                win.addstr(y, x, label_str, curses.color_pair(label_color))
                x += len(label_str)
            
            for i, ch in enumerate(bar_display):
                if x + i < win.getmaxyx()[1]:
                    color = bar_color if ch == "█" else label_color
                    win.addch(y, x + i, ord(ch), curses.color_pair(color))
            
            if show_percent:
                pct_str = f" {percent:.0f}%"
                if x + len(bar_display) + len(pct_str) < win.getmaxyx()[1]:
                    win.addstr(y, x + len(bar_display), pct_str, 
                             curses.color_pair(self.colors.get('P_HI', 0)))
        except curses.error:
            pass

    def draw_cube_frame(self, win, y: int, x: int, size: int = 4,
                       color=None, filled=False):
        """Draw a cube perspective frame (TARS-inspired geometry)"""
        if color is None:
            color = self.colors.get('P_CYAN', 0)
        
        # Simple isometric-style cube
        frames = [
            # Front face
            [" " * size, "┌" + "─" * (size - 2) + "┐", 
             *["│" + " " * (size - 2) + "│" for _ in range(size - 2)],
             "└" + "─" * (size - 2) + "┘"],
            # Tilted perspective
            [" " * (size + 1), "/" + " " * (size - 1),
             *["/" + " " * (size - 1) for _ in range(size - 2)],
             "/" + "─" * (size - 1)]
        ]
        
        try:
            for i, line in enumerate(frames[0]):
                if y + i < win.getmaxyx()[0] and x + len(line) <= win.getmaxyx()[1]:
                    win.addstr(y + i, x, line, curses.color_pair(color))
        except curses.error:
            pass

    def draw_status_indicator(self, win, y: int, x: int, status: str,
                             active_color=None, inactive_color=None):
        """Draw a colored status indicator (● active, ○ inactive)"""
        if active_color is None:
            active_color = self.colors.get('P_GREEN', 0)
        if inactive_color is None:
            inactive_color = self.colors.get('P_DIM', 0)
        
        is_active = status.lower() in ["ready", "active", "online", "enabled", "true"]
        indicator = "●" if is_active else "○"
        color = active_color if is_active else inactive_color
        
        try:
            win.addch(y, x, ord(indicator), curses.color_pair(color))
            label_str = f" {status}"
            if x + len(label_str) < win.getmaxyx()[1]:
                win.addstr(y, x + 1, label_str, curses.color_pair(color))
        except curses.error:
            pass

    def draw_spectrum_wave(self, win, y: int, x: int, width: int,
                          spectrum_data: list, color=None):
        """Draw an audio spectrum as wave (TARS data visualization)"""
        if color is None:
            color = self.colors.get('P_CYAN', 0)
        
        if not spectrum_data:
            return
        
        # Normalize spectrum to width
        normalized = []
        step = max(1, len(spectrum_data) // width)
        for i in range(0, len(spectrum_data), max(1, step)):
            normalized.append(spectrum_data[min(i, len(spectrum_data) - 1)])
        
        normalized = normalized[:width]
        
        wave_chars = "▁▂▃▄▅▆▇█"
        try:
            for i, val in enumerate(normalized):
                if x + i < win.getmaxyx()[1]:
                    char_idx = min(7, int(val * 8 / 100))
                    win.addch(y, x + i, ord(wave_chars[char_idx]), 
                            curses.color_pair(color))
        except curses.error:
            pass

    def draw_data_panel(self, win, y: int, x: int, h: int, w: int,
                       title: str, data_lines: list, color=None, 
                       highlight_idx: int = -1):
        """Draw a TARS data panel with scrollable lines"""
        if color is None:
            color = self.colors.get('P_CYAN', 0)
        
        self.draw_segment_box(win, y, x, h, w, label=title, color=color)
        
        # Draw data lines
        for i, line in enumerate(data_lines[:h-3]):
            data_y = y + 2 + i
            if data_y >= win.getmaxyx()[0] - 1:
                break
            try:
                line_display = line[:w-3] if len(line) > w - 3 else line
                line_color = self.colors.get('P_HI', 0) if i == highlight_idx else color
                win.addstr(data_y, x + 2, line_display, curses.color_pair(line_color))
            except curses.error:
                pass
