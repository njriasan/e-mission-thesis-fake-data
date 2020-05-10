import numpy as np
import requests
import json
from lxml import etree
import xml.dom.minidom as minidom
from scipy.spatial.distance import euclidean

query_template = "[out:json][timeout:25];\n(\n{});\nout body;\n>;"
node_template = "    node[\"{}\"=\"{}\"]({bbox});\n"

overpass_url = "https://lz4.overpass-api.de/"

why_map = {1 : "Home", 2 : "Work from Home", 3 : "Work", 4 : "Work Trip", 5 : "Volunteering",
        6 : "Drop Off or Pick up", 7 : "Change Transportation", 8 : "School", 9 : "Child care",
        10 : "Adult care", 11 : "Buy Goods", 12 : "Buy Services", 13 : "Buy Meals",
        14 : "Other Errands", 15 : "Recreational Activities", 16 : "Exercise", 17 : "Visit Friends",
        18 : "Health care", 19 : "Religious", -9 : "Unknown", -8 : "Unknown", -7 : "Unknown",
        97 : "Unknown"}

home_searches = [("building", "residential"), ("building", "apartments"),
        ("building", "terrace"), ("building", "semidetached house")]

work_searches = [("building", "commercial")]

school_searches = [("amenity", "school"), ("amenity", "college"), 
        ("amenity", "kindergarten"), ("building", "school"), 
        ("building", "college"), ("building", "kindergarten")]

legal_searches = []

childcare_searches = [("amenity", "nursery"), ("amenity", "childcare")]

adultcare_searches = [("social_faclitity", "nursing_home"), ("amenity", "nursing_home")]

goods_searches = [("amenity", "fuel"), ("shop", "department_store"), ("shop", "clothes"),
        ("shop", "convenience"), ("shop", "supermarket"), ("shop", "mall")]

services_searches = [("amenity", "bank"), ("shop", "dry_cleaning"), ("shop", "laundry"), 
        ("shop", "car_repair")]

meals_searches = [("amenity", "restaurant"), ("amenity", "cafe"), ("amenity", "fastfood"), 
        ("amenity", "biergarten")]

other_errands_searches = [("amenity", "library"), ("amenity", "mobile_library"), 
        ("amenity", "public_bookcase"), ("amenity", "post_office"), ("amenity", "post_box")]

recreation_searches = [("leisure", "park"), ("tourism", "museum"), ("tourism", "gallery"), 
        ("amenity", "cinema"), ("amenity", "theatre"), ("amenity", "bar"), ("amenity", "pub")]

exercise_searches = legal_searches + [("leisure", "fitness_station")]

healthcare_searches = [("amenity", "doctors"), ("amenity", "hospital"), ("amenity", "pharmacy"), 
        ("amenity", "clinic"), ("amenity", "dentist")]

religious_searches = [("building", "shrine"), ("building", "temple"), 
        ("building", "synagogue"), ("building", "mosque"), 
        ("building", "chapel"), ("building", "cathedral"), 
        ("building", "church"), ("amenity", "place_of_worship")]

search_map = {1 : home_searches, 2 : home_searches, 3 : work_searches, 
        4 : work_searches, 5 : school_searches, 6 : school_searches, 
        7 : legal_searches, 8 : school_searches, 9 : childcare_searches,
        10 : adultcare_searches, 11 : goods_searches, 12 : services_searches,
        13 : meals_searches, 14 : other_errands_searches, 15 : recreation_searches, 
        16 : exercise_searches, 17 : home_searches, 18 : healthcare_searches,
        19 : religious_searches, -9 : legal_searches, -8 : legal_searches,
        -7 : legal_searches, 97 : legal_searches}


def append_trips(base, endpoints, tour):
    person = etree.SubElement(base, 'person')
    userid = list(tour.keys())[0]
    contents = tour[userid]
    is_student = "yes" if contents["student"] else "no"
    is_employed = "yes" if contents["employed"] else "no"
    plan = contents["plan"]
    person.set("id", userid) 
    person.set("student", is_student) 
    person.set("employed", is_employed)
    plan_xml = etree.SubElement(person, "plan")
    plan_xml.set("selected", "yes")
    why = "home"
    for i, endpoint in enumerate(endpoints[:-1]):
        action = etree.SubElement(plan_xml, "act")
        action.set("type", why)
        action.set("lat", str(endpoint["lat"]))
        action.set("lon", str(endpoint["lon"]))
        action.set("end_time", plan[i]['start time'])
        leg = etree.SubElement(action, "leg")
        leg.set ("mode", plan[i]["mode"])
        why = why_map[plan[i]['dest_encoding']]
        
    endpoint = endpoints[-1]
    action = etree.SubElement(plan_xml, "act")
    action.set("type", why)
    action.set("lat", str(endpoint["lat"]))
    action.set("lon", str(endpoint["lon"]))

def decorate_tours(tour_json):
    home_options = get_home_locations()
    plans = etree.Element('plans')
    with open(tour_json, "r") as f:
        tours = json.load(f)
    for tour in tours:
        append_trips(plans, decorate_tour(tour, home_options), tour)
    xml_str = etree.tostring(plans, encoding='utf8', method='xml', pretty_print=True)
    with open("population.xml", "bw") as f:
        f.write(xml_str)

    """
    distance_in_meters = 10000
    bbox_delta = meter2deg * distance_in_meters
    latitude = 37.871666
    longitude = -122.272781
    print(get_locations_set(latitude - bbox_delta, longitude - bbox_delta,
        latitude + bbox_delta, longitude + bbox_delta, "building", "apartments"))
    """

miles2meter = 1609.34
meter2deg = 90/(10001.965729 * 1000)
def decorate_tour(tour_dict, home_options):

    home = get_home_location(home_options)
    endpoints = [home]
    current_location = home
    
    userid = list(tour_dict.keys())[0]
    plan = tour_dict[userid]['plan']

    work = get_work_location(plan, home)
    for action in plan:
        dest = action['dest_encoding']
        if dest == 1 or dest == 2:
            current_location = home
        elif dest == 3:
            if work is None:
                dist_miles = action['dist']
                # Convert the data into a larger bounding box containing the four corners
                target_dist = dist_miles * miles2meter * meter2deg
                lat, lon = current_location['lat'], current_location['lon']
                work = generate_data (dest, lat, lon, target_dist)
            current_location = work
        else:
            dist_miles = action['dist']
            # Convert the data into a larger bounding box containing the four corners
            target_dist = dist_miles * miles2meter * meter2deg
            lat, lon = current_location['lat'], current_location['lon']
            current_location = generate_data (dest, lat, lon, target_dist)
        endpoints.append(current_location)
    return endpoints

def generate_data(dest, lat, lon, target_distance):
    offset = target_distance * 2
    expand_search = True
    while expand_search:
        locations = get_locations_in_box(lat - offset, lon - offset, 
                lat + offset, lon + offset, search_map[dest])
        expand_search = len(locations) == 0
        if not expand_search:
            current_location = get_closest_to_target(lat, lon, target_distance, locations) 
        else:
            offset *= 2
    return current_location

def get_closest_to_target(lat, lon, target_dist, locations):
    old_loc = np.array([lat, lon])
    min_value = float('inf')
    loc_choice = None
    for loc in locations:
        target_loc = np.array([loc['lat'], loc['lon']])
        distance = np.absolute(euclidean(old_loc, target_loc) - target_dist)
        if distance < min_value:
            min_value = distance
            loc_choice = loc
    return loc_choice

def get_work_location(plan, home):
    home_values = [1, 2]
    prev = 1
    for action in plan:
        dest = action['dest_encoding']
        if (dest == 3 and prev in home_values) or (prev == 3 and dest in home_values):
            dist_miles = action['dist']
            lat, lon = home['lat'], home['lon']
            # Convert the data into a larger bounding box containing the four corners
            target_dist = dist_miles * miles2meter * meter2deg
            return generate_data(3, lat, lon, target_dist)
        prev = dest
    return None


def get_home_locations():
    # Bounding box that includes most of the city of berkeley and other parts of alameda county
    min_lon, min_lat, max_lon, max_lat  = -122.293971,37.835727,-122.234196,37.90669
    return get_locations_in_box(min_lat, min_lon, max_lat, max_lon, home_searches)


def get_home_location(options):
    index = np.random.randint(len(options))
    return options[index]
    

def get_locations_in_box(min_lat, min_lon, max_lat, max_lon, searches):
    min_waiting_time = 5
    bbox_string = "%s,%s,%s,%s" % (min_lat, min_lon, max_lat, max_lon)
    node_searches = [node_template.format(elem[0], elem[1], bbox=bbox_string) for elem in searches]
    combined_nodes = "".join(node_searches)
    overpass_query = query_template.format(combined_nodes)
    #print(overpass_query)
    response = requests.post(overpass_url + "api/interpreter", data=overpass_query)
    try:
        all_results = response.json()["elements"]
    except json.decoder.JSONDecodeError as e:
        logging.info("Unable to decode response with status_code %s, text %s" %
            (response.status_code, response.text))
        time.sleep(5)
        logging.info("Retrying after 5 second sleep")
        response = requests.post(overpass_url + "api/interpreter", data=overpass_query)
    try:
        all_results = response.json()["elements"]
    except json.decoder.JSONDecodeError as e:
        logging.info("Unable to decode response with status_code %s, text %s" %
            (response.status_code, response.text))
        if response.status_code == 429:
            logging.info("Checking when a slot is available")
            response = requests.get(overpass_url + "api/status")
            status_string = response.text.split("\n")
            try:
                available_slots = int(status_string[3].split(" ")[0])
                if available_slots > 0:
                    logging.info("No need to wait")
                    response = requests.post(overpass_url + "api/interpreter", data=overpass_query)
                    all_results = response.json()["elements"]
                # Some api/status returns 0 slots available and then when they will be available
                elif available_slots == 0:
                    min_waiting_time = min(int(status_string[4].split(" ")[5]), int(status_string[5].split(" ")[5]))
                    time.sleep(min_waiting_time)
                    logging.info("Retrying after " + str(min_waiting_time) +  " second sleep")
                    response = requests.post(overpass_url + "api/interpreter", data=overpass_query)
                    all_results = response.json()["elements"]
            except ValueError as e:
                # And some api/status directly returns when the slots will be available
                try:
                    min_waiting_time = min(int(status_string[3].split(" ")[5]), int(status_string[4].split(" ")[5]))
                    time.sleep(min_waiting_time)
                    logging.info("Retrying after " + str(min_waiting_time) +  " second sleep")
                    response = requests.post(overpass_url + "api/interpreter", data=overpass_query)
                    all_results = response.json()["elements"]
                except ValueError as e:
                    logging.info("Unable to find availables slots")
                    all_results = []
        else:
            all_results = []
    return all_results
