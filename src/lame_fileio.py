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
    """        
    with open(filename, 'w', newline='') as csvfile:
        csv_writer = csv.writer(csvfile)
        for key, values in dictionary.items():
            csv_writer.writerow([key] + values)