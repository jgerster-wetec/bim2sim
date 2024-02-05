import json
from typing import Optional, Tuple

import pint
from matplotlib import pyplot as plt, image as mpimg
from matplotlib.colors import LinearSegmentedColormap, to_hex
from pathlib import Path
from PIL import Image
from RWTHColors import ColorManager
import pandas as pd
# scienceplots is marked as not used but is mandatory
import scienceplots

import bim2sim
from bim2sim.kernel.ifc_file import IfcFileClass
from bim2sim.tasks.base import ITask
from bim2sim.elements.mapping.units import ureg
from bim2sim.utilities.svg_utils import create_svg_floor_plan_plot

cm = ColorManager()
plt.style.use(['science', 'grid', 'rwth'])
plt.style.use(['science', 'no-latex'])
plt.rcParams.update({'font.size': 14})


class PlotBEPSResults(ITask):
    """Plots the results for BEPS simulations.

     This holds pre configured functions to plot the results of the BEPS
     simulations with EnergyPlus or TEASER.

     Args:
         df_finals: dict of final results where key is the building name and
          value is the dataframe holding the results for this building
         sim_results_path: path where to store the plots (currently with
          simulation results, maybe change this? #TODO
         ifc_files: bim2sim IfcFileClass holding the ifcopenshell ifc instance
     """
    reads = ('df_finals', 'sim_results_path', 'ifc_files')
    final = True

    def run(self, df_finals, sim_results_path, ifc_files):
        plugin_name = self.playground.project.plugin_cls.name
        if plugin_name == 'TEASER':
            if not self.playground.sim_settings.dymola_simulation:
                self.logger.warning(
                    "Skipping task CreateResultDF as sim_setting "
                    "'dymola_simulation' is set to False and no "
                    "simulation was performed.")
                return
        for bldg_name, df in df_finals.items():
            for ifc_file in ifc_files:
                self.plot_floor_plan_specific_heat_demand(
                    df, ifc_file, sim_results_path)
            self.plot_total_consumption(
                df, sim_results_path, bldg_name)

    def plot_total_consumption(self, df, sim_results_path, bldg_name):
        export_path = sim_results_path / bldg_name
        self.plot_demands(df, "Heating", export_path, logo=False)
        self.plot_temperatures(df, "air_temp_out", export_path, logo=False)
        self.plot_demands_bar(df, export_path, logo=False)
        self.plot_demands(df, "Cooling", export_path, logo=False)

    @staticmethod
    def plot_demands(df: pd.DataFrame, demand_type: str,
                     save_path: Optional[Path] = None,
                     logo: bool = True, total_label: bool = True,
                     window: int = 12, fig_size: Tuple[int, int] = (10, 6),
                     dpi: int = 300) -> None:
        """
        Plot demands based on provided data.

        Args:
            df (pd.DataFrame): The DataFrame containing the data.
            demand_type (str): The type of demand.
            save_path (Optional[Path], optional): The path to save the plot as
             a PDF. Defaults to None, in which case the plot will be displayed
             but not saved.
            logo (bool, optional): Whether to include a logo. Defaults to True.
            total_label (bool, optional): Whether to include total energy
             label.
             Defaults to True.
            window (int, optional): window for rolling mean value to plot
            fig_size (Tuple[int, int], optional): The size of the figure in
             inches (width, height). Defaults to (10, 6).
            dpi (int, optional): Dots per inch (resolution). Defaults to 300.

        Raises:
            ValueError: If demand_type is not supported.

        Returns:
            None

        Note:
            - The plot is styled using the 'science', 'grid', and 'rwth' styles.
            - The figure is adjusted with specified spaces around the plot.
            - The y-axis unit and rolling are adjusted for better visibility.
            - The y-axis label is determined based on demand type and converted
              to kilowatts if necessary.
            - The plot is created with appropriate colors and styles.
            - Limits, labels, titles, and grid are set for the plot.
            - Font sizes and other settings are adjusted.
            - The total energy label can be displayed in the upper right corner.
            - The logo can be added to the plot.

        Example:
            Example usage of the method.

            plot_demands(df=my_dataframe, demand_type="Cooling",
                         save_path=Path("my_plot.pdf"), logo=True,
                         total_label=True, fig_size=(12, 8), dpi=300)
        """
        save_path_demand = (save_path /
                            f"{demand_type.lower()}_demand_total.pdf")
        if demand_type == "Heating":
            # Create a new variable for y-axis with converted unit and rolling
            # Smooth the data for better visibility
            y_values = df["heat_demand_total"]
            total_energy_col = "heat_energy_total"
            color = cm.RWTHRot.p(100)
        elif demand_type == "Cooling":
            # Create a new variable for y-axis with converted unit and rolling
            y_values = df["cool_demand_total"]
            total_energy_col = "cool_energy_total"
            color = cm.RWTHBlau.p(100)
        else:
            raise ValueError(f"Demand type {demand_type} is not supported.")

        total_energy = df[total_energy_col].sum()
        label_pad = 5
        # Create a new figure with specified size
        fig = plt.figure(figsize=fig_size, dpi=dpi)

        # Define spaces next to the real plot with absolute values
        fig.subplots_adjust(left=0.05, right=0.95, top=1.0, bottom=0.0)

        # Determine if y-axis needs to be in kilowatts
        if y_values.pint.magnitude.max() > 5000:
            y_values = y_values.pint.to(ureg.kilowatt)
        plt.ylabel(
            f"{demand_type} Demand / {format(y_values.pint.units, '~')}",
            labelpad=label_pad)
        # Smooth the data for better visibility
        y_values = y_values.rolling(window=window).mean()
        # Plotting the data
        plt.plot(y_values.index,
                 y_values, color=color,
                 linewidth=1, linestyle='-')
        plt.xticks(df.index, df.index.str[0:2] + '-' + df.index.str[3:5],
                   rotation=45)
        # Limits
        plt.xlim(0, y_values.index[-1])
        plt.ylim(0, y_values.max() * 1.1)
        # Adding x label
        plt.xlabel("Time", labelpad=label_pad)
        # Add title
        plt.title(f"{demand_type} Demand", pad=20)
        # Add grid
        plt.grid(True, linestyle='--', alpha=0.6)

        # Adjust further settings
        plt.gca().spines['top'].set_visible(False)
        plt.gca().spines['right'].set_visible(False)
        plt.gca().xaxis.set_major_locator(plt.MaxNLocator(prune='both'))
        plt.gca().yaxis.set_major_locator(plt.MaxNLocator(prune='both'))

        if total_label:
            y_total = format(round(total_energy.to(ureg.kilowatt_hour), 2),
                             '~')
            plt.text(0.95, 0.95,
                     f'Total energy: '
                     f'{y_total}',
                     horizontalalignment='right',
                     verticalalignment='top',
                     transform=plt.gca().transAxes,  # Use axes coordinates
                     bbox=dict(
                         facecolor='white', alpha=0.9, edgecolor='black'))

        # add bim2sim logo to plot
        if logo:
            logo_pos = [fig_size[0] * dpi * 0.005,
                        fig_size[1] * 0.95 * dpi]
            PlotBEPSResults.add_logo(dpi, fig_size, logo_pos)

        # Show or save the plot
        PlotBEPSResults.save_or_show_plot(save_path_demand, dpi, format='pdf')

    @staticmethod
    def plot_demands_bar(df: pd.DataFrame,
                         save_path: Optional[Path] = None,
                         logo: bool = True, total_label: bool = True,
                         fig_size: Tuple[int, int] = (10, 6),
                         dpi: int = 300) -> None:
        save_path_monthly = save_path / "monthly_energy_consumption.pdf"
        label_pad = 5
        df_copy = df.copy()
        # convert to datetime index to calculate monthly sums
        df_copy.index = pd.to_datetime(
            df_copy.index, format='%m/%d-%H:%M:%S')

        # calculate differences instead of cumulated values
        df_copy['hourly_heat_energy'] = df_copy['heat_energy_total']
        df_copy['hourly_cool_energy'] = df_copy['cool_energy_total']

        # convert to kilowatthours
        df_copy['hourly_heat_energy'] = df_copy['hourly_heat_energy'].pint.to(
            ureg.kilowatthours)
        df_copy['hourly_cool_energy'] = df_copy['hourly_cool_energy'].pint.to(
            ureg.kilowatthours)

        # Calculate monthly sums
        # [:-1] to get rid of next years 00:00:00 value
        monthly_sum_heat = df_copy['hourly_heat_energy'].groupby(
            df_copy.index.to_period('M')).sum()[:-1]
        monthly_sum_cool = df_copy['hourly_cool_energy'].groupby(
            df_copy.index.to_period('M')).sum()[:-1]

        # extract months as strings
        monthly_labels = monthly_sum_heat.index.strftime('%B').tolist()

        # converts month dates to strings
        monthly_sum_heat = [q.magnitude for q in monthly_sum_heat]
        monthly_sum_cool = [q.magnitude for q in monthly_sum_cool]

        # create bar plots
        # plt.figure(figsize=(10, 6))
        fig = plt.figure(figsize=fig_size, dpi=dpi)

        # Define spaces next to the real plot with absolute values
        fig.subplots_adjust(left=0.05, right=0.95, top=1.0, bottom=0.0)

        bar_width = 0.4
        index = range(len(monthly_labels))

        plt.bar(index, monthly_sum_heat, color=cm.RWTHRot.p(100),
                width=bar_width, label='Heating')
        plt.bar([p + bar_width for p in index], monthly_sum_cool,
                color=cm.RWTHBlau.p(100), width=bar_width,
                label='Cooling')

        plt.xlabel('Month', labelpad=label_pad)
        plt.ylabel(
            f"Energy Consumption /"
            f" {format(df_copy['hourly_cool_energy'].pint.units, '~')}",
            labelpad=label_pad)
        plt.title('Monthly Sum of Energy Demands', pad=20)
        plt.xticks([p + bar_width / 2 for p in index], monthly_labels,
                   rotation=45)

        # Add grid
        plt.grid(True, linestyle='--', alpha=0.6)

        # Adjust further settings
        plt.gca().spines['top'].set_visible(False)
        plt.gca().spines['right'].set_visible(False)

        plt.legend(frameon=True, loc='upper right', edgecolor='black')
        if logo:
            logo_pos = [fig_size[0] * dpi * 0.005,
                        fig_size[1] * 0.95 * dpi]
            PlotBEPSResults.add_logo(dpi, fig_size, logo_pos)
        # Show or save the plot
        PlotBEPSResults.save_or_show_plot(save_path_monthly, dpi, format='pdf')

    @staticmethod
    def save_or_show_plot(save_path, dpi, format='pdf'):
        if save_path:
            plt.ioff()
            plt.savefig(save_path, dpi=dpi, format=format)
        else:
            plt.show()

    def plot_floor_plan_specific_heat_demand(
            self, df: pd.DataFrame,
            ifc_file: IfcFileClass,
            sim_results_path: Path,
            min_area: pint.Unit = 2 * ureg.m ** 2
            # tz_mapping: dict
    ):
        """Plot a floor plan colorized based on specific heat demand.

        The plot colors each room based on the specific heat demand, while blue
        is the color for minimum heat demand and red for maximum.

        Args:
            df (DataFrame): The DataFrame containing sim result data.
            ifc_file (IfcFileClass): bim2sim IfcFileClass object.
            sim_results_path (Path): Path to store simulation results.
            tz_mapping: dict with mapping between IFC space GUIDs and
            rooms/zones
            min_area: minimal area to take space into account for plotting
        """

        # create the dict with all space guids and resulting values in the
        # first run
        # TODO this is currently not working for aggregated zones.
        svg_adjust_dict = {}
        # TODO get from task

        for col_name, col_data in df.items():
            # TODO use only tz_mapping.json for this do be able to use this
            #  without performing all tasks before
            if 'heat_demand_rooms_' in col_name and 'total' not in col_name:
                space_guid = col_name.split('heat_demand_rooms_')[-1]
                storey_guid = None
                space_area = None
                # TODO clean up when EP has tz_mapping.json
                try:
                    storey_guid = \
                        self.playground.state['tz_elements'][space_guid].storeys[
                            0].guid
                    space_area = self.playground.state['tz_elements'][
                        space_guid].net_area
                except:
                    for tz, tz_values in self.playground.state['tz_mapping'].items():
                        if space_guid in tz_values['space_guids']:
                            storey_guid = tz_values['storeys'][0]
                            space_area = tz_values['area'] * ureg.m ** 2
                    if not storey_guid or not space_area:
                        self.logger.warning(
                            f"For space with guid {space_guid} no"
                            f" fitting storey could be found. This space will be "
                            f"ignored for floor plan plots. ")
                        continue
                    if space_area < min_area:
                        self.logger.warning(
                            f"Space with guid {space_guid} is smaller than "
                            f"the minimal threhold area of {min_area}. The "
                            f"space is ignored for floorplan plotting. ")
                        continue

                svg_adjust_dict.setdefault(storey_guid, {}).setdefault(
                    "space_data", {})
                val = col_data.max() / space_area
                # update minimal and maximal value to get a useful color scale
                svg_adjust_dict[storey_guid]["storey_min_value"] = min(
                    val,  svg_adjust_dict[storey_guid]["storey_min_value"]) \
                    if "storey_min_value" in svg_adjust_dict[storey_guid] \
                    else val
                svg_adjust_dict[storey_guid]["storey_max_value"] = max(
                    val, svg_adjust_dict[storey_guid]["storey_max_value"]) \
                    if "storey_max_value" in svg_adjust_dict[storey_guid] \
                    else val
                svg_adjust_dict[storey_guid]["space_data"][space_guid] = {
                    'text': val}
        # create the color mapping, this needs to be done after the value
        # extraction to have all values for all spaces
        for storey_guid, storey_data in svg_adjust_dict.items():
            for space_guid, space_data in storey_data["space_data"].items():
                storey_min = storey_data["storey_min_value"].m.round(1)
                storey_max = storey_data["storey_max_value"].m.round(1)
                value = space_data['text']
                if storey_min == storey_max:
                    storey_min -= 1
                    storey_max += 1
                    space_data['color'] = "red"
                    cmap = self.create_color_mapping(
                        storey_min,
                        storey_max,
                        sim_results_path,
                        storey_guid,
                        colors=['red', 'red', 'red']
                        )
                else:
                    cmap = self.create_color_mapping(
                        storey_min,
                        storey_max,
                        sim_results_path,
                        storey_guid)
                space_data['color'] = (
                    self.get_color_for_value(
                        value.m, storey_min, storey_max, cmap))
                unit = value.u
                # reformat units
                if str(unit) == ("watt / meter ** 2") :
                    unit = str(unit).replace(
                        "watt ", "W").replace(
                        " ** 2", "²").replace(
                        " meter", "m")
                text_str = str(value.m.round(1)) + " " + unit
                space_data['text'] = text_str
        # delete storey_min_value and storey_max_value as no longer needed
        for entry in svg_adjust_dict.values():
            if 'storey_max_value' in entry:
                entry.pop('storey_max_value')
            if 'storey_min_value' in entry:
                entry.pop('storey_min_value')
        # TODO merge the create color_mapping.svg into each of the created
        #  *_modified svg plots.
        with open("svg_adjust_dict.json", 'w') as file:
            json.dump(svg_adjust_dict, file)
        create_svg_floor_plan_plot(ifc_file, sim_results_path, svg_adjust_dict)

    @staticmethod
    def create_color_mapping(min_val, max_val, sim_results_path, storey_guid,
                             colors=['blue', 'purple', 'red']):
        """Create a colormap from blue to red and save it as an SVG file.

        Args:
          min_val (float): Minimum value for the colormap range.
          max_val (float): Maximum value for the colormap range.

        Returns:
          LinearSegmentedColormap: Created colormap object.
        """
        # Create a colormap from blue to green to red
        cmap = LinearSegmentedColormap.from_list('custom', colors)

        # Create a normalization function to map values between 0 and 1
        normalize = plt.Normalize(vmin=min_val, vmax=max_val)

        # Create a ScalarMappable to use the colormap
        sm = plt.cm.ScalarMappable(cmap=cmap, norm=normalize)
        sm.set_array([])

        # Create a color bar to display the colormap
        fig, ax = plt.subplots(figsize=(0.5, 6))
        fig.subplots_adjust(bottom=0.5)
        cbar = plt.colorbar(sm, orientation='vertical', cax=ax)
        med_val = round(min_val + max_val / 2, 1)
        cbar.set_ticks([min_val, med_val, max_val])
        cbar.set_ticklabels(
            [f'{min_val}', f'{med_val}', f'{max_val}'])

        # Save the figure as an SVG file
        plt.savefig(sim_results_path / f'color_mapping_{storey_guid}.svg'
                    , format='svg')
        plt.close(fig)
        return cmap

    @staticmethod
    def get_color_for_value(value, min_val, max_val, cmap):
        """Get the color corresponding to a value within the given colormap.

        Args:
          value (float): Value for which the corresponding color is requested.
          min_val (float): Minimum value of the colormap range.
          max_val (float): Maximum value of the colormap range.
          cmap (LinearSegmentedColormap): Colormap object.

        Returns:
          str: Hexadecimal representation of the color corresponding to the
           value.
        """
        # Normalize the value between 0 and 1
        normalized_value = (value - min_val) / (max_val - min_val)

        # Get the color corresponding to the normalized value
        color = cmap(normalized_value)

        return to_hex(color, keep_alpha=False)


    @staticmethod
    def plot_temperatures(df: pd.DataFrame, data: str,
                     save_path: Optional[Path] = None,
                     logo: bool = True,
                     window: int = 12, fig_size: Tuple[int, int] = (10, 6),
                     dpi: int = 300) -> None:
        """
        Plot temperatures.

        """
        save_path_demand = (save_path /
                            f"{data.lower()}.pdf")
        y_values = df[data]
        color = cm.RWTHBlau.p(100)

        label_pad = 5
        # Create a new figure with specified size
        fig = plt.figure(figsize=fig_size, dpi=dpi)

        # Define spaces next to the real plot with absolute values
        fig.subplots_adjust(left=0.05, right=0.95, top=1.0, bottom=0.0)

        # Determine if y-axis needs to be in kilowatts
        y_values = y_values.pint.to(ureg.degree_Celsius)
        plt.ylabel(
            f"{data}  / {format(y_values.pint.units, '~')}",
            labelpad=label_pad)
        # Smooth the data for better visibility
        # y_values = y_values.rolling(window=window).mean()
        # take values only for plot
        y_values = y_values.pint.magnitude

        # Plotting the data
        plt.plot(y_values.index,
                 y_values, color=color,
                 linewidth=1, linestyle='-')
        plt.xticks(df.index, df.index.str[0:2] + '-' + df.index.str[3:5],
                   rotation=45)
        # Limits
        plt.xlim(0, y_values.index[-1])
        plt.ylim(0, y_values.max() * 1.1)
        # Adding x label
        plt.xlabel("Time", labelpad=label_pad)
        # Add title
        plt.title(f"{data}", pad=20)
        # Add grid
        plt.grid(True, linestyle='--', alpha=0.6)

        # Adjust further settings
        plt.gca().spines['top'].set_visible(False)
        plt.gca().spines['right'].set_visible(False)
        plt.gca().xaxis.set_major_locator(plt.MaxNLocator(prune='both'))
        plt.gca().yaxis.set_major_locator(plt.MaxNLocator(prune='both'))

        # add bim2sim logo to plot
        if logo:
            logo_pos = [fig_size[0] * dpi * 0.005,
                        fig_size[1] * 0.95 * dpi]
            PlotBEPSResults.add_logo(dpi, fig_size, logo_pos)

        # Show or save the plot
        PlotBEPSResults.save_or_show_plot(save_path_demand, dpi, format='pdf')
        # TODO
        pass

    def plot_thermal_discomfort(self):
        # TODO
        pass
    @staticmethod
    def add_logo(dpi, fig_size, logo_pos):
        # TODO: this is not completed yet
        """Adds the logo to the existing plot."""
        # Load the logo
        logo_path = Path(bim2sim.__file__).parent.parent \
                    / "docs/source/img/static/b2s_logo_only.png"
        # todo get rid of PIL package
        logo = Image.open(logo_path)
        logo.thumbnail((fig_size[0] * dpi / 10, fig_size[0] * dpi / 10))
        plt.figimage(logo, xo=logo_pos[0], yo=logo_pos[1], alpha=1)
        # TOdo resizing is not well done yet, this is an option but not finished:
        # # Calculate the desired scale factor
        # scale_factor = 0.01  # Adjust as needed
        #
        # # Load the logo
        # logo = plt.imread(logo_path)
        #
        # # Create an OffsetImage
        # img = OffsetImage(logo, zoom=scale_factor)
        #
        # # Set the position of the image
        # ab = AnnotationBbox(img, (0.95, -0.1), frameon=False,
        #                     xycoords='axes fraction', boxcoords="axes fraction")
        # plt.gca().add_artist(ab)


    def base_plot_design(self):

        plt.gca().spines['top'].set_visible(False)
        plt.gca().spines['right'].set_visible(False)
        plt.grid(True, linestyle='--', alpha=0.6)
