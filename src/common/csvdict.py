import csv

def import_csv_to_dict(filename):
    """Imports a csv to a dictionary

    Imports a csv in the format produced by ``MainWindow.export_dict_to_csv``

    Parameters
    ----------
    filename : str
        File for import, include path name.

    Returns
    -------
    dict
        Contents of filename as a dictionary.
    """        
    dictionary = {}
    with open(filename, 'r', newline='') as csvfile:
        csv_reader = csv.reader(csvfile)
        for row in csv_reader:
            key = row[0]
            values = row[1:]
            dictionary[key] = values
    return dictionary

def export_dict_to_csv(dictionary, filename):
    """Exports a dictionary to csv file

    Explorts a simple dictionary that includes a set of keyword associated with lists to a csv.
    The first column are the dictionary keys and all subsequent columns are values associated with the key.

    Parameters
    ----------
    dictionary : dict
        Dictionary to save.
    filename : str
        Name of file used to save dictionary.  Include path in the filename.

    Raises
    ------
    ValueError dictionary must be of type dict.
    """        
    if not isinstance(dictionary, dict):
        raise ValueError("Input must be a dictionary.")

    with open(filename, 'w', newline='') as csvfile:
        csv_writer = csv.writer(csvfile)
        for key, values in dictionary.items():
            csv_writer.writerow([key] + values)

def export_filtered_dict_to_csv(dictionary, filename, filter_key, filter_val, selected_keys=None):
    """
    Exports specific items from a dictionary to a CSV file based on conditions.

    Parameters
    ----------
    dictionary : dict
        The dictionary to filter and export.
    filename : str
        Name of file used to save dictionary.  Include path in the filename.
    filter_key : any
        Key used to filter dictionary
    filter_val : any
        Value associated with key to select items to add to the csv
    selected_keys : list, optional
        List of keys to include in the export, by default ``None``

    Raises
    ------
    ValueError dictionary must be of type dict.
    """        
    if not isinstance(dictionary, dict):
        raise ValueError("Input must be a dictionary.")

    if filter_key not in dictionary.keys():
        raise KeyError("filter_key must be a key of dictionary")

    if selected_keys is None:
        selected_keys = list(dictionary.keys())

    with open(filename, mode='w', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=selected_keys)
        
        # Write the header row
        writer.writeheader()
        
        for item in dictionary.values():  # Assuming the dictionary's values are the relevant records
            if item.get(filter_key) == filter_val:  # Check if "Import" is True
                # Filter out only the keys to export
                filtered_item = {key: item.get(key, "") for key in selected_keys}
                writer.writerow(filtered_item)
