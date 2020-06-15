import json

mode_map = {-9 : "Car", -8 : "Car", -7 : "Car", 1 : "Walk", 2 : "Bicycle", 
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
        f.flush()


def create_tour(nhts_info, synthpop_info):
    tour_info = dict()
    steps = []
    is_student, is_worker = synthpop_info.sample_user()
    tour = nhts_info.sample_tour(is_student, is_worker)
    for i in range(len(tour.index)):
        distance = float(tour.at[i, "TRPMILES"])
        mode = mode_map[tour.at[i, "TRPTRANS"]]
        # If distance is too large break a trip down into 2
        # 1 that doesn't do a query and one that does
        # Then omit the none query from the output
        # to avoid complex calculations
        if distance > 50.0:
            temp_dict = dict()
            temp_dict['dist'] = distance
            distance = 0.5
            temp_dict['mode'] = mode
            temp_dict['dest_encoding'] = 97
            temp_dict['temp'] = True
            steps.append(temp_dict)

        trip_dict = dict()
        trip_dict['dist'] = distance
        trip_dict['dest_encoding'] = int(tour.at[i, "WHYTO"])
        trip_dict['mode'] = mode
        time_info = str(tour.at[i, "STRTTIME"])
        trip_dict['start time'] = "{}:{}".format(time_info[:-2], time_info[-2:])
        time_info = str(tour.at[i, "ENDTIME"])
        trip_dict['end time'] = "{}:{}".format(time_info[:-2], time_info[-2:])
        trip_dict['temp'] = False
        steps.append(trip_dict)
    tour_info['plan'] = steps
    tour_info['student'] = is_student
    tour_info['employed'] = is_worker
    return tour_info

