import json

def generate_tours(nhts_info, tour_json, num_tours):
    tours = []
    for i in range(num_tours):
        tours.append({"Tour {}".format(i): create_tour(nhts_info)})
    with open(tour_json, "w") as f:
        f.write(json.dumps(tours, indent=4))


def create_tour(nhts_info):
    end = "Home"
    prevValue = "Home"
    nextValue = None
    steps = []
    while nextValue != end:
        nextValue = nhts_info.sample_desintation(prevValue)
        mode = nhts_info.sample_mode(prevValue, nextValue)
        if nextValue == "Home":
            distance = "Home Distance"
        elif nextValue == "Work":
            distance = "Work Distance"
        else:
            distance = nhts_info.sample_distance(prevValue, nextValue, mode)
        step = {"Location" : nextValue, "Mode" : mode, "Distance" : distance}
        steps.append(step)
        prevValue = nextValue
    return steps

