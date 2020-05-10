import json

mode_map = {-9 : "Car", -8 : "Car", -7 : "Car", 1 : "Walk", 2 : "Bike", 
        3 : "Car", 4 : "Car", 5 : "Car", 6 : "Car", 7 : "Car", 8 : "Car",
        9 : "Car", 10 : "Transit", 11 : "Transit", 12 : "Transit",
        13 : "Transit", 14 : "Transit", 15 : "Transit", 16 : "Transit",
        17 : "Car", 18 : "Car", 97 : "Car"}

def generate_tours(nhts_info, synthpop_info, tour_json, num_tours):
    tours = []
    for i in range(num_tours):
        tours.append({"Tour {}".format(i): create_tour(nhts_info, synthpop_info)})
    with open(tour_json, "w") as f:
        f.write(json.dumps(tours, indent=4))


def create_tour(nhts_info, synthpop_info):
    tour_info = dict()
    steps = []
    is_student, is_worker = synthpop_info.sample_user()
    tour = nhts_info.sample_tour(is_student, is_worker)
    for i in range(len(tour.index)):
        trip_dict = dict()
        trip_dict['dist'] = float(tour.at[i, "TRPMILES"])
        trip_dict['dest_encoding'] = int(tour.at[i, "WHYTO"])

        trip_dict['mode'] = mode_map[tour.at[i, "TRPTRANS"]]
        time_info = str(tour.at[i, "STRTTIME"])
        trip_dict['start time'] = "{}:{}".format(time_info[:-2], time_info[-2:])
        time_info = str(tour.at[i, "ENDTIME"])
        trip_dict['end time'] = "{}:{}".format(time_info[:-2], time_info[-2:])
        steps.append(trip_dict)
    tour_info['plan'] = steps
    tour_info['student'] = is_student
    tour_info['employed'] = is_worker
    return tour_info

