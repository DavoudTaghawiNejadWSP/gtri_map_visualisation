# -*- coding: utf-8 -*-
import pandas as pd
from plotly import graph_objects as go
from geopy.geocoders import Nominatim
from tqdm import tqdm as progress_bar
from perscache import Cache
from numpy import percentile


ROWS, COLUMNS = 0, 1

cache = Cache()

geolocator = Nominatim(user_agent="mymap")


def calculate_node_sums(df, values=['fobvalue'], reporterISO='reporterISO'):
    """ Calculates a dataframe with the nodesize and lat long position
    of each country

    Args:
        values:
            list (!) of columnname determening node and edge sizes
        reporterISO:
            columnname with reporterISO
    """
    uniques = df.groupby(reporterISO)[values].sum()
    uniques['ISO'] = uniques.index
    return uniques.set_index('ISO', drop=False)


def plot_network_on_world_map(df,
                              unique_countries,
                              node_scaling=lambda x: 2,
                              scope=None,
                              center=None, lataxis_range=None, lonaxis_range=None,
                              landcolor='rgb(243, 243, 243)',
                              countrycolor='rgb(204, 204, 204)',
                              linecolor='rgba(68, 68, 68, 255)',
                              countrymarkercolor='rgb(0, 0, 255)',
                              linewidth=1,
                              title_text=None,
                              edge_weight='fobvalue',
                              node_size='fobvalue',
                              reporterISO='reporterISO',
                              partnerISO='partnerISO',
                              width=None,
                              height=None,
                              save=None):
    """ This function plots a network on the world map. The network
    is a dataframe with three columns: ["reporterISO", "partnerISO", "fobvalue"]

    Args:
        df:
            dataframe with nework data ["reporterISO", "partnerISO", "fobvalue"]
        unique_countries:
            dataframe produced by calculate_node_sums
        node_scaling:
            function how nodes are scaled, example:
                lambda x: x / x.median() - scales linear around the median
                lambda x: x / x.max() * 4 + 1 - scales linear smalles not is size 1 and biggest node is size 5
                lambda x: np.log(x) - scale logarithmically
                lambda x: 1 - every node is of size 1
        scope:
            focus on continent available values: ["world", "usa", "europe", "asia", "africa", "north america", "south america"]
        center:
            center on countryISO
        lataxis_range, lonaxis_range:
            if centered on a country, determine size of focus, try 10 or 20
        landcolor, countrycolor, linecolor, countrymarkercolor:
            color the map
        linewidth:
            obvious
        title_text:
            obvious
        egde_weight:
            column in the dataframe that defines the edge color-transparency
        node_size:
            column in unique_countries that defines the node size
        reporterISO, partnerISO:
            alternative column names
        width:
            width of the whole 'paper'
        height:
            height of the whole 'paper'
        save:
            saves the figure. Parametern should be the filename ending in .png .jpeg .webp .svg .pdg .eps.
            For emple save='./graphs/german_trade.png'

    """
    if isinstance(linecolor, str):
        # if linecolor is string all lines have the same color
        linecolor = [linecolor] * len(df)

    if center is not None:
        center = {'lat': unique_countries.loc[center, 'lat'],
                  'lon': unique_countries.loc[center, 'long']}

    if (center is not None
        and lataxis_range is not None
            and lonaxis_range is not None):
        lataxis_range = [center['lat'] - lataxis_range,
                         center['lat'] + lataxis_range]
        lonaxis_range = [center['lon'] - lonaxis_range,
                         center['lon'] + lonaxis_range]

    if width is not None or height is not None:
        autosize = False
    else:
        autosize = None

    fig = go.Figure()

    fig.update_layout(
        title_text=title_text,
        showlegend=False,
        autosize=autosize,
        width=width,
        height=height,
        geo=dict(
            showland=True,
            landcolor=landcolor,
            countrycolor=countrycolor,
            scope=scope,
            center=center,
            lataxis_range=lataxis_range,
            lonaxis_range=lonaxis_range
        )
    )

    fig.add_trace(go.Scattergeo(
                  locations=unique_countries['ISO'],
                  hoverinfo='location',
                  mode='markers',
                  marker=dict(
                      # change this for a seperate value that is the node size
                      size=node_scaling(unique_countries[node_size]),
                      color=countrymarkercolor,
                      line=dict(
                          width=3,
                          color=countrymarkercolor))))

    for i in progress_bar(range(len(df))):
        fig.add_trace(
            go.Scattergeo(
                locations=unique_countries['ISO'],
                mode='lines',
                line=dict(width=linewidth, color=linecolor[i]),
                opacity=(float(df[edge_weight].iloc[i])
                         / float(df[edge_weight].max())),
                hoverinfo='skip',
            )
        )

    fig.show()
    if save is not None:
        fig.write_image(save)


def filter_quantiles_reporter(df, quantile, value='fobvalue', reporterISO='reporterISO'):
    """ Filter to x percentile the trade routes from a reporters perspective """
    selected = []
    for partner in df[reporterISO].unique():
        all_trade_links_of_partner = df[df[reporterISO] == partner]
        cut_off = percentile(
            all_trade_links_of_partner[value], 100 - quantile)
        selected.append(
            all_trade_links_of_partner[all_trade_links_of_partner[value] > cut_off])
    selected = pd.concat(selected, axis=ROWS)
    return selected


def filter_quantiles_partner(df, quantile, value='fobvalue', partnerISO='partnerISO'):
    """ Filter to x percentile the trade routes from a partners perspective """
    selected = []
    for partner in df[partnerISO].unique():
        all_trade_links_of_partner = df[df[partnerISO] == partner]
        cut_off = percentile(
            all_trade_links_of_partner[value], 100 - quantile)
        selected.append(
            all_trade_links_of_partner[all_trade_links_of_partner[value] > cut_off])
    selected = pd.concat(selected, axis=ROWS)
    return selected


def filter_quantiles_keep_both(df, quantile, value='fobvalue', reporterISO='reporterISO', partnerISO='partnerISO'):
    """ Filter to x percentile the trade routes from reporters and partners perspective """
    return pd.concat([filter_quantiles_reporter(df, quantile, value, reporterISO),
                      filter_quantiles_partner(df, quantile, value, partnerISO)], axis=ROWS).drop_duplicates(
                          subset=[reporterISO, partnerISO], ignore_index=True)


def filter_single_country(df, countryISO, reporterISO='reporterISO', partnerISO='partnerISO'):
    """ Filters out only traderoutes that start or end with countryISO """
    return df[(df[reporterISO] == countryISO) | (df[partnerISO] == countryISO)]


def calculate_total_trade_for_all_edges(df, value='fobvalue', reporterISO='reporterISO', partnerISO='partnerISO', result_column_name='total_trade'):
    """Calculate total trade for all edges, by summing exports and the reverse exports"""
    df_reversed = df.rename(
        columns={partnerISO: reporterISO, reporterISO: partnerISO})
    df = df.set_index([reporterISO, partnerISO], drop=False)
    df_reversed = df_reversed.set_index([reporterISO, partnerISO])
    df[result_column_name] = (df[value].add(df_reversed[value], fill_value=0))
    return df.reset_index(drop=True)
