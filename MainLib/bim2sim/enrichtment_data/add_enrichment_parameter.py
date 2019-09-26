import json
from bim2sim.ifc2python import elements
import inspect

elements_data = elements.__dict__


def new_enrichment_parameter(path):
    enriched_element = None
    elements_available = []
    for element in elements_data:
        if inspect.isclass(elements_data[element]):
            elements_available.append(element)
    while enriched_element is None:
        enriched_element = input("Enter the element to which you would like to add a parameter: ")
        if enriched_element not in elements_data:
            enriched_element = None
            print("The desired element to be enriched is not in the data base,"
                  " try the following elements: \n", ', '.join(elements_available))
    parameter = ""
    parameter_value = ""
    while not parameter:
        parameter = input("Enter the enrichment parameter to add: ")
    while not parameter_value:
        parameter_value = input("Enter the parameter value to add: ")
    data_update = json.load(open(path))

    if enriched_element in data_update:
        #check if exists in json
        if parameter in data_update[enriched_element]:
            if parameter_value in data_update[enriched_element][parameter]:
                print("The value for the selected parameter to add, already exists")
            else:
                data_update[enriched_element][parameter][parameter_value] = {}
                data_update[enriched_element][parameter][parameter_value]["name"] = enriched_element \
                                                                                    + "_enrichment_" + parameter_value
                for obj in elements_data[enriched_element].findables:
                    enrichment = obj
                    value = input("Enter the value for the enrichment of {} or press enter "
                                  "to add \"None\" as default ".format(enrichment))
                    if value:
                        data_update[enriched_element][parameter][parameter_value][enrichment] = value
                    else:
                        data_update[enriched_element][parameter][parameter_value][enrichment] = None
        else:
            data_update[enriched_element][parameter] = {}
            data_update[enriched_element][parameter][parameter_value] = {}
            data_update[enriched_element][parameter][parameter_value]["name"] = enriched_element\
                                                                                + "_enrichment_" + parameter_value
            for obj in elements_data[enriched_element].findables:
                enrichment = obj
                value = input("Enter the value for the enrichment of {} or press enter "
                              "to add \"None\" as default ".format(enrichment))
                if value:
                    data_update[enriched_element][parameter][parameter_value][enrichment] = value
                else:
                    data_update[enriched_element][parameter][parameter_value][enrichment] = None

    else:
        data_update[enriched_element] = {}
        data_update[enriched_element][parameter] = {}
        data_update[enriched_element][parameter][parameter_value] = {}
        data_update[enriched_element][parameter][parameter_value]["name"] = enriched_element \
                                                                            + "_enrichment_" + parameter_value
        for obj in elements_data[enriched_element].findables:
            enrichment = obj
            value = input("Enter the value for the enrichment of {} or press enter "
                          "to add \"None\" as default ".format(enrichment))
            if value:
                data_update[enriched_element][parameter][parameter_value][enrichment] = value
            else:
                data_update[enriched_element][parameter][parameter_value][enrichment] = None

    with open(path, 'w') as f:
        json.dump(data_update, f, indent=4)


path = 'D:\\dja-dco\\Projects\\MainLib\\bim2sim\\inputs\\TypeBuildingElements.json'
new_enrichment_parameter(path)
