import pandas as pd
import numpy as np
import scipy.stats as stats

class NHTS_Data:

    def __init__(self):
        # Find the paths to all the nhts provided data
        datafolder = "nhts-data/"
        perpub_file = datafolder + "perpub.csv"
        trippub_file = datafolder + "trippub.csv"
        # Load all of the raw data
        perpub_df = pd.read_csv(perpub_file)
        trippub_df = pd.read_csv(trippub_file)

        # Filter perpub to only include the data possibly relevant to our parameters
        # HOUSEID = household label
        # PERSONID = person number for household
        # GT1JBLWK = More than 1 job. 1 = yes, 2 = No, others not acquired or not relevant
        # WRK_HOME = Work from home. 1 = yes, 2 = No, others not acquired or not relevant
        # WRKTRANS = Transportation mode to work: 1 = Walk, 3 = Car, 4 = SUV, 5 = Van, 6 = Pickup Truck. Others can't be represented
        # NWALKTRP = Count of walk trips on travel data
        # TIMETOWK = time to work in minutes
        # NOCONG = time to work in minutes with no traffic
        # WRKTIME = work arrival time
        # SCHTRN1 = Mode to school
        # SCHTRN2 = Mode from school
        # FRSTHM17 = Travel began at home location
        # CNTTDTR = Count of person trips on travel day
        # GCDWORK = Minimum geodesic distance between home
        # TRAVDAY = Travel day of the week. 1 = Sunday, 7 = Saturday
        # SCHTYP = Student status. 1 = Public/private school, 2 = Home schooled, 3 = Not in school
        # HHSIZE = Household size
        # R_AGE_IMP = Person age
        # WORKER = Are tehy a worker? 1 = Yes, 2 = No

        kept_columns = ["HOUSEID", "PERSONID", "R_AGE_IMP", "WORKER", "TRAVDAY"]
        perpub_df_reduced = perpub_df[kept_columns]

        # Filter trippub to only include the data possibly relevant to our parameters
        # HOUSEID = household label
        # PERSONID = person number for household
        # TDTRPNUM = Counter for each trip a person takes
        # STRTTIME = start time for a trip
        # ENDTIME = end time for a trip
        # TRVLCMIN = trip duration in minutes
        # TRPMILES = trip distance in miles
        # TRPTRANS = trip mode. We care about 1 = walk, 3 = car, 4 = SUV, 5 = Van, 6 = pickup truck. We will group 3-6 together
        # WHYFROM = trip origin purpose. See https://nhts.ornl.gov/assets/codebook_v1.1.pdf for encoding.
        # WHYTO trip destination purpose
        # LOOP_TRIP = Are the start and end locations the same? 1 = Yes, 2 = No
        # DWELTIME = Time at destination in minutes
        kept_columns = ["HOUSEID", "PERSONID", "TDTRPNUM", "TRPMILES", "TRPTRANS", "WHYFROM", "LOOP_TRIP", "DWELTIME", "WHYTO", "STRTTIME"]
        trippub_df_reduced = trippub_df[kept_columns]

        # Merge together the data
        df_total = pd.merge(perpub_df_reduced, trippub_df_reduced, on=["HOUSEID","PERSONID"])
        df_total["USERID"] = df_total["HOUSEID"].astype(str) + df_total["PERSONID"].astype(str)

        # Filter our any respondants under the age of 18
        df_filter = df_total[df_total.R_AGE_IMP >= 18]
        df_filter = df_filter[df_filter.WORKER != -9]
        df_filter = df_filter[df_filter.WORKER != -1]

        # First select only the first trip
        from_values = [1, 11, 3, 13]
        walk_trips = [1]
        bike_trips = [2]
        car_trips = [3, 4, 5, 6, 17, 18]
        transit_trips = [11, 12, 13, 14, 15, 16]
        trip_numbers = walk_trips + bike_trips + car_trips + transit_trips
        df_filter = df_filter[df_filter.WHYFROM.isin(from_values)]
        df_filter = df_filter[df_filter.WHYTO.isin(from_values)]
        df_filter = df_filter[df_filter.TRPTRANS.isin(trip_numbers)]
        df_filter = df_filter[df_filter.TRAVDAY >= 2]
        df_filter = df_filter[df_filter.TRAVDAY <= 6]

        # Generate information about each type of trip by grouping first by user type
        worker_data = df_filter[df_filter.WORKER == 1]
        home = 1
        worker_data = worker_data[(worker_data.WHYFROM != home) | (worker_data.WHYTO != home)]
        work = 3
        worker_data = worker_data[(worker_data.WHYFROM != work) | (worker_data.WHYTO != work)]

        
        self._endpoint_map = {"Home" : 1, "Work" : 3, "Buy Goods" : 11, "Buy Meals" : 13}
        self._flipped_endpoint_map = {1 : "Home", 3 : "Work", 11 : "Buy Goods", 13 : "Buy Meals"}
        self._mode_map = {"Walk" : 0, "Bike" : 1, "Car" : 2, "Transit" : 3}
        self._flipped_mode_map = {0 : "Walk", 1 : "Bike", 2 : "Car", 3 : "Transit"}

        # Remove the impact of round trips
        # Reset the indices
        worker_data.reset_index(inplace=True, drop=True)
        spare_rows = []
        for i in range(len(worker_data.index)):
            if (worker_data.at[i, "LOOP_TRIP"] == 1):
                worker_data.at[i, "TRPMILES"] = worker_data.at[i, "TRPMILES"] / 2.0
                spare_row = worker_data.iloc[i,:].copy(deep=True)
                spare_row["WHYTO"], spare_row["WHYFROM"]  = spare_row["WHYFROM"], spare_row["WHYTO"]
                spare_rows.append(spare_row)
        for row in spare_rows:
            worker_data = worker_data.append(row)

        # Generate the Markov Model
        data = worker_data.groupby(["WHYFROM", "WHYTO"]).size()
        vals = data.iteritems()
        sums = {}
        totals = {}
        for val in vals:
            directions = val[0]
            count = val[1]
            from_i, to_i = directions
            if from_i not in totals:
                totals[from_i] = dict()
            if from_i not in sums:
                sums[from_i] = 0
            totals[from_i][to_i] = count
            sums[from_i] += count
        for key, val in totals.items():
            for second_key, contents in val.items():
                totals[key][second_key] = contents / sums[key]
        # Add the Markov model as an instance variable
        self._next_dists = dict()
        for mode_name, mode_value in self._endpoint_map.items():
            names = []
            probs = []
            dests = totals[mode_value]
            for dest_value, dest_prob in dests.items():
                names.append(dest_value)
                probs.append(dest_prob)
            error = 1.0 - sum(probs)
            probs[-1] += error
            self._next_dists[mode_name] = stats.rv_discrete(
                    values=(np.array(names), np.array(probs)))



        worker_data.reset_index(inplace=True, drop=True)
        data = worker_data.groupby(["WHYFROM", "WHYTO","TRPTRANS"]).size()
        vals = data.iteritems()

        sums = {}
        totals = {}
        for val in vals:
            directions = val[0][0:2]
            trans_mode = val[0][2]
            count = val[1]
            if directions not in totals:
                totals[directions] = dict()
            if directions not in sums:
                sums[directions] = 0
            if trans_mode in walk_trips:
                trans_mode = "Walk"
            elif trans_mode in bike_trips:
                trans_mode = "Bike"
            elif trans_mode in car_trips:
                trans_mode = "Car"
            else:
                trans_mode = "Transit"
            if trans_mode not in totals[directions]:
                totals[directions][trans_mode] = 0
            totals[directions][trans_mode] += count
            sums[directions] += count
        for key, val in totals.items():
            for second_key, contents in val.items():
                totals[key][second_key] = contents / sums[key]
        # Add instance variable for the distribution of selecting a mode of transportation
        self._mode_distributions = dict()
        for endpoint_vals, modes in totals.items():
            names = []
            probs = []
            for mode_name, mode_prob in modes.items():
                names.append(self._mode_map[mode_name])
                probs.append(mode_prob)
            error = 1.0 - sum(probs)
            probs[0] += error
            from_name = self._flipped_endpoint_map[endpoint_vals[0]]
            to_name = self._flipped_endpoint_map[endpoint_vals[1]]
            self._mode_distributions[(from_name, to_name)] = stats.rv_discrete(
                    values=(np.array(names), np.array(probs)))


        # Separate by mode of transportation
        worker_data = {"Walk" : worker_data[worker_data.TRPTRANS.isin(walk_trips)],
                "Car" : worker_data[worker_data.TRPTRANS.isin(car_trips)],
                "Bike" : worker_data[worker_data.TRPTRANS.isin(bike_trips)],
                "Transit" : worker_data[worker_data.TRPTRANS.isin(transit_trips)]}

        # Generate the distributions that were fitted based on empirical data


        # Add names
        dist_order = [("Home", "Work"), ("Home", "Buy Goods"), 
                ("Home", "Buy Meals"), ("Work", "Buy Goods"), 
                ("Work", "Buy Meals"), ("Buy Goods", "Buy Goods"), 
                ("Buy Goods", "Buy Meals"), ("Buy Meals", "Buy Goods"), 
                ("Buy Meals", "Buy Meals")]

        # Should encode better in the future
        self._dist_map = {("Home", "Work") : 0, ("Home", "Buy Goods") : 1, 
                ("Home", "Buy Meals") : 2, ("Work", "Buy Goods") : 3,
                ("Work", "Buy Meals") : 4, ("Buy Goods", "Buy Goods") : 5,
                ("Buy Goods", "Buy Meals") : 6, ("Buy Meals", "Buy Goods") : 7,
                ("Buy Meals", "Buy Meals") : 8}

        # first create bool vectors for if exponpow
        self._is_exponpow = {"Walk" : [True, False, False, True, False, False, 
            False, False, False], "Bike" : [False, False, False, False, False, 
            False, False, False, False], "Car" : [False, False, False, False, 
            False, True, True, True, True], "Transit" : [False, False, False, 
            False, False, False, False, False, False]}

        # Next generate the distribution
        self._transport_dist = dict()
        for key, values in self._is_exponpow.items():
            dists = []
            dataset = worker_data[key]
            for i, is_exponpow in enumerate(values):
                endpoints = dist_order[i]
                datacol = dataset[(dataset.WHYFROM == self._endpoint_map[endpoints[0]]) &
                        (dataset.WHYTO == self._endpoint_map[endpoints[1]])].TRPMILES
                if is_exponpow:
                    dists.append(self.generate_exponpow_dist(datacol))
                else:
                    dists.append(self.generate_expon_dist(datacol))
            self._transport_dist[key] = dists

    def generate_expon_dist(self, datacol):
        loc, scale = stats.expon.fit(datacol)
        if loc < 0.0001:
            loc = 0.0001
        return (loc, scale)


    def generate_exponpow_dist(self, datacol):
        b, loc, scale = stats.exponpow.fit(datacol)
        if loc < 0.0001:
            loc = 0.0001
        return (b, loc, scale)

    def sample_distance(self, from_endpoint, to_endpoint, mode):
        index = self._dist_map[(from_endpoint, to_endpoint)]
        dist = self._transport_dist[mode][index]
        is_exponpow = self._is_exponpow[mode][index]
        if is_exponpow:
            return stats.exponpow.rvs(b=dist[0], loc=dist[1], scale=dist[2])
        else:
            return stats.expon(loc=dist[0], scale=dist[1])

    def sample_destination(self, from_endpoint):
        dist = self._next_dists[from_endpoint]
        to_value = dist.rv()
        return self._flipped_endpoint_map[to_value]

    def sample_mode(self, from_endpoint, to_endpoint):
        dist = self._mode_distributions[(from_endpoint, to_endpoint)]
        mode_value = dist.rv()
        return self._flipped_mode_map[mode_value]
