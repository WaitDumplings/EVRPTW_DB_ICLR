"""Route diagrams preserve terminal identity and reject misleading inputs."""
from dataclasses import replace
import math
import re
import xml.etree.ElementTree as ET

import numpy as np
import pytest

from evrptw_core.schema import EVRPTWInstance
from evrptw_db.route_plot import write_route_svg


SVG = {'s': 'http://www.w3.org/2000/svg'}
ROUTES = [[0, 1, 4, 2, 0], [0, 3, 0]]


@pytest.fixture
def instance():
    return EVRPTWInstance.from_dict({
        'instance_id': 'diagram-instance',
        'working_start_s': 0, 'working_end_s': 10000,
        'depot': [0, 0],
        'customers': [[1, 0], [2, 1], [0, 2]],
        'charging_stations': [[1, 2]],
        'distance_matrix_km': np.zeros((5, 5)),
        'demands_cm3': [1, 1, 1], 'package_counts': [1, 1, 1],
        'service_time_s': [1, 1, 1], 'tw_s': [[0, 9999]] * 3,
        'cs_time_to_depot_s': [10],
    })


def parse(path):
    return ET.parse(path).getroot()


def text_content(root):
    return ' '.join(root.itertext())


def test_terminal_identity_directions_and_hover_sequences(instance, tmp_path):
    path = tmp_path / 'nested' / 'routes.svg'
    assert write_route_svg(instance, ROUTES, path, cost_usd=1234.56) == path
    root = parse(path)
    assert root.tag == '{http://www.w3.org/2000/svg}svg'
    assert root.attrib['data-verified'] == 'true'
    assert 'Cost: USD 1,234.56' in text_content(root)
    assert 'not actual road geometry' in text_content(root)
    groups = root.findall("s:g[@class='vehicle']", SVG)
    assert [g.attrib['data-sequence'] for g in groups] == ['0 1 4 2 0', '0 3 0']
    colors = set()
    for group, route in zip(groups, ROUTES):
        edges = group.findall("s:path[@class='route-line']", SVG)
        assert [(int(p.attrib['data-from']), int(p.attrib['data-to'])) for p in edges] == list(zip(route, route[1:]))
        assert all(p.attrib['marker-mid'].startswith('url(#direction-') for p in edges)
        colors.update(p.attrib['stroke'] for p in edges)
        legend = group.find("s:g[@data-role='vehicle-legend']/s:title", SVG)
        assert legend is not None and ' → '.join(map(str, route)) in legend.text
    assert len(colors) == 2
    terminals = root.findall("s:g[@id='terminals']/s:g", SVG)
    assert [g.attrib['data-kind'] for g in terminals] == ['depot', 'customer', 'customer', 'customer', 'station']
    assert [(float(g.attrib['data-x']), float(g.attrib['data-y'])) for g in terminals] == [(0, 0), (1, 0), (2, 1), (0, 2), (1, 2)]
    assert terminals[0].find('s:rect', SVG) is not None
    assert terminals[1].find('s:circle', SVG) is not None
    assert terminals[4].find('s:polygon', SVG) is not None
    assert not root.findall('.//s:image', SVG)
    assert not root.findall('.//s:script', SVG)
    # Uniform coordinate scale and upward y preserve actual geometry.
    circles = [terminals[i].find('s:circle', SVG).attrib for i in (1, 2, 3)]
    x1, y1 = float(circles[0]['cx']), float(circles[0]['cy'])
    x2, y2 = float(circles[1]['cx']), float(circles[1]['cy'])
    x3, y3 = float(circles[2]['cx']), float(circles[2]['cy'])
    assert x2 - x1 == pytest.approx(y1 - y2)
    assert y1 > y2 > y3 and x1 - x3 == pytest.approx(x2 - x1)


def test_text_is_xml_escaped_and_customer_labels_are_optional(instance, tmp_path):
    instance = replace(instance, instance_id='<instance & "identifier">')
    title = 'AM <script>alert("x")</script> & routes'
    path = tmp_path / 'routes.svg'
    write_route_svg(instance, ROUTES, path, title=title, annotate=True)
    root = parse(path)
    assert root.find('s:title', SVG).text == title
    assert root.attrib['data-instance-id'] == instance.instance_id
    assert root.find('.//s:script', SVG) is None
    assert [t.text for t in root.findall(".//s:text[@class='customer-label']", SVG)] == ['1', '2', '3']
    write_route_svg(instance, ROUTES, path, annotate=False)
    assert parse(path).find(".//s:text[@class='customer-label']", SVG) is None
    assert not list(tmp_path.glob('*.tmp'))


@pytest.mark.parametrize('routes', [
    [], [[]], [[0]], [[0, 0]], [[0, 4, 0]],
    [[0, -1, 0]], [[0, 5, 0]], [[0, 1.0, 0]],
    [[0, '1', 0]], [[0, True, 0]], [[0, np.bool_(True), 0]],
    ((0, 1, 0),), [(0, 1, 0)],
])
def test_malformed_routes_cannot_replace_existing_output(instance, tmp_path, routes):
    path = tmp_path / 'routes.svg'
    path.write_text('previous valid diagram')
    with pytest.raises(ValueError):
        write_route_svg(instance, routes, path, verified=False)
    assert path.read_text() == 'previous valid diagram'


@pytest.mark.parametrize('routes', [
    [[0, 1, 2, 0]],                       # missing customer 3
    [[0, 1, 2, 3, 1, 0]],                 # repeated customer
    [[0, 1, 0, 2, 3, 0]],                 # interior depot
    [[1, 2, 3, 0]], [[0, 1, 2, 3]],      # open route
])
def test_verified_status_requires_structurally_complete_routes(instance, tmp_path, routes):
    path = tmp_path / 'routes.svg'
    with pytest.raises(ValueError):
        write_route_svg(instance, routes, path)
    assert not path.exists()


def test_partial_route_is_explicitly_unverified(instance, tmp_path):
    path = tmp_path / 'partial.svg'
    write_route_svg(instance, [[0, np.int64(1)]], path, verified=False)
    root = parse(path)
    assert root.attrib['data-verified'] == 'false'
    assert 'NOT VERIFIED / INVALID OR PARTIAL' in text_content(root)
    assert 'PASS' not in text_content(root)


@pytest.mark.parametrize('field,value', [
    ('depot', None), ('depot', [math.nan, 0]), ('depot', [0, math.inf]),
    ('depot', [0, 1, 2]), ('depot', ['0', '1']),
    ('customers', None), ('customers', [[0, 1], [1, math.nan], [2, 3]]),
    ('customers', [[0, 1], [1], [2, 3]]), ('customers', []),
    ('charging_stations', None), ('charging_stations', [[math.inf, 1]]),
])
def test_missing_or_nonfinite_coordinates_are_rejected(instance, tmp_path, field, value):
    path = tmp_path / 'must-not-be-created' / 'routes.svg'
    with pytest.raises(ValueError):
        write_route_svg(replace(instance, **{field: value}), ROUTES, path)
    assert not path.parent.exists()


@pytest.mark.parametrize('kwargs', [
    {'verified': 'true'}, {'verified': 1}, {'annotate': 'false'},
    {'cost_usd': math.nan}, {'cost_usd': math.inf}, {'cost_usd': -1},
    {'cost_usd': '12.34'}, {'cost_usd': True}, {'title': 'invalid\x00title'},
])
def test_invalid_labels_or_status_are_rejected(instance, tmp_path, kwargs):
    path = tmp_path / 'routes.svg'
    with pytest.raises(ValueError):
        write_route_svg(instance, ROUTES, path, **kwargs)
    assert not path.exists()


@pytest.mark.parametrize('points', [
    [[0, 0], [1, 0], [2, 0], [3, 0], [4, 0]],
    [[1, 1]] * 5,
])
def test_collinear_and_coincident_coordinates_have_finite_paths(instance, tmp_path, points):
    instance = replace(instance, depot=points[0], customers=points[1:4], charging_stations=points[4:])
    path = tmp_path / 'routes.svg'
    write_route_svg(instance, ROUTES, path)
    root = parse(path)
    routes = root.findall(".//s:path[@class='route-line']", SVG)
    for edge in routes:
        assert not re.search(r'(?i)nan|inf', edge.attrib['d'])
        assert len(re.findall(r'-?\d+\.\d+', edge.attrib['d'])) >= 6
    if points[0] == points[1]:
        assert 'Curved loops mark coincident terminal coordinates' in text_content(root)
        assert all('C ' in edge.attrib['d'] for edge in routes)


def test_without_charging_stations(instance, tmp_path):
    instance = replace(instance, charging_stations=np.empty((0, 2)))
    path = tmp_path / 'no-stations.svg'
    write_route_svg(instance, [[0, 1, 2, 3, 0]], path)
    assert '0 stations' in text_content(parse(path))


def test_coincident_station_labels_separate_without_moving_terminals(instance, tmp_path):
    instance = replace(instance, charging_stations=[[1, 2], [1, 2]])
    path = tmp_path / 'stations.svg'
    write_route_svg(instance, ROUTES, path)
    root = parse(path)
    stations = root.findall(".//s:g[@data-kind='station']", SVG)
    assert len(stations) == 2
    # Both station symbols keep exactly the same real projected coordinate.
    assert stations[0].find('s:polygon', SVG).attrib['points'] == stations[1].find('s:polygon', SVG).attrib['points']
    labels = [s.find('s:text', SVG).attrib for s in stations]
    assert (labels[0]['x'], labels[0]['y']) != (labels[1]['x'], labels[1]['y'])
    assert stations[1].find('s:line', SVG) is not None
