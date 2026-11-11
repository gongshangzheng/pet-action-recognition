#!/usr/bin/env python3
"""Local, explicit SVG figure operations. Python 3.11+, no Python dependencies except export."""
import argparse
import copy
import importlib.util
import json
import math
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
import xml.etree.ElementTree as ET

SVG = 'http://www.w3.org/2000/svg'
XLINK = 'http://www.w3.org/1999/xlink'
ET.register_namespace('', SVG)
ET.register_namespace('xlink', XLINK)


def positive(value):
    number = float(value)
    if not math.isfinite(number) or number <= 0:
        raise ValueError('Dimensions and scales must be positive finite numbers')
    return number


def viewbox(root):
    values = [float(v) for v in re.split(r'[\s,]+', root.get('viewBox', '').strip()) if v]
    if len(values) != 4 or not all(math.isfinite(v) for v in values):
        raise ValueError('SVG requires a finite four-number viewBox')
    positive(values[2]); positive(values[3])
    return values


def load(path):
    data = Path(path).read_bytes()
    if len(data) > 10_000_000:
        raise ValueError('SVG exceeds 10 MB input limit')
    if re.search(br'<!\s*(DOCTYPE|ENTITY)', data, re.I):
        raise ValueError('DTD/entity declarations are not supported')
    root = ET.fromstring(data)
    if root.tag != f'{{{SVG}}}svg':
        raise ValueError('Expected an SVG namespace root')
    viewbox(root)
    ids = set()
    refs = []
    for node in root.iter():
        tag = node.tag.rsplit('}', 1)[-1]
        if tag in {'script', 'foreignObject', 'style', 'animate', 'animateTransform', 'set'}:
            raise ValueError(f'Unsupported element: {tag}; use static SVG with presentation attributes')
        ident = node.get('id')
        if ident:
            if ident in ids:
                raise ValueError(f'Duplicate SVG ID: {ident}')
            ids.add(ident)
        for key, value in node.attrib.items():
            local = key.rsplit('}', 1)[-1]
            if local.lower().startswith('on') or '@import' in value.lower():
                raise ValueError('Event handlers and CSS imports are not supported')
            if local == 'href':
                if value.startswith('#'):
                    refs.append(value[1:])
                elif not (tag == 'image' and re.match(r'^data:image/(png|jpeg);base64,', value)):
                    raise ValueError(f'External/unsupported reference on {tag}')
            for match in re.finditer(r'url\(\s*[\'"]?([^\)\'"\s]+)[\'"]?\s*\)', value):
                target = match.group(1)
                if not target.startswith('#'):
                    raise ValueError('Only local url(#id) references are supported')
                refs.append(target[1:])
    missing = set(refs) - ids
    if missing:
        raise ValueError(f'Unresolved SVG references: {sorted(missing)}')
    return root


def write_new(path, data):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open('xb') as stream:
        stream.write(data)


def run(command):
    if not shutil.which(command[0]):
        raise RuntimeError(f'Missing executable: {command[0]}')
    result = subprocess.run(command, capture_output=True, text=True, timeout=60)
    log = result.stdout + result.stderr
    if result.returncode or re.search(r'\bwarning\b', log, re.I):
        raise RuntimeError(f'Command failed or warned: {command[0]}\n{log}')
    return log


def formula(args):
    expression = Path(args.input).read_text().strip()
    if not expression:
        raise ValueError('Formula input is empty')
    positive(args.font_size)
    # Intentionally supports trusted math fragments only, not arbitrary TeX documents.
    document = ('\\documentclass{article}\n\\usepackage{amsmath,amssymb}\n'
                '\\pagestyle{empty}\n\\begin{document}\n'
                f'\\fontsize{{{args.font_size}}}{{{args.font_size * 1.2}}}\\selectfont\n'
                '\\(\\displaystyle ' + expression + '\\)\n\\end{document}\n')
    target = Path(args.output)
    source = target.with_suffix('.tex')
    if target.suffix != '.svg' or target.exists() or source.exists():
        raise ValueError('Use a new .svg output path with no existing .tex sibling')
    with tempfile.TemporaryDirectory(prefix='svg-formula-') as directory:
        work = Path(directory)
        tex = work / 'formula.tex'
        tex.write_text(document)
        log = run(['latex', '-no-shell-escape', '-interaction=nonstopmode', '-halt-on-error',
                   f'-output-directory={work}', str(tex)])
        if not re.search(r'Output written on .*?\(1 page,', log, re.S):
            raise ValueError('Formula must produce exactly one DVI page')
        # Pure math only: exclude PostScript specials explicitly, never require Ghostscript.
        log += run(['dvisvgm', '--no-fonts', '--no-specials=ps', '--exact-bbox', '--bbox=min',
                    f'--output={work / "formula.svg"}', str(work / 'formula.dvi')])
        root = load(work / 'formula.svg')
        desc = ET.Element(f'{{{SVG}}}desc')
        desc.text = 'LaTeX source: ' + expression
        root.insert(0, desc)
        write_new(source, document.encode())
        write_new(target, ET.tostring(root, encoding='utf-8', xml_declaration=True))
    print(json.dumps({'svg': str(target), 'tex': str(source), 'viewBox': viewbox(root)}))


def namespace_ids(root, prefix):
    mapping = {n.get('id'): prefix + n.get('id') for n in root.iter() if n.get('id')}
    for node in root.iter():
        if node.get('id'):
            node.set('id', mapping[node.get('id')])
        for key, value in list(node.attrib.items()):
            if key.rsplit('}', 1)[-1] == 'href' and value.startswith('#'):
                value = '#' + mapping[value[1:]]
            value = re.sub(r'url\(\s*[\'"]?#([^\)\'"\s]+)[\'"]?\s*\)',
                           lambda m: 'url(#' + mapping[m.group(1)] + ')', value)
            if key in {'aria-labelledby', 'aria-describedby'}:
                value = ' '.join(mapping.get(v, v) for v in value.split())
            node.set(key, value)


def compose(args):
    spec_path = Path(args.spec)
    spec = json.loads(spec_path.read_text())
    width, height = positive(spec['width']), positive(spec['height'])
    root = ET.Element(f'{{{SVG}}}svg', {'viewBox': f'0 0 {width} {height}',
                                     'width': str(width), 'height': str(height), 'role': 'img'})
    ET.SubElement(root, f'{{{SVG}}}title').text = spec['title']
    ET.SubElement(root, f'{{{SVG}}}desc').text = spec.get('description', '')
    ET.SubElement(root, f'{{{SVG}}}rect', {
        'width': str(width), 'height': str(height), 'fill': spec.get('background', 'white')})
    for i, item in enumerate(spec['items']):
        child = copy.deepcopy(load(spec_path.parent / item['file']))
        namespace_ids(child, f'part{i}_')
        box = viewbox(child)
        x, y = float(item.get('x', 0)), float(item.get('y', 0))
        w = positive(item.get('width', box[2]))
        h = positive(item.get('height', w * box[3] / box[2]))
        if not all(math.isfinite(v) for v in [x, y]) or x < 0 or y < 0 or x+w > width or y+h > height:
            raise ValueError(f'Item {i} lies outside canvas')
        child.attrib.update(x=str(x), y=str(y), width=str(w), height=str(h),
                            preserveAspectRatio='xMidYMid meet')
        root.append(child)
    write_new(args.output, ET.tostring(root, encoding='utf-8', xml_declaration=True))
    print(json.dumps({'svg': args.output, 'items': len(spec['items'])}))


def inspect(args):
    root = load(args.input)
    counts = {}
    for node in root.iter():
        tag = node.tag.rsplit('}', 1)[-1]
        counts[tag] = counts.get(tag, 0) + 1
    print(json.dumps({'viewBox': viewbox(root), 'elements': counts,
                      'note': 'Structural check only; inspect rendering and final-size text separately.'}))


def resolve_backend(requested):
    if requested != 'auto':
        return requested
    if importlib.util.find_spec('cairosvg') is not None:
        return 'cairosvg'
    if shutil.which('inkscape'):
        return 'inkscape'
    if shutil.which('rsvg-convert'):
        return 'rsvg'
    raise RuntimeError('no SVG export backend available: install cairosvg, inkscape, or rsvg-convert')


def export(args):
    load(args.input)
    suffix = Path(args.output).suffix.lower()
    if suffix not in {'.png', '.pdf'}:
        raise ValueError('Export output must be .png or .pdf')
    positive(args.dpi)
    if args.width_mm is not None:
        positive(args.width_mm)
    backend = resolve_backend(args.backend)
    root = load(args.input)
    box = viewbox(root)
    if backend == 'inkscape':
        if Path(args.output).exists():
            raise ValueError('Output already exists')
        with tempfile.TemporaryDirectory(prefix='svg-export-') as directory:
            temp = Path(directory) / ('export' + suffix)
            run(['inkscape', str(Path(args.input).resolve()), '--export-area-page',
                 f'--export-filename={temp}', f'--export-dpi={args.dpi}'])
            write_new(args.output, temp.read_bytes())
    elif backend == 'rsvg':
        if Path(args.output).exists():
            raise ValueError('Output already exists')
        with tempfile.TemporaryDirectory(prefix='svg-export-') as directory:
            temp = Path(directory) / ('export' + suffix)
            command = ['rsvg-convert', '-d', str(args.dpi), '-p', str(args.dpi)]
            if suffix == '.pdf':
                command += ['-f', 'pdf']
            if args.width_mm is not None:
                width = args.width_mm / 25.4 * args.dpi
                command += ['-w', f'{width:.4f}', '-h', f'{width * box[3] / box[2]:.4f}']
            command += ['-o', str(temp), str(Path(args.input).resolve())]
            run(command)
            write_new(args.output, temp.read_bytes())
    else:
        import cairosvg
        width = args.width_mm / 25.4 * args.dpi if args.width_mm else None
        kwargs = dict(bytestring=ET.tostring(root), dpi=args.dpi)
        if width:
            kwargs.update(output_width=width, output_height=width * box[3] / box[2])
        result = (cairosvg.svg2png if suffix == '.png' else cairosvg.svg2pdf)(**kwargs)
        write_new(args.output, result)
    print(json.dumps({'output': args.output, 'backend': backend}))


def doctor(args):
    probe = subprocess.run([sys.executable, '-c', 'import cairosvg'],
                           capture_output=True, text=True, timeout=20)
    print(json.dumps({
        'executables': {k: shutil.which(k) for k in ['latex', 'dvisvgm', 'inkscape', 'rsvg-convert']},
        'cairosvg_package_installed': importlib.util.find_spec('cairosvg') is not None,
        'cairosvg_backend_ready': probe.returncode == 0,
        'cairosvg_error': probe.stderr.strip() if probe.returncode else None,
    }))


def prepare(args):
    destination = Path(args.directory)
    destination.mkdir(parents=True, exist_ok=False)
    assets = Path(__file__).resolve().parent.parent / 'assets'
    for name in ['architecture.svg', 'equation.txt', 'composition.json']:
        shutil.copyfile(assets / name, destination / name)
    print(json.dumps({'directory': str(destination), 'next': 'formula, compose, inspect, export'}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('doctor'); p.set_defaults(func=doctor)
    p = sub.add_parser('prepare'); p.add_argument('directory'); p.set_defaults(func=prepare)
    p = sub.add_parser('formula'); p.add_argument('--input', required=True); p.add_argument('--output', required=True)
    p.add_argument('--font-size', type=float, default=10); p.set_defaults(func=formula)
    p = sub.add_parser('compose'); p.add_argument('--spec', required=True); p.add_argument('--output', required=True); p.set_defaults(func=compose)
    p = sub.add_parser('inspect'); p.add_argument('input'); p.set_defaults(func=inspect)
    p = sub.add_parser('export'); p.add_argument('input'); p.add_argument('--output', required=True)
    p.add_argument('--backend', choices=['auto', 'cairosvg', 'inkscape', 'rsvg'], default='auto')
    p.add_argument('--dpi', type=float, default=300); p.add_argument('--width-mm', type=float)
    p.set_defaults(func=export)
    args = parser.parse_args()
    if args.command == 'export' and args.backend == 'inkscape' and args.width_mm:
        parser.error('--width-mm is only supported by the cairosvg backend; set SVG physical dimensions for Inkscape')
    try:
        args.func(args)
    except (ValueError, OSError, RuntimeError, ET.ParseError, subprocess.TimeoutExpired, ImportError, KeyError) as error:
        print(f'Error: {error}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
