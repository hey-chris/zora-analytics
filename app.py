import requests
import json
import dash
import datetime

import pandas as pd
import flask_compress
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import pandas as pd

import plotly.express as px

from string import Template
API_URL = "https://api.zora.co/graphql"

projects = [
    {"label": "Art Blocks", "value": "0xa7d8d9ef8D8Ce8992Df33D8b8CF4Aebabd5bD270"},
    {"label": "Binkies", "value": "0xa06fda2caa66148603314451ba0f30c9c5d539e3"},
    {"label": "Zorbs", "value": "0xca21d4228cdcc68d4e23807e5e370c07577dd152"},
    {"label": "Doodles", "value": "0x8a90CAb2b38dba80c64b7734e58Ee1dB38B8992e"},
    {"label": "Nouns", "value": "0x4b10701Bfd7BFEdc47d50562b76b436fbB5BdB3B"},
    {"label": "SuperRare", "value": "0xb932a70A57673d89f4acfFBE830E8ed7f75Fb9e0"}
]

# ============================================================================
# FUNCTIONS
# ============================================================================


def get_data(url, query, collection_address):
    query = query.substitute(COLLECTION_ADDRESS=collection_address)
    r = requests.post(url, json={'query': query})
    data = json.loads(r.text)
    return data


def parse_sales_and_listings(sales_data, listings_data):
    # Sales
    sales_list = sales_data['data']['sales']['nodes']
    cleaned_sales = []
    for s in sales_list:
        price_usd = s['sale']['price']['usdcPrice']['decimal']
        price_eth = s['sale']['price']['chainTokenPrice']['decimal']
        ts = s['sale']['transactionInfo']['blockTimestamp']
        cleaned_sales.append([ts, price_eth, price_usd])
    df_sales = pd.DataFrame(cleaned_sales, columns=['ts', 'price_eth', 'price_usd'])
    df_sales['ts'] = pd.to_datetime(df_sales['ts'])
    df_sales['type'] = 'sale'
    
    # Listings
    listings_list = listings_data['data']['markets']['nodes']
    cleaned_listings = []
    for l in listings_list:
        price_usd = l['market']['price']['usdcPrice']['decimal']
        price_eth = l['market']['price']['chainTokenPrice']['decimal']
        ts = l['market']['transactionInfo']['blockTimestamp']
        cleaned_listings.append([ts, price_eth, price_usd])
    df_listings = pd.DataFrame(cleaned_listings, columns=['ts', 'price_eth', 'price_usd'])
    df_listings['ts'] = pd.to_datetime(df_listings['ts'])
    df_listings = df_listings[df_listings["ts"] > (datetime.datetime.now() - datetime.timedelta(days=1))]
    df_listings['type'] = 'listing'
    
    # Combined
    df = pd.concat([df_sales, df_listings]).reset_index()
    return df


def parse_volume_data(volume_data):
    cleaned_volume = [
      [
        "day",
        volume_data["data"]['aggregateStat']["daySalesVolume"]['chainTokenPrice'],
        volume_data["data"]['aggregateStat']["daySalesVolume"]['usdcPrice'],
        volume_data["data"]['aggregateStat']["daySalesVolume"]['totalCount']
      ],
      [
        "week",
        volume_data["data"]['aggregateStat']["weekSalesVolume"]['chainTokenPrice'],
        volume_data["data"]['aggregateStat']["weekSalesVolume"]['usdcPrice'],
        volume_data["data"]['aggregateStat']["weekSalesVolume"]['totalCount']        
      ]
    ]
    df = pd.DataFrame(cleaned_volume, columns=[
      'period', 'volume_eth', 'volume_usd', 'total_sales'
    ])
    return df


# ============================================================================
# QUERIES
# ============================================================================

query_project_sales = Template("""
{
  sales: sales(
      where: {
          collectionAddresses: "$COLLECTION_ADDRESS"
      },
      filter: {
          saleTypes: OPENSEA_SINGLE_SALE, 
          timeFilter: {lookbackHours: 24}
      },
      networks: {chain: MAINNET, network: ETHEREUM}, 
      sort: {sortKey: TIME, sortDirection: ASC},
      pagination: {
          limit: 500
      }
  ) {
    nodes {
      sale {
        price {
          usdcPrice {
            decimal
          }
          chainTokenPrice {
            decimal
          }
        }
        transactionInfo {
          blockTimestamp
        }
      }
    }
    pageInfo {
      hasNextPage
    }
  }
}
""")

query_project_listings = Template("""
{
  markets(
      where: {
          collectionAddresses: "$COLLECTION_ADDRESS"
      },
      filter: {
          marketFilters: [
              {marketType: V1_ASK, statuses: [ACTIVE]},
              {marketType: V3_ASK, statuses: [ACTIVE]}
          ]
      },
      sort: {sortKey: CHAIN_TOKEN_PRICE, sortDirection: ASC},
      pagination: {
          limit: 500
      }
    ) {
    nodes {
      market {
        collectionAddress
        tokenId
        status
        price {
          chainTokenPrice {
            decimal
          }
          usdcPrice {
            decimal
          }
        }
        transactionInfo {
          blockNumber
          blockTimestamp
          logIndex
          transactionHash
        }
        marketType
      }
      token {
        tokenId
        collectionAddress
        image {
          mediaEncoding {
            ... on ImageEncodingTypes {
              thumbnail
            }
          }
          url
        }
      }
    }
    pageInfo {
      hasNextPage
    }
  }
}
""")

query_project_volume = Template("""
{
  aggregateStat {
    daySalesVolume: salesVolume(where: {
      collectionAddresses: "$COLLECTION_ADDRESS"}, timeFilter: {lookbackHours: 24}, networks: {chain: MAINNET, network: ETHEREUM}) {
      chainTokenPrice
      totalCount
      usdcPrice
    },
    weekSalesVolume: salesVolume(where: {collectionAddresses: "$COLLECTION_ADDRESS"}, timeFilter: {lookbackHours: 168}, networks: {chain: MAINNET, network: ETHEREUM}) {
      chainTokenPrice
      totalCount
      usdcPrice
    }
  }
}
"""
)

# ============================================================================
# GET THE DATA
# ============================================================================

volume_data = get_data(API_URL, query_project_volume, projects[0]["value"])
df_v = parse_volume_data(volume_data)

sales_data = get_data(API_URL, query_project_sales, projects[0]["value"])
listings_data = get_data(API_URL, query_project_listings, projects[0]["value"])
df_s_and_l = parse_sales_and_listings(sales_data, listings_data)

# ============================================================================
# WEB APP
# ============================================================================
app = dash.Dash(__name__)
server = app.server
app.title = "Zora's got a brand new API"

app.layout = html.Div(
    children=[
        html.Div(className="header-container",
          children=
            html.H1(
              children="ZORA'S GOT A BRAND NEW API",
            )
        ),
        html.Div(className="links",
          children=[
            html.A("↗ Zora's API documentation ", href="https://docs.zora.co/docs/zora-api/intro"
            ),
            html.A(" ↗ Tutorial on building this kind of thing with Python ", href="https://realpython.com/python-dash/"
            ),
            html.A(className="twitter-link", children=" ↗ Follow me on Twitter", href="https://twitter.com/chr1stopherrrrr"
            )
          ]
        ),
        html.Div(className="intro",
          children=[
            html.H2(
              children="INTRO"
            ),
            html.P(className="intro-first-paragraph",
              children="Analysis is a superpower for collecting and trading NFTs."
            ),
            html.P(className="intro-body",
                children=[
                    html.P(className="intro-p", children="The first step to unlocking this power is access to data."),
                    html.P(className="intro-p", children="""Zora has recently released a GraphQL API which lets anyone query data for any ERC721 token."""),
                    html.P(className="intro-p", children="""This page is a my attempt to use this data to learn about collections."""),
                ]
            ),
            html.P(className="caveat",
              children="⚠︎ This page is very WIP (plus I'm a PM, not an engineer) but the API is sick and I'll improve the page as I go. ⚠︎"
            ),
          ]
        ),
        html.Div(className="select-a-project",
          children=[
            html.H2(
              children="SELECT A PROJECT",
              style={'width': '33%', 'display': 'inline-block', 'vertical-align': 'middle'}
            ),
            html.Div(className="dropdown",
                children=[
                dcc.Dropdown(id='project-dropdown',
                options=projects, value=projects[0]["value"]
                ),
                html.Div(id='dd-output-container')
               ],style={'width': '66%', 'display': 'inline-block', 'vertical-align': 'middle'}
            ),
          ]
        ),

        
        html.Div(
          className="q_and_a",
          children=[
            html.Div(className="question",
              children=[
                html.Div(
                  children=[
                    html.H2(
                      children="❶ Is the project seeing good sales volume?"
                    ),
                    html.P(
                      "This chart shows the volume for the project over the last day and last week."
                    ),
                    html.A("↗ Try the GraphQL explorer", href="https://api.zora.co/graphql")
                  ]
                )
              ],
              style={'width': '33%', 'display': 'inline-block', 'vertical-align': 'middle'}
            ),
            html.Div(className="answer",
              children=[
                dcc.Graph(
                  id="bar-volume",
                  #figure=fig_v
                )
              ], style={'width': '66%', 'display': 'inline-block', 'vertical-align': 'middle'}
            )
          ]
        ),

        html.Div(
          className="q_and_a",
          children=[
            html.Div(className="question",
              children=[
                html.Div(
                  children=[
                    html.H2(
                      children="❷ Are sales and listings trending up?"
                    ),
                    html.P(
                      children="This chart shows the sales and listings for the chosen project over the last"
                      " 24 hours."),
                    html.P(className="caveat",
                    children="⚠︎ I'm looking into gaps in the listings data ⚠︎"),
                    html.A("↗ Try the GraphQL explorer", href="https://api.zora.co/graphql")
                  ]
                )
              ],
              style={'width': '33%', 'display': 'inline-block', 'vertical-align': 'middle'}
            ),
            html.Div(className="answer",
              children=[
                dcc.Graph(
                  id="scatter-sales-listings",
                ),
              ], style={'width': '66%', 'display': 'inline-block', 'vertical-align': 'middle'}
            )
          ]
        ),

        html.Div(
          className="q_and_a",
          children=[
            html.Div(className="question",
              children=[
                html.Div(
                  children=[
                    html.H2(
                      children="❸ Can I buy and sell for profit, quickly?"
                    ),
                  ]
                )
              ],
              style={'width': '33%', 'display': 'inline-block', 'vertical-align': 'middle'}
            ),
            html.Div(className="answer",
              children=[
                html.P("Coming soon...")
              ], style={'width': '66%', 'display': 'inline-block', 'vertical-align': 'middle'}
            )
          ]
        ),
    ]
)

# ============================================================================
# CALLBACKS AND GRAPHS
#
# https://plotly.com/python-api-reference/
# ============================================================================

@app.callback(
    Output('dd-output-container', 'children'),
    Input('project-dropdown', 'value')
)
def update_output(value):
    return f'You have selected {value}'

@app.callback(
    Output('scatter-sales-listings', 'figure'),
    Input('project-dropdown', 'value')
)
def update_graph(value):
    sales_data = get_data(API_URL, query_project_sales, value)
    listings_data = get_data(API_URL, query_project_listings, value)
    df_s_and_l = parse_sales_and_listings(sales_data, listings_data)
    
    # ============================================================================
    # BUILD A GRAPH
    # ============================================================================
    fig_s_and_l = px.scatter(
      df_s_and_l,
      x="ts",
      y="price_eth",
      color="type",
      color_discrete_map={"sale": "#FF3366", "listing": "#011627"},
      opacity=0.7,
      title="SALES AND LISTINGS"
    )

    fig_s_and_l.update_layout(
        plot_bgcolor="#F3F4F5",
        paper_bgcolor="#F3F4F5"
    )
    
    return fig_s_and_l

@app.callback(
    Output('bar-volume', 'figure'),
    Input('project-dropdown', 'value')
)
def update_bar(value):
    volume_data = get_data(API_URL, query_project_volume, value)
    df_v = parse_volume_data(volume_data)

    fig_v = px.bar(
      df_v,
      x="period",
      y="volume_eth",
      color="period",
      color_discrete_map={"day": "#FF3366", "week": "#011627"},
      title="SALES VOLUME"
    )

    fig_v.update_layout(
        plot_bgcolor="#F3F4F5",
        paper_bgcolor="#F3F4F5"
    )

    return fig_v

# ============================================================================
# GO OFF SON
# ============================================================================

if __name__ == "__main__":
    app.run_server(debug=True)
