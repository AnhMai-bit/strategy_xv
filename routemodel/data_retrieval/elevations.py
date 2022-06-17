import pandas as pd
import sys
import os.path

sys.path.append(os.path.dirname(__file__))

# Dict to convert Base 10 to Bing's Base 64 compressed text used in points_builder function
ENCODER_DICT = {0: "A", 1: "B", 2: "C", 3: "D", 4: "E", 5: "F", 6: "G", 7: "H",
                8: "I", 9: "J", 10: "K", 11: "L", 12: "M", 13: "N", 14: "O",
                15: "P", 16: "Q", 17: "R", 18: "S", 19: "T", 20: "U", 21: "V",
                22: "W", 23: "X", 24: "Y", 25: "Z", 26: "a", 27: "b", 28: "c",
                29: "d", 30: "e", 31: "f", 32: "g", 33: "h", 34: "i", 35: "j",
                36: "k", 37: "l", 38: "m", 39: "n", 40: "o", 41: "p", 42: "q",
                43: "r", 44: "s", 45: "t", 46: "u", 47: "v", 48: "w", 49: "x",
                50: "y", 51: "z", 52: "0", 53: "1", 54: "2", 55: "3", 56: "4",
                57: "5", 58: "6", 59: "7", 60: "8", 61: "9", 62: "_", 63: "-"}


def build_elevations_points(coordinates: list):
    """
    Compresses points to compressed string
    @param coordinates: list of dictionaries of coordinates Ex: [{lat1: long1}, {lat2: long2},... {latN: longN}]
    @return: String of encoded points for sending to API  Ex: 'vx1vilihnM6hR7mEl2Q'
    Algorithm taken from:
    https://docs.microsoft.com/en-us/bingmaps/rest-services/elevations/point-compression-algorithm
    """
    compressed_points = ""
    lat = 0
    long = 0
    # Step 1: Start with a set of latitude and longitude values.
    for index, pair in enumerate(coordinates):
        for key, value in pair.items():
            # Step 2: Multiply each value by 100000 and round each result to the nearest int
            new_lat = int(round(float(key) * 100000))
            new_long = int(round(float(value) * 100000))

            # Step 3: Calculate the difference between every pair of values
            dx = new_lat - lat
            dy = new_long - long
            lat = new_lat
            long = new_long

            # Step 4: Multiply each value by 2
            dy *= 2
            dx *= 2

            # Step 5: for negative change it to be a positive value, and then subtract 1
            if dx < 0:
                dx = abs(dx) - 1
            if dy < 0:
                dy = abs(dy) - 1

            # Step 6: For each pair of latitude and longitude coordinates compute
            #         ((latitude + longitude) * (latitude + longitude + 1) / 2) + latitude
            index = int(((dx + dy) * (dx + dy + 1) / 2) + dx)

            # Step 7: For each number, form a list of numbers by dividing the number by 32 repeatedly and recording
            #         each remainder, stop when the quotient reaches zero
            rem = []
            while index > 0:
                rem.append(index % 32)
                index = index // 32

            # Step 8: Add 32 to each number except for the last number in each list.
            for i in range(len(rem) - 1):
                rem[i] += 32

            # Step 9: Form a string by converting each number to a character using the encoder_dict
            for i in rem:
                compressed_points += ENCODER_DICT[i]

    return compressed_points


def format_elevations_query(coordinates_str: str, method='default', sample_val=0, heights='sealevel'):
    """
    Retrieves elevation data response from Bing Maps API through one of these two methods:
        - default method:  Gets elevations for a set of coordinates
        - polyline method: Gets elevations at equally spaced points along polyline generated by coordinates param
                           if using polyline method, must specify a sample_val > 0
    @param coordinates_str: Compressed string containing coordinates
    @param method: string, either 'default' or 'polyline'
    @param sample_val: int that determines how many equally spaced points along polyline
    @param heights: str Specifies which sea level model to use to calculate elevation,
           either 'sealevel' or 'ellipsoid'
    @return: Requests.response.json() object from API call
    """
    if method == 'default':
        # append specified elevation URL details
        query = 'Elevation/List?'
        # add parameters to URL
        query += 'points={}&heights={}'.format(coordinates_str,
                                               heights)
    elif method == 'polyline':
        if sample_val <= 0:
            print("Error, sample_val must be greater than 0")
            sys.exit()
        # append specified elevation URL details
        query = 'Elevation/Polyline?'
        # add parameters to URL
        query += 'points={}&heights={}&samples={}'.format(coordinates_str,
                                                          heights,
                                                          sample_val)
    else:
        print("Error, incorrect method parameter")
        sys.exit()

    # request URL and return json-encoded content of a response
    return query


def parse_elevations_data(response: dict, coordinates: list, method='default'):
    """
    Parsing through Elevations API call response.
        - if API call was done using polyline method, set method parameter in parse_elevations_data to 'polyline'
    @param response: Requests.response.json() object from API call
    @param coordinates: list of dictionaries of coordinates 
        Not required for polyline method.
        Ex: [{lat1: long1}, {lat2: long2},... {latN: longN}]
    @param method: string, either 'default' or 'polyline'
    @return: dataframe containing elevation data
    """
    # Extract elevations
    elevations = response
    try:
        elevations = elevations['resourceSets'][0]['resources'][0]['elevations']
    except KeyError:
        print("Error extracting elevations")
        sys.exit()

    print("Elevations returned:", len(elevations))

    if method == 'default':
        # create DataFrame with headers
        headers = ['Latitude', 'Longitude', 'Elevation']
        elevations_df = pd.DataFrame(columns=headers)

        # loop through coordinates and write coordinates into DataFrame
        counter = 0
        for pair in coordinates:
            for key, value in pair.items():
                elevations_df = elevations_df.append({'Latitude': key,
                                                      'Longitude': value,
                                                      'Elevation': elevations[counter]},
                                                     ignore_index=True)
                counter += 1

        return elevations_df
    elif method == 'polyline':
        # create DataFrame with headers
        headers = ['Elevation']
        elevations_df = pd.DataFrame(columns=headers)
        # input elevations into dataframe
        for val in elevations:
            elevations_df = elevations_df.append({'Elevation': val},
                                                 ignore_index=True)

        return elevations_df
    else:
        print("Error, incorrect method parameter")
        sys.exit()
