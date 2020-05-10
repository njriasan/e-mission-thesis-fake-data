import argparse
import distribution
import select_trips
import decorate_tours

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("tour_json", type=str,
        help="Name of the intermediate file for the abstract tour model")
    parser.add_argument("--mode", type=int,
        help="value to indicate which steps should run. 1 is just" +  
        " the abstract tour model, 2 is just converting the abstract" +
        " tour model to real locations and 3 is both.", default=3)
    parser.add_argument("--num_tours", type=int,
        help="Number of fake tours to generate", default=100)
    args = parser.parse_args()
    if args.mode & 1:
        nhts_info = distribution.NHTS_Data()
        synthpop_info = distribution.Synthpop_Data()
        select_trips.generate_tours(nhts_info, synthpop_info, args.tour_json, args.num_tours)
    if args.mode & 2:
        decorate_tours.decorate_tours(args.tour_json)
