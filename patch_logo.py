#!/usr/bin/env python3
"""Patch script to add system OS logo to neofetch animations."""

with open('main.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find the line with "if NFS.animation_mode == "starfield":"
for i, line in enumerate(lines):
    if 'if NFS.animation_mode == "starfield":' in line and 'draw_starfield_logo' in lines[i+1]:
        # Insert system logo option before starfield
        indent = len(line) - len(line.lstrip())
        new_lines = [
            ' ' * indent + 'if NFS.animation_mode == "system":\n',
            ' ' * (indent + 4) + 'logo_h = draw_system_logo(win, AY, AX)\n',
            ' ' * indent + 'elif NFS.animation_mode == "starfield":\n',
        ]
        # Replace the original if with elif
        lines[i] = new_lines[2]
        # Insert the new lines before
        lines[i:i] = new_lines[:-1]
        break

with open('main.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("✓ Patched: Added system OS logo to animation modes")
