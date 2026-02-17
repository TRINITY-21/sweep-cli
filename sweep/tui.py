"""Sweep TUI — interactive terminal interface for selecting projects to clean."""

from __future__ import annotations

import curses
import shutil
from typing import List, Set

from sweep.scanner import Project, delete_artifacts, format_size


def run_tui(projects: List[Project]) -> int:
    """Launch the interactive TUI. Returns total bytes freed."""
    if not projects:
        print("No projects with cleanable artifacts found.")
        return 0
    return curses.wrapper(_tui_main, projects)


def _tui_main(stdscr: curses.window, projects: List[Project]) -> int:
    """Main curses TUI loop."""
    curses.curs_set(0)
    curses.use_default_colors()

    # Init color pairs
    curses.init_pair(1, curses.COLOR_GREEN, -1)    # safe / selected
    curses.init_pair(2, curses.COLOR_YELLOW, -1)   # recent
    curses.init_pair(3, curses.COLOR_RED, -1)       # git dirty
    curses.init_pair(4, curses.COLOR_CYAN, -1)      # header
    curses.init_pair(5, curses.COLOR_WHITE, curses.COLOR_BLUE)  # highlight bar
    curses.init_pair(6, curses.COLOR_MAGENTA, -1)   # accent

    cursor = 0
    scroll_offset = 0
    selected: Set[int] = set()
    sort_mode = "size"  # size, date, name

    while True:
        stdscr.clear()
        height, width = stdscr.getmaxyx()

        # Header
        total_size = sum(p.size for p in projects)
        selected_size = sum(projects[i].size for i in selected)
        header = f" SWEEP — {len(projects)} projects | {format_size(total_size)} reclaimable"
        if selected:
            header += f" | {len(selected)} selected ({format_size(selected_size)})"

        stdscr.attron(curses.color_pair(4) | curses.A_BOLD)
        stdscr.addnstr(0, 0, header.ljust(width), width - 1)
        stdscr.attroff(curses.color_pair(4) | curses.A_BOLD)

        # Column headers
        col_header = _format_row("  PROJECT", "TYPE", "SIZE", "LAST MODIFIED", "STATUS", width)
        stdscr.attron(curses.A_DIM)
        stdscr.addnstr(1, 0, col_header, width - 1)
        stdscr.addnstr(2, 0, "─" * (width - 1), width - 1)
        stdscr.attroff(curses.A_DIM)

        # Project list
        list_start = 3
        list_height = height - 6  # leave room for footer

        # Ensure cursor is visible
        if cursor < scroll_offset:
            scroll_offset = cursor
        if cursor >= scroll_offset + list_height:
            scroll_offset = cursor - list_height + 1

        for i in range(list_height):
            idx = scroll_offset + i
            if idx >= len(projects):
                break

            row_y = list_start + i
            if row_y >= height - 3:
                break

            project = projects[idx]
            is_selected = idx in selected
            is_cursor = idx == cursor

            # Checkbox
            check = "[x]" if is_selected else "[ ]"

            # Status
            if project.git_dirty:
                status = "dirty"
            elif project.git_dirty is False:
                status = "clean"
            else:
                status = ""

            row = _format_row(
                f" {check} {_truncate(project.name, 30)}",
                project.ecosystem,
                project.size_human,
                project.age_str,
                status,
                width,
            )

            # Color logic
            if is_cursor:
                attr = curses.color_pair(5) | curses.A_BOLD
            elif is_selected:
                attr = curses.color_pair(1) | curses.A_BOLD
            elif project.git_dirty:
                attr = curses.color_pair(3)
            else:
                attr = curses.A_NORMAL

            try:
                stdscr.addnstr(row_y, 0, row.ljust(width), width - 1, attr)
            except curses.error:
                pass

        # Separator
        sep_y = height - 3
        if sep_y > list_start:
            stdscr.attron(curses.A_DIM)
            try:
                stdscr.addnstr(sep_y, 0, "─" * (width - 1), width - 1)
            except curses.error:
                pass
            stdscr.attroff(curses.A_DIM)

        # Footer — controls
        footer1 = " [Space] select  [a] all  [Enter] delete  [q] quit"
        footer2 = f" [s] sort:size  [d] sort:date  [n] sort:name  |  sorting by: {sort_mode}"
        try:
            stdscr.attron(curses.color_pair(6))
            stdscr.addnstr(height - 2, 0, footer1.ljust(width), width - 1)
            stdscr.addnstr(height - 1, 0, footer2.ljust(width), width - 1)
            stdscr.attroff(curses.color_pair(6))
        except curses.error:
            pass

        stdscr.refresh()

        # Handle input
        key = stdscr.getch()

        if key == ord("q") or key == 27:  # q or ESC
            return 0

        elif key == curses.KEY_UP or key == ord("k"):
            cursor = max(0, cursor - 1)

        elif key == curses.KEY_DOWN or key == ord("j"):
            cursor = min(len(projects) - 1, cursor + 1)

        elif key == ord(" "):
            if cursor in selected:
                selected.discard(cursor)
            else:
                selected.add(cursor)
            cursor = min(len(projects) - 1, cursor + 1)

        elif key == ord("a"):
            if len(selected) == len(projects):
                selected.clear()
            else:
                selected = set(range(len(projects)))

        elif key == ord("s"):
            projects.sort(key=lambda p: p.size, reverse=True)
            sort_mode = "size"
            selected.clear()
            cursor = 0

        elif key == ord("d"):
            projects.sort(key=lambda p: p.last_modified or _MIN_DATE, reverse=False)
            sort_mode = "date"
            selected.clear()
            cursor = 0

        elif key == ord("n"):
            projects.sort(key=lambda p: p.name.lower())
            sort_mode = "name"
            selected.clear()
            cursor = 0

        elif key == curses.KEY_ENTER or key == 10 or key == 13:
            if not selected:
                continue
            # Confirm deletion
            freed = _confirm_and_delete(stdscr, projects, selected)
            return freed

        elif key == curses.KEY_PPAGE:  # Page Up
            cursor = max(0, cursor - list_height)

        elif key == curses.KEY_NPAGE:  # Page Down
            cursor = min(len(projects) - 1, cursor + list_height)

        elif key == curses.KEY_HOME:
            cursor = 0

        elif key == curses.KEY_END:
            cursor = len(projects) - 1


from datetime import datetime
_MIN_DATE = datetime(1970, 1, 1)


def _confirm_and_delete(
    stdscr: curses.window,
    projects: List[Project],
    selected: Set[int],
) -> int:
    """Show confirmation dialog and delete if confirmed."""
    height, width = stdscr.getmaxyx()
    selected_projects = [projects[i] for i in sorted(selected)]
    total = sum(p.size for p in selected_projects)

    stdscr.clear()
    stdscr.attron(curses.color_pair(3) | curses.A_BOLD)
    stdscr.addnstr(1, 2, f"Delete artifacts from {len(selected_projects)} projects?", width - 4)
    stdscr.attroff(curses.color_pair(3) | curses.A_BOLD)

    stdscr.addnstr(2, 2, f"This will free {format_size(total)}", width - 4)
    stdscr.addnstr(3, 2, "─" * (width - 4), width - 4)

    for i, project in enumerate(selected_projects[:height - 8]):
        dirty_tag = " [DIRTY]" if project.git_dirty else ""
        line = f"  {project.name} ({project.ecosystem}) — {project.size_human}{dirty_tag}"
        attr = curses.color_pair(3) if project.git_dirty else curses.A_NORMAL
        try:
            stdscr.addnstr(4 + i, 2, line, width - 4, attr)
        except curses.error:
            break

    prompt_y = min(4 + len(selected_projects), height - 3)
    stdscr.addnstr(prompt_y, 2, "─" * (width - 4), width - 4)
    stdscr.attron(curses.color_pair(6) | curses.A_BOLD)
    stdscr.addnstr(prompt_y + 1, 2, "[y] Yes, delete    [n] No, go back", width - 4)
    stdscr.attroff(curses.color_pair(6) | curses.A_BOLD)
    stdscr.refresh()

    while True:
        key = stdscr.getch()
        if key == ord("y") or key == ord("Y"):
            return _do_delete(stdscr, selected_projects)
        elif key == ord("n") or key == ord("N") or key == 27:
            return 0


def _do_delete(stdscr: curses.window, projects: List[Project]) -> int:
    """Execute deletion with progress."""
    height, width = stdscr.getmaxyx()
    total_freed = 0

    stdscr.clear()
    stdscr.attron(curses.color_pair(4) | curses.A_BOLD)
    stdscr.addnstr(1, 2, "Cleaning...", width - 4)
    stdscr.attroff(curses.color_pair(4) | curses.A_BOLD)

    for i, project in enumerate(projects):
        progress = f"  [{i + 1}/{len(projects)}] {project.name}..."
        try:
            stdscr.addnstr(3 + i, 2, progress.ljust(width - 4), width - 4)
        except curses.error:
            pass
        stdscr.refresh()

        freed = delete_artifacts(project)
        total_freed += freed

        done = f"  [{i + 1}/{len(projects)}] {project.name} — freed {format_size(freed)}"
        try:
            stdscr.addnstr(3 + i, 2, done.ljust(width - 4), width - 4, curses.color_pair(1))
        except curses.error:
            pass
        stdscr.refresh()

    # Summary
    summary_y = min(3 + len(projects) + 1, height - 3)
    stdscr.addnstr(summary_y, 2, "─" * (width - 4), width - 4)
    stdscr.attron(curses.color_pair(1) | curses.A_BOLD)
    stdscr.addnstr(summary_y + 1, 2, f"Done! Freed {format_size(total_freed)}", width - 4)
    stdscr.attroff(curses.color_pair(1) | curses.A_BOLD)
    stdscr.addnstr(summary_y + 2, 2, "Press any key to exit.", width - 4)
    stdscr.refresh()
    stdscr.getch()

    return total_freed


def _format_row(name: str, eco: str, size: str, date: str, status: str, width: int) -> str:
    """Format a table row with fixed column widths."""
    # Adaptive columns based on terminal width
    name_w = max(20, width - 50)
    return f"{name:<{name_w}} {eco:<12} {size:>10} {date:>14} {status:>8}"


def _truncate(text: str, max_len: int) -> str:
    """Truncate text with ellipsis."""
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"
