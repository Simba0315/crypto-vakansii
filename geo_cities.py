"""Where the cities in job postings are, for the jobs map (/map/).

CITIES: key -> (display name, ISO country code, latitude, longitude). Two decimals is about one kilometre: enough for a dot per city.
ALIAS:  other spellings and suburbs that postings use -> key.
A name that is ambiguous (Cambridge, Newark, Lancaster, Franklin, Columbia, Westminster, Lexington) is left out on purpose: a dot in
the wrong country is worse than no dot. city_of() reads the first part of a location line and returns a key or None.
Coordinates are city centres, written from standard references; check any new one before adding it.
"""
import re

CITIES = {
    # United States
    "san-francisco": ("San Francisco", "US", 37.77, -122.42), "new-york": ("New York", "US", 40.71, -74.01), "seattle": ("Seattle", "US", 47.61, -122.33),
    "boston": ("Boston", "US", 42.36, -71.06), "austin": ("Austin", "US", 30.27, -97.74), "chicago": ("Chicago", "US", 41.88, -87.63),
    "denver": ("Denver", "US", 39.74, -104.99), "washington-dc": ("Washington, DC", "US", 38.91, -77.04), "los-angeles": ("Los Angeles", "US", 34.05, -118.24),
    "dallas": ("Dallas", "US", 32.78, -96.80), "atlanta": ("Atlanta", "US", 33.75, -84.39), "san-jose": ("San Jose", "US", 37.34, -121.89),
    "san-diego": ("San Diego", "US", 32.72, -117.16), "pittsburgh": ("Pittsburgh", "US", 40.44, -80.00), "miami": ("Miami", "US", 25.76, -80.19),
    "raleigh": ("Raleigh", "US", 35.78, -78.64), "phoenix": ("Phoenix", "US", 33.45, -112.07), "oakland": ("Oakland", "US", 37.80, -122.27),
    "salt-lake-city": ("Salt Lake City", "US", 40.76, -111.89), "houston": ("Houston", "US", 29.76, -95.37), "las-vegas": ("Las Vegas", "US", 36.17, -115.14),
    "philadelphia": ("Philadelphia", "US", 39.95, -75.17), "detroit": ("Detroit", "US", 42.33, -83.05), "charlotte": ("Charlotte", "US", 35.23, -80.84),
    "tucson": ("Tucson", "US", 32.22, -110.97), "louisville": ("Louisville", "US", 38.25, -85.76), "nashville": ("Nashville", "US", 36.16, -86.78),
    "albuquerque": ("Albuquerque", "US", 35.08, -106.65), "kansas-city": ("Kansas City", "US", 39.10, -94.58), "portland": ("Portland", "US", 45.52, -122.68),
    "tampa": ("Tampa", "US", 27.95, -82.46), "reno": ("Reno", "US", 39.53, -119.81), "columbus": ("Columbus", "US", 39.96, -83.00),
    "cincinnati": ("Cincinnati", "US", 39.10, -84.51), "sacramento": ("Sacramento", "US", 38.58, -121.49), "minneapolis": ("Minneapolis", "US", 44.98, -93.27),
    "honolulu": ("Honolulu", "US", 21.31, -157.86), "tulsa": ("Tulsa", "US", 36.15, -95.99), "huntsville": ("Huntsville", "US", 34.73, -86.59),
    "colorado-springs": ("Colorado Springs", "US", 38.83, -104.82), "memphis": ("Memphis", "US", 35.15, -90.05), "st-louis": ("St. Louis", "US", 38.63, -90.20),
    "baltimore": ("Baltimore", "US", 39.29, -76.61), "orlando": ("Orlando", "US", 28.54, -81.38), "indianapolis": ("Indianapolis", "US", 39.77, -86.16),
    "milwaukee": ("Milwaukee", "US", 43.04, -87.91), "cleveland": ("Cleveland", "US", 41.50, -81.69), "boulder": ("Boulder", "US", 40.01, -105.27),
    "brooklyn": ("Brooklyn", "US", 40.68, -73.94), "jersey-city": ("Jersey City", "US", 40.73, -74.08), "bronx": ("Bronx", "US", 40.84, -73.86),
    # Bay Area and California
    "mountain-view": ("Mountain View", "US", 37.39, -122.08), "palo-alto": ("Palo Alto", "US", 37.44, -122.14), "sunnyvale": ("Sunnyvale", "US", 37.37, -122.04),
    "santa-clara": ("Santa Clara", "US", 37.35, -121.96), "san-mateo": ("San Mateo", "US", 37.56, -122.32), "foster-city": ("Foster City", "US", 37.56, -122.27),
    "redwood-city": ("Redwood City", "US", 37.49, -122.24), "san-carlos": ("San Carlos", "US", 37.51, -122.26), "menlo-park": ("Menlo Park", "US", 37.45, -122.18),
    "cupertino": ("Cupertino", "US", 37.32, -122.03), "milpitas": ("Milpitas", "US", 37.43, -121.90), "fremont": ("Fremont", "US", 37.55, -121.99),
    "hayward": ("Hayward", "US", 37.67, -122.08), "south-san-francisco": ("South San Francisco", "US", 37.65, -122.41), "san-bruno": ("San Bruno", "US", 37.63, -122.41),
    "berkeley": ("Berkeley", "US", 37.87, -122.27), "hawthorne": ("Hawthorne", "US", 33.92, -118.35), "long-beach": ("Long Beach", "US", 33.77, -118.19),
    "el-segundo": ("El Segundo", "US", 33.92, -118.42), "torrance": ("Torrance", "US", 33.84, -118.34), "irvine": ("Irvine", "US", 33.68, -117.83),
    "costa-mesa": ("Costa Mesa", "US", 33.64, -117.92), "pasadena": ("Pasadena", "US", 34.15, -118.14), "cypress": ("Cypress", "US", 33.82, -118.04),
    "chatsworth": ("Chatsworth", "US", 34.26, -118.60), "roseville": ("Roseville", "US", 38.75, -121.29), "vandenberg": ("Vandenberg", "US", 34.74, -120.57),
    # Washington state, Texas, the east and the rest
    "redmond": ("Redmond", "US", 47.67, -122.12), "bellevue": ("Bellevue", "US", 47.61, -122.20), "bothell": ("Bothell", "US", 47.76, -122.21),
    "woodinville": ("Woodinville", "US", 47.75, -122.16), "mercer-island": ("Mercer Island", "US", 47.57, -122.22), "bastrop": ("Bastrop", "US", 30.11, -97.32),
    "starbase": ("Starbase", "US", 25.99, -97.16), "mcgregor": ("McGregor", "US", 31.44, -97.41), "brownsville": ("Brownsville", "US", 25.90, -97.50),
    "college-station": ("College Station", "US", 30.63, -96.33), "plano": ("Plano", "US", 33.02, -96.70), "cape-canaveral": ("Cape Canaveral", "US", 28.39, -80.60),
    "southaven": ("Southaven", "US", 34.99, -90.01), "waltham": ("Waltham", "US", 42.38, -71.24), "somerville": ("Somerville", "US", 42.39, -71.10),
    "cary": ("Cary", "US", 35.79, -78.78), "southfield": ("Southfield", "US", 42.47, -83.22), "ann-arbor": ("Ann Arbor", "US", 42.28, -83.74),
    "middle-river": ("Middle River", "US", 39.33, -76.44), "bethesda": ("Bethesda", "US", 38.98, -77.10), "silver-spring": ("Silver Spring", "US", 38.99, -77.03),
    "college-park": ("College Park", "US", 38.99, -76.94), "herndon": ("Herndon", "US", 38.97, -77.39), "reston": ("Reston", "US", 38.96, -77.36),
    "chantilly": ("Chantilly", "US", 38.89, -77.43), "mclean": ("McLean", "US", 38.93, -77.18), "wallops-island": ("Wallops Island", "US", 37.94, -75.47),
    "littleton": ("Littleton", "US", 39.61, -105.02), "broomfield": ("Broomfield", "US", 39.92, -105.09), "arvada": ("Arvada", "US", 39.80, -105.09),
    "fort-collins": ("Fort Collins", "US", 40.59, -105.08), "tempe": ("Tempe", "US", 33.43, -111.94), "scottsdale": ("Scottsdale", "US", 33.49, -111.93),
    "casa-grande": ("Casa Grande", "US", 32.88, -111.76), "provo": ("Provo", "US", 40.23, -111.66), "lehi": ("Lehi", "US", 40.39, -111.85),
    "sandy": ("Sandy", "US", 40.57, -111.86), "princeton": ("Princeton", "US", 40.36, -74.67), "royersford": ("Royersford", "US", 40.18, -75.54),
    "bolingbrook": ("Bolingbrook", "US", 41.70, -88.07), "romeoville": ("Romeoville", "US", 41.65, -88.09), "stennis-space-center": ("Stennis Space Center", "US", 30.36, -89.60),
    "canandaigua": ("Canandaigua", "US", 42.89, -77.28),
    # Canada and Latin America
    "toronto": ("Toronto", "CA", 43.65, -79.38), "vancouver": ("Vancouver", "CA", 49.28, -123.12), "montreal": ("Montreal", "CA", 45.50, -73.57),
    "ottawa": ("Ottawa", "CA", 45.42, -75.70), "waterloo": ("Waterloo", "CA", 43.46, -80.52), "calgary": ("Calgary", "CA", 51.05, -114.07),
    "mexico-city": ("Mexico City", "MX", 19.43, -99.13), "guadalajara": ("Guadalajara", "MX", 20.66, -103.35), "sao-paulo": ("São Paulo", "BR", -23.55, -46.63),
    "buenos-aires": ("Buenos Aires", "AR", -34.60, -58.38), "bogota": ("Bogotá", "CO", 4.71, -74.07), "santiago": ("Santiago", "CL", -33.45, -70.67),
    # Europe
    "london": ("London", "GB", 51.51, -0.13), "manchester": ("Manchester", "GB", 53.48, -2.24), "cardiff": ("Cardiff", "GB", 51.48, -3.18),
    "oxford": ("Oxford", "GB", 51.75, -1.26), "brighton": ("Brighton", "GB", 50.82, -0.14), "edinburgh": ("Edinburgh", "GB", 55.95, -3.19),
    "dublin": ("Dublin", "IE", 53.35, -6.26), "cork": ("Cork", "IE", 51.90, -8.47), "berlin": ("Berlin", "DE", 52.52, 13.40),
    "munich": ("Munich", "DE", 48.14, 11.58), "frankfurt": ("Frankfurt", "DE", 50.11, 8.68), "hamburg": ("Hamburg", "DE", 53.55, 9.99),
    "chemnitz": ("Chemnitz", "DE", 50.83, 12.92), "dresden": ("Dresden", "DE", 51.05, 13.74), "leonberg": ("Leonberg", "DE", 48.80, 9.01),
    "paris": ("Paris", "FR", 48.86, 2.35), "amsterdam": ("Amsterdam", "NL", 52.37, 4.90), "hilversum": ("Hilversum", "NL", 52.22, 5.17),
    "barcelona": ("Barcelona", "ES", 41.39, 2.17), "madrid": ("Madrid", "ES", 40.42, -3.70), "lisbon": ("Lisbon", "PT", 38.72, -9.14),
    "stockholm": ("Stockholm", "SE", 59.33, 18.07), "copenhagen": ("Copenhagen", "DK", 55.68, 12.57), "helsinki": ("Helsinki", "FI", 60.17, 24.94),
    "oslo": ("Oslo", "NO", 59.91, 10.75), "warsaw": ("Warsaw", "PL", 52.23, 21.01), "krakow": ("Kraków", "PL", 50.06, 19.94),
    "vienna": ("Vienna", "AT", 48.21, 16.37), "prague": ("Prague", "CZ", 50.08, 14.44), "zurich": ("Zurich", "CH", 47.38, 8.54),
    "geneva": ("Geneva", "CH", 46.20, 6.14), "milan": ("Milan", "IT", 45.46, 9.19), "brussels": ("Brussels", "BE", 50.85, 4.35),
    "belgrade": ("Belgrade", "RS", 44.79, 20.45), "novi-sad": ("Novi Sad", "RS", 45.27, 19.83), "sofia": ("Sofia", "BG", 42.70, 23.32),
    "bucharest": ("Bucharest", "RO", 44.43, 26.10), "budapest": ("Budapest", "HU", 47.50, 19.04), "athens": ("Athens", "GR", 37.98, 23.73),
    "kyiv": ("Kyiv", "UA", 50.45, 30.52), "vilnius": ("Vilnius", "LT", 54.69, 25.28), "tallinn": ("Tallinn", "EE", 59.44, 24.75),
    "sliema": ("Sliema", "MT", 35.91, 14.50),
    # Middle East and Africa
    "tel-aviv": ("Tel Aviv", "IL", 32.08, 34.78), "dubai": ("Dubai", "AE", 25.20, 55.27), "abu-dhabi": ("Abu Dhabi", "AE", 24.45, 54.38),
    "riyadh": ("Riyadh", "SA", 24.71, 46.68), "king-abdullah-economic-city": ("King Abdullah Economic City", "SA", 22.45, 39.13),
    "istanbul": ("Istanbul", "TR", 41.01, 28.98), "cape-town": ("Cape Town", "ZA", -33.92, 18.42), "lagos": ("Lagos", "NG", 6.52, 3.38),
    "nairobi": ("Nairobi", "KE", -1.29, 36.82),
    # Asia-Pacific
    "singapore": ("Singapore", "SG", 1.35, 103.82), "bengaluru": ("Bengaluru", "IN", 12.97, 77.59), "tokyo": ("Tokyo", "JP", 35.68, 139.69),
    "hong-kong": ("Hong Kong", "HK", 22.32, 114.17), "sydney": ("Sydney", "AU", -33.87, 151.21), "melbourne": ("Melbourne", "AU", -37.81, 144.96),
    "brisbane": ("Brisbane", "AU", -27.47, 153.03), "auckland": ("Auckland", "NZ", -36.85, 174.76), "seoul": ("Seoul", "KR", 37.57, 126.98),
    "gurugram": ("Gurugram", "IN", 28.46, 77.03), "noida": ("Noida", "IN", 28.54, 77.39), "new-delhi": ("New Delhi", "IN", 28.61, 77.21),
    "pune": ("Pune", "IN", 18.52, 73.86), "mumbai": ("Mumbai", "IN", 19.08, 72.88), "hyderabad": ("Hyderabad", "IN", 17.39, 78.49),
    "chennai": ("Chennai", "IN", 13.08, 80.27), "kuala-lumpur": ("Kuala Lumpur", "MY", 3.14, 101.69), "manila": ("Manila", "PH", 14.60, 120.98),
    "taipei": ("Taipei", "TW", 25.03, 121.57), "shanghai": ("Shanghai", "CN", 31.23, 121.47), "beijing": ("Beijing", "CN", 39.90, 116.41),
    "shenzhen": ("Shenzhen", "CN", 22.54, 114.06), "guangzhou": ("Guangzhou", "CN", 23.13, 113.26), "bangkok": ("Bangkok", "TH", 13.76, 100.50),
    "jakarta": ("Jakarta", "ID", -6.21, 106.85), "ho-chi-minh-city": ("Ho Chi Minh City", "VN", 10.82, 106.63), "hanoi": ("Hanoi", "VN", 21.03, 105.85),
}

ALIAS = {
    "sf": "san-francisco", "san francisco bay area": "san-francisco", "bay area": "san-francisco", "sf bay area": "san-francisco",
    "nyc": "new-york", "new york city": "new-york", "ny": "new-york", "manhattan": "new-york", "washington": "washington-dc", "washington dc": "washington-dc",
    "washington d.c.": "washington-dc", "dc": "washington-dc", "bangalore": "bengaluru", "gurgaon": "gurugram", "delhi": "new-delhi", "sao paulo": "sao-paulo",
    "são paulo": "sao-paulo", "zürich": "zurich", "montréal": "montreal", "ciudad de méxico": "mexico-city", "cdmx": "mexico-city", "bogotá": "bogota",
    "tel aviv-yafo": "tel-aviv", "tel aviv-jaffa": "tel-aviv", "hong kong sar": "hong-kong", "kraków": "krakow", "münchen": "munich", "wien": "vienna",
    "praha": "prague", "lisboa": "lisbon", "greater seattle area": "seattle", "saigon": "ho-chi-minh-city", "kiev": "kyiv", "sg": "singapore",
}
_NAME = {v[0].lower(): k for k, v in CITIES.items()}
_NAME.update({k.replace("-", " "): k for k in CITIES})


def city_of(location):
    """The city key of a location line ("San Francisco, CA; New York" -> "san-francisco"), from its first part that names a city we know."""
    for part in re.split(r";|\||•| or |/", location or "")[:4]:
        p = part.strip().lower()
        p = re.sub(r"^(hybrid|in-office|on-?site|office)[- :]+", "", p)
        first = re.split(r",| - | – |\(", p)[0].strip()
        first = re.sub(r"\s+(office|hq|headquarters|metro area|area)$", "", first)
        key = ALIAS.get(first) or _NAME.get(first)
        if key: return key
    return None


def test():
    assert city_of("San Francisco, CA") == "san-francisco" and city_of("New York City, NY; Remote") == "new-york"
    assert city_of("Remote - US; Hybrid- Fremont, CA") == "fremont" and city_of("Bengaluru, Karnataka, India") == "bengaluru"
    assert city_of("Cambridge, MA") is None and city_of("Remote") is None and city_of("SF office") == "san-francisco"
    for k, (nm, cc, la, lo) in CITIES.items():
        assert -90 <= la <= 90 and -180 <= lo <= 180 and len(cc) == 2, k
        assert not (cc == "US" and not (18 <= la <= 50 and -160 <= lo <= -66)), k            # US points fall inside the US
        assert not (cc in ("GB", "IE", "DE", "FR", "NL", "ES", "PT", "IT", "SE", "PL") and not (35 <= la <= 61 and -11 <= lo <= 25)), k
    print(f"geo_cities: {len(CITIES)} cities, {len(ALIAS)} other spellings, all checks passed")


if __name__ == "__main__":
    test()
