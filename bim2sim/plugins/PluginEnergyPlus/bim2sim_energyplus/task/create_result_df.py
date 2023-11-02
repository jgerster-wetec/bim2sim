import json

import pandas as pd
from pint_pandas import PintArray

from bim2sim.plugins.PluginEnergyPlus.bim2sim_energyplus.utils import \
    PostprocessingUtils
from bim2sim.tasks.base import ITask
from bim2sim.elements.mapping.units import ureg


bim2sim_energyplus_mapping_base = {
    "NOT_AVAILABLE": "heat_demand_total",
    "SPACEGUID IDEAL LOADS AIR SYSTEM:Zone Ideal Loads Zone Total Heating "
    "Rate [W](Hourly)": "heat_demand_rooms",
    "NOT_AVAILABLE": "cooling_demand_total",
    "SPACEGUID IDEAL LOADS AIR SYSTEM:Zone Ideal Loads Zone Total Cooling "
    "Rate [W](Hourly)": "cooling_demand_rooms",
    "Heating:EnergyTransfer [J](Hourly)": "heat_energy_total",
    "Cooling:EnergyTransfer [J](Hourly) ": "cool_energy_total",
    "SPACEGUID:Zone Total Internal Total Heating Energy [J](Hourly)":
        "heat_energy_rooms",
    "SPACEGUID:Zone Total Internal Total Cooling Energy [J](Hourly)":
        "cool_energy_rooms",
    "Environment:Site Outdoor Air Drybulb Temperature [C](Hourly)":
        "air_temp_out",
    "SPACEGUID:Zone Operative Temperature [C](Hourly)":
        "operative_temp_rooms",
    "SPACEGUID:Zone Mean Air Temperature [C](Hourly)": "air_temp_rooms",
}

unit_mapping = {
    "heat_demand": ureg.watt,
    "cooling_demand": ureg.watt,
    "heat_energy": ureg.joule,
    "cool_energy": ureg.joule,
    "operative_temp": ureg.degree_Celsius,
    "air_temp": ureg.degree_Celsius,
}


class CreateResultDF(ITask):
    """This ITask creates a result dataframe for EnergyPlus BEPS simulations.

    Args:
        idf: eppy idf
    Returns:
        df_final: final dataframe that holds only relevant data, with generic
        `bim2sim` names and index in form of MM/DD-hh:mm:ss
    """
    reads = ('idf',)
    touches = ('df_finals',)

    def run(self, idf):
        # ToDO handle multiple buildings/ifcs #35
        df_finals = {}
        raw_csv_path = self.paths.export / 'EP-results/eplusout.csv'
        zone_dict_path = self.paths.export / 'zone_dict.json'
        with open (zone_dict_path) as j:
            zone_dict =json.load(j)

        df_original = PostprocessingUtils.read_csv_and_format_datetime(
            raw_csv_path)
        df_final = self.format_dataframe(df_original, zone_dict)
        df_finals[self.prj_name] = df_final
        return df_finals,

    def format_dataframe(
            self, df_original: pd.DataFrame, zone_dict: dict) -> pd.DataFrame:
        """Formats the dataframe to generic bim2sim output structure.

        This function:
         - adds the space GUIDs to the results
         - selects only the selected simulation outputs from the result

        Args:
            df_original: original dataframe directly taken from simulation
            zone_dict: dictionary with all zones, in format {GUID : Zone Usage}

        Returns:
            df_final: converted dataframe in `bim2sim` result structure
        """
        bim2sim_energyplus_mapping = self.map_zonal_results(
            bim2sim_energyplus_mapping_base, zone_dict)
        # select only relevant columns
        short_list = \
            list(bim2sim_energyplus_mapping.keys())
        short_list.remove('NOT_AVAILABLE')
        df_final = df_original[df_original.columns[
            df_original.columns.isin(short_list)]].rename(
            columns=bim2sim_energyplus_mapping)

        # convert negative cooling demands and energies to absolute values
        df_final = df_final.abs()
        heat_demand_columns = df_final.filter(like='heat_demand')
        df_final['heat_demand_total'] = heat_demand_columns.sum(axis=1)
        # handle units
        for column in df_final:
            for key, unit in unit_mapping.items():
                if key in column:
                    df_final[column] = PintArray(df_final[column], unit)

        return df_final

    def select_wanted_results(self):
        """Selected only the wanted outputs based on sim_setting sim_results"""
        bim2sim_energyplus_mapping = bim2sim_energyplus_mapping_base.copy()
        for key, value in bim2sim_energyplus_mapping_base.items():
            if value not in self.playground.sim_settings.sim_results:
                del bim2sim_energyplus_mapping[key]
        return bim2sim_energyplus_mapping

    @staticmethod
    def map_zonal_results(bim2sim_energyplus_mapping_base, zone_dict):
        """Add zone/space guids/names to mapping dict.

        EnergyPlus outputs the results referencing to the IFC-GlobalId. This
        function adds the real zone/space guids or
        aggregation names to the dict for easy readable results.
        Rooms are mapped with their space GUID, aggregated zones are mapped
        with their zone name. The mapping between zones and rooms can be taken
        from tz_mapping.json file with can be found in export directory.

        Args:
            bim2sim_energyplus_mapping_base: Holds the mapping between
             simulation outputs and generic `bim2sim` output names.
            zone_dict: dictionary with all zones, in format {GUID : Zone Usage}

        Returns:
            dict: A mapping between simulation results and space guids, with
             appropriate adjustments for aggregated zones.

        """
        bim2sim_energyplus_mapping = {}
        space_guid_list = list(zone_dict.keys())
        for key, value in bim2sim_energyplus_mapping_base.items():
            # add entry for each room/zone
            if "SPACEGUID" in key:
                for i, space_guid in enumerate(space_guid_list):
                    new_key = key.replace("SPACEGUID", space_guid.upper())
                    # todo: according to #497, names should keep a _zone_ flag
                    new_value = value.replace("rooms", space_guid.upper())
                    bim2sim_energyplus_mapping[new_key] = new_value
            else:
                bim2sim_energyplus_mapping[key] = value
        return bim2sim_energyplus_mapping

    @staticmethod
    def convert_time_index(df):
        """This converts the index of the result df to "days hh:mm:ss format"""
        # Convert the index to a timedelta object
        df.index = pd.to_timedelta(df.index, unit='s')
        # handle leap years
        if len(df.index) > 8761:
            year = 2020
        else:
            year = 2021
        # Add the specified year to the date
        df.index = pd.to_datetime(
            df.index.total_seconds(), unit='s', origin=f'{year}-01-01')

        # Format the date to [yyyy/mm/dd-hh:mm:ss]
        df.index = df.index.strftime('%y/%m/%d-%H:%M:%S')
        return df

