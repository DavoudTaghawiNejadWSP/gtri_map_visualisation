# -*- coding: utf-8 -*-
import pandas as pd
from plotly import graph_objects as go
from geopy.geocoders import Nominatim
from tqdm import tqdm as progress_bar
from perscache import Cache
from numpy import percentile
import pycountry


ROWS, COLUMNS = 0, 1

cache = Cache()

geolocator = Nominatim(user_agent="mymap")


@cache
def get_location(location):
    """ Internal function loading lat long position for an iso code or address.
    This function is cached and uses the internet for determening the lat long"""
    country = pycountry.countries.get(alpha_3=location['ISO'])
    locationlatlong = geolocator.geocode(country.name)
    if locationlatlong is None:
        location['lat'] = None
        location['long'] = None
    else:
        location['lat'] = locationlatlong.latitude
        location['long'] = locationlatlong.longitude
    return location


def get_unique_countries(df, value='fobvalue', reporterISO='reporterISO'):
    """ Calculates a dataframe with the nodesize and lat long position
    of each country

    Args:
        value:
            columnname determening node size
        reporterISO:
            columnname with reporterISO
    """
    uniques = df.groupby(reporterISO)[[value]].sum()
    uniques['ISO'] = uniques.index
    uniques_with_lat_long = uniques.apply(get_location, axis=COLUMNS)
    return uniques_with_lat_long.set_index('ISO', drop=False)


def plot_network_on_world_map(df,
                              unique_countries,
                              node_scaling=lambda x: 2,
                              scope=None,
                              center=None, lataxis_range=None, lonaxis_range=None,
                              landcolor='rgb(243, 243, 243)',
                              countrycolor='rgb(204, 204, 204)',
                              linecolor='rgba(68, 68, 68, 0)',
                              countrymarkercolor='rgb(0, 0, 255)',
                              linewidth=1,
                              title_text=None,
                              value='fobvalue',
                              reporterISO='reporterISO',
                              partnerISO='partnerISO'):
    """ This function plots a network on the world map. The network
    is a dataframe with three columns: ["reporterISO", "partnerISO", "fobvalue"]

    Args:
        df:
            dataframe with nework data ["reporterISO", "partnerISO", "fobvalue"]
        unique_countries:
            dataframe produced by get_unique_countries
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
        value, reporterISO, partnerISO:
            alternative column names

    """

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

    fig = go.Figure()

    fig.update_layout(
        title_text=title_text,
        showlegend=False,
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
                  lon=unique_countries['long'],
                  lat=unique_countries['lat'],
                  hoverinfo='location',
                  mode='markers',
                  marker=dict(
                      size=node_scaling(unique_countries[value]),
                      color=countrymarkercolor,
                      line=dict(
                          width=3,
                          color=linecolor))))

    for i in progress_bar(range(len(df))):
        reporter_lat, reporter_long = unique_countries.loc[
            df[reporterISO].iloc[i], ['lat', 'long']]
        partner_lat, partner_long = unique_countries.loc[
            df[partnerISO].iloc[i], ['lat', 'long']]

        fig.add_trace(
            go.Scattergeo(
                lon=[reporter_long, partner_long],
                lat=[reporter_lat, partner_lat],
                mode='lines',
                line=dict(width=linewidth, color='red'),
                opacity=(float(df[value].iloc[i])
                         / float(df[value].max())),
                hoverinfo='skip'
            )
        )

    fig.show()


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
