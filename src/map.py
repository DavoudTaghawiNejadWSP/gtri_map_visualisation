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


df = pd.read_feather('./data/total_trade_between_countries.feather')


@cache
def get_location(location):
    locationlatlong = geolocator.geocode(location['ISO'])
    if locationlatlong is None:
        location['lat'] = None
        location['long'] = None
    else:
        location['lat'] = locationlatlong.latitude
        location['long'] = locationlatlong.longitude
    return location


def get_unique_countries(series):
    uniques = pd.DataFrame({'ISO': series.unique()})
    uniques_with_lat_long = uniques.apply(get_location, axis=COLUMNS)
    return uniques_with_lat_long


unique_countries = get_unique_countries(df['reporterISO'])
unique_countries = unique_countries.set_index('ISO')


def plot_network_on_world_map(df):
    fig = go.Figure()

    fig.add_trace(go.Scattergeo(
                  # locationmode = 'USA-states',
                  lon=unique_countries['long'],
                  lat=unique_countries['lat'],
                  hoverinfo='text',
                  hovertext=unique_countries.index,
                  text=unique_countries.index,
                  mode='markers',
                  marker=dict(
                      size=2,
                      color='rgb(0, 0, 255)',
                      line=dict(
                          width=3,
                          color='rgba(68, 68, 68, 0)'))))

    for i in progress_bar(range(len(df))):
        reporter_lat, reporter_long = unique_countries.loc[df['reporterISO'].iloc[i]]
        partner_lat, partner_long = unique_countries.loc[df['partnerISO'].iloc[i]]

        fig.add_trace(
            go.Scattergeo(
                # locationmode = 'world',
                lon=[reporter_long, partner_long],
                lat=[reporter_lat, partner_lat],
                mode='lines',
                line=dict(width=1, color='red'),
                opacity=float(df['fobvalue'].iloc[i]) / \
                float(df['fobvalue'].max()),
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
    fig.update_traces(go.Scattergeo(
        customdata=unique_countries.index,
        hovertemplate="%{customdata}"))

    fig.show()


def filter_quantiles(df, quantile):
    selected = []
    for partner in df['partnerISO'].unique():
        all_trade_links_of_partner = df[df['partnerISO'] == partner]
        cut_off = percentile(
            all_trade_links_of_partner['fobvalue'], 100 - quantile)
        selected.append(
            all_trade_links_of_partner[all_trade_links_of_partner['fobvalue'] > cut_off])

    selected = pd.concat(selected, axis=ROWS)

    return selected
