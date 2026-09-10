#!/usr/bin/env python3
"""Install a built desktop app, launcher, icon and man page under a local prefix."""
import argparse
import os
from pathlib import Path
import shlex
import shutil
import subprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--prefix', type=Path, default=Path.home() / '.local')
parser.add_argument('--model', type=Path, help='existing local GGUF; never downloaded or copied')
args = parser.parse_args()
repo = Path(__file__).resolve().parents[2]
prefix = args.prefix.expanduser().resolve()
model = (args.model or repo / (repo / 'terminal/resources/default-model.txt').read_text().strip()).expanduser().resolve()
binary = repo / 'target/debug/caiman-terminal'
if not binary.is_file():
    parser.error('Build first: cargo build --offline --features desktop,inference')
renderer = shutil.which('rsvg-convert')
if not renderer:
    parser.error('rsvg-convert is required to install taskbar icon sizes (librsvg)')
if any(c in str(prefix) + str(model) for c in '\n\r\0'):
    parser.error('installation paths must not contain control characters')

def put(relative, source=None, text=None, mode=0o644):
    target = prefix / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    if source:
        # Replace atomically so a currently running version keeps its executable.
        temp = target.with_name(target.name + '.new')
        shutil.copyfile(source, temp)
        temp.chmod(mode)
        os.replace(temp, target)
    else:
        target.write_text(text)
        target.chmod(mode)
    print(target)

put('lib/caiman-terminal/caiman-terminal', source=binary, mode=0o755)
launcher = prefix / 'bin/caiman-terminal'
put('bin/caiman-terminal', text='#!/bin/sh\nexport CAYMAN_DEFAULT_MODEL=' + shlex.quote(str(model)) + '\nexec ' + shlex.quote(str(prefix / 'lib/caiman-terminal/caiman-terminal')) + ' "$@"\n', mode=0o755)
# Existing scripts and cached launchers continue through the canonical launcher.
put('bin/cayman-terminal', text='#!/bin/sh\nexec ' + shlex.quote(str(launcher)) + ' "$@"\n', mode=0o755)
put('share/man/man1/cayman-terminal.1', text='.so man1/caiman-terminal.1\n')
put('share/icons/hicolor/scalable/apps/io.cayman.Terminal.svg', source=repo / 'terminal/resources/icons/scalable/apps/io.cayman.Terminal.svg')
# Supply raster sizes as well as SVG for desktop panels and icon loaders.
for size in (16, 24, 32, 48, 64, 128, 256):
    target = prefix / f'share/icons/hicolor/{size}x{size}/apps/io.cayman.Terminal.png'
    target.parent.mkdir(parents=True, exist_ok=True)
    temp = target.with_name(target.name + '.new')
    subprocess.run([renderer, '-w', str(size), '-h', str(size),
                    str(repo / 'terminal/resources/icons/scalable/apps/io.cayman.Terminal.svg'),
                    '-o', str(temp)], check=True)
    temp.chmod(0o644)
    os.replace(temp, target)
    print(target)
put('share/man/man1/caiman-terminal.1', source=repo / 'terminal/resources/man/caiman-terminal.1')
# Desktop Exec has its own quoting and percent-field-code rules, not shell quoting.
quoted = str(launcher).replace('%', '%%')
for ch in ['\\', '"', '`', '$']:
    quoted = quoted.replace(ch, '\\' + ch)
desktop = (repo / 'terminal/packaging/io.cayman.Terminal.desktop').read_text().replace('Exec=caiman-terminal', 'Exec="' + quoted + '"')
# An explicit icon path also works before a running panel refreshes its theme cache.
icon = str(prefix / 'share/icons/hicolor/256x256/apps/io.cayman.Terminal.png')
icon = icon.replace('\\', '\\\\').replace('\t', '\\t').replace(' ', '\\s')
desktop = desktop.replace('Icon=io.cayman.Terminal', 'Icon=' + icon)
put('share/applications/io.cayman.Terminal.desktop', text=desktop)
for name in ['LICENSE-Gogh', 'LICENSE-MIT', 'README.md']:
    put('share/doc/caiman-terminal/themes/' + name, source=repo / 'terminal/resources/themes' / name)
if shutil.which('update-desktop-database'):
    subprocess.run(['update-desktop-database', str(prefix / 'share/applications')], check=True)
if shutil.which('gtk-update-icon-cache'):
    subprocess.run(['gtk-update-icon-cache', '--force', '--ignore-theme-index',
                    str(prefix / 'share/icons/hicolor')], check=True)
if prefix == (Path.home() / '.local').resolve() and shutil.which('kbuildsycoca6'):
    subprocess.run(['kbuildsycoca6', '--noincremental'], check=True)
print('Launch: ' + str(launcher))
print('Manual: man -l ' + str(prefix / 'share/man/man1/caiman-terminal.1'))
