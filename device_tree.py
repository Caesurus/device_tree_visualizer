#!/usr/bin/env python3
import argparse
import contextlib
import json
import sys

import dash
import dash_core_components as dcc
import dash_cytoscape as cyto
import dash_html_components as html
import fdt
import requests
from dash.dependencies import Input, Output
from dash.dependencies import State

app = dash.Dash(__name__)


def load_json(st):
    if 'http' in st:
        return requests.get(st).json()
    else:
        with open(st, 'rb') as f:
            x = json.load(f)
        return x


@app.callback(Output('cytoscape-update-layout', 'layout'),
              [Input('dropdown-update-layout', 'value')])
def update_layout(layout):
    modified_layout = {
        'name': layout,
        'idealEdgeLength': 400,
        'nodeOverlap': 20,
        'refresh': 20,
        'fit': True,
        'padding': 30,
        'randomize': False,
        'componentSpacing': 100,
        'nodeRepulsion': 2000000,
        'edgeElasticity': 500,
        'nestingFactor': 5,
        'gravity': 15,
        'numIter': 1000,
        'initialTemp': 2000,
        'coolingFactor': 0.95,
        'minTemp': 1.0,
        'animate': True
    }
    return modified_layout


@app.callback(Output('tap-node-data-json-output', 'children'),
              [Input('cytoscape-update-layout', 'tapNodeData')])
def displayTapNodeData(data):
    return json.dumps(data, indent=2)


@app.callback(Output('tap-edge-data-json-output', 'children'),
              [Input('cytoscape-update-layout', 'tapEdgeData')])
def displayTapEdgeData(data):
    return json.dumps(data, indent=2)


@app.callback(Output('selected-node-data-json-output', 'children'),
              [Input('cytoscape-update-layout', 'selectedNodeData')],
              [State('cytoscape-update-layout', 'elements'),
               State('cytoscape-update-layout', 'selectedNodeData')]
              )
def displaySelectedNodeData(data_list, elements, selected_data):
    edges = []
    edges.append(data_list)
    if data_list:
        for data in data_list:
            selected_node_name = data['name']

            for ele in elements:
                if 'data' in ele:
                    if 'source' in ele['data'] and 'target' in ele['data']:
                        src = ele['data']['source']
                        trg = ele['data']['target']
                        if selected_node_name == src or selected_node_name == trg:
                            edges.append(ele)

    return json.dumps(edges, indent=2)


@app.callback(Output('selected-edge-data-json-output', 'children'),
              [Input('cytoscape-update-layout', 'selectedEdgeData')])
def displaySelectedEdgeData(data):
    return json.dumps(data, indent=2)


server = app.server
# Load Data
stylesheet = load_json('./cy-style_local.json')

styles = {
    'container': {
        'position': 'fixed',
        'display': 'flex',
        'flex-direction': 'column',
        'height': '100%',
        'width': '100%'
    },
    'cy-container': {
        'flex': '1',
        'position': 'relative'
    },
    'cytoscape_org': {
        'position': 'absolute',
        'width': '100%',
        'height': '100%',
        'z-index': 999
    },
    'cytoscape': {
        'height': '95vh',
        'width': '100%'
    },
    'sidebar': {
        'position': 'fixed',
        'top': 0,
        'left': 0,
        'bottom': 0,
        'width': '20%',
        'padding': '20px 10px',
        'background-color': '#f8f9fa'
    },
    'json-output': {
        'overflow-y': 'scroll',
        'height': 'calc(50% - 25px)',
        'border': 'thin lightgrey solid'
    },
    'tab': {'height': 'calc(98vh - 400px)'}
}


def convert_node_to_elements(root_node):
    compatible = ''
    model = ''
    for prop in root_node.props:
        if prop.name == 'compatible':
            compatible += prop.value
        elif prop.name == 'model':
            model += prop.value

    name = root_node.name
    if model:
        name = f'{name} - {model}'
    elif compatible:
        name = f'{name} ({compatible})'

    properties = {}
    for p in root_node.props:
        try:
            properties[p.name] = p.value
            if p.name == 'reg':
                with contextlib.suppress(ValueError):
                    properties['reg_hex'] = hex(p.value)
        except AttributeError:
            pass

    if len(root_node.nodes):
        score = 1024
    else:
        score = 0

    elements = [{'data': {'id': root_node.name, 'name': name, 'compatible': compatible, 'properties': properties,
                          'size': len(root_node.nodes), 'score': score}, 'group': 'nodes'}]

    if root_node.nodes:
        for n in root_node.nodes:
            elements.append({'data': {'source': root_node.name, 'target': n.name, 'id': f'{root_node.name}->{n.name}'}})
            # recursively call to add all ids
            sub_elements = convert_node_to_elements(n)
            elements.extend(sub_elements)
    return elements


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Generate network type graph for device tree')
    parser.add_argument('-f', '--file', required=True, help='pass file to analyze')

    args = parser.parse_args()

    if '.dtb' in args.file:
        with open(args.file, 'rb') as f:
            data = f.read()
        dt2 = fdt.parse_dtb(data)
    elif '.dts' in args.file:
        with open(args.file, 'r') as f:
            data = f.read()
        dt2 = fdt.parse_dts(data)
    else:
        print('ERROR, file must be a .dts or .dtb file')
        sys.exit(1)

    elements = []
    nodes = convert_node_to_elements(dt2.root)
    elements.extend(nodes)

    # print(dt2)
    # pprint(elements)
    cyto.load_extra_layouts()
    app.layout = html.Div([
        html.Div(className='eight columns', children=[
            cyto.Cytoscape(
                id='cytoscape-update-layout',
                elements=elements,
                stylesheet=stylesheet,
                style=styles['cytoscape'],
                layout={
                    'name': 'cose',
                    'idealEdgeLength': 400,
                    'nodeOverlap': 20,
                    'refresh': 20,
                    'fit': True,
                    'padding': 30,
                    'randomize': False,
                    'componentSpacing': 100,
                    'nodeRepulsion': 4000000,
                    'edgeElasticity': 500,
                    'nestingFactor': 5,
                    'gravity': 8,
                    'numIter': 1000,
                    'initialTemp': 200,
                    'coolingFactor': 0.95,
                    'minTemp': 1.0
                },
                responsive=True
            )
        ]),
        html.Div(className='four columns', style=styles['sidebar'], children=[
            dcc.Dropdown(
                id='dropdown-update-layout',
                value='klay',
                clearable=False,
                options=[
                    {'label': name.capitalize(), 'value': name}
                    for name in
                    ['klay', 'breadthfirst', 'concentric', 'grid', 'cose', 'circle', 'cose-bilkent',
                     'cola', 'euler', 'spread', 'dagre', 'random', ]
                ]
            ),
            dcc.Tabs(id='tabs', children=[
                # dcc.Tab(label='Actions', children=[
                #    html.Button("Remove Selected Node", id='remove-button'),
                #    html.Button("Remove Unconnected Nodes", id='remove-unconnected-button'),
                # ]),
                dcc.Tab(label='Tap Data', children=[
                    html.Div(style=styles['tab'], children=[
                        html.P('Node Data JSON:'),
                        html.Pre(
                            id='tap-node-data-json-output',
                            style=styles['json-output']
                        ),
                        html.P('Edge Data JSON:'),
                        html.Pre(
                            id='tap-edge-data-json-output',
                            style=styles['json-output']
                        )
                    ])
                ]),

                dcc.Tab(label='Selected Data', children=[
                    html.Div(style=styles['tab'], children=[
                        html.P('Node Data JSON:'),
                        html.Pre(
                            id='selected-node-data-json-output',
                            style=styles['json-output']
                        ),
                        html.P('Edge Data JSON:'),
                        html.Pre(
                            id='selected-edge-data-json-output',
                            style=styles['json-output']
                        )
                    ])
                ]),
            ]),
        ]),
    ])

    app.run_server(debug=True)
