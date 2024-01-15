import streamlit as st
import pandas as pd
import datetime
from geostructures import Coordinate, GeoPoint
from geostructures.collections import Track
from geostructures.visualization.plotly import draw_collection
import plotly.express as px
import mgrs

# Setup streamlit page to be wide by default
st.set_page_config(layout='wide')

# App title
st.title('Ship Tracker')



# Allows the upload of CSV files
st.write('Upload an AIS Broadcast Points CSV file from https://marinecadastre.gov/ais/')
#@st.cache_data
uploaded_file = st.file_uploader("Upload AIS CSV file:")

if uploaded_file:
    @st.cache_data
    # Reads the CSV and returns the length of the CSV
    data = pd.read_csv(uploaded_file).sort_values(by=['BaseDateTime'])
    st.write('Rows of Data: '+str(len(data)))
    
    # Allows users to dictate minimum length of ship in meters
    l=st.number_input('Enter minimum ship length(meters):')
    if l:
        df2 = data[data['Length']> l]
        
        # Returns a set of names associated with the length then allows multi selection
        ship_list = list(set(df2['VesselName']))
        select_ship = st.multiselect('Select ship(s)', ship_list)
        
        # Filters the data based on selected ship(s)
        df3 = data[(data['VesselName'].isin(select_ship))]
        
        #Requiers the selection of at least 1 ship        
        if len(select_ship) == 0:
            st.text('Choose at least 1 ship to start')
        else:
            @st.cache_data
            # Filters the data based on the ships name, IMO, and MMSI to ensure we get all data
            df4= data[(data['IMO'].isin(df3['IMO'])) | (data['MMSI'].isin(df3['MMSI']) | (data['VesselName'].isin(df3['VesselName'])))]
            # Formats date time to MM/DD/YYY hh:mm:ss
            df4['BaseDateTime']= pd.to_datetime(df4['BaseDateTime']).dt.strftime('%m/%d/%Y %H:%M:%S')
            # Changes Vessel name to all lowercase
            df4['VesselName'] = df4['VesselName'].str.lower()
            # Converts speed from knots to meters per second
            df4['Speed'] = df4['SOG'] * 0.51444
            # Turns longitude into a float. Some data sets have it as an object
            df4['LON'] = df4['LON'].astype(float)
            # Uses Geostructures to create a GeoPoint. A Coordinate with an associated timestamp
            df4['GeoPoint'] = df4.apply(
              lambda x: GeoPoint(
                  Coordinate(x['LON'], x['LAT']),
                  dt=datetime.datetime.strptime(x['BaseDateTime'], '%m/%d/%Y %H:%M:%S'),
                  properties={k:v for k,v in x.items() if k != 'geopoint'}
              ),
              axis=1
            )
            # Creates a Track from the GeoPoints. A chronologically-ordered collection of shapes (requires that each shape be time-bounded)
            track = Track(list(df4['GeoPoint']))
            # Calculates distance traveled between point in meters
            df4['Travel Distance'] = [0, *track.centroid_distances]
            # Strips IMO from the front of each cell and places it in a URL for more ship info
            df4['IMO'] = df4['IMO'].apply(lambda x: x.strip('IMO'))
            df4['Info'] = 'https://www.vesselfinder.com/vessels/details/'+ df4['IMO']
            pd.set_option('display.max_colwidth', None)
            st.write('Total data points:', len(df4))
            
    
            # Creates a Plotly map based off of the selected data
            button = st.button('Generate Map')
            if button:
                df5 = df4.drop('GeoPoint', axis = 1)
                fig = px.scatter_mapbox(df5, lat ='LAT', lon='LON',
                                        color=df5['VesselName'],
                                        hover_data=df5.columns[0:],
                                        zoom=6)
                fig.update_layout(
                    title='<b>Ship Travel<b><br>',
                    title_x=0.5,
                    mapbox_style="open-street-map",
                    margin={"r":0,"t":50,"l":0,"b":0},
                    legend=dict(
                        x=0,
                        y=1,
                        traceorder="reversed",
                        title_font_family="Times New Roman",
                        font=dict(
                            family="Courier",
                            size=12,
                            color="black"
                        ),
                        bgcolor="White",
                        bordercolor="Black",
                        borderwidth=2
                    ),
                    legend_title_text='Legend',
                    showlegend=True
                    )

                st.plotly_chart(fig)
            
            # Allows for the download of the filtered data into a CSV
            def convert_df(df):

                return df.to_csv().encode('utf-8')


            csv = convert_df(df4)

            st.download_button(
                label="Download data as CSV",
                data=csv,
                file_name='ship_info.csv',
                mime='text/csv',
            )

            
            
