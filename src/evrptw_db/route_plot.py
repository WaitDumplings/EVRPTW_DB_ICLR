"""Standalone SVG route schematics using the instance's terminal coordinates.

This module does not infer road geometry or certify physical feasibility. The
caller must supply the independent verifier's result through ``verified``.
"""
from __future__ import annotations

import math
from numbers import Integral, Real
import os
from pathlib import Path
import tempfile
from typing import TYPE_CHECKING
import xml.etree.ElementTree as ET

if TYPE_CHECKING:
    from evrptw_core.schema import EVRPTWInstance

_SVG = 'http://www.w3.org/2000/svg'
ET.register_namespace('', _SVG)
_PALETTE = ('#0072B2', '#D55E00', '#009E73', '#CC79A7', '#7A5195',
            '#B8860B', '#008B8B', '#C43B65', '#4A6F28', '#5D5DCE')


def _element(parent, tag, text=None, **attributes):
    node = ET.SubElement(parent, f'{{{_SVG}}}{tag}', {
        key.rstrip('_').replace('_', '-'): str(value) for key, value in attributes.items()})
    if text is not None:
        node.text = text
    return node


def _text(value, name):
    if not isinstance(value, str):
        raise ValueError(f'{name} must be text')
    if any(not (c in '\t\n\r' or '\x20' <= c <= '\ud7ff'
                or '\ue000' <= c <= '\ufffd' or '\U00010000' <= c <= '\U0010ffff')
           for c in value):
        raise ValueError(f'{name} contains an invalid XML character')
    return value


def _point(value, name):
    try:
        values = list(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f'{name} must contain two finite coordinates') from exc
    if len(values) != 2 or any(isinstance(v, bool) or not isinstance(v, Real) for v in values):
        raise ValueError(f'{name} must contain two finite numeric coordinates')
    point = tuple(float(v) for v in values)
    if not all(math.isfinite(v) for v in point):
        raise ValueError(f'{name} contains non-finite coordinates')
    return point


def _coordinate_rows(value, name):
    try:
        rows = list(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f'{name} coordinates are missing or malformed') from exc
    return [_point(row, f'{name}[{i}]') for i, row in enumerate(rows)]


def _validated(instance, routes, verified):
    if type(verified) is not bool:
        raise ValueError('verified must be a boolean from the independent verifier')
    try:
        depot = _point(instance.depot, 'depot')
        customers = _coordinate_rows(instance.customers, 'customers')
        stations = _coordinate_rows(instance.charging_stations, 'charging_stations')
    except AttributeError as exc:
        raise ValueError('Instance terminal coordinates are missing') from exc
    if not customers:
        raise ValueError('Cannot draw a successful route diagram without customers')
    points = [depot, *customers, *stations]
    if not isinstance(routes, list) or not routes:
        raise ValueError('routes must be a nonempty list of nonempty routes')
    normalized = []
    for ordinal, route in enumerate(routes, 1):
        if not isinstance(route, list) or len(route) < 2:
            raise ValueError(f'Route {ordinal} must contain at least two terminal indices')
        if any(isinstance(node, bool) or not isinstance(node, Integral) for node in route):
            raise ValueError(f'Route {ordinal} contains a non-integer terminal index')
        clean = [int(node) for node in route]
        if any(node < 0 or node >= len(points) for node in clean):
            raise ValueError(f'Route {ordinal} has an out-of-range terminal index')
        if not any(1 <= node <= len(customers) for node in clean):
            raise ValueError(f'Route {ordinal} has no customer visit')
        if verified and (len(clean) < 3 or clean[0] != 0 or clean[-1] != 0 or 0 in clean[1:-1]):
            raise ValueError(f'Verified route {ordinal} must start/end at depot with no interior depot')
        normalized.append(clean)
    if verified:
        visited = [node for route in normalized for node in route if 1 <= node <= len(customers)]
        if sorted(visited) != list(range(1, len(customers) + 1)):
            raise ValueError('Verified routes must visit every customer exactly once')
    return points, len(customers), len(stations), normalized


def write_route_svg(
    instance: 'EVRPTWInstance',
    routes: list[list[int]],
    output_path: str | Path,
    *,
    title: str = 'EVRP-TW routes',
    verified: bool = True,
    cost_usd: float | None = None,
    annotate: bool = False,
) -> Path:
    """Validate and atomically write a browser-readable SVG; return its path.

    Terminal order is depot, all customers, then all charging stations. Original
    x/y coordinates are used with uniform scaling and an upward y axis. CLE views
    store longitude/latitude; no CRS is guessed for arbitrary instances.

    ``verified=True`` additionally requires closed single-trip routes and exact
    customer coverage. It is the caller's physical-verifier result, not a claim
    that this plotting function checks battery, time windows or capacity.
    ``verified=False`` can display nonempty partial/invalid routes, labeled so.
    Invalid input is rejected before touching an existing output file. Station
    labels are always shown; ``annotate`` also enables customer terminal IDs.
    """
    points, customer_count, station_count, routes = _validated(instance, routes, verified)
    title = _text(title, 'title')
    instance_id = _text(str(instance.instance_id), 'instance_id')
    if type(annotate) is not bool:
        raise ValueError('annotate must be a boolean')
    if cost_usd is not None:
        if isinstance(cost_usd, bool) or not isinstance(cost_usd, Real):
            raise ValueError('cost_usd must be a finite nonnegative number or None')
        cost_usd = float(cost_usd)
        if not math.isfinite(cost_usd) or cost_usd < 0:
            raise ValueError('cost_usd must be a finite nonnegative number or None')

    width, plot_left, plot_top, plot_width, plot_height = 1200, 56, 148, 840, 570
    legend_x, legend_y = 930, 174
    height = max(850, legend_y + 28 * len(routes) + 150)
    xs, ys = zip(*points)
    min_x, max_x, min_y, max_y = min(xs), max(xs), min(ys), max(ys)
    span_x, span_y = max_x - min_x, max_y - min_y
    if not math.isfinite(span_x) or not math.isfinite(span_y):
        raise ValueError('Coordinate extent is not finite')
    # A zero-width/height extent is valid (collinear or coincident terminals).
    scale = min((plot_width - 36) / span_x if span_x else math.inf,
                (plot_height - 36) / span_y if span_y else math.inf)
    if not math.isfinite(scale):
        scale = 1.0
    offset_x = plot_left + (plot_width - span_x * scale) / 2
    offset_y = plot_top + (plot_height - span_y * scale) / 2
    screen = [(offset_x + (x - min_x) * scale,
               offset_y + (max_y - y) * scale) for x, y in points]
    if any(not math.isfinite(value) for point in screen for value in point):
        raise ValueError('Coordinates cannot be mapped to a finite diagram')

    root = ET.Element(f'{{{_SVG}}}svg', {
        'viewBox': f'0 0 {width} {height}', 'width': str(width), 'height': str(height),
        'role': 'img', 'aria-labelledby': 'plot-title plot-description',
        'data-instance-id': instance_id, 'data-verified': str(verified).lower()})
    _element(root, 'title', title, id='plot-title')
    _element(root, 'desc',
             'Directed terminal-to-terminal route schematic, not actual road geometry. '
             'Hover a vehicle legend entry for the complete terminal visit order. '
             'Physical verification status is supplied by the caller.', id='plot-description')
    _element(root, 'style', '''text { font-family: system-ui, sans-serif; fill: #263343; }
.route-line { fill: none; stroke-width: 1.7; opacity: 0.78; }
.vehicle:hover .route-line { stroke-width: 3.5; opacity: 1; }
.terminal { stroke: #fff; stroke-width: 1.2; }
.caption { font-size: 13px; fill: #586575; }
.customer-label { font-size: 10px; paint-order: stroke; stroke: #fff; stroke-width: 2.5px; }
''')
    _element(root, 'rect', x=0, y=0, width=width, height=height, fill='#ffffff')
    _element(root, 'text', title, x=36, y=37, font_size=24, font_weight=650)
    _element(root, 'text', f'Instance: {instance_id}', x=36, y=64, font_size=14)
    status = 'PASS (reported by caller)' if verified else 'NOT VERIFIED / INVALID OR PARTIAL'
    cost_text = f' | Cost: USD {cost_usd:,.2f}' if cost_usd is not None else ''
    _element(root, 'text',
             f'{len(routes)} vehicle routes | {customer_count} customers | {station_count} stations{cost_text}',
             x=36, y=87, font_size=14)
    _element(root, 'text', f'Verification: {status}', x=36, y=110, font_size=14,
             font_weight=650, style=f'fill: {"#14643b" if verified else "#b42318"}')
    _element(root, 'rect', x=plot_left, y=plot_top, width=plot_width, height=plot_height,
             rx=8, fill='#f7f9fc', stroke='#d9e1ea')
    definitions = _element(root, 'defs')
    coincident_edges = 0
    for ordinal, route in enumerate(routes, 1):
        color = (_PALETTE[ordinal - 1] if ordinal <= len(_PALETTE)
                 else f'hsl({((ordinal - 1) * 137.508) % 360:.2f},65%,38%)')
        marker_id = f'direction-{ordinal}'
        marker = _element(definitions, 'marker', id=marker_id, markerWidth=6, markerHeight=6,
                          refX=5, refY=3, orient='auto', markerUnits='strokeWidth')
        _element(marker, 'path', d='M 0 0 L 6 3 L 0 6 Z', fill=color)
        sequence = ' → '.join(str(node) for node in route)
        vehicle = _element(root, 'g', id=f'vehicle-{ordinal}', class_='vehicle',
                           data_vehicle=ordinal, data_sequence=' '.join(map(str, route)))
        _element(vehicle, 'title', f'Vehicle {ordinal}: {sequence}')
        for step, (start, end) in enumerate(zip(route, route[1:]), 1):
            x1, y1 = screen[start]; x2, y2 = screen[end]
            if x1 == x2 and y1 == y2:
                coincident_edges += 1
                d = (f'M {x1:.4f} {y1:.4f} C {x1+24:.4f} {y1-26:.4f} '
                     f'{x1-24:.4f} {y1-26:.4f} {x1:.4f} {y1-18:.4f} '
                     f'C {x1+14:.4f} {y1-10:.4f} {x1+10:.4f} {y1-3:.4f} {x1:.4f} {y1:.4f}')
            else:
                middle_x, middle_y = x1 + .64 * (x2-x1), y1 + .64 * (y2-y1)
                d = f'M {x1:.4f} {y1:.4f} L {middle_x:.4f} {middle_y:.4f} L {x2:.4f} {y2:.4f}'
            edge = _element(vehicle, 'path', d=d, stroke=color, marker_mid=f'url(#{marker_id})',
                            data_from=start, data_to=end, data_step=step)
            edge.set('class', 'route-line')
            _element(edge, 'title', f'Vehicle {ordinal}, leg {step}: terminal {start} → {end}')
        # The legend is part of the vehicle group, so hovering it highlights its route.
        legend = _element(vehicle, 'g', data_role='vehicle-legend')
        _element(legend, 'title', f'Vehicle {ordinal}: {sequence}')
        y = legend_y + 28 * (ordinal - 1)
        _element(legend, 'line', x1=legend_x, y1=y, x2=legend_x+29, y2=y,
                 stroke=color, stroke_width=3, marker_end=f'url(#{marker_id})')
        count = sum(1 <= node <= customer_count for node in route)
        visits = 'visit' if count == 1 else 'visits'
        _element(legend, 'text', f'Vehicle {ordinal} · {count} {visits}', x=legend_x+40, y=y+5, font_size=13)
    _element(root, 'text', 'Vehicles · hover for visit order', x=legend_x, y=148, font_size=14, font_weight=650)

    node_group = _element(root, 'g', id='terminals')
    radius = max(1.8, min(4.2, 36 / math.sqrt(customer_count)))
    station_labels = []
    for index, ((x, y), (raw_x, raw_y)) in enumerate(zip(screen, points)):
        kind = 'depot' if index == 0 else ('customer' if index <= customer_count else 'station')
        node = _element(node_group, 'g', id=f'terminal-{index}', data_terminal=index,
                        data_kind=kind, data_x=repr(raw_x), data_y=repr(raw_y))
        _element(node, 'title', f'{kind.capitalize()} {index}; input x={raw_x:.9g}, y={raw_y:.9g}')
        if kind == 'depot':
            symbol = _element(node, 'rect', x=x-7, y=y-7, width=14, height=14,
                              rx=2, fill='#152437', stroke='#ffffff', stroke_width=2)
            _element(node, 'text', 'D0', x=x+10, y=y-8, font_size=12, font_weight=700)
        elif kind == 'station':
            symbol = _element(node, 'polygon', points=f'{x:.4f},{y-6:.4f} {x+6:.4f},{y:.4f} {x:.4f},{y+6:.4f} {x-6:.4f},{y:.4f}',
                              fill='#f1b736', stroke='#473710', stroke_width=1.2)
            # Nearby stations can share coordinates. Move only their text, never
            # terminal symbols or route endpoints, and connect displaced labels.
            label = f'S{index}'
            label_width = len(label) * 7
            candidates = [(x+8, y-6), (x+8, y+16),
                          (x-label_width-8, y-6), (x-label_width-8, y+16)]
            candidates += [(x+8, y+16+row*15) for row in range(1, len(station_labels)+2)]
            def penalty(position):
                lx, ly = position
                box = (lx-2, ly-11, lx+label_width+2, ly+3)
                overlaps = sum(box[0] < old[2] and box[2] > old[0]
                               and box[1] < old[3] and box[3] > old[1]
                               for old in station_labels)
                outside = not (plot_left <= box[0] and box[2] <= plot_left+plot_width
                               and plot_top <= box[1] and box[3] <= plot_top+plot_height)
                return overlaps * 2 + outside
            label_x, label_y = min(candidates, key=penalty)
            station_labels.append((label_x-2, label_y-11, label_x+label_width+2, label_y+3))
            if (label_x, label_y) != candidates[0]:
                _element(node, 'line', x1=x, y1=y, x2=label_x, y2=label_y-4,
                         stroke='#85713f', stroke_width=.6)
            _element(node, 'text', label, x=label_x, y=label_y, font_size=10)
        else:
            symbol = _element(node, 'circle', cx=x, cy=y, r=radius, fill='#415770')
            symbol.set('class', 'terminal')
            if annotate:
                label = _element(node, 'text', str(index), x=x+5, y=y-5)
                label.set('class', 'customer-label')

    footer_y = plot_top + plot_height + 32
    _element(root, 'rect', x=57, y=footer_y-10, width=12, height=12, rx=2, fill='#152437')
    _element(root, 'text', 'Depot (0)', x=79, y=footer_y, font_size=13)
    _element(root, 'circle', cx=201, cy=footer_y-4, r=4, fill='#415770')
    _element(root, 'text', 'Customer', x=214, y=footer_y, font_size=13)
    _element(root, 'polygon', points=f'329,{footer_y-11} 335,{footer_y-5} 329,{footer_y+1} 323,{footer_y-5}', fill='#f1b736', stroke='#473710')
    _element(root, 'text', 'Charging station', x=344, y=footer_y, font_size=13)
    for line, text in enumerate((
        'Terminal-to-terminal schematic — not actual road geometry.',
        'Coordinates are input x/y (longitude/latitude for CLE views); equal axis scale, y increases upward.',
        'Arrows show travel direction. Hover a vehicle legend entry for its full terminal visit order.',
    )):
        label = _element(root, 'text', text, x=56, y=footer_y+28+line*21)
        label.set('class', 'caption')
    if coincident_edges:
        label = _element(root, 'text', 'Curved loops mark coincident terminal coordinates, not road shapes.',
                         x=56, y=footer_y+91)
        label.set('class', 'caption')

    path = Path(output_path)
    content = ET.tostring(root, encoding='unicode', xml_declaration=False)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = None
    try:
        with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=path.parent,
                                         prefix=f'.{path.name}.', suffix='.tmp', delete=False) as stream:
            temporary = Path(stream.name)
            stream.write('<?xml version="1.0" encoding="UTF-8"?>\n' + content + '\n')
        os.replace(temporary, path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return path
