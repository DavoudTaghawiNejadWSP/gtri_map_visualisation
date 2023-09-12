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


df = pd.read_feather('./data/total_trade_between_countries.feather')


@cache
def get_location(location):
    country = pycountry.countries.get(alpha_3=location['ISO'])
    locationlatlong = geolocator.geocode(country.name)
    if locationlatlong is None:
        location['lat'] = None
        location['long'] = None
    else:
        location['lat'] = locationlatlong.latitude
        location['long'] = locationlatlong.longitude
    return location


def get_unique_countries(df):

    uniques = df.groupby('reporterISO')[['fobvalue']].sum()
    uniques['ISO'] = uniques.index
    uniques_with_lat_long = uniques.apply(get_location, axis=COLUMNS)
    return uniques_with_lat_long


unique_countries = get_unique_countries(df)
unique_countries = unique_countries.set_index('ISO', drop=False)


def plot_network_on_world_map(df, node_scaling=lambda x: 2):
    fig = go.Figure()

    fig.add_trace(go.Scattergeo(
                  locations=unique_countries['ISO'],
                  lon=unique_countries['long'],
                  lat=unique_countries['lat'],
                  hoverinfo='location',
                  mode='markers',
                  marker=dict(
                      size=node_scaling(unique_countries['fobvalue']),
                      color='rgb(0, 0, 255)',
                      line=dict(
                          width=3,
                          color='rgba(68, 68, 68, 0)'))))

    for i in progress_bar(range(len(df))):
        reporter_lat, reporter_long = unique_countries.loc[
            df['reporterISO'].iloc[i], ['lat', 'long']]
        partner_lat, partner_long = unique_countries.loc[
            df['partnerISO'].iloc[i], ['lat', 'long']]

        fig.add_trace(
            go.Scattergeo(
                lon=[reporter_long, partner_long],
                lat=[reporter_lat, partner_lat],
                mode='lines',
                line=dict(width=1, color='red'),
                opacity=(float(df['fobvalue'].iloc[i])
                         / float(df['fobvalue'].max())),
                hoverinfo='skip'
            )
        )

    fig.update_layout(
        title_text='TITLE',
        showlegend=False,
        geo=dict(
            # scope = 'country names',
            # projection_type = 'azimuthal equal area',
            showland=True,
            landcolor='rgb(243, 243, 243)',
            countrycolor='rgb(204, 204, 204)',
        ),
    )

    fig.show()


def filter_quantiles_reporter(df, quantile):
    selected = []
    for partner in df['reporterISO'].unique():
        all_trade_links_of_partner = df[df['reporterISO'] == partner]
        cut_off = percentile(
            all_trade_links_of_partner['fobvalue'], 100 - quantile)
        selected.append(
            all_trade_links_of_partner[all_trade_links_of_partner['fobvalue'] > cut_off])

    selected = pd.concat(selected, axis=ROWS)

    return selected


def filter_quantiles_partner(df, quantile):
    selected = []
    for partner in df['partnerISO'].unique():
        all_trade_links_of_partner = df[df['partnerISO'] == partner]
        cut_off = percentile(
            all_trade_links_of_partner['fobvalue'], 100 - quantile)
        selected.append(
            all_trade_links_of_partner[all_trade_links_of_partner['fobvalue'] > cut_off])

    selected = pd.concat(selected, axis=ROWS)

    return selected


def filter_quantiles_keep_both(df, quantile):
    return pd.concat([filter_quantiles_reporter(df, quantile),
                      filter_quantiles_partner(df, quantile)], axis=ROWS).drop_duplicates(
                          subset=['reporterISO', 'partnerISO'], ignore_index=True)
