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

        df_total = pd.merge(perpub_df_reduced, trippub_df_reduced, on=["HOUSEID","PERSONID"])
        df_total["USERID"] = df_total["HOUSEID"].astype(str) + df_total["PERSONID"].astype(str)

        # Find IDS to remove with unsupported trips
        untracked_modes = [19, 20]
        illicit_trips = df_total[df_total.TRPTRANS.isin(untracked_modes)]
        ids_to_remove = illicit_trips.USERID.unique()

        # Get a list of all people who don't start at home
        not_home_df = df_total.sort_values('TDTRPNUM', ascending=True).drop_duplicates(['USERID'])
        not_home_ids = not_home_df[not_home_df.WHYFROM != 1]
        ids_to_remove = np.concatenate((ids_to_remove, not_home_ids.USERID.unique()), axis=None)

        # Get a list of all people who don't end at home and don't have a roundtrip
        df_total = df_total[~df_total.USERID.isin(ids_to_remove)]
        not_home_df = df_total.sort_values('TDTRPNUM', ascending=False).drop_duplicates(['USERID'])
        not_home_ids = not_home_df[(not_home_df.WHYTO != 1) & ~((not_home_df.WHYFROM == 1) & (not_home_df.LOOP_TRIP == 1))]
        ids_to_remove = np.concatenate((ids_to_remove, not_home_ids.USERID.unique()), axis=None)

        # Remove the ids
        df_total = df_total[~df_total.USERID.isin(ids_to_remove)]

        # Convert round trips to 2 trips
        df_total.reset_index(inplace=True, drop=True)
        spare_rows = []
        for i in range(len(df_total.index)):
            if (df_total.at[i, "LOOP_TRIP"] == 1):
                df_total.at[i, "TRPMILES"] = df_total.at[i, "TRPMILES"] / 2.0
                spare_row = df_total.iloc[i,:].copy(deep=True)
                # Swap from and to
                spare_row["WHYTO"], spare_row["WHYFROM"]  = spare_row["WHYFROM"], spare_row["WHYTO"]
                # Increase the trip number
                spare_row['TDTRPNUM'] = spare_row['TDTRPNUM'] + 0.5
                spare_rows.append(spare_row)
        self.nhts_data = df_total.append(spare_rows, ignore_index=True)

    # TODO add a way to filter
    def sample_tour(self):
        user_id = self.sample_user()
        user_df = self.nhts_data[self.nhts_data.USERID == user_id].sort_values('TDTRPNUM', ascending=True).reset_index(drop=True)
        return user_df

    # TODO add a way to filter
    def sample_user(self):
        user_ids = self.nhts_data.USERID.unique()
        upper_bound = user_ids.shape[0]
        return user_ids[np.random.randint(upper_bound)]

