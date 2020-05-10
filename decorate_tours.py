import requests
import json

query_template = "[out:json][timeout:25];\n(\nnode[{}={}]({});\n);\nout body;\n>;"

def decorate_tours(nhts_info, tour_json):
    overpass_url = "https://lz4.overpass-api.de/"
    meter2deg = 90/(10001.965729 * 1000)
    distance_in_meters = 10000
    bbox_delta = meter2deg * distance_in_meters
    latitude = 37.871666
    longitude = -122.272781
    print(get_locations_set(latitude - bbox_delta, longitude - bbox_delta,
        latitude + bbox_delta, longitude + bbox_delta, overpass_url, "building", "apartments"))


def get_locations_set(min_lat, min_lon, max_lat, max_lon, overpass_url, label, value):
    min_waiting_time = 5
    bbox_string = "%s,%s,%s,%s" % (min_lat, min_lon, max_lat, max_lon)
    overpass_query = query_template.format(label, value, bbox_string)
    print(overpass_query)
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
